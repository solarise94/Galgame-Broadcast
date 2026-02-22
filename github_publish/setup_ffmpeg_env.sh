#!/bin/bash
# 设置 FFmpeg 环境变量
# 使用方式: source setup_ffmpeg_env.sh

# 请根据你的系统修改 FFmpeg 路径
# macOS (Homebrew): /opt/homebrew/bin/ffmpeg 或 /usr/local/bin/ffmpeg
# Linux: /usr/bin/ffmpeg
# Windows: C:/ffmpeg/bin/ffmpeg.exe

FFMPEG_PATH="/usr/bin/ffmpeg"

if [ -f "$FFMPEG_PATH" ]; then
    export IMAGEIO_FFMPEG_EXE="$FFMPEG_PATH"
    echo "✅ FFmpeg 环境已设置"
    echo "路径: $IMAGEIO_FFMPEG_EXE"
    $IMAGEIO_FFMPEG_EXE -version | head -1
else
    echo "⚠️  找不到 FFmpeg: $FFMPEG_PATH"
    echo "请修改本文件中的 FFMPEG_PATH 为你系统的实际路径"
    echo "常见路径:"
    echo "  - macOS Homebrew: /opt/homebrew/bin/ffmpeg"
    echo "  - macOS Intel: /usr/local/bin/ffmpeg"
    echo "  - Linux: /usr/bin/ffmpeg"
fi
