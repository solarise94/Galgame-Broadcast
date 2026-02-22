# IndexTTS2 语音克隆使用指南

本脚本使用硅基流动的 **IndexTeam/IndexTTS-2** 模型，可以复刻任意人的声音，只需要提供 8-10 秒的参考音频。

## 特点

- **零样本克隆**: 无需训练，直接克隆
- **本地音频支持**: 自动将本地音频转换为 base64 格式
- **URL 支持**: 也可使用网络音频作为参考
- **男女声分离**: 可分别为男声和女声设置不同的克隆音色
- **情绪控制**: 支持 9 种情绪标签，让语音更生动
- **与 video_generator 兼容**: 生成的音频可直接用于视频生成

---

## 快速开始

### 1. 准备参考音频

准备一段 8-10 秒的音频文件：
- **格式**: wav、mp3、m4a 等常见格式
- **音质**: 清晰、无背景噪音
- **内容**: 任意说话内容，记录对应的文字

### 2. 基础用法（单音色克隆）

所有对话都使用同一个克隆音色：

```bash
python tts_index_clone.py paperwork_in/你的文档.md \
    --ref-audio voice_sample.mp3 \
    --ref-text "这是参考音频的文字内容，建议8-10秒"
```

### 3. 分别克隆男声和女声

为对话中的男声和女声分别设置不同的音色：

```bash
python tts_index_clone.py paperwork_in/你的文档.md \
    --male-audio male_voice.wav \
    --male-text "大家好，欢迎收听今天的科普节目" \
    --female-audio female_voice.wav \
    --female-text "谢谢主持人，很高兴来到这里"
```

### 4. 使用配置文件

```bash
# 使用默认配置文件
python tts_index_clone.py paperwork_in/你的文档.md

# 使用自定义配置文件
python tts_index_clone.py paperwork_in/你的文档.md -c configs/tts/config_index_clone.yaml
```

---

## 支持的情绪标签

IndexTTS2 支持通过情绪标签控制语音情感：

| 情绪 | 说明 | IndexTTS2 映射 |
|------|------|---------------|
| `gentle` | 温柔/中性 | Neutral |
| `happy` | 开心 | Happy |
| `confident` | 自信 | Neutral + 稳定语速 |
| `expectant` | 期待 | Happy + 音调上扬 |
| `confused` | 困惑 | Surprised + 语速放慢 |
| `shocked` | 震惊 | Surprised |
| `angry` | 愤怒 | Angry |
| `sad` | 悲伤 | Sad |
| `resigned` | 无奈 | Sad + 低音 |

### 在 Markdown 中使用情绪

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

---

## 命令行参数

| 参数 | 说明 | 示例 |
|------|------|------|
| `markdown` | Markdown 对话文件路径 | `paperwork_in/文档.md` |
| `--ref-audio` | 通用参考音频路径/URL | `--ref-audio voice.mp3` |
| `--ref-text` | 参考音频文字内容 | `--ref-text "参考文本"` |
| `--male-audio` | 男声参考音频 | `--male-audio male.wav` |
| `--male-text` | 男声参考文字 | `--male-text "男声文本"` |
| `--female-audio` | 女声参考音频 | `--female-audio female.wav` |
| `--female-text` | 女声参考文字 | `--female-text "女声文本"` |
| `--output, -o` | 输出目录 | `--output ./my_audio` |
| `--no-timestamp` | 不使用时间子文件夹 | `--no-timestamp` |
| `--prefix` | 文件名前缀 | `--prefix myvoice` |
| `--api-key` | API Key | `--api-key sk-xxxxx` |
| `--config, -c` | 配置文件路径 | `--config configs/tts/config_index_clone.yaml` |
| `--enable-mood` | 启用情绪功能 | `--enable-mood` (默认开启) |

---

## 配置文件

配置文件位置：`configs/tts/config_index_clone.yaml`

