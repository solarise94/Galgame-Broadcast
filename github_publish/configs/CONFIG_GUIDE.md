# 配置文件使用指南

本项目支持多个 TTS 提供商和语音克隆功能，每个功能有独立的配置文件，避免参数混淆。

---

## 快速选择

| 配置文件 | 提供商 | 特点 | 适合场景 |
|---------|--------|------|---------|
| `configs/tts/config.yaml` | 阿里云 Qwen | 速度快、稳定、性价比高 | 日常使用、批量生产 |
| `configs/tts/config_siliconflow.yaml` | 硅基流动 | 支持 IndexTTS2、CosyVoice | 需要语音克隆、双人对话 |
| `configs/tts/config_moss_ttsd.yaml` | 硅基流动 MOSS | 一次性生成双人对话 | AI播客、对话场景 |
| `configs/tts/config_minimax.yaml` | MiniMax | 高清语音合成，自然度高 | 内容生产、高品质场景 |
| `configs/tts/config_index_clone.yaml` | IndexTTS2 克隆 | 零样本语音克隆 | 复刻特定人物声音 |

---

## 使用方法

### 1. 阿里云百炼 Qwen-TTS (默认，推荐新手)

```bash
# 编辑配置文件
vim configs/tts/config.yaml

# 只需要修改这一行
api:
  api_key: "YOUR_API_KEY_HERE"

# 运行
python tts_generator.py 你的文件.md
```

**获取 API Key**: https://bailian.console.aliyun.com/

---

### 2. 硅基流动 SiliconFlow (IndexTTS2 / CosyVoice)

```bash
# 编辑 SiliconFlow 专用配置文件
vim configs/tts/config_siliconflow.yaml

# 只需要修改这一行
api:
  api_key: "YOUR_API_KEY_HERE"

# 可选：切换模型
api:
  model: "IndexTeam/IndexTTS-2"        # B站开源，支持语音克隆
  # model: "FunAudioLLM/CosyVoice2-0.5B"  # 阿里开源，支持情感控制

# 运行
python tts_generator.py 你的文件.md -c configs/tts/config_siliconflow.yaml
```

**获取 API Key**: https://cloud.siliconflow.cn/account/ak

**注意**: 硅基流动需要账户有余额才能使用 API，新用户有免费额度。

---

### 3. IndexTTS2 语音克隆 (推荐用于音色复刻)

使用 **tts_index_clone.py** 脚本和专用配置：

```bash
# 编辑语音克隆配置文件
vim configs/tts/config_index_clone.yaml

# 配置参考音频
references:
  male:
    audio: "./voice_samples/male_host.wav"
    text: "这是男声参考音频的文字内容"
  female:
    audio: "./voice_samples/female_guest.wav"
    text: "这是女声参考音频的文字内容"

# 运行
python tts_index_clone.py 你的文件.md -c configs/tts/config_index_clone.yaml
```

**特点**：
- 🎭 零样本克隆，只需 8-10 秒参考音频
- 👥 支持男女声分别克隆
- 😊 支持情绪标签控制
- 🔗 详见 [INDEX_CLONE_USAGE.md](../INDEX_CLONE_USAGE.md)

---

### 4. 硅基流动 MOSS-TTSD (双人对话)

```bash
# 编辑 MOSS-TTSD 专用配置文件
vim configs/tts/config_moss_ttsd.yaml

# 运行（一次性生成完整的双人对话音频）
python tts_generator.py 你的文件.md -c configs/tts/config_moss_ttsd.yaml
```

详见下方的"MOSS-TTSD 双人对话"部分。

---

### 5. MiniMax Speech (高清语音)

```bash
# 编辑 MiniMax 专用配置文件
vim configs/tts/config_minimax.yaml

# 只需要修改这一行
api:
  api_key: "YOUR_API_KEY_HERE"
  # group_id: "你的Group ID"  # 部分账户需要

# 可选：切换模型
api:
  model: "speech-2.6-hd"     # 高清模式（推荐）
  # model: "speech-2.6-turbo"  # 快速模式

# 运行
python tts_generator.py 你的文件.md -c configs/tts/config_minimax.yaml
```

