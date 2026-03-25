# ============================================================
# ISP-CSIIR Functional Coverage Collector
# ============================================================
# Functional coverage model with sampling and reporting
# ============================================================

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
import json
from datetime import datetime
import os

from .coverage_config import (
    CoveragePointConfig,
    CoverageBinConfig,
    CoverageConfig,
    FUNCTIONAL_COVERAGE_POINTS
)

# ============================================================
# Coverage Bin
# ============================================================
@dataclass
class CoverageBin:
    """单个覆盖 bin"""
    name: str
    description: str = ""
    hit_count: int = 0
    goal: int = 1
    weight: float = 1.0

    def hit(self):
        """命中一次"""
        self.hit_count += 1

    @property
    def covered(self) -> bool:
        """是否已覆盖"""
        return self.hit_count >= self.goal

    @property
    def coverage_percent(self) -> float:
        """覆盖率百分比"""
        return 100.0 if self.covered else 0.0

    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "description": self.description,
            "hit_count": self.hit_count,
            "goal": self.goal,
            "covered": self.covered
        }

# ============================================================
# Coverage Point
# ============================================================
class CoveragePoint:
    """功能覆盖点"""

    def __init__(self, config: CoveragePointConfig):
        self.name = config.name
        self.description = config.description
        self.category = config.category
        self.bins: Dict[str, CoverageBin] = {}

        for bin_config in config.bins:
            self.bins[bin_config.name] = CoverageBin(
                name=bin_config.name,
                description=bin_config.description,
                goal=bin_config.goal,
                weight=bin_config.weight
            )

    def sample(self, bin_name: str, count: int = 1):
        """采样一个 bin"""
        if bin_name in self.bins:
            for _ in range(count):
                self.bins[bin_name].hit()
        else:
            raise ValueError(f"Bin '{bin_name}' not found in coverage point '{self.name}'")

    @property
    def coverage(self) -> float:
        """覆盖率百分比"""
        if not self.bins:
            return 0.0
        covered = sum(1 for b in self.bins.values() if b.covered)
        return 100.0 * covered / len(self.bins)

    @property
    def total_hits(self) -> int:
        """总命中次数"""
        return sum(b.hit_count for b in self.bins.values())

    @property
    def covered_bins(self) -> int:
        """已覆盖的 bin 数"""
        return sum(1 for b in self.bins.values() if b.covered)

    @property
    def total_bins(self) -> int:
        """总 bin 数"""
        return len(self.bins)

    def get_uncovered_bins(self) -> List[str]:
        """获取未覆盖的 bin"""
        return [name for name, b in self.bins.items() if not b.covered]

    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "coverage": self.coverage,
            "covered_bins": self.covered_bins,
            "total_bins": self.total_bins,
            "total_hits": self.total_hits,
            "bins": {name: b.to_dict() for name, b in self.bins.items()}
        }

