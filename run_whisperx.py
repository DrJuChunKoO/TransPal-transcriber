import os
import modal
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
)
async def run_whisperx(audio):
    import whisperx
    import gc

    device = "cuda"
    batch_size = 16  # reduce if low on GPU mem
    # change to "int8" if low on GPU mem (may reduce accuracy)
    compute_type = "float16"
    # 1. Transcribe audio to text
    model = whisperx.load_model(
        "large-v3", device, compute_type=compute_type, asr_options={
            "initial_prompt": "請使用台灣中文",
            "no_speech_threshold": 0.4,
            "compression_ratio_threshold": 2.2,
        })

    result = model.transcribe(
        audio, batch_size=batch_size, language="zh", chunk_size=4)
    print(result["segments"])  # before alignment

    # delete model if low on GPU resources
    # import gc; gc.collect(); torch.cuda.empty_cache(); del model

    # 2. Align whisper output
    model_a, metadata = whisperx.load_align_model(
        language_code=result["language"], device=device, model_name="StevenLimcorn/wav2vec2-xls-r-300m-zh-TW")
    result = whisperx.align(
        result["segments"], model_a, metadata, audio, device, return_char_alignments=False)

    print(result["segments"])  # after alignment

    # delete model if low on GPU resources
    # import gc; gc.collect(); torch.cuda.empty_cache(); del model_a

    # 3. Assign speaker labels
    diarize_model = whisperx.DiarizationPipeline(
        use_auth_token=os.environ["HUGGINGFACE_ACCESS_TOKEN"], device=device)

    # add min/max number of speakers if known
    diarize_segments = diarize_model(audio)
    # diarize_model(audio, min_speakers=min_speakers, max_speakers=max_speakers)

    result = whisperx.assign_word_speakers(diarize_segments, result)
    print(diarize_segments)
    print(result["segments"])  # segments are now assigned speaker IDs

    return result["segments"]
