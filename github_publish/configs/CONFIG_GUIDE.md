# 配置文件使用指南

本项目支持三个 TTS 提供商，每个提供商有独立的配置文件，避免参数混淆。

## 快速选择

| 配置文件 | 提供商 | 特点 | 适合场景 |
|---------|--------|------|---------|
| `configs/config.yaml` | 阿里云 Qwen | 速度快、稳定、性价比高 | 日常使用、批量生产 |
| `configs/config_siliconflow.yaml` | 硅基流动 | 支持 IndexTTS2、CosyVoice、MOSS-TTSD | 需要语音克隆、双人对话 |
| `configs/config_moss_ttsd.yaml` | 硅基流动 MOSS | 一次性生成双人对话 | AI播客、对话场景 |
| `configs/config_minimax.yaml` | MiniMax | 高清语音合成，自然度高 | 内容生产、高品质场景 |

## 使用方法

### 1. 阿里云百炼 Qwen-TTS (默认，推荐新手)

```bash
# 编辑配置文件
vim configs/config.yaml

# 只需要修改这一行
api:
  api_key: "sk-你的API密钥"

# 运行
python tts_generator.py 你的文件.md
```

**获取 API Key**: https://bailian.console.aliyun.com/

---

### 2. 硅基流动 SiliconFlow (IndexTTS2 / CosyVoice)

```bash
# 编辑 SiliconFlow 专用配置文件
vim configs/config_siliconflow.yaml

# 只需要修改这一行
api:
  api_key: "你的API密钥"

# 可选：切换模型
api:
  model: "IndexTeam/IndexTTS-2"        # B站开源，支持语音克隆
  # model: "FunAudioLLM/CosyVoice2-0.5B"  # 阿里开源，支持情感控制

# 运行
python tts_generator.py 你的文件.md -c configs/config_siliconflow.yaml
```

**获取 API Key**: https://cloud.siliconflow.cn/account/ak

**注意**: 硅基流动需要账户有余额才能使用 API，新用户有免费额度。

---

### 3. 硅基流动 MOSS-TTSD (双人对话)

```bash
# 编辑 MOSS-TTSD 专用配置文件
vim configs/config_moss_ttsd.yaml

# 运行（一次性生成完整的双人对话音频）
python tts_generator.py 你的文件.md -c configs/config_moss_ttsd.yaml
```

详见下方的"MOSS-TTSD 双人对话"部分。

---

### 4. MiniMax Speech (高清语音)

```bash
# 编辑 MiniMax 专用配置文件
vim configs/config_minimax.yaml

# 只需要修改这一行
api:
  api_key: "你的API密钥"
  # group_id: "你的Group ID"  # 部分账户需要

# 可选：切换模型
api:
  model: "speech-2.6-hd"     # 高清模式（推荐）
  # model: "speech-2.6-turbo"  # 快速模式

# 运行
python tts_generator.py 你的文件.md -c configs/config_minimax.yaml
```

**获取 API Key**: https://platform.minimax.io/

**特点**：
- 🎵 高清语音合成，音质优秀
- 🎭 多种中文音色可选（演讲、纪录片、旁白风格）
- ⚡ 支持快速模式和高质量模式
- 🎚️ 可调节语速、音量、音调

---

## 音色选择参考

### Qwen-TTS 推荐音色

| 性别 | 音色 | 特点 | 适合内容 |
|-----|------|------|---------|
| 男 | Ethan | 成熟稳重 | 学术讲解、新闻 |
| 男 | Eric | 青年活泼 | 轻松内容、对话 |
| 女 | Cherry | 活泼自然 | 日常对话、科普 |
| 女 | Bella | 知性优雅 | 专业内容、商务 |

### SiliconFlow 推荐音色 (IndexTTS2 / CosyVoice2)

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

## 常见问题

### Q: 我应该选择哪个提供商？

| 需求 | 推荐提供商 |
|------|-----------|
| 追求性价比和稳定性 | 阿里云 Qwen |
| 需要语音克隆功能 | 硅基流动 IndexTTS2 |
| 需要情感控制 | 硅基流动 CosyVoice2 |
| 需要生成双人对话 | 硅基流动 MOSS-TTSD |
| 追求高品质语音 | MiniMax Speech |

### Q: 为什么需要多个配置文件？

不同提供商的参数体系不同：
- Qwen 使用 `language_type`、`instructions`
- SiliconFlow 使用 `speed`、`gain`、`sample_rate`
- MiniMax 使用 `voice_id`、`speed`、`vol`、`pitch`

分开配置可以避免混淆和错误。

### Q: 可以复制一份配置文件然后修改使用吗？

可以，建议这样做：
```bash
# 复制一份自己的配置
cp configs/config_siliconflow.yaml configs/my_config.yaml

# 编辑并运行
vim configs/my_config.yaml
python tts_generator.py 文件.md -c configs/my_config.yaml
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
python tts_generator.py 你的文件.md -c configs/config_moss_ttsd.yaml
```

默认使用 **alex (男声)** 和 **anna (女声)** 作为两个说话人。

#### 2. 使用参考音频克隆声音（高级）

编辑 `configs/config_moss_ttsd.yaml`：

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
audio_output/
└── moss_dialogue_dialogue_combined.wav  # 完整的双人对话
```

而不是像其他模型那样生成多个独立片段。

### 示例

```bash
# 使用示例对话文件测试
python tts_generator.py configs/example_moss_dialogue.md -c configs/config_moss_ttsd.yaml
```
