#!/usr/bin/env python3
"""
IndexTTS2 语音克隆脚本 - 使用硅基流动 API 复刻任意音色

╔══════════════════════════════════════════════════════════════════╗
║  功能: 通过参考音频克隆特定说话人的声音                            ║
║  模型: IndexTeam/IndexTTS-2 (B站开源，零样本语音克隆)              ║
╠══════════════════════════════════════════════════════════════════╣
║  使用方法:                                                        ║
║    python tts_index_clone.py <markdown文件> --ref-audio <音频>    ║
║              --ref-text <参考文本> [选项]                         ║
╠══════════════════════════════════════════════════════════════════╣
║  示例命令:                                                        ║
║    # 基础用法 (单说话人克隆)                                       ║
║    python tts_index_clone.py 文案.md --ref-audio voice.mp3         ║
║              --ref-text "这是参考音频的文字内容"                   ║
║                                                                   ║
║    # 分别克隆男声和女声                                            ║
║    python tts_index_clone.py 文案.md                               ║
║              --male-audio male.wav --male-text "男声参考文本"      ║
║              --female-audio female.wav --female-text "女声参考文本" ║
║                                                                   ║
║    # 使用 URL 作为参考音频                                         ║
║    python tts_index_clone.py 文案.md                               ║
║              --ref-audio https://example.com/voice.mp3             ║
║              --ref-text "参考音频的文字内容"                       ║
╚══════════════════════════════════════════════════════════════════╝
"""

import os
import sys
import argparse
import base64
import requests
import yaml
import re
from pathlib import Path
from typing import Optional, Dict, List
from dataclasses import dataclass
from datetime import datetime


@dataclass
class VoiceCloneConfig:
    """语音克隆配置"""
    # API 配置
    api_key: str
    base_url: str = "https://api.siliconflow.cn/v1"
    model: str = "IndexTeam/IndexTTS-2"
    
    # 参考音频配置 (用于单一声色克隆)
    reference_audio: Optional[str] = None  # 本地路径或 URL
    reference_text: Optional[str] = None
    
    # 分别配置男女声
    male_reference_audio: Optional[str] = None
    male_reference_text: Optional[str] = None
    female_reference_audio: Optional[str] = None
    female_reference_text: Optional[str] = None
    
    # 输出配置
    output_dir: str = "./tts_output"
    use_timestamp_subdir: bool = True
    prefix: str = "cloned"
    response_format: str = "wav"
    sample_rate: int = 44100
    
    # 语速和音量
    speed: float = 1.0
    gain: float = 0.0
    
    # 情绪功能开关，默认开启
    enable_mood: bool = True


# 情绪到 TTS 参数的映射 (通用)
MOOD_TO_TTS = {
    'gentle': {'speed': 1.0, 'pitch': 0, 'vol': 1.0},
    'happy': {'speed': 1.1, 'pitch': 0.5, 'vol': 1.0},
    'confident': {'speed': 1.0, 'pitch': 0, 'vol': 1.1},
    'expectant': {'speed': 1.1, 'pitch': 1.0, 'vol': 1.0},
    'confused': {'speed': 0.9, 'pitch': 0.5, 'vol': 1.0},
    'shocked': {'speed': 1.2, 'pitch': 2.0, 'vol': 1.1},
    'angry': {'speed': 1.2, 'pitch': -1.0, 'vol': 1.2},
    'sad': {'speed': 0.8, 'pitch': -1.5, 'vol': 0.9},
    'resigned': {'speed': 1.0, 'pitch': -0.5, 'vol': 1.0},
}

# IndexTTS2 情绪映射 (SiliconFlow)
# IndexTTS2 支持的情绪: Neutral, Happy, Sad, Angry, Fearful, Disgusted, Surprised
MOOD_TO_INDEXTTS = {
    'gentle': 'Neutral',
    'happy': 'Happy',
    'confident': 'Neutral',
    'expectant': 'Happy',
    'confused': 'Surprised',
    'shocked': 'Surprised',
    'angry': 'Angry',
    'sad': 'Sad',
    'resigned': 'Sad',
}

