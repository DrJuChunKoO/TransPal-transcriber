import requests
from slack_bolt.adapter.socket_mode import SocketModeHandler
from slack_bolt import App
import random
import string
import json
import numpy as np
import os
import logging
import subprocess
import time
import modal
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

run_whisperx = modal.Function.lookup('transpal-whisperx', "run_whisperx")

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
            # convert to wav
            app.client.chat_postMessage(
                channel=channel_id,
                text=f"正在處裡中⋯⋯",
                thread_ts=thread_ts,
            )

            try:
                # Launches a subprocess to decode audio while down-mixing and resampling as necessary.
                # Requires the ffmpeg CLI to be installed.
                cmd = [
                    "ffmpeg",
                    "-nostdin",
                    "-threads",
                    "0",
                    "-i",
                    temp_input_filename,
                    "-f",
                    "s16le",
                    "-ac",
                    "1",
                    "-acodec",
                    "pcm_s16le",
                    "-ar",
                    str(16000),
                    "-",
                ]
                out = subprocess.run(
                    cmd, capture_output=True, check=True).stdout
            except subprocess.CalledProcessError as e:
                raise RuntimeError(
                    f"Failed to load audio: {e.stderr.decode()}") from e

            file_float32 = np.frombuffer(
                out, np.int16).flatten().astype(np.float32) / 32768.0

            # remove the original file
            if os.path.exists(temp_input_filename):
                os.remove(temp_input_filename)
                print("Removed temp_input_filename")

            whisperx_result = run_whisperx.remote(file_float32)
            result = {
                "version": "1.0",
                "info": {
                    "filename": filename,
                },
                "raw": {
                },
                "content": []
            }
            for segment in whisperx_result:
                random_id = ''.join(random.choices(string.ascii_letters, k=6))
                result["content"].append({
                    "id":  random_id,
                    "start": segment["start"],
                    "end": segment["end"],
                    "type": "speech",
                    "speaker": segment["speaker"],
                    "text": segment["text"]
                })

            logger.info("Returning result")
            # write the result to a file
            result_filename = f"result-{time.time_ns()}.json"
            with open(result_filename, "w") as file_object:
                file_object.write(json.dumps(result))
            # upload the result file
            total_time = time.time() - start_time
            app.client.chat_postMessage(
                channel=channel_id,
                text="轉換完成",
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
                                "text": f"*總耗時*\n{total_time:.2f} 秒"
                            }
                        ]
                    }
                ],
                thread_ts=thread_ts,
            )
            app.client.files_upload_v2(
                channels=channel_id,
                file=result_filename,
                thread_ts=thread_ts,
            )
            # remove the result file
            if os.path.exists(result_filename):
                os.remove(result_filename)
        except Exception as e:
            app.client.chat_postMessage(
                channel=channel_id,
                text=f"發生錯誤：{str(e)}",
                thread_ts=thread_ts,
            )

    else:
        app.client.chat_postMessage(
            channel=channel_id,
            text=f"不支援的檔案類型：{file_extension}",
            thread_ts=thread_ts,
        )


SocketModeHandler(
    app, os.environ["SLACK_APP_TOKEN"]).start()
