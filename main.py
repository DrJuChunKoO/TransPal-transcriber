import modal
from slack_bolt import App
import random
import string
import json
import os
import logging
import time
from dotenv import load_dotenv

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# 檢查是否在 Cloud Run 上運行
if "K_SERVICE" not in os.environ:
    # 本地環境，載入 .env 文件
    logger.info("Running locally, loading .env file")
    load_dotenv()
else:
    # Cloud Run 環境，直接使用環境變數
    logger.info("Running on Cloud Run, using environment variables")


SLACK_BOT_CHANNEL = os.environ["SLACK_BOT_CHANNEL"]

app = App(
    token=os.environ.get("SLACK_BOT_TOKEN"),
    signing_secret=os.environ.get("SLACK_SIGNING_SECRET")
)


@app.event("message")
def handle_message_events(body):
    channel_id = body["event"]["channel"]
    thread_ts = body["event"]["ts"]
    if channel_id != SLACK_BOT_CHANNEL or body["event"].get("files") is None:
        return
    # check file extension
    filename = body["event"]["files"][0]["name"]
    file_url = body["event"]["files"][0]["url_private_download"]
    file_extension = filename.split(".")[-1]

    try:
        start_time = time.time()

        app.client.chat_postMessage(
            channel=channel_id,
            text=f"開始進行轉錄⋯⋯",
            thread_ts=thread_ts,
        )
        print(f"transcribe file {filename} ...")
        transcribe = modal.Function.from_name(
            "whisperx-transpal", "transcribe")
        whisperx_result = transcribe.remote(
            file_url, os.environ.get('SLACK_BOT_TOKEN'))  # 透過實例呼叫方法
        print(f"transcribe.remote completed, result: {whisperx_result}")
        result = {
            "version": "1.0",
            "info": {
                "filename": filename,
            },
            "raw": {
            },
            "content": []
        }
        for segment in whisperx_result["segments"]:
            if "speaker" in segment:  # only include segments with speaker information
                random_id = ''.join(random.choices(
                    string.ascii_letters, k=6))
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
                    "type": "divider"
                },
                {
                    "type": "section",
                    "fields": [
                        {
                            "type": "mrkdwn",
                            "text": f"*檔案名稱*\n{filename}"
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*下載*\n{whisperx_result['info']['download_time']:.2f} 秒"
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*轉檔*\n{whisperx_result['info']['transcode_time']:.2f} 秒"
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*音訊轉錄*\n{whisperx_result['info']['transcribe_time']:.2f} 秒"
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*語者辨識*\n{whisperx_result['info']['diarize_time']:.2f} 秒"
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*總耗時*\n{total_time:.2f} 秒"
                        },
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


if __name__ == "__main__":
    app.start(port=int(os.environ.get("PORT", 3000)))
