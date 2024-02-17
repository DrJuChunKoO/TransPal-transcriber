# TransPal-python

## Setup

- You need to have a Hugging Face API token and OpenAI API key to run this project. You can get them from [Hugging Face](https://huggingface.co/join) and [OpenAI](https://beta.openai.com/signup/).
- Accept [pyannote/segmentation-3.0](https://hf.co/pyannote/segmentation-3.0) user conditions
- Accept [pyannote/speaker-diarization-3.1](https://hf.co/pyannote-speaker-diarization-3.1) user conditions

## Deployment

```bash
docker run \
 -e HUGGINGFACE_ACCESS_TOKEN='<HF_TOKEN_HERE>' \
 -e OPENAI_API_KEY='<OPENAI_KEY_HERE>' \
 -e SLACK_BOT_TOKEN='<YOUR_SLACK_BOT_TOKEN>' \
 -e SLACK_APP_TOKEN='<SLACK_APP_TOKEN>' \
 -e SLACK_BOT_CHANNEL='<SLACK_BOT_CHANNEL_ID>'  \
 transpal
```

### Environment Variables

- HUGGINGFACE_ACCESS_TOKEN - Hugging Face API token, used for Speaker Diarization model download
- OPENAI_API_KEY - OpenAI API key, used for Whisper
- SLACK_BOT_TOKEN - Slack bot token
- SLACK_APP_TOKEN - Slack app token
- SLACK_BOT_CHANNEL - Watch channel for the bot