**获取 API Key**: https://platform.minimax.io/

**特点**：
- 🎵 高清语音合成，音质优秀
- 🎭 多种中文音色可选（演讲、纪录片、旁白风格）
- ⚡ 支持快速模式和高质量模式
- 🎚️ 可调节语速、音量、音调

---

## 情绪功能详解

### 支持的情绪标签

所有 TTS 脚本都支持 **9 种情绪标签**：

| 情绪 | 说明 | 适用场景 |
|------|------|---------|
| `gentle` | 温柔/中性 | 日常对话、介绍 |
| `happy` | 开心 | 兴奋、喜悦的内容 |
| `confident` | 自信 | 专业讲解、总结 |
| `expectant` | 期待 | 展望、期待未来 |
| `confused` | 困惑 | 疑问、不确定 |
| `shocked` | 震惊 | 惊讶、意外发现 |
| `angry` | 愤怒 | 批评、强烈情绪 |
| `sad` | 悲伤 | 遗憾、坏消息 |
| `resigned` | 无奈 | 无奈接受、妥协 |

### Markdown 情绪格式

```markdown
### male speaker ###
### happy ###
### 大家好！今天是非常开心的一天！###

### female speaker ###
### surprised ###
### 哇，这太令人惊讶了！###

### male speaker ###
### confident ###
### 当然，这是最新的研究发现...###
```

### 情绪配置

在配置文件中控制情绪功能：

```yaml
# IndexTTS2 示例 (config_index_clone.yaml)
mood:
  enable: true  # 启用情绪功能

# MiniMax 示例 (config_minimax.yaml)
emotion:
  use_emotion: true        # 使用 Markdown 中的情绪
  default_emotion: "gentle" # 默认情绪
  pass_voice_params: false  # 是否传递音色参数
```

### 视频中的情绪立绘

video_generator 支持根据情绪自动切换立绘：

```yaml
# video_generator_config.yaml
enable_mood: true
avatar_base_path: "avatar"
```

需要准备对应的情绪立绘图片：
- `avatar/male-happy.png`
- `avatar/male-surprised.png`
- `avatar/female-happy.png`
- `avatar/female-sad.png`
- ...等等

---

## 音色选择参考

### Qwen-TTS 推荐音色

| 性别 | 音色 | 特点 | 适合内容 |
|-----|------|------|---------|
| 男 | Ethan | 成熟稳重 | 学术讲解、新闻 |
| 男 | Eric | 青年活泼 | 轻松内容、对话 |
| 女 | Cherry | 活泼自然 | 日常对话、科普 |
| 女 | Bella | 知性优雅 | 专业内容、商务 |

### SiliconFlow 推荐音色 (IndexTTS2 / CosyVoice2 / MOSS-TTSD)

| 性别 | 音色 | 特点 |
|-----|------|------|
| 男 | alex | 沉稳 |
| 男 | charles | 磁性 |
| 女 | anna | 沉稳 |
| 女 | claire | 温柔 |

### MiniMax 推荐音色

| 性别 | 音色 | 特点 |
|-----|------|------|
| 男 | Chinese_Male_Speech_Speaker_01 | 成熟男声（推荐） |
| 男 | Chinese_Male_Documentary_Speaker_01 | 纪录片风格 |
| 女 | Chinese_Female_Speech_Speaker_01 | 成熟女声（推荐） |
| 女 | Chinese_Female_Speech_Speaker_02 | 温柔女声 |

---

## 视频生成配置

视频生成器配置文件：`video_generator_config.yaml`（从 example 复制）

```bash
cp video_generator_config.yaml.example video_generator_config.yaml
vim video_generator_config.yaml
```

### 关键配置项

