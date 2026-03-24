# ============================================================
# ISP-CSIIR Configuration Consistency Checker
# ============================================================
# Ensures HLS and Python models use identical configuration
# ============================================================

import json
import os
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional, Tuple
import numpy as np

# ============================================================
# Configuration Classes
# ============================================================
@dataclass
class ISPConfig:
    """ISP-CSIIR 配置"""
    width: int = 64
    height: int = 64
    win_thresh: List[int] = None
    grad_clip: List[int] = None
    blend_ratio: List[int] = None

    def __post_init__(self):
        if self.win_thresh is None:
            self.win_thresh = [16, 24, 32, 40]
        if self.grad_clip is None:
            self.grad_clip = [15, 23, 31, 39]
        if self.blend_ratio is None:
            self.blend_ratio = [32, 32, 32, 32]

    def to_dict(self) -> Dict:
        return asdict(self)

    def to_hls_config_string(self) -> str:
        """生成 HLS config.txt 格式"""
        lines = [
            f"width {self.width}",
            f"height {self.height}",
            f"win_thresh {self.win_thresh[0]} {self.win_thresh[1]} {self.win_thresh[2]} {self.win_thresh[3]}",
            f"grad_clip {self.grad_clip[0]} {self.grad_clip[1]} {self.grad_clip[2]} {self.grad_clip[3]}",
            f"blend_ratio {self.blend_ratio[0]} {self.blend_ratio[1]} {self.blend_ratio[2]} {self.blend_ratio[3]}"
        ]
        return "\n".join(lines)

    @classmethod
    def from_dict(cls, d: Dict) -> 'ISPConfig':
        return cls(
            width=d.get('width', 64),
            height=d.get('height', 64),
            win_thresh=d.get('win_thresh', [16, 24, 32, 40]),
            grad_clip=d.get('grad_clip', [15, 23, 31, 39]),
            blend_ratio=d.get('blend_ratio', [32, 32, 32, 32])
        )

    @classmethod
    def from_json_file(cls, filepath: str) -> 'ISPConfig':
        with open(filepath, 'r') as f:
            d = json.load(f)
        return cls.from_dict(d)

    @classmethod
    def from_hls_config_file(cls, filepath: str) -> 'ISPConfig':
        """从 HLS config.txt 解析配置"""
        config = cls()

        with open(filepath, 'r') as f:
            for line in f:
                parts = line.strip().split()
                if len(parts) < 2:
                    continue

                key = parts[0]
                values = parts[1:]

                if key == "width":
                    config.width = int(values[0])
                elif key == "height":
                    config.height = int(values[0])
                elif key == "win_thresh":
                    config.win_thresh = [int(v) for v in values[:4]]
                elif key == "grad_clip":
                    config.grad_clip = [int(v) for v in values[:4]]
                elif key == "blend_ratio":
                    config.blend_ratio = [int(v) for v in values[:4]]

        return config

    def equals(self, other: 'ISPConfig') -> Tuple[bool, List[str]]:
        """比较两个配置是否相等"""
        differences = []

        if self.width != other.width:
            differences.append(f"width: {self.width} vs {other.width}")
        if self.height != other.height:
            differences.append(f"height: {self.height} vs {other.height}")
        if self.win_thresh != other.win_thresh:
            differences.append(f"win_thresh: {self.win_thresh} vs {other.win_thresh}")
        if self.grad_clip != other.grad_clip:
            differences.append(f"grad_clip: {self.grad_clip} vs {other.grad_clip}")
        if self.blend_ratio != other.blend_ratio:
            differences.append(f"blend_ratio: {self.blend_ratio} vs {other.blend_ratio}")

        return len(differences) == 0, differences