# 支持的情绪列表
SUPPORTED_MOODS = list(MOOD_TO_TTS.keys())


def audio_to_base64(audio_path: str) -> str:
    """将本地音频文件转换为 base64"""
    with open(audio_path, 'rb') as f:
        audio_data = f.read()
    
    # 检测文件类型
    ext = Path(audio_path).suffix.lower()
    mime_types = {
        '.mp3': 'audio/mpeg',
        '.wav': 'audio/wav',
        '.m4a': 'audio/mp4',
        '.ogg': 'audio/ogg',
        '.aac': 'audio/aac'
    }
    mime_type = mime_types.get(ext, 'audio/mpeg')
    
    b64_data = base64.b64encode(audio_data).decode('utf-8')
    return f"data:{mime_type};base64,{b64_data}"


def prepare_reference(audio_source: str, text: str) -> Dict:
    """
    准备参考音频数据
    
    Args:
        audio_source: 本地音频路径 或 URL
        text: 参考音频对应的文字内容
    
    Returns:
        {"audio": base64或URL, "text": text}
    """
    # 判断是 URL 还是本地文件
    if audio_source.startswith(('http://', 'https://')):
        audio_data = audio_source
        print(f"  使用 URL 参考音频: {audio_source[:60]}...")
    else:
        # 本地文件，转换为 base64
        if not os.path.exists(audio_source):
            raise FileNotFoundError(f"参考音频文件不存在: {audio_source}")
        
        print(f"  正在转换参考音频为 base64: {audio_source}")
        audio_data = audio_to_base64(audio_source)
        print(f"  转换完成 (大小: {len(audio_data)} 字符)")
    
    return {
        "audio": audio_data,
        "text": text
    }


def synthesize_siliconflow(
    text: str,
    config: VoiceCloneConfig,
    reference: Optional[Dict] = None,
    mood: str = "gentle"
) -> bytes:
    """
    调用硅基流动 API 合成语音
    
    Args:
        text: 要合成的文本
        config: 配置
        reference: 参考音频配置 {"audio": ..., "text": ...}
        mood: 情绪标签
    
    Returns:
        音频数据 bytes
    """
    url = f"{config.base_url}/audio/speech"
    
    headers = {
        "Authorization": f"Bearer {config.api_key}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": config.model,
        "input": text,
        "voice": "",  # 使用动态音色
        "response_format": config.response_format,
        "sample_rate": config.sample_rate,
        "speed": config.speed,
        "gain": config.gain
    }
    
    # 添加参考音频
    if reference:
        payload["references"] = [reference]
    
    # IndexTTS2 情绪控制
    if 'IndexTTS' in config.model and config.enable_mood:
        # emo_vector: 情绪向量
        emo_vector = MOOD_TO_INDEXTTS.get(mood, 'Neutral')
        payload['emo_vector'] = emo_vector
        # emo_alpha: 情感强度 (0.0 ~ 1.0)
        payload['emo_alpha'] = 0.7
        # 打印调试信息
        print(f"[IndexTTS2: {emo_vector}]", end=' ')
    
    response = requests.post(url, headers=headers, json=payload, timeout=120)
    
    if response.status_code != 200:
        error_msg = response.text
        try:
            error_json = response.json()
            error_msg = error_json.get('message', error_msg)
        except:
            pass
        raise Exception(f"API 请求失败 (状态码 {response.status_code}): {error_msg}")
    
    return response.content


