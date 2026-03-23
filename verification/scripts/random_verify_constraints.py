#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ISP-CSIIR 随机验证约束定义

定义随机测试生成器的约束范围，确保生成的测试用例
在有效范围内并且能够覆盖关键边界条件。

作者: rtl-verf
日期: 2026-03-23
版本: v1.0
"""

from dataclasses import dataclass
from typing import List, Tuple


@dataclass
class ImageConstraints:
    """
    图像尺寸约束

    定义随机生成图像的尺寸范围
    """
    # 图像宽度范围
    WIDTH_MIN: int = 16
    WIDTH_MAX: int = 128

    # 图像高度范围
    HEIGHT_MIN: int = 16
    HEIGHT_MAX: int = 128

    # 推荐的测试尺寸（覆盖典型场景）
    PRESET_SIZES: Tuple[Tuple[int, int], ...] = (
        (16, 16),    # 最小尺寸
        (32, 32),    # 小尺寸
        (64, 64),    # 标准尺寸
        (80, 60),    # 非对称尺寸
        (128, 128),  # 大尺寸
    )


@dataclass
class PixelConstraints:
    """
    像素值约束

    定义像素值的范围和特殊值
    """
    # 像素值范围（10-bit）
    MIN_VALUE: int = 0
    MAX_VALUE: int = 1023

    # 中间灰度值
    MID_VALUE: int = 512

    # 常用测试值
    TEST_VALUES: Tuple[int, ...] = (
        0,      # 最小值
        255,    # 低亮度
        511,    # 中间值附近
        512,    # 中间值
        513,    # 中间值附近
        768,    # 高亮度
        1023,   # 最大值
    )

    # 边界测试值对
    BOUNDARY_PAIRS: Tuple[Tuple[int, int], ...] = (
        (0, 1023),      # 极端对比
        (0, 512),       # 暗区到中间
        (512, 1023),    # 中间到亮区
        (256, 768),     # 温和对比
    )


@dataclass
class ConfigConstraints:
    """
    配置参数约束

    定义ISP-CSIIR处理参数的有效范围
    """
    # win_thresh: 窗口阈值，控制多尺度平均的核选择
    # 范围 [8, 48]，必须递增顺序
    WIN_THRESH_MIN: int = 8
    WIN_THRESH_MAX: int = 48
    WIN_THRESH_COUNT: int = 4  # 固定4个阈值

    # grad_clip: 梯度裁剪阈值，控制自适应窗口大小
    # 范围 [8, 48]，必须递增顺序
    GRAD_CLIP_MIN: int = 8
    GRAD_CLIP_MAX: int = 48
    GRAD_CLIP_COUNT: int = 4  # 固定4个阈值

    # blend_ratio: 混合比例
    # 范围 [0, 64]，控制平滑强度
    BLEND_RATIO_MIN: int = 0
    BLEND_RATIO_MAX: int = 64
    BLEND_RATIO_COUNT: int = 4  # 固定4个比例

    # edge_protect: 边缘保护系数
    EDGE_PROTECT_MIN: int = 0
    EDGE_PROTECT_MAX: int = 64
    EDGE_PROTECT_DEFAULT: int = 32

    # 默认配置
    DEFAULT_WIN_THRESH: Tuple[int, int, int, int] = (16, 24, 32, 40)
    DEFAULT_GRAD_CLIP: Tuple[int, int, int, int] = (15, 23, 31, 39)
    DEFAULT_BLEND_RATIO: Tuple[int, int, int, int] = (32, 32, 32, 32)


@dataclass
class RandomTestConstraints:
    """
    随机测试约束

    定义随机测试生成器的全局约束
    """
    # 默认测试数量
    DEFAULT_TEST_COUNT: int = 100

    # 最大测试数量
    MAX_TEST_COUNT: int = 10000

    # 随机种子范围
    SEED_MIN: int = 0
    SEED_MAX: int = 2**31 - 1

    # Pattern类型分布权重
    PATTERN_WEIGHTS: dict = None

    def __post_init__(self):
        if self.PATTERN_WEIGHTS is None:
            self.PATTERN_WEIGHTS = {
                'random': 30,      # 完全随机
                'gradient': 20,    # 梯度图案
                'edge': 15,        # 边缘图案
                'corner': 10,      # 角点图案
                'extreme': 10,     # 极值测试
                'textured': 15,    # 纹理图案
            }


class ConstraintValidator:
    """
    约束验证器

    提供验证函数确保生成的参数满足约束
    """

    @staticmethod
    def validate_image_size(width: int, height: int) -> bool:
        """验证图像尺寸是否在有效范围内"""
        img_const = ImageConstraints()
        return (img_const.WIDTH_MIN <= width <= img_const.WIDTH_MAX and
                img_const.HEIGHT_MIN <= height <= img_const.HEIGHT_MAX)

    @staticmethod
    def validate_pixel_value(value: int) -> bool:
        """验证像素值是否在有效范围内"""
        pix_const = PixelConstraints()
        return pix_const.MIN_VALUE <= value <= pix_const.MAX_VALUE

    @staticmethod
    def validate_win_thresh(win_thresh: List[int]) -> bool:
        """
        验证窗口阈值是否有效

        要求:
        1. 长度为4
        2. 每个值在有效范围内
        3. 严格递增
        """
        cfg_const = ConfigConstraints()

        if len(win_thresh) != cfg_const.WIN_THRESH_COUNT:
            return False

        for val in win_thresh:
            if not (cfg_const.WIN_THRESH_MIN <= val <= cfg_const.WIN_THRESH_MAX):
                return False

        # 检查严格递增
        for i in range(len(win_thresh) - 1):
            if win_thresh[i] >= win_thresh[i + 1]:
                return False

        return True

    @staticmethod
    def validate_grad_clip(grad_clip: List[int]) -> bool:
        """
        验证梯度裁剪阈值是否有效

        要求同 win_thresh
        """
        cfg_const = ConfigConstraints()

        if len(grad_clip) != cfg_const.GRAD_CLIP_COUNT:
            return False

        for val in grad_clip:
            if not (cfg_const.GRAD_CLIP_MIN <= val <= cfg_const.GRAD_CLIP_MAX):
                return False

        # 检查严格递增
        for i in range(len(grad_clip) - 1):
            if grad_clip[i] >= grad_clip[i + 1]:
                return False

        return True

    @staticmethod
    def validate_blend_ratio(blend_ratio: List[int]) -> bool:
        """验证混合比例是否有效"""
        cfg_const = ConfigConstraints()

        if len(blend_ratio) != cfg_const.BLEND_RATIO_COUNT:
            return False

        for val in blend_ratio:
            if not (cfg_const.BLEND_RATIO_MIN <= val <= cfg_const.BLEND_RATIO_MAX):
                return False

        return True

    @staticmethod
    def validate_config(win_thresh: List[int], grad_clip: List[int],
                        blend_ratio: List[int]) -> Tuple[bool, str]:
        """
        验证完整配置

        Returns:
            (是否有效, 错误信息)
        """
        if not ConstraintValidator.validate_win_thresh(win_thresh):
            return False, "win_thresh 无效：需要4个递增值，范围[8, 48]"

        if not ConstraintValidator.validate_grad_clip(grad_clip):
            return False, "grad_clip 无效：需要4个递增值，范围[8, 48]"

        if not ConstraintValidator.validate_blend_ratio(blend_ratio):
            return False, "blend_ratio 无效：需要4个值，范围[0, 64]"

        return True, "配置有效"


def get_constraint_summary() -> str:
    """
    获取约束摘要信息

    Returns:
        约束描述字符串
    """
    img_const = ImageConstraints()
    pix_const = PixelConstraints()
    cfg_const = ConfigConstraints()
    rand_const = RandomTestConstraints()

    summary = """
