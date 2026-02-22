# 🎙️ Galgame Broadcast - TTS + 视频播客生成器

一站式对话式语音合成与视频播客制作工具，支持多情绪立绘系统。

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
| 😊 **情绪立绘** | 支持 9 种情绪立绘切换，视频更生动 |
| 🎨 **GalGame 风格** | 支持 GalGame 风格的字幕和立绘展示 |

---

## 📁 项目结构

```
github_publish/
│
├── 🎙️ 语音合成
│   ├── tts_generator.py          # 命令行 TTS 工具（支持多提供商）
│   ├── tts_index_clone.py        # IndexTTS2 语音克隆工具
│   ├── tts_batch.py              # 分批生成脚本（支持断点续传）
│   └── configs/                  # 配置文件目录
│       ├── tts/
│       │   ├── config.yaml              # 阿里云 Qwen 配置
│       │   ├── config_siliconflow.yaml  # 硅基流动配置
│       │   ├── config_moss_ttsd.yaml    # MOSS-TTSD 双人对话配置
│       │   ├── config_minimax.yaml      # MiniMax Speech 配置
│       │   └── config_index_clone.yaml  # IndexTTS2 语音克隆配置
│       └── video/
│           └── config.yaml              # 视频生成配置示例
│
├── 🎬 视频生成
│   ├── video_generator.py        # 视频生成脚本（支持情绪立绘）
│   └── video_generator_config.yaml.example  # 视频配置模板
│
├── 🚀 一键脚本
│   └── run.sh                    # 一键生成完整流程
│
└── 📖 文档
    ├── README.md                 # 本文件
    └── configs/CONFIG_GUIDE.md   # 配置使用指南
```

---

## 🚀 快速开始

### 1️⃣ 安装依赖

```bash
pip install pyyaml requests pillow numpy
```

**需要 ffmpeg**（用于视频生成）:
```bash
# macOS
brew install ffmpeg

# Ubuntu
apt-get install ffmpeg
```

### 2️⃣ 选择并配置 TTS 提供商

我们提供了五个独立的配置文件，每个对应一个 TTS 提供商：

| 配置文件 | 提供商 | 特点 |
|---------|--------|------|
| `configs/tts/config.yaml` | 阿里云 Qwen | 速度快、稳定、性价比高 |
| `configs/tts/config_siliconflow.yaml` | 硅基流动 | 支持 IndexTTS2、CosyVoice |
| `configs/tts/config_moss_ttsd.yaml` | 硅基流动 MOSS | 一次性生成双人对话 |
| `configs/tts/config_minimax.yaml` | MiniMax | 高清语音合成，自然度高 |
| `configs/tts/config_index_clone.yaml` | IndexTTS2 克隆 | 语音克隆特定音色 |

#### 方案一：阿里云百炼 Qwen-TTS（推荐新手）

```bash
# 1. 获取 API Key: https://bailian.console.aliyun.com/
# 2. 编辑 configs/tts/config.yaml，填入你的 API Key
vim configs/tts/config.yaml

# 3. 运行
python tts_generator.py 你的文件.md
```

#### 方案二：硅基流动 SiliconFlow (IndexTTS2)

```bash
# 1. 获取 API Key: https://cloud.siliconflow.cn/account/ak
# 2. 编辑 configs/tts/config_siliconflow.yaml
vim configs/tts/config_siliconflow.yaml

# 3. 运行
python tts_generator.py 你的文件.md -c configs/tts/config_siliconflow.yaml
```

#### 方案三：IndexTTS2 语音克隆

```bash
# 1. 准备一段 8-10 秒的参考音频
# 2. 编辑 configs/tts/config_index_clone.yaml
vim configs/tts/config_index_clone.yaml

# 3. 运行
python tts_index_clone.py 你的文件.md -c configs/tts/config_index_clone.yaml
```

### 3️⃣ 配置视频生成器

```bash
# 复制配置文件模板
cp video_generator_config.yaml.example video_generator_config.yaml

# 编辑配置
vim video_generator_config.yaml
```

### 4️⃣ 一键生成

```bash
# 使用默认配置文件
./run.sh

# 使用自定义配置文件
./run.sh my_config.yaml
```

---

## 🎭 情绪立绘系统

本项目支持 **9 种情绪** 的立绘系统，让视频更加生动：

| 情绪 | 说明 | 文件名示例 |
|------|------|-----------|
| 😐 neutral | 中性/默认 | `male-neutral.png`, `female-neutral.png` |
| 😊 happy | 开心 | `male-happy.png`, `female-happy.png` |
| 😠 angry | 愤怒 | `male-angry.png`, `female-angry.png` |
| 😔 sad | 悲伤 | `male-sad.png`, `female-sad.png` |
| 😕 confused | 困惑 | `male-confused.png`, `female-confused.png` |
| 😮 surprised | 惊讶 | `male-surprised.png`, `female-surprised.png` |
| 😨 fearful | 恐惧 | `male-fearful.png`, `female-fearful.png` |
| 😎 confident | 自信 | `male-confident.png`, `female-confident.png` |
| 😢 cry | 哭泣 | `male-cry.png`, `female-cry.png` |

