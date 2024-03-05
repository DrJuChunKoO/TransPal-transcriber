# TransPal-transcriber

WhisperX Slack bot for transcribing audio files

## Setup

### pyannote

- Accept [pyannote/segmentation-3.0](https://hf.co/pyannote/segmentation-3.0) user conditions
- Accept [pyannote/speaker-diarization-3.1](https://hf.co/pyannote-speaker-diarization-3.1) user conditions

### modal

- Create an account on [Modal](https://modal.com/)
- Save the Hugging Face token on the secrets page, naming it `my-huggingface-secret`, with the key `HUGGINGFACE_ACCESS_TOKEN`.
- Get the token id and secret

### Slack API

- Create a new Slack app
- Go to "Event Subscriptions" and subscribe to `message.channels`
- Go to "OAuth & Permissions" and add the following scopes:
  - `chat:write`
  - `files:read`
  - `files:write`
  - `channels:read`
  - `channels:history`
  - `groups:history`
  - `im:history`
- Get `SLACK_BOT_TOKEN` from "Install App" page (starts with `xoxb-`)
- Get `SLACK_APP_TOKEN` from "Basic Information" page > "App-Level Tokens" (starts with `xapp-`)

### Slack

- Get `SLACK_BOT_CHANNEL` from the channel you want the bot to watch
- Add the bot to the channel

## Deployment

```bash
docker run \
 -e SLACK_BOT_TOKEN='<YOUR_SLACK_BOT_TOKEN>' \
 -e SLACK_APP_TOKEN='<SLACK_APP_TOKEN>' \
 -e SLACK_BOT_CHANNEL='<SLACK_BOT_CHANNEL_ID>'  \
 -e MODAL_TOKEN_ID='<MODAL_TOKEN_ID>' \
 -e MODAL_TOKEN='<MODAL_TOKEN_SECRET>' \
 ghcr.io/drjuchunkoo/transpal-transcriber:latest
```

### Environment Variables

- `SLACK_BOT_TOKEN` - Slack bot token
- `SLACK_APP_TOKEN` - Slack app token
- `SLACK_BOT_CHANNEL` - Watch channel for the bot
- `MODAL_TOKEN_ID` - [Modal](https://modal.com/) token id
- `MODAL_TOKEN_SECRET` - [Modal](https://modal.com/) token secret

## Tech Stack

- [m-bain/whisperX](https://github.com/m-bain/whisperX)
- [pyannote/segmentation-3.0](https://hf.co/pyannote/segmentation-3.0)
- [pyannote/speaker-diarization-3.1](https://hf.co/pyannote-speaker-diarization-3.1)
- [slackapi/bolt-python](https://github.com/slackapi/bolt-python)
- [Modal](https://modal.com/)