def parse_markdown(file_path: str, enable_mood: bool = True) -> List[Dict]:
    """
    解析 Markdown 对话文件
    
    支持两种格式:
    
    格式1 (带情绪，新格式):
    ### male speaker ###
    ### happy ###
    ### 文本内容 ###
    
    格式2 (旧格式):
    ## 主持人 (男)
    这是男声要说的内容
    """
    dialogues = []
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 首先尝试解析新格式（带情绪）
    # 新格式: ### speaker ### \n ### mood ### \n ### text ###
    if enable_mood:
        new_pattern = r'###\s*(male|female)\s*speaker\s*###\s*\n\s*###\s*(\w+)\s*###\s*\n\s*###\s*(.*?)\s*###'
        new_matches = re.findall(new_pattern, content, re.DOTALL)
        
        if new_matches:
            for idx, (speaker, mood, text) in enumerate(new_matches, 1):
                # 验证情绪是否有效
                mood = mood.lower()
                if mood not in SUPPORTED_MOODS:
                    mood = "gentle"  # 默认情绪
                
                text = _clean_text(text)
                if text:
                    dialogues.append({
                        'index': idx,
                        'speaker': speaker.lower(),
                        'text': text,
                        'mood': mood
                    })
            return dialogues
    
    # 如果没有匹配到新格式，使用旧格式解析
    lines = content.split('\n')
    current_speaker = None
    current_text = []
    index = 1
    
    for line in lines:
        line = line.strip()
        
        # 检测说话人 (## 开头)
        if line.startswith('##') or line.startswith('**'):
            # 保存上一个人的内容
            if current_speaker and current_text:
                dialogues.append({
                    'index': index,
                    'speaker': current_speaker,
                    'text': '\n'.join(current_text).strip(),
                    'mood': 'gentle'  # 默认情绪
                })
                index += 1
                current_text = []
            
            # 解析新的说话人
            speaker_line = line.lstrip('#*').strip()
            if '(男)' in speaker_line or '男' in speaker_line or 'male' in speaker_line.lower():
                current_speaker = 'male'
            elif '(女)' in speaker_line or '女' in speaker_line or 'female' in speaker_line.lower():
                current_speaker = 'female'
            else:
                # 默认根据序号判断，奇数为男，偶数为女
                current_speaker = 'male' if index % 2 == 1 else 'female'
        
        elif line and current_speaker:
            # 跳过 markdown 标记
            if not line.startswith('```') and not line.startswith('---'):
                current_text.append(line)
    
    # 保存最后一个人的内容
    if current_speaker and current_text:
        dialogues.append({
            'index': index,
            'speaker': current_speaker,
            'text': '\n'.join(current_text).strip(),
            'mood': 'gentle'  # 默认情绪
        })
    
    return dialogues


def _clean_text(text: str) -> str:
    """清理文本"""
    # 移除换行符
    text = text.replace('\n', ' ')
    # 移除多余空格
    text = re.sub(r'\s+', ' ', text).strip()
    # 移除括号内容
    text = re.sub(r'[（(][^）)]+[）)]', '', text)
    return text


