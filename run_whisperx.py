import os
import modal
import time
stub = modal.Stub('transpal-whisperx')


@stub.function(
    image=modal.Image.debian_slim()
    .apt_install(
        "libglib2.0-0", "libsm6", "libxrender1", "libxext6", "ffmpeg", "libgl1", "libgomp1", "libsndfile1", "git"
    )
    .pip_install("torch==2.0.0", "torchaudio==2.0.0", index_url="https://download.pytorch.org/whl/cu118")
    .run_commands("pip install git+https://github.com/m-bain/whisperx.git"),
    secrets=[modal.Secret.from_name("my-huggingface-secret")],
    gpu="any",
    timeout=900
)
async def run_whisperx(audio):
    import whisperx
    start_time = time.time()

    device = "cuda"
    batch_size = 16
    compute_type = "float16"

    # 1. Transcribe audio to text
    model = whisperx.load_model(
        "large-v3", device, compute_type=compute_type, asr_options={
            "initial_prompt": "請使用台灣中文，並加入標點符號",
            "no_speech_threshold": 0.5,
            "compression_ratio_threshold": 2.2,
        })

    result = model.transcribe(
        audio, batch_size=batch_size, language="zh", chunk_size=4)
    print("Transcription done")

    transcribe_time = time.time() - start_time

    # 2. Assign speaker labels
    diarize_model = whisperx.DiarizationPipeline(
        use_auth_token=os.environ["HUGGINGFACE_ACCESS_TOKEN"], device=device)

    diarize_segments = diarize_model(audio)

    result = whisperx.assign_word_speakers(diarize_segments, result)
    print(diarize_segments)
    print("Diarization done")

    diarize_time = time.time() - start_time - transcribe_time

    print(f"Transcribe time: {transcribe_time:.2f}s")
    print(f"Diarize time: {diarize_time:.2f}s")
    print(f"Total time: {time.time() - start_time:.2f}s")

    result = {
        "segments": result["segments"],
        "info": {
            "transcribe_time": transcribe_time,
            "diarize_time": diarize_time,
        }
    }

    return result
