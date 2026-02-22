#!/usr/bin/env python3
"""
视频播客生成器 - 将音频转换为带字幕的视频播客
支持字幕、说话人标签、渐变背景等功能

╔══════════════════════════════════════════════════════════════════╗
║  使用方法:                                                        ║
║    python video_generator.py [选项]                               ║
╠══════════════════════════════════════════════════════════════════╣
║  依赖安装:                                                        ║
║    pip install moviepy Pillow numpy                              ║
║    # macOS 需要 ffmpeg: brew install ffmpeg                      ║
╠══════════════════════════════════════════════════════════════════╣
║  常用命令:                                                        ║
║    # 基础用法 (使用渐变背景)                                      ║
║    python video_generator.py -i audio_output -o podcast.mp4      ║
║                                                                   ║
║    # 指定 Markdown 文件 (用于提取字幕文本)                        ║
║    python video_generator.py -i audio_output -m 文案.md -o output.mp4
║                                                                   ║
║    # 使用纯色背景                                                 ║
║    python video_generator.py -i audio -o out.mp4 -b color        ║
║                                                                   ║
║    # 使用自定义背景图片                                           ║
║    python video_generator.py -i audio -o out.mp4 -b image --bg-path bg.jpg
╠══════════════════════════════════════════════════════════════════╣
║  背景类型说明:                                                    ║
║    • gradient (默认) - 蓝/紫渐变色，男声蓝色、女声紫色           ║
║    • color           - 纯色背景                                   ║
║    • image           - 自定义图片背景                             ║
╚══════════════════════════════════════════════════════════════════╝
"""

import os
import re
import yaml
import time
import argparse
import tempfile
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass

# 优先使用系统 FFmpeg（Homebrew 安装的 FFmpeg 8.0+）
if os.path.exists('/opt/homebrew/bin/ffmpeg'):
    os.environ['IMAGEIO_FFMPEG_EXE'] = '/opt/homebrew/bin/ffmpeg'
    print(f"🎬 使用系统 FFmpeg: /opt/homebrew/bin/ffmpeg")

import numpy as np
from PIL import Image, ImageDraw, ImageFont
try:
    # moviepy 2.x
    from moviepy import (
        AudioFileClip, ImageClip, CompositeVideoClip, TextClip,
        concatenate_videoclips, ColorClip, concatenate_audioclips
    )
    from moviepy.video.fx import FadeIn, FadeOut
except ImportError:
    # moviepy 1.x
    from moviepy.editor import (
        AudioFileClip, ImageClip, CompositeVideoClip, TextClip,
        concatenate_videoclips, ColorClip, concatenate_audioclips
    )
    from moviepy.video.fx.all import fadein, fadeout


@dataclass
class DialogueSegment:
    """对话段落数据"""
    index: int
    speaker: str  # 'male' 或 'female'
    text: str
    audio_path: str
    duration: float
    mood: str = "gentle"  # 情绪: gentle, happy, confident, expectant, confused, shocked, angry, sad, resigned