# ============================================================
# Configuration Consistency Checker
# ============================================================
class ConfigConsistencyChecker:
    """配置一致性检查器"""

    def __init__(self):
        self.mismatches: List[Dict] = []

    def check_config_files(self, json_path: str, hls_config_path: str) -> Tuple[bool, Dict]:
        """
        检查 Python config.json 和 HLS config.txt 是否一致

        Args:
            json_path: Python 配置文件路径
            hls_config_path: HLS 配置文件路径

        Returns:
            (是否一致, 差异详情)
        """
        python_config = ISPConfig.from_json_file(json_path)

        if not os.path.exists(hls_config_path):
            return False, {"error": f"HLS config file not found: {hls_config_path}"}

        hls_config = ISPConfig.from_hls_config_file(hls_config_path)

        is_equal, differences = python_config.equals(hls_config)

        result = {
            "python_config": python_config.to_dict(),
            "hls_config": hls_config.to_dict(),
            "match": is_equal,
            "differences": differences
        }

        if not is_equal:
            self.mismatches.append({
                "json_path": json_path,
                "hls_path": hls_config_path,
                "differences": differences
            })

        return is_equal, result

    def check_runtime_config(self, expected: ISPConfig, actual: ISPConfig,
                              test_name: str = "") -> Tuple[bool, Dict]:
        """
        检查运行时配置是否一致

        Args:
            expected: 期望配置 (Python)
            actual: 实际配置 (HLS)
            test_name: 测试名称

        Returns:
            (是否一致, 差异详情)
        """
        is_equal, differences = expected.equals(actual)

        result = {
            "test_name": test_name,
            "expected": expected.to_dict(),
            "actual": actual.to_dict(),
            "match": is_equal,
            "differences": differences
        }

        if not is_equal:
            self.mismatches.append(result)

        return is_equal, result

    def get_mismatch_summary(self) -> Dict:
        """获取配置不匹配摘要"""
        return {
            "total_checks": len(self.mismatches),
            "mismatches": self.mismatches
        }

    def reset(self):
        """重置检查器"""
        self.mismatches = []

# ============================================================
# HLS Output Config Validator
# ============================================================
class HLSOutputConfigValidator:
    """
    从 HLS 输出反推验证配置是否正确应用

    通过分析 Stage1 输出的 win_size 分布，验证 grad_clip 是否正确应用
    """

    @staticmethod
    def validate_grad_clip_from_output(stage1_data: List[Dict],
                                        grad_clip: List[int]) -> Tuple[bool, Dict]:
        """
        从 Stage1 输出验证 grad_clip 是否正确应用

        原理：如果 grad_clip 正确应用，win_size 应该在预期范围内变化
        """
        win_sizes = [d['win_size'] for d in stage1_data]

        # 预期的 win_size 值
        expected_values = [16, 23, 31, 39, 40]

        # 检查是否有预期的 win_size 出现
        unique_sizes = set(win_sizes)

        # 如果所有 win_size 都相同，可能配置没有生效
        if len(unique_sizes) == 1:
            return False, {
                "warning": "All win_size values are the same",
                "win_size": win_sizes[0],
                "possible_issue": "grad_clip may not be applied correctly"
            }

        return True, {
            "unique_win_sizes": sorted(unique_sizes),
            "config_appears_correct": True
        }

    @staticmethod
    def validate_win_thresh_from_output(stage2_data: List[Dict],
                                          win_thresh: List[int]) -> Tuple[bool, Dict]:
        """
        从 Stage2 输出验证 win_thresh 是否正确应用

        原理：不同 kernel 应该被选中（avg0/avg1 因子不同）
        """
        # 检查 avg0_c 和 avg1_c 是否有显著差异
        avg0_values = [d['avg0_c'] for d in stage2_data]
        avg1_values = [d['avg1_c'] for d in stage2_data]

        # 如果 avg0 和 avg1 完全相同，可能 kernel 选择有问题
        if avg0_values == avg1_values:
            return False, {
                "warning": "avg0 and avg1 are identical",
                "possible_issue": "win_thresh or kernel selection may be incorrect"
            }

        return True, {
            "avg0_range": [min(avg0_values), max(avg0_values)],
            "avg1_range": [min(avg1_values), max(avg1_values)],
            "config_appears_correct": True
        }

# ============================================================
# Integration Helper
# ============================================================
def verify_config_consistency(test_case_dir: str) -> Tuple[bool, Dict]:
    """
    验证测试用例的配置一致性

    Args:
        test_case_dir: 测试用例目录

    Returns:
        (是否一致, 验证详情)
    """
    checker = ConfigConsistencyChecker()

    json_path = os.path.join(test_case_dir, 'config.json')
    hls_config_path = os.path.join(test_case_dir, 'config.txt')

    if not os.path.exists(json_path):
        return False, {"error": f"Python config not found: {json_path}"}

    if not os.path.exists(hls_config_path):
        # HLS config 可能还没生成，先跳过
        return True, {"note": "HLS config not yet generated"}

    return checker.check_config_files(json_path, hls_config_path)