#!/usr/bin/env python3
"""
TTS 语音合成脚本 - 将 Markdown 对话转换为语音
支持阿里云百炼 Qwen-TTS、硅基流动 SiliconFlow TTS (含 IndexTTS2、CosyVoice2、MOSS-TTSD 等) 和 MiniMax Speech

╔══════════════════════════════════════════════════════════════════╗
║  使用方法:                                                        ║
║    python tts_generator.py <markdown文件> [选项]                  ║
╠══════════════════════════════════════════════════════════════════╣
║  常用命令:                                                        ║
║    # 使用默认配置生成                                             ║
║    python tts_generator.py 文献解读对话文案-2.md                  ║
║                                                                   ║
║    # 指定配置文件                                                 ║
║    python tts_generator.py 文献解读对话文案-2.md -c config.yaml   ║
╠══════════════════════════════════════════════════════════════════╣
║  配置文件 (config.yaml) 说明:                                     ║
║    • provider         - TTS提供商 (qwen/siliconflow/minimax)     ║
║    • api.api_key      - API Key                                  ║
║    • api.model        - TTS模型 (仅部分提供商需要)               ║
║    • voices.male      - 男声音色                                 ║
║    • voices.female    - 女声音色                                 ║
╠══════════════════════════════════════════════════════════════════╣
║  输出文件:                                                        ║
║    • dialogue_001_male.wav, dialogue_002_female.wav...           ║
║    • dialogue_complete.wav (合并后的完整音频)                     ║
╚══════════════════════════════════════════════════════════════════╝
"""

import os
import re
import yaml
import time
import uuid
import requests
import base64
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from abc import ABC, abstractmethod
import wave
import struct
import json


@dataclass
class DialogueLine:
    """对话行数据结构"""
    speaker: str  # 'male' 或 'female'
    text: str
    index: int
    mood: str = "gentle"  # 情绪: gentle, happy, confident, expectant, confused, shocked, angry, sad, resigned


class BaseTTSClient(ABC):
    """TTS API 客户端抽象基类"""
    
    @abstractmethod
    def synthesize(self, text: str, voice_config: Dict, output_path: str) -> bool:
        """合成单段语音"""
        pass


