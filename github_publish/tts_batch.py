#!/usr/bin/env python3
"""
分批生成语音 - 用于断点续传或测试
"""

import sys
import os

# 导入主程序
from tts_generator import TTSGenerator

def generate_batch(start: int = 1, end: int = None):
    """
    生成指定范围的对话
    
    Args:
        start: 起始序号（从1开始）
        end: 结束序号（包含，None表示到最后）
    """
    config_path = "config.yaml"
    markdown_path = "ADAR1文献解读对话文案.md"
    
    # 初始化
    generator = TTSGenerator(config_path)
    
    # 解析对话
    print(f"正在解析文件: {markdown_path}")
    from tts_generator import MarkdownParser
    parser = MarkdownParser(generator.config)
    dialogues = parser.parse(markdown_path)
    
    total = len(dialogues)
    end = end or total
    
    print(f"总共 {total} 段，本次生成范围: {start} - {end}")
    print("="*50)
    
    # 过滤指定范围
    target_dialogues = [d for d in dialogues if start <= d.index <= end]
    
    # 生成
    from tts_generator import QwenTTSClient, AudioMerger
    import time
    
    client = QwenTTSClient(generator.config)
    merger = AudioMerger()
    output_dir = generator.output_dir
    
    audio_files = []
    failed_count = 0
    
    for dialogue in target_dialogues:
        filename = f"{generator.config['output']['prefix']}_{dialogue.index:03d}_{dialogue.speaker}.wav"
        output_path = output_dir / filename
        
        # 检查是否已存在
        if output_path.exists() and output_path.stat().st_size > 0:
            print(f"[{dialogue.index}/{total}] ✓ 已存在，跳过: {filename}")
            audio_files.append(str(output_path))
            continue
        
        print(f"[{dialogue.index}/{total}] 生成中: {dialogue.speaker} - {dialogue.text[:30]}...")
        
        voice_config = generator.config['voices'][dialogue.speaker]
        success = client.synthesize(dialogue.text, voice_config, str(output_path))
        
        if success:
            print(f"  ✓ 完成: {filename}")
            audio_files.append(str(output_path))
            time.sleep(0.3)
        else:
            print(f"  ✗ 失败")
            failed_count += 1
    
    print("\n" + "="*50)
    print(f"批次完成！成功: {len(audio_files)} 段, 失败: {failed_count} 段")

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='分批生成语音')
    parser.add_argument('--start', type=int, default=1, help='起始序号（默认: 1）')
    parser.add_argument('--end', type=int, default=None, help='结束序号（默认: 最后）')
    
    args = parser.parse_args()
    generate_batch(args.start, args.end)
