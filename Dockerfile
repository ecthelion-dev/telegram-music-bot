FROM python:3.12-slim

# FFmpeg converts to MP3; Node runs yt-dlp signature deciphering and the PO token
# provider. Debian ships Node 18, but the provider needs 20+, so use NodeSource.
ARG NODE_MAJOR=22
ARG POT_PROVIDER_VERSION=2.0.0

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    curl \
    ca-certificates \
    gnupg \
    && curl -fsSL https://deb.nodesource.com/setup_${NODE_MAJOR}.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && rm -rf /var/lib/apt/lists/*

# YouTube refuses datacenter IPs with "Sign in to confirm you're not a bot" unless
# a proof-of-origin token is supplied. This provider mints one per video in script
# mode, so no cookies, Google account or second container is needed.
ENV POT_PROVIDER_HOME=/opt/bgutil/server
RUN curl -fsSL "https://github.com/Brainicism/bgutil-ytdlp-pot-provider/archive/refs/tags/${POT_PROVIDER_VERSION}.tar.gz" \
      | tar xz -C /opt \
    && mv "/opt/bgutil-ytdlp-pot-provider-${POT_PROVIDER_VERSION}" /opt/bgutil \
    && cd "${POT_PROVIDER_HOME}" \
    && npm ci --silent \
    && npx tsc


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
