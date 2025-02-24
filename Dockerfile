FROM python:3.11-slim as base


# Install the required packages
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

FROM base as builder
# Set the working directory in the container
WORKDIR /app
COPY . /app/

# ENV
ENV SLACK_BOT_TOKEN=YOUR_SLACK_BOT_TOKEN
ENV SLACK_BOT_CHANNEL=YOUR_SLACK_BOT_CHANNEL
ENV SLACK_APP_TOKEN=YOUR_SLACK_APP_TOKEN
ENV SLACK_SIGNING_SECRET=YOUR_SLACK_APP_TOKEN
ENV MODAL_TOKEN_ID=MODAL_TOKEN_ID
ENV MODAL_TOKEN_SECRET=MODAL_TOKEN_SECRET
ENV PYTHONUNBUFFERED=1

CMD ["sh", "-c", "python main.py"]

