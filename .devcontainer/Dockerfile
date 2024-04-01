ARG VARIANT=3.10-bullseye
FROM --platform=linux/amd64 mcr.microsoft.com/vscode/devcontainers/python:${VARIANT}

# [Choice] Node.js version: none, lts/*, 16, 14, 12, 10
ARG NODE_VERSION="none"
RUN if [ "${NODE_VERSION}" != "none" ]; then su vscode -c "umask 0002 && . /usr/local/share/nvm/nvm.sh && nvm install ${NODE_VERSION} 2>&1"; fi

# Install Chromium
RUN apt-get update && apt-get install -y \
    chromium \
    chromium-driver \
    && rm -rf /var/lib/apt/lists/*

# Install LibreOffice
RUN apt-get update && apt-get install -y \
    libreoffice \
    && rm -rf /var/lib/apt/lists/*

RUN useradd --no-log-init --system --create-home --shell /bin/bash worker

# Running as non sudo user 'worker'
USER worker
WORKDIR /home/worker

# Add Agent Core inside the image
RUN mkdir -p /home/worker/bin && \
    mkdir -p /home/worker/.robocorp && \
    mkdir -p /home/worker/bin/conda && \
    mkdir -p /home/worker/instance