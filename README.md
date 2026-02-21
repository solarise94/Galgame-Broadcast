# 🎙️ TTS + 视频播客生成器

一站式对话式语音合成与视频播客制作工具。

支持 **阿里云百炼 Qwen-TTS**、**硅基流动 SiliconFlow TTS** (含 IndexTTS2、CosyVoice2、MOSS-TTSD 等) 和 **MiniMax Speech** 三种语音合成模型，提供文本转语音、批量生成、视频合成等功能。

---

## ✨ 功能特性

| 功能 | 描述 |
|------|------|
| 🎙️ **语音合成** | 支持 Qwen-TTS / SiliconFlow (IndexTTS2, MOSS-TTSD) / MiniMax |
| 🎭 **多音色** | 支持 30+ 种音色（男声/女声），可指令控制 |
| 🔧 **多提供商** | 一键切换 Qwen / SiliconFlow / MiniMax 语音合成模型 |
| 📄 **批量处理** | 自动解析 Markdown 对话格式，批量生成音频 |
| 🎬 **视频生成** | 将音频合成为带字幕、头像、波形可视化的视频播客 |
| 🔥 **一键完成** | 文本 → 语音 → 视频，全自动流程 |

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

**详细配置指南**: [configs/CONFIG_GUIDE.md](configs/CONFIG_GUIDE.md)

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

### 4️⃣ 一键生成

```bash
# 使用默认配置文件
./run.sh

# 使用自定义配置文件
./run.sh my_config.yaml
```

---

## 📖 使用流程

### 方式一：一键脚本（推荐）

1. 编辑 `video_generator_config.yaml` 配置你的参数
2. 运行：

```bash
./run.sh
```

### 方式二：分步执行

```bash
# Step 1: 生成音频
python tts_generator.py 文献解读对话文案-2.md

# Step 2: 生成视频（使用配置文件）
python video_generator.py

# 或使用自定义配置
python video_generator.py -c my_config.yaml
```

### 方式三：命令行覆盖配置

```bash
# 覆盖配置文件中的特定参数
python video_generator.py -m 另一个文件.md -t "新标题"
```

---

## 💰 费用说明

| 提供商 | 模型 | 价格 | 你的文档(5754字符) |
|--------|------|------|-------------------|
| 阿里云 | `qwen3-tts-flash` | ~0.5-1元/万字符 | **~0.3-0.6元** |
| 阿里云 | `qwen3-tts-instruct-flash` | ~1-2元/万字符 | **~0.6-1.2元** |
| 硅基流动 | `IndexTTS-2` / `CosyVoice2` | ~0.5-1元/万字符 | **~0.3-0.6元** |
| MiniMax | `speech-2.6-hd` | ~1-2元/万字符 | **~0.6-1.2元** |
| MiniMax | `speech-2.6-turbo` | ~0.5-1元/万字符 | **~0.3-0.6元** |

- 新用户有免费额度
- 按量计费，无需预付费
- 视频生成免费（本地计算）

---

## 🎨 支持的音色

### Qwen-TTS 音色

**男声**: `Ethan`（成熟）、`Eric`（青年）、`Peter`（专业）、`Ryan`（温暖）

**女声**: `Cherry`（活泼）、`Serena`（温柔）、`Bella`（知性）

### SiliconFlow 音色 (IndexTTS2 / CosyVoice2 / MOSS-TTSD)

**男声**: `alex`（沉稳）、`benjamin`（低沉）、`charles`（磁性）、`david`（欢快）

**女声**: `anna`（沉稳）、`bella`（激情）、`claire`（温柔）、`diana`（欢快）

> 完整音色列表: https://docs.siliconflow.cn/cn/userguide/capabilities/text-to-speech
> 
> **特色功能**: 支持上传参考音频进行零样本语音克隆

### MiniMax Speech 音色

**男声**: 
- `Chinese_Male_Speech_Speaker_01` - 成熟男声（推荐）
- `Chinese_Male_Speech_Speaker_02` - 温和男声
- `Chinese_Male_Documentary_Speaker_01` - 纪录片风格
- `Chinese_Male_Narration_Speaker_01` - 旁白风格

**女声**:
- `Chinese_Female_Speech_Speaker_01` - 成熟女声（推荐）
- `Chinese_Female_Speech_Speaker_02` - 温柔女声
- `Chinese_Female_Documentary_Speaker_01` - 纪录片风格
- `Chinese_Female_Narration_Speaker_01` - 旁白风格

> 完整音色列表: https://platform.minimax.io/docs/api-reference/speech/voice

## 👤 自定义头像

将头像图片放在项目根目录：
- `male.png` - 男声头像（显示为 Alex）
- `female.png` - 女声头像（显示为 Cherry）

支持透明背景，会自动裁剪为圆形。

---

## 🎯 输出示例

### 音频输出
```
audio_output/
├── dialogue_001_male.wav
├── dialogue_002_female.wav
├── ...
└── dialogue_complete.wav    # 合并版
```

### 视频输出
```
output/
└── podcast_20250218_203000.mp4
    ├── 🎬 1080p 高清视频
    ├── 👤 自定义头像（Alex/Cherry）
    ├── 🔊 音频波形可视化
    ├── 📝 动态字幕
    ├── 🎨 渐变/图片背景
    ├── 📌 智能标题（自动换行+字体调整）
    └── ⏸️ 段落间隔（可配置）
```

---

## 📚 详细文档

| 文档 | 内容 |
|------|------|
| [README_TTS.md](archive/docs/README_TTS.md) | 语音合成详细指南 |
| [README_VIDEO.md](archive/docs/README_VIDEO.md) | 视频生成详细指南 |
| [MODEL_GUIDE.md](archive/docs/MODEL_GUIDE.md) | 模型选择与切换 |

---

## 🛠️ 故障排查

### 依赖安装失败

```bash
# 使用国内镜像
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

### 找不到 ffmpeg

```bash
# macOS
brew install ffmpeg
```

### API 调用失败

1. 检查 API Key 是否正确
2. 检查地域设置（北京/新加坡）
3. 查看阿里云百炼控制台额度

---

## 📝 Markdown 格式

支持的对话格式：

```markdown
### male speaker ###
### 大家好，我是阿杰。今天我们要聊的这篇文献... ###

### female speaker ###
### 说到免疫治疗，现在PD-1/PD-L1抑制剂... ###
```

---

## 🎉 开始使用

```bash
# 一键生成播客视频
./run.sh 文献解读对话文案-2.md
```

---

## 📞 获取帮助

遇到问题？
1. 查看详细文档（archive/docs/*.md）
2. 检查控制台错误信息
3. 使用 `--help` 查看脚本帮助

---

## 📄 License

MIT License - 自由使用和修改

---

**祝你创作愉快！** 🎉