class SubtitleGenerator:
    """字幕生成器"""
    
    # 支持的情绪列表
    MOODS = ['gentle', 'happy', 'confident', 'expectant', 'confused', 
             'shocked', 'angry', 'sad', 'resigned']
    
    def __init__(self, font_path: str = None, font_size: int = 40, style: str = "default", 
                 enable_mood: bool = True, avatar_base_path: str = "avatar",
                 galgame_avatar_config: Dict = None):
        self.font_size = font_size
        self.font_path = font_path or self._get_default_font()
        self.style = style  # "default" 或 "galgame"
        self.avatar_size = 100  # 头像尺寸
        self.enable_mood = enable_mood  # 是否启用情绪立绘
        self.avatar_base_path = avatar_base_path  # 立绘基础路径
        self.galgame_avatar_config = galgame_avatar_config or {}  # GalGame 立绘配置
        self.avatars = self._load_avatars()
        self.min_lines = 2  # 最少显示2行（保证字幕框有一定高度）
        self.max_lines = 6  # 最多显示6行（防止过长）
        self.line_height = 52  # 每行高度
        self.bg_padding = 40  # 字幕框上下边距
        
        # 字幕长度限制配置
        self.max_chars_per_screen = 80  # 每屏最多字符数（更严格的限制）
        self.max_subtitle_parts = 4  # 最多拆分几段
        self.min_chars_for_split = 60  # 超过这个长度才考虑拆分
    
    def split_long_text(self, text: str, video_width: int = 1920) -> List[Tuple[str, float]]:
        """
        将长文本拆分成多个适合屏幕显示的子字幕，并计算每段的相对时长
        
        策略：
        1. 如果文本较短，直接返回
        2. 优先按句子拆分（。！？；）
        3. 如果句子仍太长，按逗号或长度拆分
        4. 根据字符数和标点符号计算每段的相对时长
        
        Returns:
            [(子字幕文本, 相对时长比例), ...]
            相对时长比例总和为 1.0
        """
        # 使用配置的最大字符数限制
        max_chars_total = self.max_chars_per_screen
        
        # 如果文本不长，不需要拆分
        if len(text) <= self.min_chars_for_split:
            return [(text, 1.0)]
        
        parts = []
        remaining = text
        
        # 句子结束符
        sentence_ends = '。！？；'
        
        while remaining and len(parts) < self.max_subtitle_parts:
            # 尝试找到合适的拆分点
            cut_pos = self._find_cut_position(remaining, max_chars_total, sentence_ends)
            
            if cut_pos > 0:
                parts.append(remaining[:cut_pos].strip())
                remaining = remaining[cut_pos:].strip()
            else:
                # 找不到好的拆分点，强制按长度拆分
                cut_pos = min(max_chars_total, len(remaining))
                parts.append(remaining[:cut_pos])
                remaining = remaining[cut_pos:]
        
        # 如果还有剩余，合并到最后一段
        if remaining:
            if len(parts) < self.max_subtitle_parts:
                parts.append(remaining)
            else:
                parts[-1] = parts[-1] + remaining
        
        if not parts:
            return [(text, 1.0)]
        
        # 计算每段的相对时长（基于字符数 + 标点停顿）
        part_weights = []
        for part in parts:
            weight = self._calculate_part_weight(part)
            part_weights.append(weight)
        
        # 归一化得到时间比例
        total_weight = sum(part_weights)
        result = []
        for part, weight in zip(parts, part_weights):
            ratio = weight / total_weight if total_weight > 0 else 1.0 / len(parts)
            result.append((part, ratio))
        
        return result
    
    def _calculate_part_weight(self, text: str) -> float:
        """
        计算文本段的朗读权重
        
        基于：
        - 基础字符数（每个字符算 1）
        - 标点符号增加停顿时间
        """
        # 基础权重 = 字符数
        weight = len(text)
        
        # 句子结束符增加停顿（相当于 0.5 个字符时间）
        weight += text.count('。') * 0.5
        weight += text.count('！') * 0.5
        weight += text.count('？') * 0.5
        weight += text.count('；') * 0.5
        
        # 逗号增加短停顿（相当于 0.3 个字符时间）
        weight += text.count('，') * 0.3
        weight += text.count('、') * 0.2
        
        return max(weight, 1.0)  # 至少 1.0 的权重
    
    def _find_cut_position(self, text: str, max_len: int, sentence_ends: str) -> int:
        """找到最佳拆分位置"""
        # 限制搜索范围
        search_end = min(len(text), max_len)
        
        # 1. 优先找句子结束符
        for i in range(search_end - 1, -1, -1):
            if text[i] in sentence_ends:
                return i + 1
        
        # 2. 其次找逗号
        for i in range(search_end - 1, -1, -1):
            if text[i] in '，,':
                return i + 1
        
        # 3. 找空格（英文）
        for i in range(search_end - 1, -1, -1):
            if text[i] == ' ':
                return i + 1
        
        return 0  # 找不到好的拆分点
        
    def _load_avatars(self) -> Dict[str, Image.Image]:
        """加载头像图片（支持情绪立绘）"""
        avatars = {}
        
        if self.enable_mood:
            # 启用情绪功能：加载所有情绪立绘
            for speaker in ['male', 'female']:
                for mood in self.MOODS:
                    key = f"{speaker}_{mood}"
                    path = f"{self.avatar_base_path}/{speaker}-{mood}.png"
                    if os.path.exists(path):
                        try:
                            img = Image.open(path).convert('RGBA')
                            # 调整大小为圆形头像
                            img = img.resize((self.avatar_size, self.avatar_size), Image.Resampling.LANCZOS)
                            # 创建圆形遮罩
                            mask = Image.new('L', (self.avatar_size, self.avatar_size), 0)
                            mask_draw = ImageDraw.Draw(mask)
                            mask_draw.ellipse((0, 0, self.avatar_size, self.avatar_size), fill=255)
                            # 应用圆形遮罩
                            img.putalpha(mask)
                            avatars[key] = img
                        except Exception as e:
                            print(f"⚠ 加载头像失败 {path}: {e}")
            
            if avatars:
                print(f"✓ 已加载 {len(avatars)} 个情绪立绘")
        
        # 同时加载默认立绘作为后备
        default_paths = {
            'male': f'{self.avatar_base_path}/male.png',
            'female': f'{self.avatar_base_path}/female.png'
        }
        
        for speaker, path in default_paths.items():
            if os.path.exists(path):
                try:
                    img = Image.open(path).convert('RGBA')
                    img = img.resize((self.avatar_size, self.avatar_size), Image.Resampling.LANCZOS)
                    mask = Image.new('L', (self.avatar_size, self.avatar_size), 0)
                    mask_draw = ImageDraw.Draw(mask)
                    mask_draw.ellipse((0, 0, self.avatar_size, self.avatar_size), fill=255)
                    img.putalpha(mask)
                    avatars[speaker] = img
                    print(f"✓ 加载默认头像: {path}")
                except Exception as e:
                    print(f"⚠ 加载默认头像失败 {path}: {e}")
        
        return avatars
    
    def get_avatar(self, speaker: str, mood: str = "gentle") -> Optional[Image.Image]:
        """获取指定说话人和情绪的头像"""
        if self.enable_mood:
            # 优先返回情绪立绘
            key = f"{speaker}_{mood}"
            if key in self.avatars:
                return self.avatars[key]
        
        # 返回默认立绘
        return self.avatars.get(speaker)
    
    def _get_default_font(self) -> str:
        """获取系统默认中文字体"""
        possible_fonts = [
            "/System/Library/Fonts/PingFang.ttc",  # macOS 苹方
            "/System/Library/Fonts/STHeiti Light.ttc",  # macOS 黑体
            "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",  # Linux 文泉驿
            "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",  # Linux Noto
            "C:/Windows/Fonts/simhei.ttf",  # Windows 黑体
            "C:/Windows/Fonts/simsun.ttc",  # Windows 宋体
        ]
        for font in possible_fonts:
            if os.path.exists(font):
                return font
        return None
    
    def create_subtitle_image(self, text: str, size: Tuple[int, int], 
                             speaker: str = None, mood: str = "gentle") -> np.ndarray:
        """
        创建字幕图片
        
        Args:
            text: 字幕文本
            size: (width, height)
            speaker: 说话人标签
            mood: 情绪标签
        """
        if self.style == "galgame":
            return self._create_galgame_subtitle(text, size, speaker, mood=mood)
        else:
            return self._create_default_subtitle(text, size, speaker, mood=mood)
    
    def _create_default_subtitle(self, text: str, size: Tuple[int, int], 
                                  speaker: str = None, **kwargs) -> np.ndarray:
        """默认样式：头像在左上方，深色字幕框"""
        width, height = size
        
        # 创建透明背景
        img = Image.new('RGBA', size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        # ========== 先计算文本需要的行数 ==========
        bg_left = 50
        bg_right = width - 50
        avatar_area_width = self.avatar_size + 40
        text_left = bg_left + avatar_area_width
        text_right = bg_right - 30
        max_text_width = text_right - text_left
        
        font, lines = self._get_adaptive_font_and_lines(
            text, max_text_width, float('inf'), self.max_lines
        )
        
        actual_lines = max(len(lines), self.min_lines)
        subtitle_bg_height = self.bg_padding + actual_lines * self.line_height
        min_bg_height = self.avatar_size + 60
        subtitle_bg_height = max(subtitle_bg_height, min_bg_height)
        
        # ========== 绘制底部字幕框 ==========
        bg_bottom = height - 50
        bg_top = bg_bottom - subtitle_bg_height
        
        draw.rectangle(
            [(bg_left, bg_top), (bg_right, bg_bottom)],
            fill=(0, 0, 0, 180)
        )
        
        # ========== 绘制头像和名字 ==========
        if speaker:
            speaker_name = "Alex" if speaker == "male" else "Cherry"
            label_color = (100, 180, 255) if speaker == "male" else (255, 150, 200)
            
            avatar_x = bg_left + 15
            avatar_y = bg_top + 15
            
            # 获取头像（支持情绪立绘）
            avatar = self.get_avatar(speaker, kwargs.get('mood', 'gentle'))
            if avatar:
                img.paste(avatar, (avatar_x, avatar_y), avatar)
                
                try:
                    name_font = ImageFont.truetype(self.font_path, 24) if self.font_path else ImageFont.load_default()
                except:
                    name_font = ImageFont.load_default()
                name_bbox = draw.textbbox((0, 0), speaker_name, font=name_font)
                name_width = name_bbox[2] - name_bbox[0]
                name_x = avatar_x + (self.avatar_size - name_width) // 2
                name_y = avatar_y + self.avatar_size + 8
                draw.text((name_x, name_y), speaker_name, font=name_font, fill=label_color)
        
        # ========== 绘制字幕文本 ==========
        actual_text_height = len(lines) * self.line_height
        text_start_y = bg_top + (subtitle_bg_height - actual_text_height) // 2
        
        y = text_start_y
        for line in lines:
            bbox = draw.textbbox((0, 0), line, font=font)
            text_width = bbox[2] - bbox[0]
            x = text_left + (max_text_width - text_width) // 2
            draw.text((x, y), line, font=font, fill=(255, 255, 255))
            y += self.line_height
        
        return np.array(img)
    
    def _create_galgame_subtitle(self, text: str, size: Tuple[int, int], 
                                  speaker: str = None, **kwargs) -> np.ndarray:
        """
        GalGame 风格字幕：
        - 半透明白色对话框（底部居中，全宽）
        - 圆角设计
        - 名字标签在对话框上方左侧
        - 渐变边框
        
        注意：立绘不在这里绘制，而是作为独立的视频层
        """
        width, height = size
        
        img = Image.new('RGBA', size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        # ========== 布局参数 ==========
        dialog_margin = 60
        
        # 对话框区域（底部居中，全宽）
        dialog_left = dialog_margin
        dialog_right = width - dialog_margin
        dialog_bottom = height - 40
        dialog_width = dialog_right - dialog_left
        
        # 计算文本区域
        text_padding_left = 50
        text_padding_top = 40
        text_padding_bottom = 30
        max_text_width = dialog_width - text_padding_left * 2
        
        # ========== 计算文本行数 ==========
        font, lines = self._get_adaptive_font_and_lines(
            text, max_text_width, float('inf'), self.max_lines
        )
        
        actual_lines = max(len(lines), self.min_lines)
        text_height = actual_lines * self.line_height
        
        # 对话框高度
        dialog_height = text_padding_top + text_height + text_padding_bottom
        dialog_top = dialog_bottom - dialog_height
        
        # ========== 绘制名字标签（在对话框上方左侧） ==========
        if speaker:
            speaker_name = "Alex" if speaker == "male" else "Cherry"
            name_bg_color = (100, 150, 220, 230) if speaker == "male" else (220, 120, 160, 230)
            name_text_color = (255, 255, 255)
            
            try:
                name_font = ImageFont.truetype(self.font_path, 28) if self.font_path else ImageFont.load_default()
            except:
                name_font = ImageFont.load_default()
            
            name_bbox = draw.textbbox((0, 0), speaker_name, font=name_font)
            name_width = name_bbox[2] - name_bbox[0]
            name_height = name_bbox[3] - name_bbox[1]
            
            name_padding_x = 25
            name_padding_y = 8
            name_bg_width = name_width + name_padding_x * 2
            name_bg_height = name_height + name_padding_y * 2
            
            # 名字标签位置（对话框左上角上方）
            name_x = dialog_left + 30
            name_y = dialog_top - name_bg_height + 10  # 稍微重叠
            
            # 绘制名字背景（圆角）
            self._draw_rounded_rect(
                draw, 
                (name_x, name_y, name_x + name_bg_width, name_y + name_bg_height),
                radius=8,
                fill=name_bg_color
            )
            
            # 绘制名字
            name_text_x = name_x + name_padding_x
            name_text_y = name_y + name_padding_y - 2
            draw.text((name_text_x, name_text_y), speaker_name, font=name_font, fill=name_text_color)
        
        # ========== 绘制对话框主体（圆角半透明） ==========
        dialog_bg_color = (255, 255, 255, 200)  # 半透明白色
        dialog_border_color = (200, 200, 220, 150)  # 淡紫边框
        
        self._draw_rounded_rect(
            draw,
            (dialog_left, dialog_top, dialog_right, dialog_bottom),
            radius=20,
            fill=dialog_bg_color,
            outline=dialog_border_color,
            width=2
        )
        
        # 绘制内边框（装饰效果）
        inner_margin = 6
        self._draw_rounded_rect(
            draw,
            (dialog_left + inner_margin, dialog_top + inner_margin, 
             dialog_right - inner_margin, dialog_bottom - inner_margin),
            radius=15,
            outline=(255, 255, 255, 100),
            width=1
        )
        
        # ========== 绘制字幕文本（左对齐） ==========
        text_start_x = dialog_left + text_padding_left
        text_start_y = dialog_top + text_padding_top
        
        y = text_start_y
        for line in lines:
            draw.text((text_start_x, y), line, font=font, fill=(50, 50, 60))
            y += self.line_height
        
        # 注意：立绘不再这里绘制，而是作为独立层在视频合成时添加
        # 这样可以确保立绘在字幕框后面
        
        return np.array(img)
    
    def _calc_galgame_dialog_top(self, text: str, size: Tuple[int, int]) -> int:
        """
        计算 GalGame 风格字幕框的顶部 Y 坐标
        
        Args:
            text: 字幕文本
            size: 视频尺寸 (width, height)
        
        Returns:
            dialog_top: 字幕框顶部 Y 坐标
        """
        width, height = size
        
        # ========== 布局参数（与 _create_galgame_subtitle 保持一致）==========
        dialog_margin = 60
        dialog_left = dialog_margin
        dialog_right = width - dialog_margin
        dialog_bottom = height - 40
        dialog_width = dialog_right - dialog_left
        
        text_padding_left = 50
        text_padding_top = 40
        text_padding_bottom = 30
        max_text_width = dialog_width - text_padding_left * 2
        
        # ========== 计算文本行数 ==========
        font, lines = self._get_adaptive_font_and_lines(
            text, max_text_width, float('inf'), self.max_lines
        )
        
        actual_lines = max(len(lines), self.min_lines)
        text_height = actual_lines * self.line_height
        
        # 对话框高度
        dialog_height = text_padding_top + text_height + text_padding_bottom
        dialog_top = dialog_bottom - dialog_height
        
        return dialog_top
    
    def get_galgame_avatar_clip(self, size: Tuple[int, int], speaker: str, 
                                mood: str = "gentle", duration: float = 1.0, 
                                fps: int = 30, dialog_top: int = None):
        """
        获取 GalGame 风格的立绘视频层（用于放在字幕后面）
        
        Args:
            size: 视频尺寸 (width, height)
            speaker: 说话人
            mood: 情绪
            duration: 持续时间
            fps: 帧率
            dialog_top: 字幕框顶部 Y 坐标（用于定位立绘位置）
        
        Returns:
            ImageClip 或 None
        """
        width, height = size
        
        if not speaker:
            return None
        
        # 读取配置参数
        config = self.galgame_avatar_config
        height_ratio = config.get('height_ratio', 0.45)  # 默认占屏幕高度 45%
        horizontal_position = config.get('horizontal_position', 0.7)  # 默认在右侧 70% 位置
        vertical_offset = config.get('vertical_offset', -20)  # 默认向上偏移 20px
        
        # 计算立绘尺寸
        avatar_max_height = int(height * height_ratio)
        
        # 加载立绘
        avatar_img = self._get_large_avatar_by_height(speaker, avatar_max_height, mood)
        
        if not avatar_img:
            print(f"⚠️ 无法加载立绘: {speaker}-{mood}")
            return None
        
        # 等比缩放确保不超过最大高度
        if avatar_img.height > avatar_max_height:
            ratio = avatar_max_height / avatar_img.height
            new_width = int(avatar_img.width * ratio)
            avatar_img = avatar_img.resize((new_width, avatar_max_height), Image.Resampling.LANCZOS)
        
        # 创建透明背景的图片（全屏尺寸）
        full_img = Image.new('RGBA', size, (0, 0, 0, 0))
        
        # 计算立绘水平位置：根据 horizontal_position 参数
        # horizontal_position 0.0 = 最左, 0.5 = 居中, 1.0 = 最右
        # 立绘中心点位于 horizontal_position 对应的位置
        avatar_center_x = int(width * horizontal_position)
        avatar_x = avatar_center_x - avatar_img.width // 2
        
        # 计算立绘垂直位置：贴着字幕框上方
        if dialog_top is not None:
            # 贴着字幕框上方，加上垂直偏移
            avatar_y = dialog_top - avatar_img.height + vertical_offset
        else:
            # 回退：使用默认位置（屏幕底部偏上）
            avatar_y = height - avatar_img.height - 100
        
        # 确保立绘不会完全超出屏幕
        if avatar_x < -avatar_img.width // 2:
            avatar_x = -avatar_img.width // 2
        if avatar_x > width - avatar_img.width // 2:
            avatar_x = width - avatar_img.width // 2
        
        # 将立绘粘贴到透明背景上
        full_img.paste(avatar_img, (avatar_x, avatar_y), avatar_img)
        
        # 转换为 numpy 数组并创建 ImageClip
        import numpy as np
        from moviepy import ImageClip as MCImageClip
        
        avatar_clip = MCImageClip(np.array(full_img)).with_duration(duration).with_fps(fps)
        
        return avatar_clip
    
    def _draw_rounded_rect(self, draw, bbox, radius, fill=None, outline=None, width=1):
        """绘制圆角矩形"""
        x1, y1, x2, y2 = bbox
        
        # 主体矩形
        if fill:
            draw.rectangle([x1 + radius, y1, x2 - radius, y2], fill=fill)
            draw.rectangle([x1, y1 + radius, x2, y2 - radius], fill=fill)
            # 四个圆角
            draw.pieslice([x1, y1, x1 + radius * 2, y1 + radius * 2], 180, 270, fill=fill)
            draw.pieslice([x2 - radius * 2, y1, x2, y1 + radius * 2], 270, 360, fill=fill)
            draw.pieslice([x1, y2 - radius * 2, x1 + radius * 2, y2], 90, 180, fill=fill)
            draw.pieslice([x2 - radius * 2, y2 - radius * 2, x2, y2], 0, 90, fill=fill)
        
        # 边框
        if outline:
            draw.arc([x1, y1, x1 + radius * 2, y1 + radius * 2], 180, 270, fill=outline, width=width)
            draw.arc([x2 - radius * 2, y1, x2, y1 + radius * 2], 270, 360, fill=outline, width=width)
            draw.arc([x1, y2 - radius * 2, x1 + radius * 2, y2], 90, 180, fill=outline, width=width)
            draw.arc([x2 - radius * 2, y2 - radius * 2, x2, y2], 0, 90, fill=outline, width=width)
            draw.line([x1 + radius, y1, x2 - radius, y1], fill=outline, width=width)
            draw.line([x1 + radius, y2, x2 - radius, y2], fill=outline, width=width)
            draw.line([x1, y1 + radius, x1, y2 - radius], fill=outline, width=width)
            draw.line([x2, y1 + radius, x2, y2 - radius], fill=outline, width=width)
    
    def _get_large_avatar(self, speaker: str, target_width: int, mood: str = "gentle") -> Image.Image:
        """获取大尺寸头像（立绘风格，支持情绪）"""
        # 确定要加载的文件路径
        if self.enable_mood:
            # 优先尝试情绪立绘
            mood_path = f"{self.avatar_base_path}/{speaker}-{mood}.png"
            if os.path.exists(mood_path):
                try:
                    img = Image.open(mood_path).convert('RGBA')
                    ratio = target_width / img.width
                    new_height = int(img.height * ratio)
                    img = img.resize((target_width, new_height), Image.Resampling.LANCZOS)
                    return img
                except:
                    pass
        
        # 使用默认立绘
        default_path = f"{self.avatar_base_path}/{speaker}.png"
        if os.path.exists(default_path):
            try:
                img = Image.open(default_path).convert('RGBA')
                ratio = target_width / img.width
                new_height = int(img.height * ratio)
                img = img.resize((target_width, new_height), Image.Resampling.LANCZOS)
                return img
            except:
                pass
        
        # 失败则返回已加载的头像
        return self.get_avatar(speaker, mood)
    
    def _get_large_avatar_by_height(self, speaker: str, target_height: int, mood: str = "gentle") -> Image.Image:
        """获取大尺寸头像（按目标高度缩放，立绘风格，支持情绪）"""
        # 情绪名称映射（代码中的情绪 -> 文件名中的情绪）
        mood_mapping = {
            'gentle': 'neutral',
            'shocked': 'surprised',
            'resigned': 'sad',
            'expectant': 'expectant',
            'confused': 'confused',
            'angry': 'angry',
            'happy': 'happy',
            'confident': 'confident',
            'sad': 'sad'
        }
        
        # 确定要加载的文件路径
        if self.enable_mood:
            # 优先尝试情绪立绘（使用映射后的名称）
            mapped_mood = mood_mapping.get(mood, mood)
            mood_path = f"{self.avatar_base_path}/{speaker}-{mapped_mood}.png"
            if os.path.exists(mood_path):
                try:
                    img = Image.open(mood_path).convert('RGBA')
                    ratio = target_height / img.height
                    new_width = int(img.width * ratio)
                    img = img.resize((new_width, target_height), Image.Resampling.LANCZOS)
                    return img
                except Exception as e:
                    print(f"⚠️ 加载立绘失败 {mood_path}: {e}")
        
        # 回退到 neutral 立绘
        neutral_path = f"{self.avatar_base_path}/{speaker}-neutral.png"
        if os.path.exists(neutral_path):
            try:
                img = Image.open(neutral_path).convert('RGBA')
                ratio = target_height / img.height
                new_width = int(img.width * ratio)
                img = img.resize((new_width, target_height), Image.Resampling.LANCZOS)
                return img
            except Exception as e:
                print(f"⚠️ 加载默认立绘失败 {neutral_path}: {e}")
        
        # 失败则尝试使用 _get_large_avatar 并按比例调整
        fallback = self.get_avatar(speaker, mood)
        if fallback:
            try:
                ratio = target_height / fallback.height
                new_width = int(fallback.width * ratio)
                return fallback.resize((new_width, target_height), Image.Resampling.LANCZOS)
            except:
                pass
        return fallback
    
    def _get_adaptive_font_and_lines(self, text: str, max_width: int, 
                                      max_height: int, max_lines: int) -> Tuple[ImageFont.FreeTypeFont, List[str]]:
        """
        获取自适应字体大小和换行后的文本
        
        策略:
        1. 优先使用较大字体
        2. 根据文本长度自适应行数（最少2行，最多max_lines行）
        3. 如果文本很长，逐渐减小字体以适应行数限制
        
        Returns:
            (字体, 行列表)
        """
        # 尝试的字体大小范围（从大到小）
        font_sizes = [42, 38, 34, 30, 26, 22, 18]
        
        for font_size in font_sizes:
            try:
                if self.font_path:
                    font = ImageFont.truetype(self.font_path, font_size)
                else:
                    font = ImageFont.load_default()
            except:
                font = ImageFont.load_default()
            
            # 换行（传入最大行数限制）
            lines = self._wrap_text_to_lines(text, font, max_width, max_lines)
            
            # 检查高度是否合适（使用固定的行高）
            total_height = len(lines) * self.line_height
            
            # 如果高度合适且行数在限制内，使用这个字体大小
            if total_height <= max_height and len(lines) <= max_lines:
                return font, lines
            
            # 如果行数太多，继续尝试更小的字体
            if len(lines) > max_lines:
                continue
        
        # 如果所有字体大小都尝试了还是不行，使用最小字体并强制截断
        try:
            font = ImageFont.truetype(self.font_path, 18) if self.font_path else ImageFont.load_default()
        except:
            font = ImageFont.load_default()
        
        lines = self._wrap_text_to_lines(text, font, max_width, max_lines)
        
        # 如果还是超过最大行数，截断并添加省略号
        if len(lines) > max_lines:
            lines = lines[:max_lines]
            if lines[-1]:
                lines[-1] = lines[-1][:20] + "..."
        
        return font, lines
    
    def _wrap_text_to_lines(self, text: str, font, max_width: int, max_lines: int) -> List[str]:
        """
        将文本换行为指定行数，智能处理标点符号
        """
        # 先尝试完整换行
        all_lines = []
        current_line = ""
        
        for char in text:
            test_line = current_line + char
            bbox = font.getbbox(test_line) if hasattr(font, 'getbbox') else (0, 0, len(test_line) * self.font_size * 0.6, self.font_size)
            text_width = bbox[2] - bbox[0] if len(bbox) >= 4 else len(test_line) * self.font_size * 0.6
            
            if text_width > max_width and current_line:
                all_lines.append(current_line)
                current_line = char
            else:
                current_line = test_line
        
        if current_line:
            all_lines.append(current_line)
        
        # 如果行数在限制内，直接返回
        if len(all_lines) <= max_lines:
            return all_lines
        
        # 如果行数过多，需要合并一些行（尽量保持语义）
        # 重新计算，使用更短的行
        lines = []
        current_line = ""
        avg_chars_per_line = len(text) // max_lines + 1
        
        for i, char in enumerate(text):
            current_line += char
            
            # 检查是否需要换行
            should_break = False
            
            # 1. 达到平均字符数且当前字符是标点符号
            if len(current_line) >= avg_chars_per_line and char in '，。！？、；：':
                should_break = True
            
            # 2. 检查宽度是否超限
            bbox = font.getbbox(current_line) if hasattr(font, 'getbbox') else (0, 0, len(current_line) * self.font_size * 0.6, self.font_size)
            text_width = bbox[2] - bbox[0] if len(bbox) >= 4 else len(current_line) * self.font_size * 0.6
            
            if text_width > max_width * 0.95:
                should_break = True
            
            # 3. 已到最后
            if i == len(text) - 1:
                should_break = True
            
            if should_break and current_line:
                lines.append(current_line)
                current_line = ""
                
                if len(lines) >= max_lines:
                    # 如果达到最大行数，将剩余内容附加到最后一行
                    remaining = text[i+1:]
                    if remaining:
                        lines[-1] += remaining[:20]  # 只加一部分，避免溢出
                        if len(remaining) > 20:
                            lines[-1] += "..."
                    break
        
        if current_line and len(lines) < max_lines:
            lines.append(current_line)
        
        return lines[:max_lines]
    
    def _wrap_text(self, text: str, font, max_width: int) -> List[str]:
        """自动换行 - 移除末尾空行"""
        lines = []
        current_line = ""
        
        # 预处理：移除文本末尾的空白字符
        text = text.rstrip()
        
        for char in text:
            test_line = current_line + char
            bbox = font.getbbox(test_line) if hasattr(font, 'getbbox') else (0, 0, len(test_line) * self.font_size * 0.6, self.font_size)
            text_width = bbox[2] - bbox[0] if len(bbox) >= 4 else len(test_line) * self.font_size * 0.6
            
            if text_width > max_width and current_line:
                lines.append(current_line)
                current_line = char
            else:
                current_line = test_line
        
        # 添加最后一行（确保不为空）
        if current_line and current_line.strip():
            lines.append(current_line)
        
        return lines if lines else [text]


class PodcastVideoGenerator:
    """播客视频生成器"""
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        self.width = self.config.get('width', 1920)
        self.height = self.config.get('height', 1080)
        self.fps = self.config.get('fps', 30)
        self.enable_mood = self.config.get('enable_mood', True)
        if self.enable_mood:
            print("✨ 情绪立绘功能已启用")
        self.subtitle_gen = SubtitleGenerator(
            font_path=self.config.get('font_path'),
            font_size=self.config.get('font_size', 40),
            style=self.config.get('subtitle_style', 'default'),
            enable_mood=self.enable_mood,
            avatar_base_path=self.config.get('avatar_base_path', 'avatar'),
            galgame_avatar_config=self.config.get('galgame_avatar', {})
        )
        
    def create_podcast_video(self, 
                           segments: List[DialogueSegment],
                           output_path: str,
                           background_type: str = "gradient",
                           background_path: str = None,
                           add_waveform: bool = False,
                           transition_duration: float = 0.5) -> str:
        """
        创建播客视频
        
        Args:
            segments: 对话段落列表
            output_path: 输出视频路径
            background_type: 背景类型 (gradient, image, video)
            background_path: 背景图片/视频路径
            add_waveform: 是否添加音频波形
            transition_duration: 段落间过渡时间（秒）
        
        Returns:
            输出视频路径
        """
        print(f"🎬 开始生成视频播客...")
        print(f"   分辨率: {self.width}x{self.height}")
        print(f"   段落数: {len(segments)}")
        print(f"   背景类型: {background_type}")
        if background_path:
            print(f"   背景路径: {background_path}")
        print(f"   段落间隔: {transition_duration}秒")
        
        video_clips = []
        audio_clips = []
        
        for i, seg in enumerate(segments):
            print(f"[{i+1}/{len(segments)}] 处理: {seg.speaker} - {seg.text[:30]}...")
            
            # 加载音频
            audio_clip = AudioFileClip(seg.audio_path)
            duration = audio_clip.duration
            
            # 创建视频帧
            if background_type == "gradient":
                video_clip = self._create_gradient_background(duration, seg.speaker)
            elif background_type == "image" and background_path:
                video_clip = self._create_image_background(duration, background_path)
            else:
                video_clip = self._create_color_background(duration, seg.speaker)
            
            # 检查字幕长度，自动拆分长字幕（返回 [(文本, 时间比例), ...]）
            subtitle_parts_with_ratio = self.subtitle_gen.split_long_text(seg.text, self.width)
            
            # 获取情绪标签
            mood = getattr(seg, 'mood', 'gentle') if self.enable_mood else 'gentle'
            
            # 判断是否使用 galgame 风格（需要单独添加立绘层）
            is_galgame_style = self.config.get('subtitle_style', 'default') == 'galgame'
            
            if len(subtitle_parts_with_ratio) > 1:
                # 长字幕拆分成多个子片段，根据内容权重分配时间
                subtitle_clips = []
                avatar_clips = []  # 每个子片段的立绘层
                current_start = 0.0
                
                for part_text, time_ratio in subtitle_parts_with_ratio:
                    # 根据权重计算该段字幕的显示时长
                    part_duration = duration * time_ratio
                    
                    # 创建字幕 clip
                    subtitle_img = self.subtitle_gen.create_subtitle_image(
                        part_text, (self.width, self.height), seg.speaker, mood
                    )
                    subtitle_clip = (ImageClip(subtitle_img)
                                   .with_start(current_start)
                                   .with_duration(part_duration)
                                   .with_fps(self.fps))
                    subtitle_clips.append(subtitle_clip)
                    
                    # 对于 galgame 风格，为每个子片段单独创建立绘层
                    if is_galgame_style and seg.speaker:
                        dialog_top = self.subtitle_gen._calc_galgame_dialog_top(part_text, (self.width, self.height))
                        avatar_clip = self.subtitle_gen.get_galgame_avatar_clip(
                            (self.width, self.height), seg.speaker, mood, 
                            part_duration, self.fps, dialog_top
                        )
                        if avatar_clip:
                            avatar_clip = avatar_clip.with_start(current_start)
                            avatar_clips.append(avatar_clip)
                    
                    current_start += part_duration
                
                # 合成视频片段（背景 + 立绘 + 字幕）
                # 层级：背景在最底层，然后是立绘，字幕在最上层
                all_clips = [video_clip]
                all_clips.extend(avatar_clips)
                all_clips.extend(subtitle_clips)
                composite = CompositeVideoClip(all_clips)
            else:
                # 普通字幕（只有一段）
                part_text, _ = subtitle_parts_with_ratio[0]
                subtitle_img = self.subtitle_gen.create_subtitle_image(
                    part_text, (self.width, self.height), seg.speaker, mood
                )
                subtitle_clip = (ImageClip(subtitle_img)
                               .with_duration(duration)
                               .with_fps(self.fps))
                
                # 对于 galgame 风格，创建立绘层
                if is_galgame_style and seg.speaker:
                    dialog_top = self.subtitle_gen._calc_galgame_dialog_top(part_text, (self.width, self.height))
                    avatar_clip = self.subtitle_gen.get_galgame_avatar_clip(
                        (self.width, self.height), seg.speaker, mood, 
                        duration, self.fps, dialog_top
                    )
                    # 合成视频片段（背景 + 立绘 + 字幕）
                    if avatar_clip:
                        composite = CompositeVideoClip([video_clip, avatar_clip, subtitle_clip])
                    else:
                        composite = CompositeVideoClip([video_clip, subtitle_clip])
                else:
                    composite = CompositeVideoClip([video_clip, subtitle_clip])
            
            composite = composite.with_audio(audio_clip)
            
            video_clips.append(composite)
            audio_clips.append(audio_clip)
            
            # 添加段落间的过渡（除了最后一段）
            if transition_duration > 0 and i < len(segments) - 1:
                # 创建过渡片段（静音+渐隐渐现效果）
                if background_type == "gradient":
                    # 使用中性渐变作为过渡
                    trans_bg = self._create_gradient_background(transition_duration, 'male')
                elif background_type == "image" and background_path:
                    trans_bg = self._create_image_background(transition_duration, background_path)
                else:
                    trans_bg = self._create_color_background(transition_duration, 'male')
                
                # 创建静音音频
                from moviepy.audio.AudioClip import AudioArrayClip
                import numpy as np
                silent_audio = AudioArrayClip(
                    np.zeros((int(transition_duration * 44100), 2)), 
                    fps=44100
                )
                
                trans_clip = trans_bg.with_audio(silent_audio)
                video_clips.append(trans_clip)
        
        # 合并所有片段
        print("🔄 合并视频片段...")
        final_video = concatenate_videoclips(video_clips, method="compose")
        
        # 添加片头（可选）
        if self.config.get('add_intro', False):
            intro = self._create_intro_clip()
            final_video = concatenate_videoclips([intro, final_video], method="compose")
        
        # 输出视频
        print(f"💾 导出视频: {output_path}")
        
        # 检测平台并选择编码器
        import platform
        system = platform.system()
        
        # 基础参数
        write_params = {
            'fps': self.fps,
            'audio_codec': 'aac',
            'temp_audiofile': 'temp-audio.m4a',
            'remove_temp': True,
        }
        
        # macOS 编码设置
        # 注意：当前 FFmpeg 版本的 VideoToolbox 性能不佳，使用软件编码更快
        if system == 'Darwin':
            print("💻 使用软件编码 (libx264 ultrafast)")
            write_params['codec'] = 'libx264'
            write_params['preset'] = 'ultrafast'  # 最快预设
            write_params['threads'] = 0  # 自动使用所有 CPU 核心
            write_params['ffmpeg_params'] = ['-b:v', '4000k']
        else:
            # 其他平台使用软件编码
            print("💻 使用软件编码 (libx264)")
            write_params['codec'] = 'libx264'
            write_params['preset'] = 'medium'
            write_params['threads'] = 4
        
        final_video.write_videofile(output_path, **write_params)
        
        # 清理
        for clip in video_clips:
            clip.close()
        for clip in audio_clips:
            clip.close()
        final_video.close()
        
        print(f"✅ 视频生成完成: {output_path}")
        return output_path
    
    def _create_gradient_background(self, duration: float, speaker: str) -> ImageClip:
        """创建渐变背景"""
        # 根据说话人选择不同的渐变色
        if speaker == 'male':
            colors = [(30, 60, 114), (50, 100, 150)]  # 蓝色系
        else:
            colors = [(100, 50, 100), (150, 80, 130)]  # 紫色系
        
        # 创建渐变图像
        gradient = np.zeros((self.height, self.width, 3), dtype=np.uint8)
        for y in range(self.height):
            ratio = y / self.height
            for c in range(3):
                gradient[y, :, c] = int(colors[0][c] * (1 - ratio) + colors[1][c] * ratio)
        
        return ImageClip(gradient).with_duration(duration).with_fps(self.fps)
    
    def _create_color_background(self, duration: float, speaker: str) -> ImageClip:
        """创建纯色背景"""
        if speaker == 'male':
            color = (40, 70, 120)  # 深蓝
        else:
            color = (120, 60, 100)  # 深紫
        
        return ColorClip(size=(self.width, self.height), color=color)\
                        .with_duration(duration).with_fps(self.fps)
    
    def _create_image_background(self, duration: float, image_path: str) -> ImageClip:
        """创建图片背景"""
        img = Image.open(image_path)
        # 调整大小并裁剪以适应视频尺寸
        img_ratio = img.width / img.height
        video_ratio = self.width / self.height
        
        if img_ratio > video_ratio:
            new_height = self.height
            new_width = int(self.height * img_ratio)
        else:
            new_width = self.width
            new_height = int(self.width / img_ratio)
        
        img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        # 居中裁剪
        left = (new_width - self.width) // 2
        top = (new_height - self.height) // 2
        img = img.crop((left, top, left + self.width, top + self.height))
        
        return ImageClip(np.array(img)).with_duration(duration).with_fps(self.fps)
    
    def _get_system_font(self) -> str:
        """获取系统支持的中文字体"""
        font_paths = [
            "/System/Library/Fonts/PingFang.ttc",  # macOS 苹方
            "/System/Library/Fonts/STHeiti Light.ttc",  # macOS 黑体
            "/System/Library/Fonts/Helvetica.ttc",  # macOS Helvetica
            "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",  # Linux 文泉驿
            "C:/Windows/Fonts/simhei.ttf",  # Windows 黑体
            "C:/Windows/Fonts/simsun.ttc",  # Windows 宋体
            "Arial",  # 默认回退
        ]
        for font in font_paths:
            if font == "Arial" or os.path.exists(font):
                return font
        return "Arial"
    
    def _wrap_text_for_title(self, text: str, font_path: str, max_width: int, 
                              initial_font_size: int) -> Tuple[str, int]:
        """
        根据宽度自动调整字体大小并换行
        
        Returns:
            (换行后的文本, 实际使用的字体大小)
        """
        from PIL import ImageFont
        
        # 尝试不同的字体大小
        for font_size in range(initial_font_size, 20, -5):  # 从大到小尝试
            try:
                font = ImageFont.truetype(font_path, font_size)
            except:
                font = ImageFont.load_default()
            
            # 尝试不换行
            try:
                bbox = font.getbbox(text)
                text_width = bbox[2] - bbox[0]
            except:
                text_width = len(text) * font_size * 0.6
            
            if text_width <= max_width:
                # 字体大小合适，不需要换行
                return text, font_size
            
            # 需要换行，尝试找到最佳换行位置
            lines = []
            current_line = ""
            
            for char in text:
                test_line = current_line + char
                try:
                    bbox = font.getbbox(test_line)
                    line_width = bbox[2] - bbox[0]
                except:
                    line_width = len(test_line) * font_size * 0.6
                
                if line_width > max_width and current_line:
                    lines.append(current_line)
                    current_line = char
                else:
                    current_line = test_line
            
            if current_line:
                lines.append(current_line)
            
            # 检查行数是否合适（最多2行）
            if len(lines) <= 2:
                return "\n".join(lines), font_size
        
        # 如果都不行，返回最小字体的强制换行
        try:
            font = ImageFont.truetype(font_path, 20)
        except:
            font = ImageFont.load_default()
        
        lines = []
        current_line = ""
        for char in text:
            test_line = current_line + char
            try:
                bbox = font.getbbox(test_line)
                line_width = bbox[2] - bbox[0]
            except:
                line_width = len(test_line) * 20 * 0.6
            
            if line_width > max_width and current_line:
                lines.append(current_line)
                current_line = char
            else:
                current_line = test_line
        
        if current_line:
            lines.append(current_line)
        
        return "\n".join(lines[:3]), 20  # 最多3行
    
    def _create_intro_clip(self, title_text: str = None, subtitle_text: str = None) -> CompositeVideoClip:
        """创建片头 - 支持自动调整字体大小和换行"""
        duration = 3
        
        # 背景
        bg = self._create_gradient_background(duration, 'male')
        
        # 标题文本 - 使用传入的参数或默认值
        title_text = title_text or self.config.get('title', '文献解读')
        subtitle_text = subtitle_text or self.config.get('subtitle', '对话式科普播客')
        
        # 获取中文字体
        font = self._get_system_font()
        
        # 计算安全边距
        margin = int(self.width * 0.1)  # 左右各10%边距
        max_text_width = self.width - 2 * margin
        
        # 处理主标题 - 自动调整字体大小和换行
        wrapped_title, title_font_size = self._wrap_text_for_title(
            title_text, font, max_text_width, initial_font_size=80
        )
        
        print(f"   主标题: {title_text[:30]}...")
        print(f"   字体大小: {title_font_size}px")
        if "\n" in wrapped_title:
            print(f"   已自动换行: {wrapped_title.count(chr(10)) + 1} 行")
        
        title = TextClip(
            text=wrapped_title,
            font_size=title_font_size,
            color='white',
            font=font,
            stroke_color='black',
            stroke_width=2,
            method='label',
            text_align='center'
        ).with_duration(duration).with_position('center')
        
        # 处理副标题 - 字体小一些
        wrapped_subtitle, subtitle_font_size = self._wrap_text_for_title(
            subtitle_text, font, max_text_width, initial_font_size=40
        )
        
        # 根据主标题行数调整副标题位置
        title_lines = wrapped_title.count('\n') + 1
        subtitle_y = self.height * 0.55 + title_lines * title_font_size * 0.3
        
        subtitle = TextClip(
            text=wrapped_subtitle,
            font_size=subtitle_font_size,
            color='yellow',
            font=font,
            method='label',
            text_align='center'
        ).with_duration(duration).with_position(('center', subtitle_y))
        
        intro = CompositeVideoClip([bg, title, subtitle])
        try:
            # moviepy 2.x
            intro = FadeIn(duration=0.5).apply(intro)
            intro = FadeOut(duration=0.5).apply(intro)
        except:
            # moviepy 1.x
            intro = intro.fx(fadein, duration=0.5)
            intro = intro.fx(fadeout, duration=0.5)
        
        return intro


class AudioVideoPipeline:
    """音频到视频的完整流程"""
    
    def __init__(self, video_config: Dict = None):
        self.video_config = video_config or {
            'width': 1920,
            'height': 1080,
            'fps': 30,
            'font_size': 40,
            'font_path': None,
            'add_intro': True,
            'title': '文献解读',
            'subtitle': '对话式科普播客'
        }
    
    def run(self, 
           audio_dir: str,
           markdown_path: str,
           output_path: str = "podcast_video.mp4",
           background_type: str = "gradient",
           background_path: str = None,
           title: str = None,
           subtitle: str = None,
           transition_duration: float = 0.5) -> str:
        """
        执行完整流程
        
        Args:
            audio_dir: 音频文件目录
            markdown_path: Markdown 文件路径（用于获取文本）
            output_path: 输出视频路径
            background_type: 背景类型
            background_path: 背景图片/视频路径（当 background_type=image 时使用）
            title: 片头标题（可选）
            subtitle: 片头副标题（可选）
            transition_duration: 段落间过渡时间（秒）
        """
        # 1. 解析 Markdown 获取对话文本
        print("📖 解析对话文本...")
        dialogues = self._parse_markdown(markdown_path)
        
        # 2. 匹配音频文件
        print("🎵 匹配音频文件...")
        segments = self._match_audio_files(dialogues, audio_dir)
        
        if not segments:
            raise ValueError("未找到匹配的音频文件")
        
        print(f"   找到 {len(segments)} 个音频片段")
        
        # 更新视频配置
        if title:
            self.video_config['title'] = title
        if subtitle:
            self.video_config['subtitle'] = subtitle
        
        # 3. 生成视频
        generator = PodcastVideoGenerator(self.video_config)
        output = generator.create_podcast_video(
            segments, 
            output_path,
            background_type=background_type,
            background_path=background_path,
            transition_duration=transition_duration
        )
        
        return output
    
    def _parse_markdown(self, markdown_path: str) -> List[Dict]:
        """解析 Markdown 文件（支持情绪标注）"""
        with open(markdown_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        dialogues = []
        
        # 首先尝试解析新格式（带情绪）
        # 新格式: ### speaker ### \n ### mood ### \n ### text ###
        new_pattern = r'###\s*(male|female)\s*speaker\s*###\s*\n\s*###\s*(\w+)\s*###\s*\n\s*###\s*(.*?)\s*###'
        new_matches = re.findall(new_pattern, content, re.DOTALL)
        
        # 旧格式: ### speaker ### \n ### text ###
        old_pattern = r'###\s*(male|female)\s*speaker\s*###\s*\n\s*###\s*(.*?)\s*###'
        old_matches = re.findall(old_pattern, content, re.DOTALL)
        
        # 如果新格式匹配成功且数量合理，使用新格式
        if new_matches and len(new_matches) >= len(old_matches) / 2:
            for idx, (speaker, mood, text) in enumerate(new_matches, 1):
                text = self._clean_text(text)
                if text:
                    dialogues.append({
                        'index': idx,
                        'speaker': speaker.lower(),
                        'text': text,
                        'mood': mood.lower()
                    })
        else:
            # 使用旧格式解析，情绪默认为 gentle
            for idx, (speaker, text) in enumerate(old_matches, 1):
                text = self._clean_text(text)
                if text:
                    dialogues.append({
                        'index': idx,
                        'speaker': speaker.lower(),
                        'text': text,
                        'mood': 'gentle'
                    })
        
        return dialogues
    
    def _match_audio_files(self, dialogues: List[Dict], audio_dir: str) -> List[DialogueSegment]:
        """匹配音频文件"""
        segments = []
        audio_dir = Path(audio_dir)
        
        for d in dialogues:
            # 寻找匹配的音频文件
            pattern = f"*{d['index']:03d}*{d['speaker']}*.wav"
            matching_files = list(audio_dir.glob(pattern))
            
            if matching_files:
                audio_path = str(matching_files[0])
                # 获取音频时长
                try:
                    audio = AudioFileClip(audio_path)
                    duration = audio.duration
                    audio.close()
                except:
                    duration = 0
                
                segments.append(DialogueSegment(
                    index=d['index'],
                    speaker=d['speaker'],
                    text=d['text'],
                    audio_path=audio_path,
                    duration=duration,
                    mood=d.get('mood', 'gentle')
                ))
        
        return segments
    
    def _clean_text(self, text: str) -> str:
        """清理文本"""
        # 移除各种换行符和多余空白
        text = text.replace('\n', ' ').replace('\r', ' ')
        text = re.sub(r'\s+', ' ', text).strip()
        # 移除括号内的内容（如备注）
        text = re.sub(r'[（(][^）)]+[）)]', '', text)
        # 确保文本末尾没有多余空白
        text = text.rstrip()
        return text


def load_config(config_path: str = "configs/video/config.yaml") -> Dict:
    """加载配置文件"""
    default_config = {
        'audio_dir': 'audio_output',
        'markdown_file': 'paperwork_in/文献解读对话文案-2.md',
        'output_dir': 'broadcast_output',
        'output_filename': '',
        'resolution': {'width': 1920, 'height': 1080},
        'fps': 30,
        'background_type': 'gradient',
        'background_image': '',
        'show_intro': True,
        'title': '',
        'subtitle': '对话式科普播客',
        'transition_duration': 0.5,
        'male_avatar': 'avatar/male.png',
        'female_avatar': 'avatar/female.png',
        'male_name': 'Alex',
        'female_name': 'Cherry',
        'subtitle_style': 'default',
        'font_size': 40,
        'enable_mood': True,  # 情绪功能开关，默认开启
        'avatar_base_path': 'avatar',  # 立绘基础路径
        'galgame_avatar': {  # GalGame 风格立绘配置
            'height_ratio': 0.45,  # 立绘高度占屏幕比例（默认 45%）
            'horizontal_position': 0.7,  # 水平位置（0.0=左, 0.5=中, 1.0=右）
            'vertical_offset': -20,  # 垂直偏移（像素，负值向上）
        },
    }
    
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                user_config = yaml.safe_load(f)
                if user_config:
                    default_config.update(user_config)
                    print(f"✅ 已加载配置文件: {config_path}")
        except Exception as e:
            print(f"⚠️  加载配置文件失败: {e}，使用默认配置")
    else:
        print(f"⚠️  未找到配置文件 {config_path}，使用默认配置")
        print(f"   提示: 复制 configs/video/config.yaml.example 进行修改")
    
    return default_config


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='视频播客生成器 - 将音频转换为带字幕的视频',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用方式:
  # 方式1: 使用配置文件（推荐）
  python video_generator.py
  
  # 方式2: 指定配置文件路径
  python video_generator.py -c configs/video/my_config.yaml
  
  # 方式3: 命令行参数覆盖配置
  python video_generator.py -i audio_output -m 文献.md

提示:
  • 首次使用请复制 configs/video/config.yaml.example 为 configs/video/config.yaml
  • 音频文件命名格式: dialogue_001_male.wav, dialogue_002_female.wav
  • 男声显示 Alex 头像(蓝色)，女声显示 Cherry 头像(粉色)
  • 支持情绪立绘: 在对话脚本中添加 mood 标签，如 ### happy ###
        """
    )
    
    parser.add_argument(
        '-c', '--config',
        default='configs/video/config.yaml',
        help='配置文件路径 (默认: configs/video/config.yaml)'
    )
    parser.add_argument(
        '-i', '--input',
        default=None,
        help='音频文件目录 (覆盖配置文件)'
    )
    parser.add_argument(
        '-m', '--markdown',
        default=None,
        help='Markdown 文件路径 (覆盖配置文件)'
    )
    parser.add_argument(
        '-o', '--output',
        default=None,
        help='输出视频路径 (覆盖配置文件)'
    )
    parser.add_argument(
        '-t', '--title',
        default=None,
        help='片头标题 (覆盖配置文件)'
    )
    
    args = parser.parse_args()
    
    # 加载配置
    config = load_config(args.config)
    
    # 命令行参数覆盖配置文件
    if args.input:
        config['audio_dir'] = args.input
    if args.markdown:
        config['markdown_file'] = args.markdown
    if args.output:
        config['output_filename'] = args.output
    if args.title:
        config['title'] = args.title
    
    # 检查依赖
    try:
        import moviepy
    except ImportError:
        print("❌ 请先安装依赖: pip install moviepy Pillow numpy")
        return
    
    # 检查必要参数
    # 如果 audio_dir 是 tts_output，尝试查找最新的时间编号子文件夹
    audio_dir = config['audio_dir']
    if audio_dir == 'tts_output' and os.path.exists(audio_dir):
        try:
            subdirs = [d for d in os.listdir(audio_dir) 
                      if os.path.isdir(os.path.join(audio_dir, d)) and d[0].isdigit()]
            if subdirs:
                # 按名称排序获取最新的时间文件夹
                subdirs.sort(reverse=True)
                latest_subdir = subdirs[0]
                audio_dir = os.path.join(audio_dir, latest_subdir)
                print(f"📁 自动使用最新的 TTS 输出目录: {audio_dir}")
        except Exception:
            pass
    config['audio_dir'] = audio_dir
    
    if not os.path.exists(config['audio_dir']):
        print(f"❌ 错误: 找不到音频目录 '{config['audio_dir']}'")
        print(f"   请先运行: python tts_generator.py {config['markdown_file']}")
        return
    
    if not os.path.exists(config['markdown_file']):
        print(f"❌ 错误: 找不到 Markdown 文件 '{config['markdown_file']}'")
        return
    
    # 生成输出路径
    if config['output_filename']:
        output_path = os.path.join(config['output_dir'], config['output_filename'])
    else:
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        output_path = os.path.join(config['output_dir'], f"podcast_{timestamp}.mp4")
    
    # 确保输出目录存在
    os.makedirs(config['output_dir'], exist_ok=True)
    
    # 准备视频配置
    video_config = {
        'width': config['resolution']['width'],
        'height': config['resolution']['height'],
        'fps': config['fps'],
        'add_intro': config['show_intro'],
        'title': config['title'] or os.path.splitext(os.path.basename(config['markdown_file']))[0],
        'subtitle': config['subtitle'],
        'subtitle_style': config.get('subtitle_style', 'default'),
        'font_size': config.get('font_size', 40),
        'enable_mood': config.get('enable_mood', True),
        'avatar_base_path': config.get('avatar_base_path', 'avatar'),
        'galgame_avatar': config.get('galgame_avatar', {}),
    }
    
    # 运行流程
    print(f"\n🎬 开始生成视频...")
    print(f"   音频目录: {config['audio_dir']}")
    print(f"   输出文件: {output_path}")
    print(f"   背景类型: {config['background_type']}")
    print(f"   段落间隔: {config['transition_duration']}秒")
    
    pipeline = AudioVideoPipeline(video_config)
    
    try:
        output = pipeline.run(
            audio_dir=config['audio_dir'],
            markdown_path=config['markdown_file'],
            output_path=output_path,
            background_type=config['background_type'],
            background_path=config['background_image'] if config['background_type'] == 'image' else None,
            title=config['title'] if config['show_intro'] else None,
            subtitle=config['subtitle'] if config['show_intro'] else None,
            transition_duration=config['transition_duration']
        )
        print(f"\n✅ 视频播客生成成功!")
        print(f"📁 文件位置: {output}")
    except Exception as e:
        print(f"\n❌ 生成失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
