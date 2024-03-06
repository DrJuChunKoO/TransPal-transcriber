FROM python:3.11-slim as base
# install ffmpeg
COPY --from=mwader/static-ffmpeg:6.1.1 /ffmpeg /usr/local/bin/
COPY --from=mwader/static-ffmpeg:6.1.1 /ffprobe /usr/local/bin/
RUN apt-get update && apt-get install -y --no-install-recommends apt-utils
RUN apt-get -y install curl libgomp1 libsndfile1
# Install the required packages
RUN pip install requests python-multipart slack_bolt modal numpy

FROM base as builder
# Set the working directory in the container
WORKDIR /app
COPY . /app
ENV SLACK_BOT_TOKEN=YOUR_SLACK_BOT_TOKEN
ENV SLACK_BOT_CHANNEL=YOUR_SLACK_BOT_CHANNEL
ENV SLACK_APP_TOKEN=YOUR_SLACK_APP_TOKEN
ENV MODAL_TOKEN_ID=YOUR_MODAL_TOKEN_ID
ENV MODAL_TOKEN_SECRET=YOUR_MODAL_TOKEN_SECRET
# ENV
CMD ["sh", "-c", "modal deploy run_whisperx.py && python main.py"]

