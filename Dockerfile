FROM python:3.12-slim

# Install system dependencies (FFmpeg is required for yt-dlp & audio conversion)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Ensure temp and downloads directories exist
RUN mkdir -p downloads temp

# Expose port for health checks (Render / Koyeb)
EXPOSE 8080

CMD ["python", "main.py"]
