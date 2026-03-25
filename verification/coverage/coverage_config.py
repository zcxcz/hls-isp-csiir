# ============================================================
# ISP-CSIIR Coverage Configuration
# ============================================================
# Defines coverage points, goals, and thresholds
# ============================================================

from dataclasses import dataclass, field
from typing import List, Dict, Any
from enum import Enum

# ============================================================
# Coverage Types
# ============================================================
class CoverageType(Enum):
    STATEMENT = "statement"
    BRANCH = "branch"
    CONDITION = "condition"
    FUNCTION = "function"
    MCDC = "mcdc"

class CoverageGoal(Enum):
    MINIMUM = 80
    RECOMMENDED = 95
    STRICT = 100

# ============================================================
# Configuration Classes
# ============================================================
@dataclass
class CodeCoverageConfig:
    """代码覆盖率配置"""
    enabled: bool = True
    line_coverage_goal: float = 100.0
    branch_coverage_goal: float = 100.0
    function_coverage_goal: float = 100.0

    # 编译选项
    coverage_flags: List[str] = field(default_factory=lambda: [
        "-fprofile-arcs",
        "-ftest-coverage",
        "-O0",
        "-g"
    ])

    # 排除文件
    exclude_files: List[str] = field(default_factory=lambda: [
        "tb_*.cpp",  # 排除测试台
        "*_test.cpp"
    ])

@dataclass
class CoverageBinConfig:
    """覆盖点 bin 配置"""
    name: str
    description: str = ""
    goal: int = 1  # 目标命中次数
    weight: float = 1.0  # 权重

@dataclass
class CoveragePointConfig:
    """功能覆盖点配置"""
    name: str
    description: str
    bins: List[CoverageBinConfig]
    category: str = "functional"

    def get_bin_names(self) -> List[str]:
        return [b.name for b in self.bins]

