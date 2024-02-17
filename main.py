
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
import logging
import subprocess
import os
import requests
import time
import torch
import subprocess
from openai import OpenAI
from pyannote.audio import Pipeline
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

pipeline = Pipeline.from_pretrained(
    "pyannote/speaker-diarization-3.1",
    use_auth_token=os.environ.get("HUGGINGFACE_ACCESS_TOKEN"))
openai_client = OpenAI(
    api_key=os.environ.get("OPENAI_API_KEY"),
)

SLACK_BOT_CHANNEL = os.environ["SLACK_BOT_CHANNEL"]
app = App(token=os.environ["SLACK_BOT_TOKEN"])


@app.event("message")
def handle_message_events(body):
    print(body)
    logger.info(body)
    channel_id = body["event"]["channel"]
    thread_ts = body["event"]["ts"]
    if channel_id != SLACK_BOT_CHANNEL or body["event"].get("files") is None:
        return
    # check file extension
    filename = body["event"]["files"][0]["name"]
    file_url = body["event"]["files"][0]["url_private_download"]
    file_extension = filename.split(".")[-1]

    # determine the file type as audio or video

    if file_extension in ["mp3", "wav", "flac", "m4a", "mkv", "mp4", "webm"]:
        try:
            start_time = time.time()
            # download the file
            r = requests.get(file_url, headers={
                "Authorization": f"Bearer {os.environ.get('SLACK_BOT_TOKEN')}"})
            temp_input_filename = f"temp-{time.time_ns()}.{file_extension}"
            with open(temp_input_filename, "wb") as file_object:
                file_object.write(r.content)
            download_time = time.time() - start_time
            # convert to wav
            app.client.chat_postMessage(
                token=os.environ.get("SLACK_BOT_TOKEN"),
                channel=channel_id,
                text=f"正在處裡中⋯⋯",
                thread_ts=thread_ts,
            )
            temp_wav_filename_wav = f"temp-{time.time_ns()}_ff.wav"
            subprocess.run(
                [
                    "ffmpeg",
                    "-i",
                    temp_input_filename,
                    "-ar",
                    "16000",
                    "-ac",
                    "1",
                    "-c:a",
                    "pcm_s16le",
                    temp_wav_filename_wav,
                ]
            )
            # remove the original file
            if os.path.exists(temp_input_filename):
                os.remove(temp_input_filename)
                print("Removed temp_input_filename")
            transcode_time = time.time() - start_time - download_time
            logger.info("Running pipeline")
            diarization = pipeline(temp_wav_filename_wav)
            diarization_time = time.time() - start_time - download_time - transcode_time
            logger.info("Running Whisper")
            audio_file = open(temp_wav_filename_wav, "rb")
            transcript = openai_client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                response_format='verbose_json',
                timestamp_granularities=["segment"],
            )
            transcript_time = time.time() - start_time - download_time - \
                transcode_time - diarization_time
            diarization_result = []
            for speech_turn, track, speaker in diarization.itertracks(yield_label=True):
                diarization_result.append(
                    {
                        "start": speech_turn.start,
                        "end": speech_turn.end,
                        "speaker": speaker,
                    }
                )
            result = {
                "version": "1.0",
                "info": {
                    "filename": filename,
                },
                "raw": {
                    "diarization": diarization_result,
                    "transcript": transcript.segments,
                },
            }

            logger.info("Removing temp files")
            # remove the temp files
            if os.path.exists(temp_wav_filename_wav):
                os.remove(temp_wav_filename_wav)
            logger.info("Returning result")
            # write the result to a file
            result_filename = f"result-{time.time_ns()}.json"
            with open(result_filename, "w") as file_object:
                file_object.write(str(result))
            # upload the result file
            total_time = time.time() - start_time
            app.client.chat_postMessage(
                token=os.environ.get("SLACK_BOT_TOKEN"),
                channel=channel_id,
                blocks=[
                    {
                        "type": "header",
                        "text": {
                                "type": "plain_text",
                                "text": "✨ 轉換完成"
                        }
                    },
                    {
                        "type": "section",
                        "text": {
                                "type": "mrkdwn",
                                "text": filename
                        }
                    },
                    {
                        "type": "section",
                        "fields": [
                                {
                                    "type": "mrkdwn",
                                    "text": f"*下載*\n{download_time:.2f} 秒"
                                },
                            {
                                    "type": "mrkdwn",
                                    "text": f"*轉檔*\n{transcode_time:.2f} 秒"
                                },
                            {
                                    "type": "mrkdwn",
                                    "text": f"*語者分離*\n{diarization_time:.2f} 秒"
                                },
                            {
                                    "type": "mrkdwn",
                                    "text": f"*音訊轉錄*\n{transcript_time:.2f} 秒"
                                },
                            {
                                    "type": "mrkdwn",
                                    "text": f"*總耗時*\n{total_time:.2f} 秒"
                            }
                        ]
                    }
                ],
                thread_ts=thread_ts,
            )
            app.client.files_upload(
                token=os.environ.get("SLACK_BOT_TOKEN"),
                channels=channel_id,
                file=result_filename,
                thread_ts=thread_ts,
            )
            # remove the result file
            if os.path.exists(result_filename):
                os.remove(result_filename)
        except Exception as e:
            app.client.chat_postMessage(
                token=os.environ.get("SLACK_BOT_TOKEN"),
                channel=channel_id,
                text=f"發生錯誤：{str(e)}",
                thread_ts=thread_ts,
            )

    else:
        app.client.chat_postMessage(
            token=os.environ.get("SLACK_BOT_TOKEN"),
            channel=channel_id,
            text=f"不支援的檔案類型：{file_extension}",
            thread_ts=thread_ts,
        )


if __name__ == "__main__":
    SocketModeHandler(
        app, os.environ["SLACK_APP_TOKEN"]).start()
