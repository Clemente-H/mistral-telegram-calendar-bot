FROM python:3.11-slim

WORKDIR /app

# Install compilation tools needed for whisper and FFmpeg
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    gcc g++ make cmake ffmpeg && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*


COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV ENVIRONMENT production

CMD ["python", "telegram_bot.py"]