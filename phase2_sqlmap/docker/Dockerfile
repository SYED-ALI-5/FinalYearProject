FROM kalilinux/kali-rolling

RUN apt update && apt install -y \
    kali-linux-headless \
    bash \
    python3 \
    python3-pip \
    git \
    curl \
    vim \
    && apt clean

WORKDIR /workspace