# ============================================================
# Functional Coverage Points Definition
# ============================================================
FUNCTIONAL_COVERAGE_POINTS: List[CoveragePointConfig] = [
    # FP-01: 配置空间覆盖
    CoveragePointConfig(
        name="config_win_thresh",
        description="窗口阈值区间覆盖",
        category="configuration",
        bins=[
            # Note: below_t0 is removed because win_size minimum is 16
            # and can never be below the minimum threshold
            CoverageBinConfig("t0_t1", "t0 <= win_size < t1", goal=10),
            CoverageBinConfig("t1_t2", "t1 <= win_size < t2", goal=10),
            CoverageBinConfig("t2_t3", "t2 <= win_size < t3", goal=10),
            CoverageBinConfig("above_t3", "win_size >= t3", goal=10),
        ]
    ),

    CoveragePointConfig(
        name="config_grad_clip",
        description="梯度裁剪区间覆盖",
        category="configuration",
        bins=[
            CoverageBinConfig("g0", "grad <= clip[0]", goal=10),
            CoverageBinConfig("g1", "clip[0] < grad <= clip[1]", goal=10),
            CoverageBinConfig("g2", "clip[1] < grad <= clip[2]", goal=10),
            CoverageBinConfig("g3", "clip[2] < grad <= clip[3]", goal=10),
            CoverageBinConfig("g4", "grad > clip[3]", goal=10),
        ]
    ),

    CoveragePointConfig(
        name="blend_ratio",
        description="混合比例值覆盖",
        category="configuration",
        bins=[
            CoverageBinConfig("ratio_0", "ratio idx = 0", goal=5),
            CoverageBinConfig("ratio_1", "ratio idx = 1", goal=5),
            CoverageBinConfig("ratio_2", "ratio idx = 2", goal=5),
            CoverageBinConfig("ratio_3", "ratio idx = 3", goal=5),
        ]
    ),

    # FP-02: 图像特征覆盖
    CoveragePointConfig(
        name="pattern_type",
        description="Pattern类型覆盖",
        category="image_feature",
        bins=[
            CoverageBinConfig("random", "随机噪声", goal=5),
            CoverageBinConfig("gradient", "梯度图像", goal=5),
            CoverageBinConfig("edge", "边缘图像", goal=5),
            CoverageBinConfig("corner", "角点图像", goal=5),
            CoverageBinConfig("extreme", "极值图像", goal=5),
            CoverageBinConfig("textured", "纹理图像", goal=5),
        ]
    ),

    CoveragePointConfig(
        name="image_size",
        description="图像尺寸覆盖",
        category="image_feature",
        bins=[
            CoverageBinConfig("min", "16x16", goal=3),
            CoverageBinConfig("small", "32x32", goal=5),
            CoverageBinConfig("std", "64x64", goal=5),
            CoverageBinConfig("large", "128x128", goal=5),
            CoverageBinConfig("asymm", "非对称尺寸", goal=5),
        ]
    ),

    CoveragePointConfig(
        name="pixel_distribution",
        description="像素值分布覆盖",
        category="image_feature",
        bins=[
            CoverageBinConfig("all_zero", "全零", goal=1),
            CoverageBinConfig("low", "低值区域 (0-255)", goal=10),
            CoverageBinConfig("mid", "中间值 (256-767)", goal=10),
            CoverageBinConfig("high", "高值区域 (768-1022)", goal=10),
            CoverageBinConfig("all_max", "全最大值", goal=1),
            CoverageBinConfig("mixed", "混合分布", goal=10),
        ]
    ),

    # FP-03: 边界条件覆盖
    CoveragePointConfig(
        name="boundary_position",
        description="边界位置覆盖",
        category="boundary",
        bins=[
            CoverageBinConfig("top_row", "顶行", goal=10),
            CoverageBinConfig("bottom_row", "底行", goal=10),
            CoverageBinConfig("left_col", "左列", goal=10),
            CoverageBinConfig("right_col", "右列", goal=10),
            CoverageBinConfig("corners", "四角", goal=5),
            CoverageBinConfig("interior", "内部像素", goal=100),
        ]
    ),

    CoveragePointConfig(
        name="window_completeness",
        description="5x5窗口完整性覆盖",
        category="boundary",
        bins=[
            CoverageBinConfig("full", "完整窗口", goal=100),
            CoverageBinConfig("partial_top", "顶部不完整", goal=10),
            CoverageBinConfig("partial_bottom", "底部不完整", goal=10),
            CoverageBinConfig("partial_left", "左侧不完整", goal=10),
            CoverageBinConfig("partial_right", "右侧不完整", goal=10),
        ]
    ),

    # FP-04: 数据通路覆盖
    # Note: overflow_event is removed because the algorithm internally clamps
    # output to [0, 1023], making overflow/underflow impossible
    CoveragePointConfig(
        name="division_type",
        description="除法类型覆盖",
        category="data_path",
        bins=[
            CoverageBinConfig("div_by_5", "除以5近似", goal=50),
            CoverageBinConfig("div_by_lookup", "查表除法", goal=50),
            CoverageBinConfig("div_by_nr", "NR迭代除法", goal=50),
        ]
    ),

    CoveragePointConfig(
        name="gradient_direction",
        description="梯度方向覆盖",
        category="data_path",
        bins=[
            CoverageBinConfig("zero", "零梯度", goal=10),
            CoverageBinConfig("horizontal", "水平梯度主导", goal=10),
            CoverageBinConfig("vertical", "垂直梯度主导", goal=10),
            CoverageBinConfig("diagonal", "对角梯度", goal=10),
            CoverageBinConfig("mixed", "混合梯度", goal=10),
        ]
    ),
]

# ============================================================
# Coverage Report Configuration
# ============================================================
@dataclass
class ReportConfig:
    """报告配置"""
    output_dir: str = "reports/coverage"
    html_report: bool = True
    json_report: bool = True
    xml_report: bool = False

    # 覆盖率门限
    pass_threshold: float = 80.0
    warn_threshold: float = 95.0

    # 报告包含的内容
    include_uncovered: bool = True
    include_source: bool = True
    include_trends: bool = False

# ============================================================
# Global Configuration Instance
# ============================================================
@dataclass
class CoverageConfig:
    """覆盖率总配置"""
    code_coverage: CodeCoverageConfig = field(default_factory=CodeCoverageConfig)
    functional_coverage_points: List[CoveragePointConfig] = field(
        default_factory=lambda: FUNCTIONAL_COVERAGE_POINTS
    )
    report: ReportConfig = field(default_factory=ReportConfig)

    def get_point_by_name(self, name: str) -> CoveragePointConfig:
        for point in self.functional_coverage_points:
            if point.name == name:
                return point
        raise ValueError(f"Coverage point not found: {name}")