========================================
ISP-CSIIR 随机验证约束摘要
========================================

图像尺寸约束:
  - 宽度: [%d, %d]
  - 高度: [%d, %d]

像素值约束:
  - 范围: [%d, %d] (10-bit)
  - 中间值: %d

配置参数约束:
  - win_thresh: [%d, %d], 4个递增值
  - grad_clip: [%d, %d], 4个递增值
  - blend_ratio: [%d, %d], 4个值
  - edge_protect: [%d, %d]

默认配置:
  - win_thresh: %s
  - grad_clip: %s
  - blend_ratio: %s

Pattern类型分布:
""" % (
        img_const.WIDTH_MIN, img_const.WIDTH_MAX,
        img_const.HEIGHT_MIN, img_const.HEIGHT_MAX,
        pix_const.MIN_VALUE, pix_const.MAX_VALUE, pix_const.MID_VALUE,
        cfg_const.WIN_THRESH_MIN, cfg_const.WIN_THRESH_MAX,
        cfg_const.GRAD_CLIP_MIN, cfg_const.GRAD_CLIP_MAX,
        cfg_const.BLEND_RATIO_MIN, cfg_const.BLEND_RATIO_MAX,
        cfg_const.EDGE_PROTECT_MIN, cfg_const.EDGE_PROTECT_MAX,
        cfg_const.DEFAULT_WIN_THRESH,
        cfg_const.DEFAULT_GRAD_CLIP,
        cfg_const.DEFAULT_BLEND_RATIO
    )

    for pattern, weight in rand_const.PATTERN_WEIGHTS.items():
        summary += f"  - {pattern}: {weight}%\n"

    summary += "========================================\n"

    return summary


# ============================================================
# 导出接口
# ============================================================
__all__ = [
    'ImageConstraints',
    'PixelConstraints',
    'ConfigConstraints',
    'RandomTestConstraints',
    'ConstraintValidator',
    'get_constraint_summary'
]


# ============================================================
# 测试入口
# ============================================================
if __name__ == "__main__":
    print(get_constraint_summary())

    # 测试验证器
    validator = ConstraintValidator()

    print("\n约束验证测试:")

    # 测试有效配置
    valid, msg = validator.validate_config([16, 24, 32, 40], [15, 23, 31, 39], [32, 32, 32, 32])
    print(f"  有效配置: {valid} - {msg}")

    # 测试无效配置
    valid, msg = validator.validate_config([16, 24, 24, 40], [15, 23, 31, 39], [32, 32, 32, 32])
    print(f"  无效win_thresh: {valid} - {msg}")

    valid, msg = validator.validate_config([16, 24, 32, 40], [15, 10, 31, 39], [32, 32, 32, 32])
    print(f"  无效grad_clip: {valid} - {msg}")

    print("\n约束模块测试完成!")