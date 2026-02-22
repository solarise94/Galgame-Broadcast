#!/bin/bash
#
# 语音播客生成一键脚本
# 使用配置文件: video_generator_config.yaml
#
# 用法: ./run.sh [配置文件路径]
#   ./run.sh                          # 使用默认配置
#   ./run.sh my_config.yaml           # 使用自定义配置

set -e

CONFIG_FILE="${1:-video_generator_config.yaml}"

echo "🎬 语音播客生成器"
echo "=================="

# 检查配置文件
if [ ! -f "$CONFIG_FILE" ]; then
    echo "⚠️  配置文件不存在: $CONFIG_FILE"
    echo ""
    echo "首次使用请复制配置文件模板:"
    echo "  cp video_generator_config.yaml.example video_generator_config.yaml"
    echo ""
    echo "然后修改配置后再次运行。"
    exit 1
fi

# Step 1: 生成音频
echo ""
echo "Step 1/2: 生成音频..."

# 从配置文件中读取 markdown 文件路径
MD_FILE=$(python3 -c "import yaml; print(yaml.safe_load(open('$CONFIG_FILE'))['markdown_file'])" 2>/dev/null || echo "")

if [ -z "$MD_FILE" ]; then
    echo "❌ 无法从配置文件中读取 markdown_file"
    exit 1
fi

if [ ! -f "$MD_FILE" ]; then
    echo "❌ 找不到 Markdown 文件: $MD_FILE"
    exit 1
fi

python tts_generator.py "$MD_FILE"

# 检查音频是否生成成功
AUDIO_DIR=$(python3 -c "import yaml; print(yaml.safe_load(open('$CONFIG_FILE'))['audio_dir'])" 2>/dev/null || echo "audio_output")

if [ ! -d "$AUDIO_DIR" ] || [ -z "$(ls -A $AUDIO_DIR/*.wav 2>/dev/null)" ]; then
    echo "❌ 音频生成失败"
    exit 1
fi

echo "✅ 音频生成完成"

# Step 2: 生成视频
echo ""
echo "Step 2/2: 生成视频..."
python video_generator.py -c "$CONFIG_FILE"

echo ""
echo "=================="
echo "✅ 全部完成!"