```yaml
# ---------------------- API 配置 ----------------------
api:
  api_key: "YOUR_API_KEY_HERE"
  base_url: "https://api.siliconflow.cn/v1"
  model: "IndexTeam/IndexTTS-2"

# ---------------------- 参考音频配置 ----------------------
references:
  # 通用参考音频（单音色克隆）
  audio: "./voice_samples/reference.mp3"
  text: "这是参考音频的文字内容"
  
  # 分别配置男女声（可选）
  male:
    audio: "./voice_samples/male.wav"
    text: "这是男声参考音频的文字内容"
  female:
    audio: "./voice_samples/female.wav"
    text: "这是女声参考音频的文字内容"

# ---------------------- 音色配置 ----------------------
voices:
  male:
    response_format: "wav"
    sample_rate: 44100
    speed: 1.0
    gain: 0.0
  female:
    response_format: "wav"
    sample_rate: 44100
    speed: 1.0
    gain: 0.0

# ---------------------- 输出配置 ----------------------
output:
  format: "wav"
  output_dir: "./tts_output"
  use_timestamp_subdir: true
  prefix: "cloned"

# ---------------------- 情绪功能配置 ----------------------
mood:
  # 是否启用情绪功能，默认开启
  enable: true
  
  # 情绪映射说明:
  # gentle -> Neutral, happy -> Happy, angry -> Angry
  # sad -> Sad, shocked -> Surprised, confused -> Surprised
```

---

## 工作流程

```
准备参考音频 → 运行 tts_index_clone.py → 生成到 tts_output/YYYYMMDD_HHMMSS/
                                                    ↓
                                          运行 video_generator.py
                                                    ↓
                                          自动生成视频到 broadcast_output/
```

---

## 完整示例

假设你有一段播客对话的 Markdown 文件：

```markdown
### male speaker ###
### happy ###
### 大家好，欢迎收听今天的科普节目！###

### female speaker ###
### gentle ###
### 谢谢主持人，很高兴来到这里。###
```

### 步骤1：准备参考音频

- `host_voice.mp3` - 主持人的声音（8-10秒）
- `guest_voice.mp3` - 嘉宾的声音（8-10秒）

### 步骤2：运行克隆脚本

```bash
python tts_index_clone.py paperwork_in/播客对话.md \
    --male-audio host_voice.mp3 --male-text "大家好，欢迎收听今天的节目" \
    --female-audio guest_voice.mp3 --female-text "谢谢主持人，很高兴来到这里"
```

输出：
```
🔊 准备男声参考音频...
  正在转换参考音频为 base64: host_voice.mp3
  转换完成 (大小: 123456 字符)
🔊 准备女声参考音频...
  正在转换参考音频为 base64: guest_voice.mp3
  转换完成 (大小: 123456 字符)

📄 解析 Markdown: paperwork_in/播客对话.md
✓ 共 2 段对话
📁 输出目录: tts_output/20260221_123045

🎙️ 开始合成语音...
  [1] 合成 male (happy): 大家好，欢迎收听今天的科普节目！... ✓
  [2] 合成 female (gentle): 谢谢主持人，很高兴来到这里... ✓

==================================================
生成完成!
成功: 2 个
输出目录: tts_output/20260221_123045
```

### 步骤3：生成视频

video_generator 会自动找到最新的 tts_output 子文件夹：

```bash
python video_generator.py -c video_generator_config.yaml
```

---

## 注意事项

1. **参考音频质量**: 参考音频的清晰度直接影响克隆效果，建议使用安静环境下录制的高质量音频
2. **API Key**: 需要在配置文件或通过 `--api-key` 参数设置有效的硅基流动 API Key
3. **费用**: IndexTTS2 模型调用会产生费用，请参考硅基流动官方定价
4. **时长限制**: 参考音频建议 8-10 秒，过长或过短可能影响效果
5. **情绪效果**: 情绪控制需要配合 video_generator 的情绪立绘功能使用

---

## 故障排除

### "参考音频文件不存在"
请检查音频文件路径是否正确，可以使用相对路径或绝对路径。

### "API 请求失败"
- 检查 API Key 是否有效
- 检查网络连接
- 参考音频格式是否支持

### "转换失败"
- 确保参考音频对应的文字内容准确
- 检查音频文件是否损坏

### 情绪不生效
- 确保 Markdown 中正确使用了情绪标签格式：`### happy ###`
- 检查配置文件中的 `mood.enable` 是否为 `true`
- IndexTTS2 的情绪映射是近似的，效果可能因内容而异