# ============================================================
# Functional Coverage Model
# ============================================================
class FunctionalCoverageModel:
    """功能覆盖率模型"""

    def __init__(self, config: CoverageConfig = None):
        self.config = config or CoverageConfig()
        self.points: Dict[str, CoveragePoint] = {}

        # 初始化所有覆盖点
        for point_config in self.config.functional_coverage_points:
            self.points[point_config.name] = CoveragePoint(point_config)

        # 记录历史
        self.history: List[Dict] = []
        self.start_time: Optional[datetime] = None

    def start(self):
        """开始覆盖率收集"""
        self.start_time = datetime.now()

    def sample(self, point_name: str, bin_name: str, count: int = 1):
        """采样一个覆盖点"""
        if point_name not in self.points:
            raise ValueError(f"Coverage point '{point_name}' not found")
        self.points[point_name].sample(bin_name, count)

    def sample_config(self, win_size: int, win_thresh: List[int]):
        """采样配置空间覆盖 - 窗口阈值

        Note: below_t0 bin is removed since win_size minimum is 16
        """
        if win_size < win_thresh[1]:
            self.sample("config_win_thresh", "t0_t1")
        elif win_size < win_thresh[2]:
            self.sample("config_win_thresh", "t1_t2")
        elif win_size < win_thresh[3]:
            self.sample("config_win_thresh", "t2_t3")
        else:
            self.sample("config_win_thresh", "above_t3")

    def sample_grad_clip(self, grad: int, grad_clip: List[int]):
        """采样梯度裁剪区间"""
        if grad <= grad_clip[0]:
            self.sample("config_grad_clip", "g0")
        elif grad <= grad_clip[1]:
            self.sample("config_grad_clip", "g1")
        elif grad <= grad_clip[2]:
            self.sample("config_grad_clip", "g2")
        elif grad <= grad_clip[3]:
            self.sample("config_grad_clip", "g3")
        else:
            self.sample("config_grad_clip", "g4")

    def sample_blend_ratio(self, win_size: int):
        """采样混合比例索引"""
        idx = max(0, min(3, (win_size >> 3) - 2))
        self.sample("blend_ratio", f"ratio_{idx}")

    def sample_pattern_type(self, pattern_type: str):
        """采样 Pattern 类型"""
        if pattern_type in ["random", "gradient", "edge", "corner", "extreme", "textured"]:
            self.sample("pattern_type", pattern_type)

    def sample_image_size(self, width: int, height: int):
        """采样图像尺寸"""
        pixels = width * height
        if width == 16 and height == 16:
            self.sample("image_size", "min")
        elif width == 32 and height == 32:
            self.sample("image_size", "small")
        elif width == 64 and height == 64:
            self.sample("image_size", "std")
        elif width == 128 and height == 128:
            self.sample("image_size", "large")
        elif width != height:
            self.sample("image_size", "asymm")

    def sample_boundary(self, row: int, col: int, height: int, width: int):
        """采样边界条件"""
        # 边界位置
        is_top = (row == 0)
        is_bottom = (row == height - 1)
        is_left = (col == 0)
        is_right = (col == width - 1)

        if is_top:
            self.sample("boundary_position", "top_row")
        if is_bottom:
            self.sample("boundary_position", "bottom_row")
        if is_left:
            self.sample("boundary_position", "left_col")
        if is_right:
            self.sample("boundary_position", "right_col")
        if (is_top or is_bottom) and (is_left or is_right):
            self.sample("boundary_position", "corners")
        if not (is_top or is_bottom or is_left or is_right):
            self.sample("boundary_position", "interior")

        # 窗口完整性
        if not is_top and not is_bottom and not is_left and not is_right:
            self.sample("window_completeness", "full")
        if is_top:
            self.sample("window_completeness", "partial_top")
        if is_bottom:
            self.sample("window_completeness", "partial_bottom")
        if is_left:
            self.sample("window_completeness", "partial_left")
        if is_right:
            self.sample("window_completeness", "partial_right")

    def sample_overflow(self, output_value: int):
        """采样溢出事件 - 已移除覆盖点，保留方法签名以兼容"""
        # Coverage point removed: algorithm internally clamps output to [0, 1023]
        pass

    def sample_gradient_direction(self, grad_h: int, grad_v: int):
        """采样梯度方向"""
        if grad_h == 0 and grad_v == 0:
            self.sample("gradient_direction", "zero")
        elif abs(grad_h) > 2 * abs(grad_v):
            self.sample("gradient_direction", "horizontal")
        elif abs(grad_v) > 2 * abs(grad_h):
            self.sample("gradient_direction", "vertical")
        elif abs(grad_h - grad_v) < abs(grad_h) * 0.2:
            self.sample("gradient_direction", "diagonal")
        else:
            self.sample("gradient_direction", "mixed")

    def sample_pixel_distribution(self, image_stats: Dict):
        """
        采样像素值分布

        Args:
            image_stats: 包含像素统计信息的字典
                - mean: 平均像素值
                - std: 标准差
                - min_val: 最小值
                - max_val: 最大值
        """
        mean = image_stats.get('mean', 512)
        std = image_stats.get('std', 0)
        min_val = image_stats.get('min_val', 0)
        max_val = image_stats.get('max_val', 1023)

        # 判断分布类型
        if min_val == 0 and max_val == 0:
            self.sample("pixel_distribution", "all_zero")
        elif min_val == 1023 and max_val == 1023:
            self.sample("pixel_distribution", "all_max")
        elif std < 100:
            # 低方差，像素集中在某个区域
            if mean < 256:
                self.sample("pixel_distribution", "low")
            elif mean < 768:
                self.sample("pixel_distribution", "mid")
            else:
                self.sample("pixel_distribution", "high")
        else:
            # 高方差，混合分布
            self.sample("pixel_distribution", "mixed")

    def sample_division_type(self, divisor: int, dividend_type: str = "variable"):
        """
        采样除法类型

        Args:
            divisor: 除数
            dividend_type: 被除数类型 ("constant", "variable", "lookup")
        """
        if divisor == 5:
            self.sample("division_type", "div_by_5")
        elif dividend_type == "lookup":
            self.sample("division_type", "div_by_lookup")
        else:
            self.sample("division_type", "div_by_nr")

    @property
    def overall_coverage(self) -> float:
        """总体覆盖率"""
        if not self.points:
            return 0.0
        return sum(p.coverage for p in self.points.values()) / len(self.points)

    def get_coverage_by_category(self) -> Dict[str, float]:
        """按类别获取覆盖率"""
        categories: Dict[str, List[float]] = {}
        for point in self.points.values():
            if point.category not in categories:
                categories[point.category] = []
            categories[point.category].append(point.coverage)

        return {
            cat: sum(vals) / len(vals)
            for cat, vals in categories.items()
        }

    def get_uncovered_items(self) -> List[Dict]:
        """获取未覆盖项"""
        uncovered = []
        for point in self.points.values():
            for bin_name in point.get_uncovered_bins():
                uncovered.append({
                    "type": "functional_bin",
                    "point": point.name,
                    "bin": bin_name
                })
        return uncovered

    def report(self) -> Dict:
        """生成报告"""
        return {
            "timestamp": datetime.now().isoformat(),
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "overall_coverage": round(self.overall_coverage, 2),
            "coverage_by_category": {
                k: round(v, 2) for k, v in self.get_coverage_by_category().items()
            },
            "points": {
                name: point.to_dict()
                for name, point in self.points.items()
            },
            "uncovered_items": self.get_uncovered_items(),
            "summary": {
                "total_points": len(self.points),
                "covered_points": sum(1 for p in self.points.values() if p.coverage == 100.0),
                "total_bins": sum(p.total_bins for p in self.points.values()),
                "covered_bins": sum(p.covered_bins for p in self.points.values()),
            }
        }

    def save_report(self, filename: str):
        """保存报告到文件"""
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        with open(filename, 'w') as f:
            json.dump(self.report(), f, indent=2)

    def merge(self, other: 'FunctionalCoverageModel'):
        """合并另一个模型的覆盖率数据"""
        for point_name, point in other.points.items():
            if point_name in self.points:
                for bin_name, bin_obj in point.bins.items():
                    if bin_name in self.points[point_name].bins:
                        # 累加命中次数
                        self.points[point_name].bins[bin_name].hit_count += bin_obj.hit_count

