#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ISP-CSIIR 随机Pattern生成器

生成多种类型的随机测试Pattern，包括：
- random: 完全随机像素
- gradient: 随机方向梯度
- edge: 随机位置边缘
- corner: 随机角点
- extreme: 极值测试（全0、全1023、交替0/1023）
- textured: 纹理图案

作者: rtl-verf
日期: 2026-03-23
版本: v1.0
"""

import os
import sys
import json
import random
import numpy as np
from typing import Tuple, List, Dict, Optional
from dataclasses import dataclass, asdict

# 导入约束定义
from random_verify_constraints import (
    ImageConstraints, PixelConstraints, ConfigConstraints,
    ConstraintValidator
)


# ============================================================
# 数据结构定义
# ============================================================
@dataclass
class TestCase:
    """
    测试用例数据结构

    包含测试Pattern和配置参数
    """
    # 用例标识
    case_id: str
    pattern_type: str
    seed: int

    # 图像参数
    width: int
    height: int

    # 配置参数
    win_thresh: List[int]
    grad_clip: List[int]
    blend_ratio: List[int]
    edge_protect: int

    # 图像数据
    image: Optional[np.ndarray] = None


@dataclass
class TestCaseMetadata:
    """
    测试用例元数据

    用于保存和加载测试用例
    """
    case_id: str
    pattern_type: str
    seed: int
    width: int
    height: int
    win_thresh: List[int]
    grad_clip: List[int]
    blend_ratio: List[int]
    edge_protect: int
    image_stats: Dict[str, float]


# ============================================================
# Pattern生成器
# ============================================================
class PatternGenerator:
    """
    随机Pattern生成器

    支持多种Pattern类型的生成
    """

    def __init__(self, seed: Optional[int] = None):
        """
        初始化生成器

        Args:
            seed: 随机种子，用于可复现性
        """
        self.seed = seed if seed is not None else random.randint(0, 2**31 - 1)
        self.rng = np.random.RandomState(self.seed)
        random.seed(self.seed)

        self.pix_const = PixelConstraints()
        self.img_const = ImageConstraints()

    def generate_random(self, width: int, height: int) -> np.ndarray:
        """
        生成完全随机像素Pattern

        每个像素独立随机取值
        """
        return self.rng.randint(
            self.pix_const.MIN_VALUE,
            self.pix_const.MAX_VALUE + 1,
            (height, width),
            dtype=np.uint16
        )

    def generate_gradient(self, width: int, height: int) -> np.ndarray:
        """
        生成随机方向梯度Pattern

        随机选择梯度方向：水平、垂直、对角线
        """
        image = np.zeros((height, width), dtype=np.uint16)
        direction = self.rng.choice(['horizontal', 'vertical', 'diagonal', 'radial'])

        if direction == 'horizontal':
            # 水平梯度
            for col in range(width):
                value = int(col * self.pix_const.MAX_VALUE / max(width - 1, 1))
                image[:, col] = value

        elif direction == 'vertical':
            # 垂直梯度
            for row in range(height):
                value = int(row * self.pix_const.MAX_VALUE / max(height - 1, 1))
                image[row, :] = value

        elif direction == 'diagonal':
            # 对角线梯度
            for row in range(height):
                for col in range(width):
                    value = int((row + col) * self.pix_const.MAX_VALUE / max(width + height - 2, 1))
                    image[row, col] = min(value, self.pix_const.MAX_VALUE)

        else:  # radial
            # 径向梯度
            center_x = width // 2
            center_y = height // 2
            max_dist = np.sqrt(center_x**2 + center_y**2)

            for row in range(height):
                for col in range(width):
                    dist = np.sqrt((col - center_x)**2 + (row - center_y)**2)
                    value = int((1 - dist / max_dist) * self.pix_const.MAX_VALUE)
                    image[row, col] = max(0, min(value, self.pix_const.MAX_VALUE))

        return image

    def generate_edge(self, width: int, height: int) -> np.ndarray:
        """
        生成随机边缘Pattern

        在随机位置放置边缘
        """
        image = np.full((height, width), self.pix_const.MID_VALUE, dtype=np.uint16)

        edge_type = self.rng.choice(['vertical', 'horizontal', 'diagonal', 'cross', 'multiple'])

        if edge_type == 'vertical':
            # 垂直边缘
            edge_col = self.rng.randint(width // 4, 3 * width // 4)
            low_val = self.rng.randint(0, 300)
            high_val = self.rng.randint(700, 1024)
            image[:, :edge_col] = low_val
            image[:, edge_col:] = high_val

        elif edge_type == 'horizontal':
            # 水平边缘
            edge_row = self.rng.randint(height // 4, 3 * height // 4)
            low_val = self.rng.randint(0, 300)
            high_val = self.rng.randint(700, 1024)
            image[:edge_row, :] = low_val
            image[edge_row:, :] = high_val

        elif edge_type == 'diagonal':
            # 对角边缘
            low_val = self.rng.randint(0, 300)
            high_val = self.rng.randint(700, 1024)
            for row in range(height):
                edge_col = int(row * width / height)
                image[row, :edge_col] = low_val
                image[row, edge_col:] = high_val

        elif edge_type == 'cross':
            # 十字交叉边缘
            mid_row = height // 2
            mid_col = width // 2
            image[mid_row-1:mid_row+2, :] = self.rng.randint(800, 1024)
            image[:, mid_col-1:mid_col+2] = self.rng.randint(800, 1024)

        else:  # multiple
            # 多条边缘
            num_edges = self.rng.randint(2, 5)
            for _ in range(num_edges):
                edge_col = self.rng.randint(0, width)
                image[:, max(0, edge_col-1):min(width, edge_col+2)] = self.rng.randint(0, 1024)

        return image

    def generate_corner(self, width: int, height: int) -> np.ndarray:
        """
        生成随机角点Pattern

        在随机位置放置角点特征
        """
        image = np.full((height, width), self.pix_const.MID_VALUE, dtype=np.uint16)

        corner_type = self.rng.choice(['single', 'multiple', 'l_shape', 'rectangle'])

        if corner_type == 'single':
            # 单个角点
            corner_x = self.rng.randint(width // 4, 3 * width // 4)
            corner_y = self.rng.randint(height // 4, 3 * height // 4)
            intensity = self.rng.randint(800, 1024)
            image[corner_y-2:corner_y+3, corner_x-2:corner_x+3] = intensity

        elif corner_type == 'multiple':
            # 多个角点
            num_corners = self.rng.randint(3, 8)
            for _ in range(num_corners):
                cx = self.rng.randint(2, width - 2)
                cy = self.rng.randint(2, height - 2)
                intensity = self.rng.randint(700, 1024)
                image[cy-1:cy+2, cx-1:cx+2] = intensity

        elif corner_type == 'l_shape':
            # L形角点
            cx = self.rng.randint(width // 4, 3 * width // 4)
            cy = self.rng.randint(height // 4, 3 * height // 4)
            arm_len = self.rng.randint(5, max(6, min(width, height) // 4))
            intensity = self.rng.randint(700, 1024)
            image[cy:cy+arm_len, cx:cx+2] = intensity
            image[cy:cy+2, cx:cx+arm_len] = intensity

        else:  # rectangle
            # 矩形（4个角点）
            x1 = self.rng.randint(0, width // 2)
            y1 = self.rng.randint(0, height // 2)
            x2 = self.rng.randint(width // 2, width)
            y2 = self.rng.randint(height // 2, height)
            intensity = self.rng.randint(700, 1024)
            image[y1:y2, x1:x1+2] = intensity
            image[y1:y2, x2-2:x2] = intensity
            image[y1:y1+2, x1:x2] = intensity
            image[y2-2:y2, x1:x2] = intensity

        return image

    def generate_extreme(self, width: int, height: int) -> np.ndarray:
        """
        生成极值测试Pattern

        测试边界值处理
        """
        extreme_type = self.rng.choice([
            'all_zero', 'all_max', 'alternating', 'checkerboard',
            'mostly_zero', 'mostly_max', 'sparse_peaks'
        ])

        if extreme_type == 'all_zero':
            # 全零图像
            return np.zeros((height, width), dtype=np.uint16)

        elif extreme_type == 'all_max':
            # 全最大值图像
            return np.full((height, width), self.pix_const.MAX_VALUE, dtype=np.uint16)

        elif extreme_type == 'alternating':
            # 交替0和最大值
            image = np.zeros((height, width), dtype=np.uint16)
            image[::2, ::2] = self.pix_const.MAX_VALUE
            image[1::2, 1::2] = self.pix_const.MAX_VALUE
            return image

        elif extreme_type == 'checkerboard':
            # 棋盘格（0和1023）
            image = np.zeros((height, width), dtype=np.uint16)
            block_size = self.rng.randint(2, 8)
            for row in range(height):
                for col in range(width):
                    if ((row // block_size) + (col // block_size)) % 2 == 0:
                        image[row, col] = self.pix_const.MAX_VALUE
            return image

        elif extreme_type == 'mostly_zero':
            # 大部分为0，少量非零
            image = np.zeros((height, width), dtype=np.uint16)
            num_peaks = self.rng.randint(1, max(2, width * height // 50))
            for _ in range(num_peaks):
                r, c = self.rng.randint(0, height), self.rng.randint(0, width)
                image[r, c] = self.rng.randint(800, 1024)
            return image

        elif extreme_type == 'mostly_max':
            # 大部分为最大值，少量低值
            image = np.full((height, width), self.pix_const.MAX_VALUE, dtype=np.uint16)
            num_valleys = self.rng.randint(1, max(2, width * height // 50))
            for _ in range(num_valleys):
                r, c = self.rng.randint(0, height), self.rng.randint(0, width)
                image[r, c] = self.rng.randint(0, 200)
            return image

        else:  # sparse_peaks
            # 稀疏峰值
            image = np.zeros((height, width), dtype=np.uint16)
            num_peaks = self.rng.randint(3, 10)
            for _ in range(num_peaks):
                cx = self.rng.randint(0, width)
                cy = self.rng.randint(0, height)
                radius = self.rng.randint(1, 4)
                intensity = self.pix_const.MAX_VALUE
                for dr in range(-radius, radius + 1):
                    for dc in range(-radius, radius + 1):
                        r, c = cy + dr, cx + dc
                        if 0 <= r < height and 0 <= c < width:
                            image[r, c] = intensity
            return image

    def generate_textured(self, width: int, height: int) -> np.ndarray:
        """
        生成纹理Pattern

        包含周期性和非周期性纹理
        """
        texture_type = self.rng.choice([
            'sine_wave', 'stripe', 'noise_with_regions', 'blended_patterns'
        ])

        if texture_type == 'sine_wave':
            # 正弦波纹理
            freq = self.rng.uniform(0.05, 0.2)
            direction = self.rng.choice(['horizontal', 'vertical', 'diagonal'])
            image = np.zeros((height, width), dtype=np.uint16)

            for row in range(height):
                for col in range(width):
                    if direction == 'horizontal':
                        phase = col * freq * 2 * np.pi
                    elif direction == 'vertical':
                        phase = row * freq * 2 * np.pi
                    else:
                        phase = (row + col) * freq * 2 * np.pi

                    value = int(512 + 400 * np.sin(phase))
                    image[row, col] = max(0, min(value, 1023))

            return image

        elif texture_type == 'stripe':
            # 条纹纹理
            stripe_width = self.rng.randint(4, 16)
            val1 = self.rng.randint(100, 400)
            val2 = self.rng.randint(600, 900)
            direction = self.rng.choice(['horizontal', 'vertical'])

            image = np.zeros((height, width), dtype=np.uint16)
            for row in range(height):
                for col in range(width):
                    if direction == 'horizontal':
                        idx = row // stripe_width
                    else:
                        idx = col // stripe_width

                    image[row, col] = val1 if idx % 2 == 0 else val2

            return image

        elif texture_type == 'noise_with_regions':
            # 带区域划分的噪声
            image = self.rng.randint(200, 400, (height, width), dtype=np.uint16)

            # 添加几个高亮区域
            num_regions = self.rng.randint(2, 5)
            for _ in range(num_regions):
                x = self.rng.randint(0, max(1, width - width // 4))
                y = self.rng.randint(0, max(1, height - height // 4))
                w = self.rng.randint(max(1, width // 8), max(2, width // 4))
                h = self.rng.randint(max(1, height // 8), max(2, height // 4))
                image[y:y+h, x:x+w] = self.rng.randint(600, 900, (h, w), dtype=np.uint16)

            return image

        else:  # blended_patterns
            # 混合Pattern
            # 基础梯度
            base = np.zeros((height, width), dtype=np.float32)
            for col in range(width):
                base[:, col] = col * 1023 / max(width - 1, 1)

            # 添加噪声
            noise = self.rng.randint(-100, 100, (height, width))
            blended = base + noise

            # 裁剪到有效范围
            image = np.clip(blended, 0, 1023).astype(np.uint16)
            return image

    def generate(self, pattern_type: str, width: int, height: int) -> np.ndarray:
        """
        根据类型生成Pattern

        Args:
            pattern_type: Pattern类型
            width: 图像宽度
            height: 图像高度

        Returns:
            生成的图像数组
        """
        generators = {
            'random': self.generate_random,
            'gradient': self.generate_gradient,
            'edge': self.generate_edge,
            'corner': self.generate_corner,
            'extreme': self.generate_extreme,
            'textured': self.generate_textured,
        }

        if pattern_type not in generators:
            raise ValueError(f"未知的Pattern类型: {pattern_type}")

        return generators[pattern_type](width, height)


# ============================================================
# 配置生成器
# ============================================================
class ConfigGenerator:
    """
    随机配置参数生成器

    生成满足约束的配置参数
    """

    def __init__(self, seed: Optional[int] = None):
        self.seed = seed if seed is not None else random.randint(0, 2**31 - 1)
        self.rng = np.random.RandomState(self.seed)
        random.seed(self.seed)

        self.cfg_const = ConfigConstraints()

    def generate_win_thresh(self) -> List[int]:
        """
        生成窗口阈值配置

        生成4个递增的阈值
        """
        # 生成4个随机间隔
        min_val = self.cfg_const.WIN_THRESH_MIN
        max_val = self.cfg_const.WIN_THRESH_MAX
        range_size = max_val - min_val

        # 确保至少有4个可区分的值
        step = max(range_size // 5, 1)

        # 生成随机基础值
        base = self.rng.randint(min_val, max_val - 3 * step)

        # 生成递增序列
        values = []
        current = base
        for i in range(4):
            increment = self.rng.randint(step, step * 2 + 1)
            current = min(current + increment, max_val)
            values.append(current)

        # 确保严格递增
        result = [values[0]]
        for i in range(1, 4):
            result.append(max(values[i], result[-1] + 1))

        return result

    def generate_grad_clip(self) -> List[int]:
        """
        生成梯度裁剪配置

        生成4个递增的阈值
        """
        min_val = self.cfg_const.GRAD_CLIP_MIN
        max_val = self.cfg_const.GRAD_CLIP_MAX
        range_size = max_val - min_val

        step = max(range_size // 5, 1)
        base = self.rng.randint(min_val, max_val - 3 * step)

        values = []
        current = base
        for i in range(4):
            increment = self.rng.randint(step, step * 2 + 1)
            current = min(current + increment, max_val)
            values.append(current)

        result = [values[0]]
        for i in range(1, 4):
            result.append(max(values[i], result[-1] + 1))

        return result

    def generate_blend_ratio(self) -> List[int]:
        """
        生成混合比例配置

        可以是任意值，不要求递增
        """
        return [
            self.rng.randint(self.cfg_const.BLEND_RATIO_MIN, self.cfg_const.BLEND_RATIO_MAX + 1)
            for _ in range(4)
        ]

    def generate_edge_protect(self) -> int:
        """生成边缘保护系数"""
        return self.rng.randint(
            self.cfg_const.EDGE_PROTECT_MIN,
            self.cfg_const.EDGE_PROTECT_MAX + 1
        )

    def generate_config(self) -> Dict[str, List[int]]:
        """生成完整配置"""
        return {
            'win_thresh': self.generate_win_thresh(),
            'grad_clip': self.generate_grad_clip(),
            'blend_ratio': self.generate_blend_ratio(),
            'edge_protect': self.generate_edge_protect()
        }


# ============================================================
# 测试用例生成器
# ============================================================
class TestCaseGenerator:
    """
    测试用例生成器

    生成完整的测试用例，包括图像和配置
    """

    def __init__(self, output_dir: str, seed: Optional[int] = None):
        """
        初始化生成器

        Args:
            output_dir: 输出目录
            seed: 随机种子
        """
        self.output_dir = output_dir
        self.seed = seed if seed is not None else random.randint(0, 2**31 - 1)

        self.pattern_gen = PatternGenerator(self.seed)
        self.config_gen = ConfigGenerator(self.seed + 1)  # 不同种子增加多样性

        self.img_const = ImageConstraints()
        self.validator = ConstraintValidator()

    def generate_size(self) -> Tuple[int, int]:
        """生成随机图像尺寸"""
        # 50%概率使用预设尺寸，50%完全随机
        if random.random() < 0.5:
            return random.choice(self.img_const.PRESET_SIZES)
        else:
            width = random.randint(self.img_const.WIDTH_MIN, self.img_const.WIDTH_MAX)
            height = random.randint(self.img_const.HEIGHT_MIN, self.img_const.HEIGHT_MAX)
            return width, height

    def generate_test_case(self, case_id: str, pattern_type: Optional[str] = None) -> TestCase:
        """
        生成单个测试用例

        Args:
            case_id: 用例ID
            pattern_type: 指定Pattern类型，None则随机选择

        Returns:
            TestCase对象
        """
        # 选择Pattern类型
        if pattern_type is None:
            pattern_weights = {
                'random': 30,
                'gradient': 20,
                'edge': 15,
                'corner': 10,
                'extreme': 10,
                'textured': 15,
            }
            pattern_type = random.choices(
                list(pattern_weights.keys()),
                weights=list(pattern_weights.values())
            )[0]

        # 生成尺寸
        width, height = self.generate_size()

        # 生成图像
        image = self.pattern_gen.generate(pattern_type, width, height)

        # 生成配置
        config = self.config_gen.generate_config()

        # 创建测试用例
        test_case = TestCase(
            case_id=case_id,
            pattern_type=pattern_type,
            seed=self.seed,
            width=width,
            height=height,
            win_thresh=config['win_thresh'],
            grad_clip=config['grad_clip'],
            blend_ratio=config['blend_ratio'],
            edge_protect=config['edge_protect'],
            image=image
        )

        return test_case

    def save_test_case(self, test_case: TestCase) -> str:
        """
        保存测试用例到文件

        Args:
            test_case: 测试用例对象

        Returns:
            保存的文件路径
        """
        # 创建用例目录
        case_dir = os.path.join(self.output_dir, test_case.case_id)
        os.makedirs(case_dir, exist_ok=True)

        # 保存图像
        image_file = os.path.join(case_dir, 'input.txt')
        height, width = test_case.image.shape
        with open(image_file, 'w') as f:
            for row in range(height):
                for col in range(width):
                    f.write(f"{test_case.image[row, col]}\n")

        # 保存配置
        config_file = os.path.join(case_dir, 'config.json')
        config = {
            'case_id': test_case.case_id,
            'pattern_type': test_case.pattern_type,
            'seed': test_case.seed,
            'width': test_case.width,
            'height': test_case.height,
            'win_thresh': test_case.win_thresh,
            'grad_clip': test_case.grad_clip,
            'blend_ratio': test_case.blend_ratio,
            'edge_protect': test_case.edge_protect,
        }
        with open(config_file, 'w') as f:
            json.dump(config, f, indent=2)

        # 保存元数据
        metadata = TestCaseMetadata(
            case_id=test_case.case_id,
            pattern_type=test_case.pattern_type,
            seed=test_case.seed,
            width=test_case.width,
            height=test_case.height,
            win_thresh=test_case.win_thresh,
            grad_clip=test_case.grad_clip,
            blend_ratio=test_case.blend_ratio,
            edge_protect=test_case.edge_protect,
            image_stats={
                'min': float(np.min(test_case.image)),
                'max': float(np.max(test_case.image)),
                'mean': float(np.mean(test_case.image)),
                'std': float(np.std(test_case.image))
            }
        )

        return case_dir

    def generate_batch(self, num_cases: int, start_id: int = 0) -> List[str]:
        """
        批量生成测试用例

        Args:
            num_cases: 生成数量
            start_id: 起始ID

        Returns:
            生成的用例目录列表
        """
        case_dirs = []

        for i in range(num_cases):
            case_id = f"case_{start_id + i:04d}"

            # 更新种子
            self.pattern_gen.rng = np.random.RandomState(self.seed + i * 2)
            self.config_gen.rng = np.random.RandomState(self.seed + i * 2 + 1)
            random.seed(self.seed + i)

            test_case = self.generate_test_case(case_id)
            case_dir = self.save_test_case(test_case)
            case_dirs.append(case_dir)

            print(f"  生成: {case_id} ({test_case.pattern_type}, {test_case.width}x{test_case.height})")

        return case_dirs


# ============================================================
# 命令行接口
# ============================================================
def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description='ISP-CSIIR 随机Pattern生成器')
    parser.add_argument('-n', '--num-cases', type=int, default=10,
                        help='生成的测试用例数量（默认10）')
    parser.add_argument('-s', '--seed', type=int, default=None,
                        help='随机种子')
    parser.add_argument('-o', '--output', type=str, default=None,
                        help='输出目录')
    parser.add_argument('-p', '--pattern', type=str, default=None,
                        choices=['random', 'gradient', 'edge', 'corner', 'extreme', 'textured'],
                        help='指定Pattern类型')

    args = parser.parse_args()

    # 设置输出目录
    script_dir = os.path.dirname(os.path.abspath(__file__))
    if args.output:
        output_dir = args.output
    else:
        output_dir = os.path.join(os.path.dirname(script_dir), 'test_vectors', 'random')

    print("=" * 50)
    print("ISP-CSIIR 随机Pattern生成器")
    print("=" * 50)
    print(f"输出目录: {output_dir}")
    print(f"测试数量: {args.num_cases}")
    print(f"随机种子: {args.seed if args.seed else '随机'}")
    print(f"Pattern类型: {args.pattern if args.pattern else '随机'}")

    # 创建输出目录
    os.makedirs(output_dir, exist_ok=True)

    # 生成测试用例
    generator = TestCaseGenerator(output_dir, args.seed)

    print(f"\n生成测试用例:")
    case_dirs = generator.generate_batch(args.num_cases)

    print(f"\n完成！共生成 {len(case_dirs)} 个测试用例")
    print(f"保存在: {output_dir}")


if __name__ == "__main__":
    main()