### Markdown 情绪脚本格式

```markdown
### male speaker ###
### happy ###
### 大家好，今天我们要聊一个非常有趣的话题！###

### female speaker ###
### surprised ###
### 真的吗？太令人惊讶了！###

### male speaker ###
### confident ###
### 当然，这是最新的研究发现...###
```

### 配置情绪立绘

在 `video_generator_config.yaml` 中启用：

```yaml
# 情绪立绘设置
enable_mood: true
avatar_base_path: "avatar"

# GalGame 风格设置（可选）
subtitle_style: "galgame"
galgame_avatar:
  height_ratio: 0.35
  horizontal_position: 0.7
  vertical_offset: 5
```

---

## 📖 使用流程

### 方式一：一键脚本（推荐）

1. 准备 Markdown 对话脚本
2. 编辑 `video_generator_config.yaml` 配置你的参数
3. 运行：

```bash
./run.sh
```

### 方式二：分步执行

```bash
# Step 1: 生成音频
python tts_generator.py dialogue_script.md

# Step 2: 生成视频（使用配置文件）
python video_generator.py -c video_generator_config.yaml
```

### 方式三：命令行覆盖配置

```bash
# 覆盖配置文件中的特定参数
python video_generator.py -m another_file.md -t "新标题"
```

---

## 💰 费用说明

| 提供商 | 模型 | 价格 | 1万字文档 |
|--------|------|------|----------|
| 阿里云 | `qwen3-tts-flash` | ~0.5-1元/万字符 | **~0.5-1元** |
| 阿里云 | `qwen3-tts-instruct-flash` | ~1-2元/万字符 | **~1-2元** |
| 硅基流动 | `IndexTTS-2` / `CosyVoice2` | ~0.5-1元/万字符 | **~0.5-1元** |
| MiniMax | `speech-2.6-hd` | ~1-2元/万字符 | **~1-2元** |

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

### MiniMax Speech 音色

获取完整音色列表: https://platform.minimax.io/docs/api-reference/speech/voice

---

## 🎯 输出示例

### 音频输出
```
tts_output/
├── 20250221_120000/
│   ├── dialogue_001_male.wav
│   ├── dialogue_002_female.wav
│   ├── ...
│   └── dialogue_complete.wav    # 合并版
```

### 视频输出
```
broadcast_output/
└── podcast_20250221_203000.mp4
    ├── 🎬 1080p 高清视频
    ├── 👤 情绪立绘（根据脚本自动切换）
    ├── 🔊 音频波形可视化
    ├── 📝 动态字幕
    ├── 🎨 渐变/图片背景
    └── 📌 智能标题
```

---

## 📝 Markdown 格式

支持的对话格式：

```markdown
### male speaker ###
### 大家好，我是主持人。今天我们要聊的这篇文献... ###

### female speaker ###
### 说到这个话题，我认为... ###
```

带情绪的格式：

```markdown
### male speaker ###
### happy ###
### 大家好！今天是非常开心的一天！###

### female speaker ###
### surprised ###
### 哇，这太令人惊讶了！###
```

---

## 🛠️ 故障排查

### 依赖安装失败

```bash
# 使用国内镜像
pip install pyyaml requests pillow numpy -i https://pypi.tuna.tsinghua.edu.cn/simple
```

### 找不到 ffmpeg

```bash
# macOS
brew install ffmpeg

# Ubuntu/Debian
sudo apt-get install ffmpeg
```

### API 调用失败

1. 检查 API Key 是否正确（应填入配置文件中的 `YOUR_API_KEY_HERE` 位置）
2. 检查账户是否有足够余额
3. 查看对应平台的控制台额度

---

## 📚 详细文档

- `configs/CONFIG_GUIDE.md` - 配置文件详细指南
- 各脚本内嵌 `--help` 命令行帮助

---

## 🎉 开始使用

```bash
# 1. 克隆仓库
git clone <your-repo-url>
cd github_publish

# 2. 安装依赖
pip install pyyaml requests pillow numpy

# 3. 配置 API Key
vim configs/tts/config.yaml  # 填入你的 API Key

# 4. 准备对话脚本
cp your_dialogue.md paperwork_in/

# 5. 一键生成
./run.sh
```

---

## 📄 License

MIT License - 自由使用和修改

---

**祝你创作愉快！** 🎉