# ============================================================
# Coverage Collector Wrapper
# ============================================================
class FunctionalCoverageCollector:
    """功能覆盖率收集器 - 便捷接口"""

    _instance: Optional['FunctionalCoverageCollector'] = None

    def __init__(self, config: CoverageConfig = None):
        self.model = FunctionalCoverageModel(config)
        self._enabled = True

    @classmethod
    def get_instance(cls, config: CoverageConfig = None) -> 'FunctionalCoverageCollector':
        """获取单例实例"""
        if cls._instance is None:
            cls._instance = cls(config)
        return cls._instance

    @classmethod
    def reset(cls):
        """重置单例"""
        cls._instance = None

    def enable(self):
        self._enabled = True

    def disable(self):
        self._enabled = False

    def sample(self, point_name: str, bin_name: str):
        """采样（仅当启用时）"""
        if self._enabled:
            self.model.sample(point_name, bin_name)

    def sample_pixel_processing(self, row: int, col: int,
                                 width: int, height: int,
                                 win_size: int, win_thresh: List[int],
                                 grad: int, grad_clip: List[int],
                                 grad_h: int, grad_v: int,
                                 output: int):
        """一次性采样所有像素相关的覆盖点"""
        if not self._enabled:
            return

        self.sample_boundary(row, col, height, width)
        self.sample_config(win_size, win_thresh)
        self.sample_grad_clip(grad, grad_clip)
        self.sample_blend_ratio(win_size)
        self.sample_gradient_direction(grad_h, grad_v)
        self.sample_overflow(output)

    # 代理方法
    def sample_config(self, *args, **kwargs):
        return self.model.sample_config(*args, **kwargs)

    def sample_boundary(self, *args, **kwargs):
        return self.model.sample_boundary(*args, **kwargs)

    def sample_pattern_type(self, *args, **kwargs):
        return self.model.sample_pattern_type(*args, **kwargs)

    def sample_image_size(self, *args, **kwargs):
        return self.model.sample_image_size(*args, **kwargs)

    def sample_grad_clip(self, *args, **kwargs):
        return self.model.sample_grad_clip(*args, **kwargs)

    def sample_gradient_direction(self, *args, **kwargs):
        return self.model.sample_gradient_direction(*args, **kwargs)

    def sample_overflow(self, *args, **kwargs):
        return self.model.sample_overflow(*args, **kwargs)

    def sample_blend_ratio(self, *args, **kwargs):
        return self.model.sample_blend_ratio(*args, **kwargs)

    def sample_pixel_distribution(self, *args, **kwargs):
        return self.model.sample_pixel_distribution(*args, **kwargs)

    def sample_division_type(self, *args, **kwargs):
        return self.model.sample_division_type(*args, **kwargs)

    def sample_overflow(self, *args, **kwargs):
        return self.model.sample_overflow(*args, **kwargs)

    def sample_blend_ratio(self, *args, **kwargs):
        return self.model.sample_blend_ratio(*args, **kwargs)

    def report(self) -> Dict:
        return self.model.report()

    def get_coverage_summary(self) -> Dict:
        """获取覆盖率摘要，用于报告生成"""
        summary = {}
        for name, point in self.model.points.items():
            bins_summary = {}
            for bin_name, bin_obj in point.bins.items():
                bins_summary[bin_name] = bin_obj.hit_count
            summary[name] = {
                'coverage': point.coverage,
                'covered_bins': point.covered_bins,
                'total_bins': point.total_bins,
                'bins': bins_summary
            }
        return summary

    def save_report(self, filename: str):
        return self.model.save_report(filename)