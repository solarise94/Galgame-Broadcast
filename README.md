# 🎙️ Galgame视频播客生成器，完全个人爱好看心情改改

一站式对话式语音合成与视频播客制作工具。

支持 **阿里云百炼 Qwen-TTS**、**硅基流动 SiliconFlow TTS** (含 IndexTTS2、CosyVoice2、MOSS-TTSD 等) 和 **MiniMax Speech** 三种语音合成模型，提供文本转语音、批量生成、视频合成等功能。

---

## ✨ 功能特性

| 功能 | 描述 |
|------|------|
| 🎙️ **语音合成** | 支持 Qwen-TTS / SiliconFlow (IndexTTS2, MOSS-TTSD) / MiniMax |
| 🔧 **多提供商** | 一键切换 Qwen / SiliconFlow / MiniMax 语音合成模型 |
| 📄 **批量处理** | 自动解析 Markdown 对话格式，批量生成音频 |

---

## 📁 项目结构

```
Voice Work Flow/
│
├── 🎙️ 语音合成
│   ├── tts_generator.py          # 命令行 TTS 工具
│   ├── tts_batch.py              # 分批生成脚本（支持断点续传）
│   └── configs/                  # 配置文件目录
│       ├── config.yaml              # 阿里云 Qwen 配置
│       ├── config_siliconflow.yaml  # 硅基流动配置
│       ├── config_moss_ttsd.yaml    # MOSS-TTSD 双人对话配置
│       ├── config_minimax.yaml      # MiniMax Speech 配置
│       └── CONFIG_GUIDE.md          # 配置使用指南
│
├── 🎬 视频生成
│   ├── video_generator.py        # 视频生成脚本
│   └── output/                   # 默认输出目录
│
├── 🚀 一键脚本
│   └── run.sh                    # 一键生成完整流程
│
└── 📖 文档
    ├── README.md                 # 本文件
    ├── README_TTS.md             # TTS 使用指南
    ├── README_VIDEO.md           # 视频生成指南
    └── MODEL_GUIDE.md            # 模型选择指南
```

---

## 🚀 快速开始

### 1️⃣ 安装依赖

```bash
pip install -r requirements.txt
```

**需要 ffmpeg**（用于视频生成）:
```bash
# macOS
brew install ffmpeg

# Ubuntu
apt-get install ffmpeg
```

### 2️⃣ 选择并配置 TTS 提供商

我们提供了四个独立的配置文件，每个对应一个 TTS 提供商：

| 配置文件 | 提供商 | 特点 |
|---------|--------|------|
| `configs/config.yaml` | 阿里云 Qwen | 速度快、稳定、性价比高 |
| `configs/config_siliconflow.yaml` | 硅基流动 | 支持 IndexTTS2、CosyVoice |
| `configs/config_moss_ttsd.yaml` | 硅基流动 MOSS | 一次性生成双人对话 |
| `configs/config_minimax.yaml` | MiniMax | 高清语音合成，自然度高 |


#### 方案一：阿里云百炼 Qwen-TTS（推荐新手）

```bash
# 1. 获取 API Key: https://bailian.console.aliyun.com/
# 2. 编辑 configs/config.yaml，填入你的 API Key
vim configs/config.yaml

# 3. 运行
python tts_generator.py 你的文件.md
```

#### 方案二：硅基流动 SiliconFlow (IndexTTS2)

```bash
# 1. 获取 API Key: https://cloud.siliconflow.cn/account/ak
# 2. 编辑 configs/config_siliconflow.yaml
vim configs/config_siliconflow.yaml

# 3. 运行
python tts_generator.py 你的文件.md -c configs/config_siliconflow.yaml
```

#### 方案三：MOSS-TTSD 双人对话（特殊）

```bash
# 1. 获取 API Key: https://cloud.siliconflow.cn/account/ak
# 2. 编辑 configs/config_moss_ttsd.yaml
vim configs/config_moss_ttsd.yaml

# 3. 运行（一次性生成完整的双人对话音频）
python tts_generator.py 你的文件.md -c configs/config_moss_ttsd.yaml
```

> 🎭 MOSS-TTSD 是复旦开源的双人对话 TTS 模型，可以一次性生成完整的对话音频，而不是分段合成。
> 详见 [configs/CONFIG_GUIDE.md](configs/CONFIG_GUIDE.md) 中的"MOSS-TTSD 双人对话"部分。

#### 方案四：MiniMax Speech（高清语音）

```bash
# 1. 获取 API Key: https://platform.minimax.io/
# 2. 编辑 configs/config_minimax.yaml
vim configs/config_minimax.yaml

# 3. 运行
python tts_generator.py 你的文件.md -c configs/config_minimax.yaml
```

> 🔊 MiniMax Speech 提供高清语音合成（speech-2.6-hd），音质优秀、自然度高，特别适合内容生产场景。

### 3️⃣ 配置视频生成器

编辑 `video_generator_config.yaml`，设置你的参数：

编辑 `video_generator_config.yaml`，修改你的设置：

```yaml
# 输入文件
markdown_file: "文献解读对话文案-2.md"
audio_dir: "audio_output"

# 视频设置
background_type: "gradient"  # 或 "image"
# background_image: "./bg.jpg"

# 标题
title: "你的视频标题"
subtitle: "副标题"
```
