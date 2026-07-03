FROM arm64v8/ros:jazzy-ros-base

ENV DEBIAN_FRONTEND=noninteractive

RUN apt update && apt install -y \
    python3-pip \
    python3-opencv \
    python3-numpy \
    python3-serial \
    python3-flask \
    python3-colcon-common-extensions \
    ffmpeg \
    libgl1 \
    libglib2.0-0 \
    nano \
    git \
    htop \
    ros-jazzy-std-msgs \
    ros-jazzy-sensor-msgs \
    ros-jazzy-launch \
    ros-jazzy-launch-ros \
    && rm -rf /var/lib/apt/lists/*

RUN pip3 install --break-system-packages \
    ultralytics \
    pyserial \
    flask \
    numpy \
    pillow \
    pyyaml \
    tqdm \
    requests

SHELL ["/bin/bash", "-c"]

CMD ["bash"]