def generate_cloned_audio(
    markdown_path: str,
    config: VoiceCloneConfig
) -> List[str]:
    """
    生成克隆音色的音频
    
    Args:
        markdown_path: Markdown 文件路径
        config: 语音克隆配置
    
    Returns:
        生成的音频文件列表
    """
    # 准备参考音频
    references = {}
    
    if config.male_reference_audio and config.male_reference_text:
        print("🔊 准备男声参考音频...")
        references['male'] = prepare_reference(
            config.male_reference_audio, 
            config.male_reference_text
        )
    
    if config.female_reference_audio and config.female_reference_text:
        print("🔊 准备女声参考音频...")
        references['female'] = prepare_reference(
            config.female_reference_audio,
            config.female_reference_text
        )
    
    # 如果只提供了一组参考音频，用于所有说话人
    if not references and config.reference_audio and config.reference_text:
        print("🔊 准备通用参考音频...")
        ref = prepare_reference(config.reference_audio, config.reference_text)
        references['male'] = ref
        references['female'] = ref
    
    if not references:
        raise ValueError("请提供参考音频! 使用 --ref-audio/--ref-text 或 --male-audio/--female-audio")
    
    # 解析 Markdown
    print(f"\n📄 解析 Markdown: {markdown_path}")
    if config.enable_mood:
        print("✨ 情绪功能已启用")
    else:
        print("ℹ️ 情绪功能已禁用")
    dialogues = parse_markdown(markdown_path, enable_mood=config.enable_mood)
    print(f"✓ 共 {len(dialogues)} 段对话")
    
    # 创建输出目录
    output_dir = Path(config.output_dir)
    if config.use_timestamp_subdir:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = output_dir / timestamp
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"📁 输出目录: {output_dir}")
    
    # 生成音频
    audio_files = []
    failed_count = 0
    
    print("\n🎙️ 开始合成语音...")
    for dialogue in dialogues:
        speaker = dialogue['speaker']
        text = dialogue['text']
        index = dialogue['index']
        mood = dialogue.get('mood', 'gentle')
        
        filename = f"{config.prefix}_{index:03d}_{speaker}.{config.response_format}"
        output_path = output_dir / filename
        
        # 检查是否已有参考音频
        if speaker not in references:
            # 使用另一个性别的参考音频
            fallback_speaker = 'female' if speaker == 'male' else 'male'
            if fallback_speaker in references:
                print(f"  [{index}] {speaker} 使用 {fallback_speaker} 的参考音频")
                ref = references[fallback_speaker]
            else:
                print(f"  ⚠ 跳过 [{index}] {speaker}: 无参考音频")
                failed_count += 1
                continue
        else:
            ref = references[speaker]
        
        # 显示情绪信息
        mood_info = f" [{mood}]" if config.enable_mood else ""
        print(f"  [{index}] 合成 {speaker}{mood_info}: {text[:30]}...", end=' ')
        
        try:
            # 根据情绪调整语速
            current_config = config
            if config.enable_mood and mood in MOOD_TO_TTS:
                mood_params = MOOD_TO_TTS[mood]
                # 创建临时配置对象，应用情绪参数
                current_config = VoiceCloneConfig(
                    api_key=config.api_key,
                    base_url=config.base_url,
                    model=config.model,
                    reference_audio=config.reference_audio,
                    reference_text=config.reference_text,
                    male_reference_audio=config.male_reference_audio,
                    male_reference_text=config.male_reference_text,
                    female_reference_audio=config.female_reference_audio,
                    female_reference_text=config.female_reference_text,
                    output_dir=config.output_dir,
                    use_timestamp_subdir=config.use_timestamp_subdir,
                    prefix=config.prefix,
                    response_format=config.response_format,
                    sample_rate=config.sample_rate,
                    speed=mood_params['speed'],  # 应用情绪语速
                    gain=config.gain,
                    enable_mood=config.enable_mood
                )
            
            audio_data = synthesize_siliconflow(text, current_config, ref, mood=mood)
            with open(output_path, 'wb') as f:
                f.write(audio_data)
            print(f"✓")
            audio_files.append(str(output_path))
        except Exception as e:
            print(f"✗ 失败: {e}")
            failed_count += 1
    
    # 打印结果
    print(f"\n{'='*50}")
    print(f"生成完成!")
    print(f"成功: {len(audio_files)} 个")
    if failed_count > 0:
        print(f"失败: {failed_count}")
    print(f"输出目录: {output_dir}")
    
    return audio_files


