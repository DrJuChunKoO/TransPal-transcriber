FROM python:3.11-slim as base
# install ffmpeg
COPY --from=mwader/static-ffmpeg:6.1.1 /ffmpeg /usr/local/bin/
COPY --from=mwader/static-ffmpeg:6.1.1 /ffprobe /usr/local/bin/
RUN apt-get update && apt-get install -y --no-install-recommends apt-utils
RUN apt-get -y install curl
RUN apt-get install libgomp1 libsndfile1 -y
# Install the required packages
RUN pip install torch==2.1.1 torchaudio==2.1.1 pyannote.audio==3.1.1
RUN pip install fastapi hypercorn requests python-multipart openai slack_bolt

FROM base as builder
# Set the working directory in the container
WORKDIR /app
COPY . /app
ENV HUGGINGFACE_ACCESS_TOKEN=YOUR_HUGGING_FACE_ACCESS_TOKEN
ENV OPENAI_API_KEY=YOUR_OPENAI_API_KEY
ENV SLACK_BOT_TOKEN=YOUR_SLACK_BOT_TOKEN
ENV SLACK_BOT_CHANNEL=YOUR_SLACK_BOT_CHANNEL
ENV SLACK_APP_TOKEN=YOUR_SLACK_APP_TOKEN
# ENV
CMD python main.py