class QwenTTSClient(BaseTTSClient):
    """阿里云百炼 Qwen TTS API 客户端"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.api_key = config['api']['api_key']
        self.model = config['api']['model']
        self.base_url = config['api']['base_url']
        
        # 检查 API Key
        if self.api_key == "YOUR_API_KEY_HERE" or not self.api_key:
            raise ValueError("请在 config.yaml 中设置有效的 API Key")
    
    def synthesize(self, text: str, voice_config: Dict, output_path: str) -> bool:
        """
        合成单段语音
        
        Args:
            text: 要合成的文本
            voice_config: 音色配置
            output_path: 输出文件路径
        
        Returns:
            bool: 是否成功
        """
        url = f"{self.base_url}/services/aigc/multimodal-generation/generation"
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "input": {
                "text": text,
                "voice": voice_config['voice'],
                "language_type": voice_config.get('language_type', 'Chinese')
            }
        }
        
        # 如果是指令控制模型，添加指令
        if 'instructions' in voice_config and 'instruct' in self.model:
            payload['input']['instructions'] = voice_config['instructions']
            payload['input']['optimize_instructions'] = voice_config.get('optimize_instructions', True)
        
        try:
            # 第一步：调用 API 获取音频 URL
            response = requests.post(url, headers=headers, json=payload, timeout=60)
            response.raise_for_status()
            
            result = response.json()
            
            # 解析响应获取音频 URL
            if 'output' in result and 'audio' in result['output']:
                audio_info = result['output']['audio']
                
                # 优先从 URL 下载音频
                if isinstance(audio_info, dict) and 'url' in audio_info and audio_info['url']:
                    audio_url = audio_info['url']
                    # 下载音频文件
                    audio_response = requests.get(audio_url, timeout=60)
                    audio_response.raise_for_status()
                    
                    with open(output_path, 'wb') as f:
                        f.write(audio_response.content)
                    return True
                
                # 如果 URL 不可用，尝试 base64 数据
                elif isinstance(audio_info, dict) and 'data' in audio_info and audio_info['data']:
                    audio_bytes = base64.b64decode(audio_info['data'])
                    with open(output_path, 'wb') as f:
                        f.write(audio_bytes)
                    return True
                else:
                    print(f"警告: 无法获取音频数据")
                    return False
            else:
                print(f"API 响应异常: {result}")
                return False
                
        except requests.exceptions.RequestException as e:
            print(f"API 请求失败: {e}")
            return False
        except Exception as e:
            print(f"合成失败: {e}")
            return False
    
    def synthesize_streaming(self, text: str, voice_config: Dict, output_path: str) -> bool:
        """
        流式合成语音（适用于长文本）
        """
        url = f"{self.base_url}/services/aigc/multimodal-generation/generation"
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "input": {
                "text": text,
                "voice": voice_config['voice'],
                "language_type": voice_config.get('language_type', 'Chinese')
            },
            "stream": True
        }
        
        try:
            response = requests.post(url, headers=headers, json=payload, stream=True, timeout=120)
            response.raise_for_status()
            
            audio_chunks = []
            for line in response.iter_lines():
                if line:
                    try:
                        data = json.loads(line.decode('utf-8'))
                        if 'output' in data and 'audio' in data['output']:
                            audio_chunk = base64.b64decode(data['output']['audio'])
                            audio_chunks.append(audio_chunk)
                    except:
                        pass
            
            if audio_chunks:
                with open(output_path, 'wb') as f:
                    for chunk in audio_chunks:
                        f.write(chunk)
                return True
            return False
            
        except Exception as e:
            print(f"流式合成失败: {e}")
            return False


class MiniMaxTTSClient(BaseTTSClient):
    """MiniMax Speech TTS API 客户端
    
    支持模型:
    - speech-2.6-hd (高清语音合成)
    - speech-2.6-turbo (快速语音合成)
    - speech-02-hd / speech-02-turbo
    - speech-01-hd / speech-01-turbo
    """
    
    def __init__(self, config: Dict):
        self.config = config
        self.api_key = config['api']['api_key']
        self.model = config['api'].get('model', 'speech-2.6-hd')
        self.base_url = config['api'].get('base_url', 'https://api.minimax.chat')
        self.group_id = config['api'].get('group_id', '')
        
        # 检查 API Key
        if self.api_key == "YOUR_API_KEY_HERE" or not self.api_key:
            raise ValueError("请在 config.yaml 中设置有效的 API Key")
        
        # 检查 Group ID (MiniMax 需要)
        if not self.group_id:
            print("警告: 未设置 Group ID，MiniMax API 可能需要 Group ID")
    
    def synthesize(self, text: str, voice_config: Dict, output_path: str) -> bool:
        """
        合成单段语音
        
        Args:
            text: 要合成的文本
            voice_config: 音色配置
            output_path: 输出文件路径
        
        Returns:
            bool: 是否成功
        """
        # 构建 API URL
        url = f"{self.base_url}/v1/t2a_v2"
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        # 构建 voice_setting
        voice_setting = {
            "voice_id": voice_config.get('voice_id', 'Chinese (Mandarin)_Reliable_Executive'),
            "speed": voice_config.get('speed', 1.0),
            "vol": voice_config.get('vol', 1.0),
            "pitch": voice_config.get('pitch', 0)
        }
        
        # 添加 emotion 参数（如果配置中有）
        if 'emotion' in voice_config:
            voice_setting['emotion'] = voice_config['emotion']
        
        # 构建请求体
        payload = {
            "model": self.model,
            "text": text,
            "stream": False,
            "voice_setting": voice_setting,
            "audio_setting": {
                "sample_rate": voice_config.get('sample_rate', 32000),
                "bitrate": voice_config.get('bitrate', 128000),
                "format": voice_config.get('format', 'mp3'),
                "channel": voice_config.get('channel', 1)
            }
        }
        
        # 可选参数
        if 'language_boost' in voice_config:
            payload['language_boost'] = voice_config['language_boost']
        
        if 'pronunciation_dict' in voice_config:
            payload['pronunciation_dict'] = voice_config['pronunciation_dict']
        
        if 'voice_modify' in voice_config:
            payload['voice_modify'] = voice_config['voice_modify']
        
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=120)
            response.raise_for_status()
            
            result = response.json()
            
            # 解析响应获取音频数据
            if 'data' in result and 'audio' in result['data']:
                audio_hex = result['data']['audio']
                # 移除可能的 0x 前缀
                if audio_hex.startswith('0x'):
                    audio_hex = audio_hex[2:]
                audio_bytes = bytes.fromhex(audio_hex)
                
                with open(output_path, 'wb') as f:
                    f.write(audio_bytes)
                return True
            else:
                # 检查错误信息
                if 'base_resp' in result and result['base_resp'].get('status_code') != 0:
                    error_msg = result['base_resp'].get('status_msg', 'Unknown error')
                    # 识别 rate limit 错误
                    if 'rate limit' in error_msg.lower() or 'rpm' in error_msg.lower():
                        print(f"API 错误: {error_msg} (需要增加 rate_limit.delay)")
                    else:
                        print(f"API 错误: {error_msg}")
                else:
                    print(f"API 响应异常: {result}")
                return False
                
        except requests.exceptions.RequestException as e:
            print(f"API 请求失败: {e}")
            return False
        except Exception as e:
            print(f"合成失败: {e}")
            return False
    
    def synthesize_streaming(self, text: str, voice_config: Dict, output_path: str) -> bool:
        """
        流式合成语音（适用于长文本）
        """
        url = f"{self.base_url}/v1/t2a_v2"
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        # 构建 voice_setting
        voice_setting = {
            "voice_id": voice_config.get('voice_id', 'Chinese (Mandarin)_Reliable_Executive'),
            "speed": voice_config.get('speed', 1.0),
            "vol": voice_config.get('vol', 1.0),
            "pitch": voice_config.get('pitch', 0)
        }
        
        # 添加 emotion 参数（如果配置中有）
        if 'emotion' in voice_config:
            voice_setting['emotion'] = voice_config['emotion']
        
        payload = {
            "model": self.model,
            "text": text,
            "stream": True,
            "voice_setting": voice_setting,
            "audio_setting": {
                "sample_rate": voice_config.get('sample_rate', 32000),
                "bitrate": voice_config.get('bitrate', 128000),
                "format": voice_config.get('format', 'mp3'),
                "channel": voice_config.get('channel', 1)
            }
        }
        
        try:
            response = requests.post(url, headers=headers, json=payload, stream=True, timeout=120)
            response.raise_for_status()
            
            audio_chunks = []
            for line in response.iter_lines():
                if line:
                    try:
                        data = json.loads(line.decode('utf-8'))
                        if 'data' in data and 'audio' in data['data']:
                            audio_hex = data['data']['audio']
                            if audio_hex.startswith('0x'):
                                audio_hex = audio_hex[2:]
                            audio_bytes = bytes.fromhex(audio_hex)
                            audio_chunks.append(audio_bytes)
                    except:
                        pass
            
            if audio_chunks:
                with open(output_path, 'wb') as f:
                    for chunk in audio_chunks:
                        f.write(chunk)
                return True
            return False
            
        except Exception as e:
            print(f"流式合成失败: {e}")
            return False


class SiliconFlowTTSClient(BaseTTSClient):
    """硅基流动 SiliconFlow TTS API 客户端
    
    支持模型:
    - IndexTeam/IndexTTS-2 (IndexTTS2, B站开源)
      * 支持情绪控制: emo_vector (Neutral, Happy, Sad, Angry, Fearful, Disgusted, Surprised)
      * 支持情感强度: emo_alpha (0.0 ~ 1.0)
      * 支持情感参考音频: emo_audio_prompt
    - FunAudioLLM/CosyVoice2-0.5B (阿里CosyVoice)
    - fnlp/MOSS-TTSD-v0.5 (复旦大学MOSS对话TTS)
    """
    
    # IndexTTS2 支持的情绪向量
    INDEXTTS_EMOTIONS = ['Neutral', 'Happy', 'Sad', 'Angry', 'Fearful', 'Disgusted', 'Surprised']
    
    # 我们的情绪 -> IndexTTS2 情绪映射
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
    
    def __init__(self, config: Dict):
        self.config = config
        self.api_key = config['api']['api_key']
        self.model = config['api'].get('model', 'IndexTeam/IndexTTS-2')
        self.base_url = config['api']['base_url']
        
        # 检查 API Key
        if self.api_key == "YOUR_API_KEY_HERE" or not self.api_key:
            raise ValueError("请在 config.yaml 中设置有效的 API Key")
        
        # 检测是否为 MOSS-TTSD 模型
        self.is_moss_model = 'MOSS-TTSD' in self.model
        
        # 检测是否为 IndexTTS2 模型
        self.is_indextts_model = 'IndexTTS' in self.model
    
    def synthesize(self, text: str, voice_config: Dict, output_path: str) -> bool:
        """
        合成单段语音 (OpenAI 兼容接口)
        
        Args:
            text: 要合成的文本
            voice_config: 音色配置
            output_path: 输出文件路径
        
        Returns:
            bool: 是否成功
        """
        url = f"{self.base_url}/v1/audio/speech"
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        # 构建音色标识
        voice = voice_config.get('voice', '')
        if voice and not voice.startswith(self.model):
            # 如果不是完整路径，添加模型前缀
            voice = f"{self.model}:{voice}"
        
        # 基础请求体
        payload = {
            "model": self.model,
            "input": text,
            "voice": voice,
            "response_format": voice_config.get('response_format', 'wav'),
        }
        
        # 可选参数
        if 'speed' in voice_config:
            payload['speed'] = voice_config['speed']
        
        if 'gain' in voice_config:
            payload['gain'] = voice_config['gain']
        
        if 'sample_rate' in voice_config:
            payload['sample_rate'] = voice_config['sample_rate']
        
        # 动态音色/参考音频 (用于声音克隆)
        if 'references' in voice_config:
            payload['references'] = voice_config['references']
        
        # IndexTTS2 情绪控制参数
        if self.is_indextts_model:
            # emo_vector: 情绪向量 (Neutral, Happy, Sad, Angry, Fearful, Disgusted, Surprised)
            if 'emo_vector' in voice_config:
                payload['emo_vector'] = voice_config['emo_vector']
            
            # emo_alpha: 情感强度 (0.0 ~ 1.0, 默认 0.7)
            if 'emo_alpha' in voice_config:
                payload['emo_alpha'] = voice_config['emo_alpha']
            
            # emo_audio_prompt: 情感参考音频 (base64 或 URL)
            if 'emo_audio_prompt' in voice_config:
                payload['emo_audio_prompt'] = voice_config['emo_audio_prompt']
            
            # use_emo_text: 是否使用情感文本提示
            if 'use_emo_text' in voice_config:
                payload['use_emo_text'] = voice_config['use_emo_text']
        
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=120)
            response.raise_for_status()
            
            # 直接获取二进制音频数据
            if response.content:
                with open(output_path, 'wb') as f:
                    f.write(response.content)
                return True
            else:
                print(f"警告: 响应中没有音频数据")
                return False
                
        except requests.exceptions.RequestException as e:
            # 尝试解析错误响应
            try:
                error_data = response.json() if response.text else {}
                error_msg = error_data.get('error', {}).get('message', str(e))
                print(f"API 请求失败: {error_msg}")
            except:
                print(f"API 请求失败: {e}")
            return False
        except Exception as e:
            print(f"合成失败: {e}")
            return False
    
    def synthesize_dialogue(self, dialogues: List[DialogueLine], voice_config: Dict, output_path: str) -> bool:
        """
        MOSS-TTSD 专用：一次性合成双人对话
        
        Args:
            dialogues: 对话列表
            voice_config: 音色配置 (包含两个说话人的 references)
            output_path: 输出文件路径
        
        Returns:
            bool: 是否成功
        """
        if not self.is_moss_model:
            print("警告: 当前不是 MOSS-TTSD 模型，无法使用对话合成功能")
            return False
        
        url = f"{self.base_url}/v1/audio/speech"
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        # 构建带 [S1]/[S2] 标签的对话文本
        # male -> [S1], female -> [S2]
        dialogue_text = ""
        for dialogue in dialogues:
            speaker_tag = "[S1]" if dialogue.speaker == 'male' else "[S2]"
            dialogue_text += f"{speaker_tag}{dialogue.text}"
        
        print(f"  合成双人对话，共 {len(dialogues)} 轮对话...")
        print(f"  文本长度: {len(dialogue_text)} 字符")
        
        # 构建请求体
        payload = {
            "model": self.model,
            "input": dialogue_text,
            "response_format": voice_config.get('response_format', 'wav'),
        }
        
        # MOSS-TTSD 需要通过 references 指定两个说话人的声音
        # 而不是使用 voice 字段
        if 'references' in voice_config:
            payload['references'] = voice_config['references']
        else:
            # 如果没有提供 references，使用系统预置音色
            # 需要构建两个 references 项
            voice = voice_config.get('voice', 'fnlp/MOSS-TTSD-v0.5:alex')
            # 提取基本音色名
            if ':' in voice:
                voice_name = voice.split(':')[-1]
            else:
                voice_name = 'alex'
            
            # 为 S1 和 S2 分配不同音色（如果可能）
            male_voices = ['alex', 'benjamin', 'charles', 'david']
            female_voices = ['anna', 'bella', 'claire', 'diana']
            
            # 默认使用 alex 和 anna 作为 S1 和 S2
            s1_voice = voice_name if voice_name in male_voices else 'alex'
            s2_voice = 'anna'  # 默认女声
            
            # 使用默认参考音频 URL（SiliconFlow 提供的示例）
            payload['references'] = [
                {
                    "audio": f"https://sf-maas-uat-prod.oss-cn-shanghai.aliyuncs.com/voice_template/fish_audio-{s1_voice.capitalize()}.mp3",
                    "text": "在一无所知中，梦里的一天结束了，一个新的轮回便会开始"
                },
                {
                    "audio": f"https://sf-maas-uat-prod.oss-cn-shanghai.aliyuncs.com/voice_template/fish_audio-{s2_voice.capitalize()}.mp3",
                    "text": "在一无所知中，梦里的一天结束了，一个新的轮回便会开始"
                }
            ]
        
        # 可选参数
        if 'speed' in voice_config:
            payload['speed'] = voice_config['speed']
        
        if 'gain' in voice_config:
            payload['gain'] = voice_config['gain']
        
        if 'max_tokens' in voice_config:
            payload['max_tokens'] = voice_config['max_tokens']
        
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=180)
            response.raise_for_status()
            
            # 直接获取二进制音频数据
            if response.content:
                with open(output_path, 'wb') as f:
                    f.write(response.content)
                print(f"  ✓ 双人对话音频已生成: {output_path}")
                return True
            else:
                print(f"  ✗ 警告: 响应中没有音频数据")
                return False
                
        except requests.exceptions.RequestException as e:
            try:
                error_data = response.json() if response.text else {}
                error_msg = error_data.get('error', {}).get('message', str(e))
                print(f"  ✗ API 请求失败: {error_msg}")
            except:
                print(f"  ✗ API 请求失败: {e}")
            return False
        except Exception as e:
            print(f"  ✗ 合成失败: {e}")
            return False


class MarkdownParser:
    """Markdown 对话文件解析器"""
    
    # 支持的情绪列表
    MOODS = ['gentle', 'happy', 'confident', 'expectant', 'confused', 
             'shocked', 'angry', 'sad', 'resigned']
    
    def __init__(self, config: Dict):
        self.config = config
        # 是否启用情绪功能，默认开启
        self.enable_mood = config.get('mood', {}).get('enable', True)
        # 是否使用 Markdown 中的情绪参数，默认开启
        self.use_emotion = config.get('emotion', {}).get('use_emotion', True)
        # 默认情绪
        self.default_emotion = config.get('emotion', {}).get('default_emotion', 'gentle')
    
    def parse(self, file_path: str) -> List[DialogueLine]:
        """
        解析 Markdown 文件，提取对话内容
        
        格式 (带情绪):
        ### male speaker ###
        ### happy ###
        ### 文本内容 ###
        
        格式 (无情绪，向后兼容):
        ### male speaker ###
        ### 文本内容 ###
        """
        dialogues = []
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 检测是否使用新格式（包含情绪标注）
        # 新格式: ### speaker ### \n ### mood ### \n ### text ###
        new_pattern = r'###\s*(male|female)\s*speaker\s*###\s*\n\s*###\s*(\w+)\s*###\s*\n\s*###\s*(.*?)\s*###'
        new_matches = re.findall(new_pattern, content, re.DOTALL)
        
        # 旧格式: ### speaker ### \n ### text ###
        old_pattern = r'###\s*(male|female)\s*speaker\s*###\s*\n\s*###\s*(.*?)\s*###'
        old_matches = re.findall(old_pattern, content, re.DOTALL)
        
        # 如果新格式匹配成功且数量合理（约为旧格式的一半或更少，说明中间插入了mood行）
        if new_matches and len(new_matches) >= len(old_matches) / 2:
            # 使用新格式解析
            for idx, (speaker, mood, text) in enumerate(new_matches, 1):
                # 验证情绪是否有效
                mood = mood.lower()
                if mood not in self.MOODS:
                    mood = self.default_emotion  # 使用默认情绪
                
                # 如果配置为不使用情绪参数，则使用默认情绪
                if not self.use_emotion:
                    mood = self.default_emotion
                
                text = self._clean_text(text)
                if text:
                    dialogues.append(DialogueLine(
                        speaker=speaker.lower(),
                        text=text,
                        index=idx,
                        mood=mood
                    ))
        else:
            # 使用旧格式解析
            default_mood = self.default_emotion if not self.use_emotion else "gentle"
            for idx, (speaker, text) in enumerate(old_matches, 1):
                text = self._clean_text(text)
                if text:
                    dialogues.append(DialogueLine(
                        speaker=speaker.lower(),
                        text=text,
                        index=idx,
                        mood=default_mood
                    ))
        
        return dialogues
    
    def _clean_text(self, text: str) -> str:
        """清理和预处理文本"""
        # 移除换行符
        text = text.replace('\n', ' ')
        
        # 移除多余空格
        text = re.sub(r'\s+', ' ', text).strip()
        
        # 移除括号内容（如: （打断））
        if self.config['text_processing'].get('remove_parentheses', True):
            text = re.sub(r'[（(][^）)]+[）)]', '', text)
        
        # 替换 Figure X 为中文
        if self.config['text_processing'].get('localize_figures', True):
            text = re.sub(r'Figure\s*(\d+)', r'图\1', text, flags=re.IGNORECASE)
        
        # 清理多余空格
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text
    
    def split_long_text(self, text: str, max_length: int = 500) -> List[str]:
        """将长文本分段"""
        if len(text) <= max_length:
            return [text]
        
        segments = []
        current = ""
        
        # 按句子分割
        sentences = re.split(r'([。！？.!?])', text)
        
        for i in range(0, len(sentences) - 1, 2):
            sentence = sentences[i] + (sentences[i+1] if i+1 < len(sentences) else "")
            
            if len(current) + len(sentence) > max_length:
                if current:
                    segments.append(current.strip())
                current = sentence
            else:
                current += sentence
        
        if current:
            segments.append(current.strip())
        
        return segments


class AudioMerger:
    """音频合并工具"""
    
    @staticmethod
    def merge_wav_files(file_list: List[str], output_path: str, silence_duration: float = 0.5):
        """
        合并多个 WAV 文件，在片段间添加静音
        
        Args:
            file_list: WAV 文件列表
            output_path: 输出文件路径
            silence_duration: 静音时长（秒）
        """
        if not file_list:
            return
        
        # 读取第一个文件获取参数
        with wave.open(file_list[0], 'rb') as wf:
            n_channels = wf.getnchannels()
            sample_width = wf.getsampwidth()
            frame_rate = wf.getframerate()
        
        # 生成静音数据
        silence_frames = int(frame_rate * silence_duration)
        silence_data = b'\x00' * (silence_frames * sample_width * n_channels)
        
        # 合并所有文件
        with wave.open(output_path, 'wb') as output:
            output.setnchannels(n_channels)
            output.setsampwidth(sample_width)
            output.setframerate(frame_rate)
            
            for i, file_path in enumerate(file_list):
                with wave.open(file_path, 'rb') as wf:
                    output.writeframes(wf.readframes(wf.getnframes()))
                
                # 在片段间添加静音（最后一个除外）
                if i < len(file_list) - 1:
                    output.writeframes(silence_data)


class TTSGenerator:
    """语音合成主类"""
    
    # 情绪到 TTS 参数的映射
    # 不同提供商支持的情绪参数不同：
    # - MiniMax: 支持 emotion 参数 (happy, sad, angry, fearful, disgusted, surprised, neutral)
    #            同时支持 speed, pitch(整数), vol
    # - Qwen: 使用 instruction 文本描述
    # - SiliconFlow: 部分模型不支持 pitch/emotion，使用 speed 调节
    MOOD_TO_TTS = {
        'gentle': {'speed': 1.0, 'pitch': 0, 'vol': 1.0, 'emotion': 'neutral', 'instruction': '语速适中，语气温柔平和'},
        'happy': {'speed': 1.1, 'pitch': 2, 'vol': 1.0, 'emotion': 'happy', 'instruction': '语速稍快，语气轻快愉悦'},
        'confident': {'speed': 1.0, 'pitch': 0, 'vol': 1.1, 'emotion': 'neutral', 'instruction': '语速适中，语气坚定自信'},
        'expectant': {'speed': 1.1, 'pitch': 4, 'vol': 1.0, 'emotion': 'happy', 'instruction': '语速稍快，语气充满期待和好奇'},
        'confused': {'speed': 0.9, 'pitch': 2, 'vol': 1.0, 'emotion': 'surprised', 'instruction': '语速稍慢，语气带有疑问和困惑'},
        'shocked': {'speed': 1.2, 'pitch': 8, 'vol': 1.1, 'emotion': 'surprised', 'instruction': '语速较快，语气惊讶震惊'},
        'angry': {'speed': 1.2, 'pitch': -4, 'vol': 1.2, 'emotion': 'angry', 'instruction': '语速较快，语气愤怒不满'},
        'sad': {'speed': 0.8, 'pitch': -6, 'vol': 0.9, 'emotion': 'sad', 'instruction': '语速较慢，语气悲伤低沉'},
        'resigned': {'speed': 1.0, 'pitch': -2, 'vol': 1.0, 'emotion': 'sad', 'instruction': '语速适中，语气无奈平淡'},
    }
    
    def __init__(self, config_path: str = "configs/config.yaml"):
        # 加载配置
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)
        
        # 是否启用情绪功能，默认开启
        self.enable_mood = self.config.get('mood', {}).get('enable', True)
        # 是否使用 Markdown 中的情绪参数，默认开启
        self.use_emotion = self.config.get('emotion', {}).get('use_emotion', True)
        # 默认情绪
        self.default_emotion = self.config.get('emotion', {}).get('default_emotion', 'gentle')
        # 当 use_emotion 为 false 时，是否传递 speed/pitch/vol 参数
        self.pass_voice_params = self.config.get('emotion', {}).get('pass_voice_params', False)
        
        if self.enable_mood:
            if self.use_emotion:
                print("✨ 情绪功能已启用（使用文本标注的情绪）")
            else:
                if self.pass_voice_params:
                    print("✨ 情绪功能已启用（API 自动判断情绪，保留音色参数）")
                else:
                    print("✨ 情绪功能已启用（API 完全自动判断）")
        else:
            print("ℹ️ 情绪功能已禁用")
        
        # 初始化 TTS 客户端
        provider = self.config.get('provider', 'qwen').lower()
        
        if provider == 'siliconflow':
            self.client = SiliconFlowTTSClient(self.config)
            print(f"使用提供商: 硅基流动 (SiliconFlow) - 模型: {self.config.get('api', {}).get('model', 'IndexTeam/IndexTTS-2')}")
        elif provider == 'qwen':
            self.client = QwenTTSClient(self.config)
            print(f"使用提供商: 阿里云百炼 (Qwen)")
        elif provider == 'minimax':
            self.client = MiniMaxTTSClient(self.config)
            print(f"使用提供商: MiniMax - 模型: {self.config.get('api', {}).get('model', 'speech-2.6-hd')}")
        else:
            raise ValueError(f"不支持的 TTS 提供商: {provider}，请使用 'qwen'、'siliconflow' 或 'minimax'")
        
        # 初始化其他组件
        self.parser = MarkdownParser(self.config)
        self.merger = AudioMerger()
        
        # 创建输出目录
        base_output_dir = Path(self.config['output']['output_dir'])
        
        # 检查是否使用时间编号子文件夹
        use_timestamp_subdir = self.config['output'].get('use_timestamp_subdir', False)
        if use_timestamp_subdir:
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.output_dir = base_output_dir / timestamp
        else:
            self.output_dir = base_output_dir
        
        self.output_dir.mkdir(parents=True, exist_ok=True)
        print(f"📁 输出目录: {self.output_dir.absolute()}")
    
    def generate(self, markdown_path: str):
        """
        生成语音
        
        Args:
            markdown_path: Markdown 文件路径
        """
        print(f"正在解析文件: {markdown_path}")
        dialogues = self.parser.parse(markdown_path)
        print(f"共解析到 {len(dialogues)} 段对话")
        
        if not dialogues:
            print("未找到对话内容，请检查文件格式")
            return
        
        # 检测是否为 MOSS-TTSD 模型（双人对话模式）
        if isinstance(self.client, SiliconFlowTTSClient) and self.client.is_moss_model:
            self._generate_moss_dialogue(dialogues)
        else:
            self._generate_standard(dialogues)
    
    def _generate_moss_dialogue(self, dialogues: List[DialogueLine]):
        """
        MOSS-TTSD 专用：一次性生成双人对话
        """
        print(f"\n🎭 使用 MOSS-TTSD 双人对话模式")
        print(f"   将 {len(dialogues)} 段对话一次性合成...")
        
        audio_files = []
        failed_count = 0
        
        # 生成输出文件名
        filename = f"{self.config['output']['prefix']}_dialogue_combined.wav"
        output_path = self.output_dir / filename
        
        # 检查是否已存在
        if output_path.exists() and output_path.stat().st_size > 0:
            print(f"✓ 已存在: {filename}")
            audio_files.append(str(output_path))
        else:
            # 获取 male 配置的音色（包含 references）
            voice_config = self.config['voices']['male']
            
            # 一次性合成整个对话
            success = self.client.synthesize_dialogue(dialogues, voice_config, str(output_path))
            
            if success:
                audio_files.append(str(output_path))
            else:
                failed_count += 1
        
        print(f"\n{'='*50}")
        print(f"生成完成!")
        print(f"成功: {len(audio_files)} 个对话音频")
        if failed_count > 0:
            print(f"失败: {failed_count}")
        print(f"输出目录: {self.output_dir.absolute()}")
    
    def _generate_standard(self, dialogues: List[DialogueLine]):
        """
        标准模式：逐段合成语音
        """
        audio_files = []
        failed_count = 0
        
        # 获取速率限制配置
        rate_limit = self.config.get('rate_limit', {})
        delay = rate_limit.get('delay', 0.3)  # 默认 0.3 秒
        max_retries = rate_limit.get('max_retries', 0)
        retry_delay = rate_limit.get('retry_delay', 5.0)
        
        for dialogue in dialogues:
            # 生成文件名
            filename = f"{self.config['output']['prefix']}_{dialogue.index:03d}_{dialogue.speaker}.wav"
            output_path = self.output_dir / filename
            
            # 检查是否已存在
            if output_path.exists() and output_path.stat().st_size > 0:
                print(f"[{dialogue.index}/{len(dialogues)}] ✓ 已存在: {filename}")
                audio_files.append(str(output_path))
                continue
            
            print(f"[{dialogue.index}/{len(dialogues)}] {dialogue.speaker}: {dialogue.text[:40]}...")
            
            # 获取音色配置
            voice_config = self.config['voices'][dialogue.speaker].copy()
            
            # 如果启用情绪功能，应用情绪参数
            if self.enable_mood and dialogue.mood in self.MOOD_TO_TTS:
                mood_params = self.MOOD_TO_TTS[dialogue.mood]
                # 根据提供商应用不同的参数
                provider = self.config.get('provider', 'qwen').lower()
                
                if provider == 'minimax':
                    # MiniMax 支持 emotion 参数 (happy, sad, angry, fearful, disgusted, surprised, neutral)
                    # 同时支持 speed, pitch(整数), vol
                    if self.use_emotion:
                        # 使用文本标注的情绪参数
                        voice_config['speed'] = mood_params['speed']
                        voice_config['pitch'] = int(mood_params['pitch'])
                        voice_config['vol'] = mood_params['vol']
                        voice_config['emotion'] = mood_params['emotion']
                        print(f"  [MiniMax 情绪: {mood_params['emotion']}]")
                    else:
                        # 不传递情绪参数，让 MiniMax 自动判断
                        if self.pass_voice_params:
                            # 只传递 speed/pitch/vol，让 API 自动判断情绪
                            voice_config['speed'] = mood_params['speed']
                            voice_config['pitch'] = int(mood_params['pitch'])
                            voice_config['vol'] = mood_params['vol']
                            print("  [MiniMax 自动判断情绪，使用配置音色参数]")
                        else:
                            # 完全不传递情绪相关参数，让 API 完全自动判断
                            print("  [MiniMax 完全自动判断情绪和音色]")
                elif provider == 'siliconflow':
                    # SiliconFlow 不同模型支持不同的情绪参数
                    model = self.config.get('api', {}).get('model', '')
                    
                    if self.use_emotion:
                        # IndexTTS2 支持 emo_vector 等情绪参数
                        if 'IndexTTS' in model:
                            # IndexTTS2 情绪映射
                            indextts_emotion = SiliconFlowTTSClient.MOOD_TO_INDEXTTS.get(dialogue.mood, 'Neutral')
                            voice_config['emo_vector'] = indextts_emotion
                            # 情感强度 (0.0 ~ 1.0)
                            voice_config['emo_alpha'] = 0.7
                            # 语速
                            voice_config['speed'] = mood_params['speed']
                            print(f"  [IndexTTS2 情绪: {indextts_emotion}]")
                        else:
                            # 其他模型仅使用 speed
                            voice_config['speed'] = mood_params['speed']
                    else:
                        if self.pass_voice_params:
                            # 只传递 speed，让 API 自动判断情绪
                            voice_config['speed'] = mood_params['speed']
                            print("  [SiliconFlow 自动判断情绪，使用配置语速]")
                        else:
                            print("  [SiliconFlow 完全自动判断情绪和音色]")
                elif provider == 'qwen':
                    # Qwen 使用 instructions 控制风格
                    if self.use_emotion:
                        if 'instructions' in voice_config:
                            # 在原有指令基础上添加情绪描述
                            base_instruction = voice_config['instructions']
                            voice_config['instructions'] = f"{base_instruction}，{mood_params['instruction']}"
                        else:
                            voice_config['instructions'] = mood_params['instruction']
                        # 标记需要优化指令
                        voice_config['optimize_instructions'] = True
                        print(f"  [Qwen 情绪: {dialogue.mood}]")
                    else:
                        if self.pass_voice_params and 'instructions' in voice_config:
                            # 保留原有指令，不添加情绪描述
                            print("  [Qwen 自动判断情绪，使用配置音色]")
                        else:
                            # 清除指令，让 API 完全自动判断
                            if 'instructions' in voice_config:
                                del voice_config['instructions']
                            print("  [Qwen 完全自动判断情绪和音色]")
            
            # 分段处理长文本
            max_length = self.config['text_processing'].get('max_text_length', 500)
            segments = self.parser.split_long_text(dialogue.text, max_length)
            
            segment_files = []
            for seg_idx, segment in enumerate(segments):
                if len(segments) == 1:
                    seg_filename = filename
                else:
                    seg_filename = f"{self.config['output']['prefix']}_{dialogue.index:03d}_{dialogue.speaker}_part{seg_idx+1}.wav"
                
                seg_path = self.output_dir / seg_filename
                
                # 合成语音（带重试机制）
                success = False
                retries = 0
                while not success and retries <= max_retries:
                    if retries > 0:
                        wait_time = retry_delay * retries
                        print(f"  等待 {wait_time:.0f} 秒后重试...")
                        time.sleep(wait_time)
                    
                    success = self.client.synthesize(segment, voice_config, str(seg_path))
                    
                    if not success and retries < max_retries:
                        retries += 1
                    else:
                        break
                
                if success:
                    segment_files.append(str(seg_path))
                    # 请求间隔延迟（避免触发 rate limit）
                    time.sleep(delay)
                else:
                    failed_count += 1
            
            # 合并分段
            if len(segment_files) > 1:
                merged_path = self.output_dir / filename
                self.merger.merge_wav_files(segment_files, str(merged_path), silence_duration=0.2)
                audio_files.append(str(merged_path))
                # 删除临时分段文件
                for f in segment_files:
                    if os.path.exists(f):
                        os.remove(f)
            elif segment_files:
                audio_files.append(segment_files[0])
                print(f"  ✓ 已生成: {filename}")
            else:
                failed_count += 1
                print(f"  ✗ 生成失败")
        
        print(f"\n{'='*50}")
        print(f"生成完成!")
        print(f"成功: {len(audio_files)} 段")
        print(f"失败: {failed_count} 段")
        print(f"输出目录: {self.output_dir.absolute()}")
        
        # 合并所有音频
        if self.config['output'].get('merge_audio', True) and len(audio_files) > 1:
            final_path = self.output_dir / f"{self.config['output']['prefix']}_complete.wav"
            if final_path.exists():
                print(f"合并文件已存在: {final_path.name}")
            else:
                print("正在合并所有音频...")
                silence = self.config['output'].get('silence_between', 0.5)
                self.merger.merge_wav_files(audio_files, str(final_path), silence)
                print(f"合并完成: {final_path.name}")


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='TTS 语音合成工具 - 将 Markdown 对话转换为语音',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 基本使用
  python tts_generator.py 文献解读对话文案-2.md
  
  # 指定自定义配置
  python tts_generator.py 文献.md -c my_config.yaml
  
  # 批量处理多个文件
  for f in *.md; do python tts_generator.py "$f"; done

支持的 TTS 提供商:
  • qwen         - 阿里云百炼 Qwen-TTS
  • siliconflow  - 硅基流动 SiliconFlow (支持 IndexTTS2, CosyVoice2-0.5B, MOSS-TTSD 等)
  • minimax      - MiniMax Speech (支持 speech-2.6-hd, speech-2.6-turbo 等)

相关脚本:
  tts_batch.py          - 分批生成，支持断点续传
  video_generator.py    - 将生成的音频转换为视频播客
        """
    )
    
    parser.add_argument(
        'input', 
        nargs='?', 
        default='ADAR1文献解读对话文案.md',
        help='输入的 Markdown 文件路径 (默认: ADAR1文献解读对话文案.md)'
    )
    parser.add_argument(
        '-c', '--config', 
        default='configs/config.yaml',
        help='配置文件路径 (默认: configs/config.yaml)'
    )
    
    args = parser.parse_args()
    
    # 检查输入文件
    if not os.path.exists(args.input):
        print(f"错误: 找不到输入文件 '{args.input}'")
        return
    
    # 检查配置文件
    if not os.path.exists(args.config):
        print(f"错误: 找不到配置文件 '{args.config}'")
        return
    
    # 生成语音
    try:
        generator = TTSGenerator(args.config)
        generator.generate(args.input)
    except ValueError as e:
        print(f"配置错误: {e}")
    except Exception as e:
        print(f"运行错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