def main():
    parser = argparse.ArgumentParser(
        description='IndexTTS2 语音克隆 - 复刻任意音色',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 单音色克隆（所有对话使用同一个声音）
  python tts_index_clone.py paperwork_in/文档.md \\
      --ref-audio voice_sample.mp3 \\
      --ref-text "这是参考音频的文字内容，建议8-10秒"
  
  # 分别克隆男声和女声
  python tts_index_clone.py paperwork_in/文档.md \\
      --male-audio male_voice.wav --male-text "男声参考文本" \\
      --female-audio female_voice.wav --female-text "女声参考文本"
  
  # 使用 URL 作为参考音频
  python tts_index_clone.py paperwork_in/文档.md \\
      --ref-audio https://example.com/voice.mp3 \\
      --ref-text "参考音频的文字内容"
  
  # 指定输出目录
  python tts_index_clone.py paperwork_in/文档.md \\
      --ref-audio voice.mp3 --ref-text "参考文本" \\
      --output ./my_cloned_audio
        """
    )
    
    parser.add_argument('markdown', help='Markdown 对话文件路径')
    
    # 通用参考音频选项
    parser.add_argument('--ref-audio', help='参考音频路径或 URL')
    parser.add_argument('--ref-text', help='参考音频对应的文字内容')
    
    # 分别配置男女声
    parser.add_argument('--male-audio', help='男声参考音频路径或 URL')
    parser.add_argument('--male-text', help='男声参考音频文字内容')
    parser.add_argument('--female-audio', help='女声参考音频路径或 URL')
    parser.add_argument('--female-text', help='女声参考音频文字内容')
    
    # 输出配置
    parser.add_argument('--output', '-o', default='./tts_output', 
                       help='输出目录 (默认: ./tts_output)')
    parser.add_argument('--no-timestamp', action='store_true',
                       help='不使用时间子文件夹')
    parser.add_argument('--prefix', default='cloned',
                       help='文件名前缀 (默认: cloned)')
    
    # API 配置
    parser.add_argument('--api-key', help='硅基流动 API Key')
    parser.add_argument('--config', '-c', default='configs/tts/config_index_clone.yaml',
                       help='配置文件路径')
    
    # 情绪功能
    parser.add_argument('--no-mood', action='store_true',
                       help='禁用情绪功能')
    
    args = parser.parse_args()
    
    # 检查 markdown 文件
    if not os.path.exists(args.markdown):
        print(f"❌ 错误: 找不到文件 '{args.markdown}'")
        sys.exit(1)
    
    # 加载配置文件
    config_data = {}
    if os.path.exists(args.config):
        with open(args.config, 'r', encoding='utf-8') as f:
            config_data = yaml.safe_load(f) or {}
        print(f"✓ 加载配置文件: {args.config}")
    
    # 获取 API Key
    api_key = args.api_key or config_data.get('api', {}).get('api_key') or os.environ.get('SILICONFLOW_API_KEY')
    if not api_key or api_key == "YOUR_API_KEY_HERE":
        print("❌ 错误: 请提供 API Key")
        print("   方式1: 设置环境变量 SILICONFLOW_API_KEY")
        print("   方式2: 使用 --api-key 参数")
        print("   方式3: 在配置文件中设置 api.api_key")
        sys.exit(1)
    
    # 创建配置对象
    # 情绪功能开关（默认开启，可通过 --no-mood 或配置文件关闭）
    enable_mood = not args.no_mood
    if 'mood' in config_data:
        enable_mood = config_data['mood'].get('enable', enable_mood)
    
    config = VoiceCloneConfig(
        api_key=api_key,
        base_url=config_data.get('api', {}).get('base_url', 'https://api.siliconflow.cn/v1'),
        model=config_data.get('api', {}).get('model', 'IndexTeam/IndexTTS-2'),
        reference_audio=args.ref_audio,
        reference_text=args.ref_text,
        male_reference_audio=args.male_audio,
        male_reference_text=args.male_text,
        female_reference_audio=args.female_audio,
        female_reference_text=args.female_text,
        output_dir=args.output,
        use_timestamp_subdir=not args.no_timestamp,
        prefix=args.prefix,
        response_format=config_data.get('output', {}).get('format', 'wav'),
        sample_rate=config_data.get('voices', {}).get('male', {}).get('sample_rate', 44100),
        speed=config_data.get('voices', {}).get('male', {}).get('speed', 1.0),
        gain=config_data.get('voices', {}).get('male', {}).get('gain', 0.0),
        enable_mood=enable_mood
    )
    
    # 运行生成
    try:
        generate_cloned_audio(args.markdown, config)
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
