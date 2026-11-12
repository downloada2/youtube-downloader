FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir yt-dlp curl_cffi
WORKDIR /app
COPY yt_downloader.py ./
COPY ui ./ui
COPY web ./web
USER nobody
EXPOSE 8080
CMD ["python", "web/server.py", "--host", "0.0.0.0", "--port", "8080"]