```yaml
# 输入输出
audio_dir: "tts_output"  # 音频目录，自动查找最新子文件夹
markdown_file: "paperwork_in/dialogue.md"
output_dir: "broadcast_output"

# 视频设置
resolution:
  width: 1920
  height: 1080
fps: 30

# 背景
background_type: "gradient"  # gradient | color | image
background_image: ""  # image 类型时填写路径

# 标题
show_intro: true
title: ""
subtitle: "对话式科普播客"

# 头像
male_avatar: "avatar/male.png"
female_avatar: "avatar/female.png"
male_name: "Alex"
female_name: "Cherry"

# 字幕样式
subtitle_style: "default"  # default | galgame
font_size: 40

# 情绪立绘
enable_mood: true
avatar_base_path: "avatar"

# GalGame 风格设置
galgame_avatar:
  height_ratio: 0.35
  horizontal_position: 0.7
  vertical_offset: 5
```

---

## 常见问题

### Q: 我应该选择哪个提供商？

| 需求 | 推荐提供商 |
|------|-----------|
| 追求性价比和稳定性 | 阿里云 Qwen |
| 需要语音克隆功能 | 硅基流动 IndexTTS2 (tts_index_clone.py) |
| 需要情感控制 | 硅基流动 CosyVoice2 |
| 需要生成双人对话 | 硅基流动 MOSS-TTSD |
| 追求高品质语音 | MiniMax Speech |

### Q: 为什么需要多个配置文件？

不同提供商的参数体系不同：
- Qwen 使用 `language_type`、`instructions`
- SiliconFlow 使用 `speed`、`gain`、`sample_rate`、`emo_vector`
- MiniMax 使用 `voice_id`、`speed`、`vol`、`pitch`

分开配置可以避免混淆和错误。

### Q: 可以复制一份配置文件然后修改使用吗？

可以，建议这样做：
```bash
# 复制一份自己的配置
cp configs/tts/config_siliconflow.yaml configs/tts/my_config.yaml

# 编辑并运行
vim configs/tts/my_config.yaml
python tts_generator.py 文件.md -c configs/tts/my_config.yaml
```

---

## 特殊功能：MOSS-TTSD 双人对话

### 什么是 MOSS-TTSD？

`fnlp/MOSS-TTSD-v0.5` 是复旦大学开源的**双人对话语音合成模型**，它的特点是：

- **一次请求生成完整对话**：不需要逐段合成再合并
- **自然对话语调**：说话人之间的切换更自然流畅
- **支持语音克隆**：可以上传参考音频克隆任意两个声音

### 使用方法

#### 1. 使用系统预置音色（简单）

```bash
# 使用 MOSS-TTSD 专用配置
python tts_generator.py 你的文件.md -c configs/tts/config_moss_ttsd.yaml
```

默认使用 **alex (男声)** 和 **anna (女声)** 作为两个说话人。

#### 2. 使用参考音频克隆声音（高级）

编辑 `configs/tts/config_moss_ttsd.yaml`：

```yaml
voices:
  male:
    # 不使用 voice 字段，而是使用 references
    references:
      # 说话人 1 (S1) 的参考音频
      - audio: "https://your-domain.com/speaker1.mp3"
        text: "参考音频对应的文字内容，建议8-10秒"
      # 说话人 2 (S2) 的参考音频  
      - audio: "https://your-domain.com/speaker2.mp3"
        text: "参考音频对应的文字内容，建议8-10秒"
```

**参考音频要求**：
- 时长：8-10秒
- 音质：清晰、无背景噪音
- 内容：单人说话，不要混音

#### 3. Markdown 文件格式

和其他模型一样使用 `male speaker` / `female speaker` 标记：

```markdown
### male speaker ###
### 大家好，我是主持人。 ###

### female speaker ###
### 你好，很高兴来到这里。 ###

### male speaker ###
### 今天我们聊聊这个话题... ###
```

程序会自动转换为 MOSS-TTSD 的 `[S1]` `[S2]` 格式。

#### 4. 输出结果

MOSS-TTSD 会输出**单个完整的对话音频文件**：
```
tts_output/
└── moss_dialogue_dialogue_combined.wav  # 完整的双人对话
```

而不是像其他模型那样生成多个独立片段。
