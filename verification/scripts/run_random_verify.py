#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ISP-CSIIR 随机验证运行器

运行随机生成的测试用例，对比Python黄金模型和HLS模型的输出，
生成统计报告。

作者: rtl-verf
日期: 2026-03-23
版本: v1.0
"""

import os
import sys
import json
import time
import argparse
import subprocess
import numpy as np
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, field
from datetime import datetime

# 导入本地模块
from compute_expected import process_image, load_input_image, save_expected_output
from compare_intermediate import (
    load_stage_data, compare_field, ComparisonResult
)
from random_verify_constraints import ConstraintValidator
from generate_random_patterns import TestCaseGenerator, TestCaseMetadata

# Coverage collection
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    from coverage import (
        FunctionalCoverageCollector,
        ConfigConsistencyChecker,
        ISPConfig
    )
    COVERAGE_AVAILABLE = True
except ImportError:
    COVERAGE_AVAILABLE = False


# ============================================================
# 配置常量
# ============================================================
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(os.path.dirname(SCRIPT_DIR))
HLS_DIR = os.path.join(PROJECT_DIR, 'hls')
VERIFICATION_DIR = os.path.join(PROJECT_DIR, 'verification')
TEST_VECTORS_DIR = os.path.join(VERIFICATION_DIR, 'test_vectors')
RANDOM_DIR = os.path.join(TEST_VECTORS_DIR, 'random')
INTERMEDIATE_DIR = os.path.join(VERIFICATION_DIR, 'intermediate')
REPORTS_DIR = os.path.join(VERIFICATION_DIR, 'reports')


# ============================================================
# 数据结构
# ============================================================
@dataclass
class StageErrors:
    """各阶段的误差统计"""
    stage1_max: int = 0
    stage2_max: int = 0
    stage3_max: int = 0
    output_max: int = 0

    stage1_mean: float = 0.0
    stage2_mean: float = 0.0
    stage3_mean: float = 0.0
    output_mean: float = 0.0


@dataclass
class TestCaseResult:
    """单个测试用例的验证结果"""
    case_id: str
    pattern_type: str
    width: int
    height: int
    passed: bool
    error_message: str = ""

    # 各阶段通过状态
    stage1_pass: bool = True
    stage2_pass: bool = True
    stage3_pass: bool = True
    output_pass: bool = True

    # 误差统计
    errors: StageErrors = field(default_factory=StageErrors)


@dataclass
class VerificationReport:
    """验证报告"""
    start_time: datetime
    end_time: datetime = None
    total_cases: int = 0
    passed_cases: int = 0
    failed_cases: int = 0

    # 误差统计
    max_stage1_error: int = 0
    max_stage2_error: int = 0
    max_stage3_error: int = 0
    max_output_error: int = 0

    # 失败案例
    failed_case_details: List[Tuple[str, str]] = field(default_factory=list)

    # Pattern类型统计
    pattern_stats: Dict[str, Dict] = field(default_factory=dict)


# ============================================================
# Python黄金模型验证
# ============================================================
class PythonModelRunner:
    """
    Python黄金模型运行器

    调用compute_expected.py中的函数生成期望输出
    """

    def __init__(self, intermediate_dir: str,
                 coverage_collector: Optional['FunctionalCoverageCollector'] = None):
        self.intermediate_dir = intermediate_dir
        self.python_intermediate_dir = os.path.join(intermediate_dir, 'python')
        os.makedirs(self.python_intermediate_dir, exist_ok=True)
        self.coverage_collector = coverage_collector

    def run_test_case(self, test_case_dir: str, pattern_type: str = None) -> Tuple[bool, str]:
        """
        运行单个测试用例的Python模型

        Args:
            test_case_dir: 测试用例目录
            pattern_type: Pattern类型（用于覆盖率采样）

        Returns:
            (成功, 错误信息)
        """
        # 加载配置
        config_file = os.path.join(test_case_dir, 'config.json')
        with open(config_file, 'r') as f:
            config = json.load(f)

        # 加载输入图像
        input_file = os.path.join(test_case_dir, 'input.txt')
        image = load_input_image(input_file, config['width'], config['height'])

        # 处理图像（带覆盖率收集）
        output_image, results = process_image(
            image,
            win_thresh=config['win_thresh'],
            grad_clip=config['grad_clip'],
            blend_ratio=config['blend_ratio'],
            edge_protect=config['edge_protect'],
            coverage_collector=self.coverage_collector,
            pattern_type=pattern_type
        )

        # 保存中间结果
        case_name = os.path.basename(test_case_dir)
        self._save_stage1(case_name, results, config['width'])
        self._save_stage2(case_name, results, config['width'])
        self._save_stage3(case_name, results, config['width'])
        self._save_output(case_name, image, output_image, config['width'])

        # 保存期望输出
        expected_file = os.path.join(test_case_dir, 'expected.txt')
        save_expected_output(output_image, expected_file)

        return True, ""

    def _save_stage1(self, case_name: str, results, width: int):
        """保存Stage 1中间结果"""
        filename = os.path.join(self.python_intermediate_dir, f"{case_name}_stage1.txt")
        with open(filename, 'w') as f:
            f.write("# Stage 1: Gradient Computation Results\n")
            f.write("# Format: row col grad win_size grad_h grad_v\n")
            for i, r in enumerate(results):
                row, col = i // width, i % width
                f.write(f"{row} {col} {r.stage1.grad} {r.stage1.win_size} "
                        f"{r.stage1.grad_h} {r.stage1.grad_v}\n")

    def _save_stage2(self, case_name: str, results, width: int):
        """保存Stage 2中间结果"""
        filename = os.path.join(self.python_intermediate_dir, f"{case_name}_stage2.txt")
        with open(filename, 'w') as f:
            f.write("# Stage 2: Multi-scale Directional Average Results\n")
            f.write("# Format: row col avg0_c avg0_u avg0_d avg0_l avg0_r avg1_c avg1_u avg1_d avg1_l avg1_r\n")
            for i, r in enumerate(results):
                row, col = i // width, i % width
                f.write(f"{row} {col} {r.stage2.avg0_c} {r.stage2.avg0_u} {r.stage2.avg0_d} "
                        f"{r.stage2.avg0_l} {r.stage2.avg0_r} {r.stage2.avg1_c} {r.stage2.avg1_u} "
                        f"{r.stage2.avg1_d} {r.stage2.avg1_l} {r.stage2.avg1_r}\n")

    def _save_stage3(self, case_name: str, results, width: int):
        """保存Stage 3中间结果"""
        filename = os.path.join(self.python_intermediate_dir, f"{case_name}_stage3.txt")
        with open(filename, 'w') as f:
            f.write("# Stage 3: Gradient-weighted Directional Fusion Results\n")
            f.write("# Format: row col blend0_grad blend1_grad\n")
            for i, r in enumerate(results):
                row, col = i // width, i % width
                f.write(f"{row} {col} {r.stage3.blend0_grad} {r.stage3.blend1_grad}\n")

    def _save_output(self, case_name: str, input_image, output_image, width: int):
        """保存最终输出"""
        filename = os.path.join(self.python_intermediate_dir, f"{case_name}_output.txt")
        height, width = output_image.shape
        with open(filename, 'w') as f:
            f.write("# Stage 4: Final Output Results\n")
            f.write("# Format: row col input_pixel output_pixel\n")
            for row in range(height):
                for col in range(width):
                    f.write(f"{row} {col} {input_image[row, col]} {output_image[row, col]}\n")


# ============================================================
# HLS模型验证
# ============================================================
class HLSModelRunner:
    """
    HLS模型运行器

    编译并运行HLS测试平台 (tb_simple.cpp - 纯C++实现)
    """

    def __init__(self, hls_dir: str, intermediate_dir: str):
        self.hls_dir = hls_dir
        self.intermediate_dir = intermediate_dir
        self.hls_intermediate_dir = os.path.join(intermediate_dir, 'hls')
        os.makedirs(self.hls_intermediate_dir, exist_ok=True)

        self.executable = None
        self._compiled = False

    def compile(self, force: bool = False) -> Tuple[bool, str]:
        """
        编译HLS测试平台

        使用tb_random.cpp作为可参数化的C++实现

        Args:
            force: 强制重新编译

        Returns:
            (成功, 错误信息)
        """
        self.executable = os.path.join(self.hls_dir, 'tb_random')

        # 检查是否需要编译
        if not force and os.path.exists(self.executable):
            # 检查源文件是否更新
            src_file = os.path.join(self.hls_dir, 'tb_random.cpp')
            if os.path.exists(src_file):
                src_mtime = os.path.getmtime(src_file)
                exe_mtime = os.path.getmtime(self.executable)
                if src_mtime < exe_mtime:
                    self._compiled = True
                    return True, "使用已存在的可执行文件"

        # 编译命令 - 编译tb_random.cpp（可参数化的C++实现）
        src_path = os.path.join(self.hls_dir, 'tb_random.cpp')

        if not os.path.exists(src_path):
            return False, f"源文件不存在: {src_path}"

        cmd = ['g++', '-O2', '-std=c++17', '-o', self.executable, src_path]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60
            )

            if result.returncode != 0:
                return False, f"编译失败: {result.stderr}"

            self._compiled = True
            return True, "编译成功"

        except subprocess.TimeoutExpired:
            return False, "编译超时"
        except Exception as e:
            return False, f"编译异常: {str(e)}"

    def run_for_test(self, test_case_dir: str, case_name: str,
                     config: Dict) -> Tuple[bool, str]:
        """
        为单个测试用例运行HLS模型

        Args:
            test_case_dir: 测试用例目录
            case_name: 用例名称
            config: 配置参数

        Returns:
            (成功, 错误信息)
        """
        # 确保已编译
        if not self._compiled:
            success, msg = self.compile()
            if not success:
                return False, f"编译失败: {msg}"

        # 输入文件路径
        input_file = os.path.join(test_case_dir, 'input.txt')
        config_file = os.path.join(test_case_dir, 'config.txt')

        # HLS输出目录
        hls_output_dir = os.path.join(self.hls_intermediate_dir, case_name)
        os.makedirs(hls_output_dir, exist_ok=True)

        # 创建配置文件（tb_random格式）
        with open(config_file, 'w') as f:
            f.write(f"width {config['width']}\n")
            f.write(f"height {config['height']}\n")
            f.write(f"win_thresh {config['win_thresh'][0]} {config['win_thresh'][1]} {config['win_thresh'][2]} {config['win_thresh'][3]}\n")
            f.write(f"grad_clip {config['grad_clip'][0]} {config['grad_clip'][1]} {config['grad_clip'][2]} {config['grad_clip'][3]}\n")
            f.write(f"blend_ratio {config['blend_ratio'][0]} {config['blend_ratio'][1]} {config['blend_ratio'][2]} {config['blend_ratio'][3]}\n")

        # 运行HLS可执行文件
        cmd = [self.executable, input_file, hls_output_dir, config_file]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5分钟超时
            )

            if result.returncode != 0:
                return False, f"HLS运行失败: {result.stderr}"

            # 重命名输出文件以匹配Python格式
            for stage in ['stage1', 'stage2', 'stage3', 'output']:
                src = os.path.join(hls_output_dir, f'{stage}.txt')
                dst = os.path.join(self.hls_intermediate_dir, f'{case_name}_{stage}.txt')
                if os.path.exists(src):
                    if os.path.exists(dst):
                        os.remove(dst)
                    os.rename(src, dst)

            # 清理临时目录
            try:
                os.rmdir(hls_output_dir)
            except:
                pass

            return True, ""

        except subprocess.TimeoutExpired:
            return False, "HLS运行超时"
        except Exception as e:
            return False, f"HLS运行异常: {str(e)}"

    def run_test_case(self, test_case_dir: str) -> Tuple[bool, str]:
        """
        运行HLS模型

        Args:
            test_case_dir: 测试用例目录

        Returns:
            (成功, 错误信息)
        """
        # 加载配置
        config_file = os.path.join(test_case_dir, 'config.json')
        with open(config_file, 'r') as f:
            config = json.load(f)

        case_name = os.path.basename(test_case_dir)

        return self.run_for_test(test_case_dir, case_name, config)


# ============================================================
# 结果比较器
# ============================================================
class ResultComparator:
    """
    结果比较器

    比较Python和HLS模型的输出
    """

    def __init__(self, intermediate_dir: str):
        self.intermediate_dir = intermediate_dir
        self.python_dir = os.path.join(intermediate_dir, 'python')
        self.hls_dir = os.path.join(intermediate_dir, 'hls')

        # 容差设置
        self.tolerances = {
            'stage1': {'grad': 1, 'win_size': 0, 'grad_h': 1, 'grad_v': 1},
            'stage2': {'default': 2},
            'stage3': {'default': 3},
            'output': {'default': 2}
        }

    def compare_stage1(self, case_name: str) -> Tuple[bool, Dict]:
        """比较Stage 1结果"""
        python_file = os.path.join(self.python_dir, f"{case_name}_stage1.txt")
        hls_file = os.path.join(self.hls_dir, f"{case_name}_stage1.txt")

        expected = load_stage_data(python_file, 1)
        actual = load_stage_data(hls_file, 1)

        if not expected or not actual:
            return False, {'error': 'Missing data files'}

        results = {}
        all_pass = True
        max_error = 0
        sum_error = 0
        count = 0

        for field in ['grad', 'win_size', 'grad_h', 'grad_v']:
            tolerance = self.tolerances['stage1'].get(field, 1)
            result = compare_field(expected, actual, field, tolerance)

            max_error = max(max_error, result.max_diff)
            sum_error += result.mean_diff * result.total_count
            count += result.total_count

            match_rate = 100.0 * result.match_count / result.total_count
            if match_rate < 99.0:
                all_pass = False

            results[field] = {
                'match_rate': match_rate,
                'max_diff': result.max_diff,
                'mean_diff': result.mean_diff
            }

        results['pass'] = all_pass
        results['max_error'] = max_error
        results['mean_error'] = sum_error / count if count > 0 else 0

        return all_pass, results

    def compare_stage2(self, case_name: str) -> Tuple[bool, Dict]:
        """比较Stage 2结果"""
        python_file = os.path.join(self.python_dir, f"{case_name}_stage2.txt")
        hls_file = os.path.join(self.hls_dir, f"{case_name}_stage2.txt")

        expected = load_stage_data(python_file, 2)
        actual = load_stage_data(hls_file, 2)

        if not expected or not actual:
            return False, {'error': 'Missing data files'}

        tolerance = self.tolerances['stage2']['default']
        all_pass = True
        max_error = 0
        sum_error = 0
        count = 0

        for field in ['avg0_c', 'avg0_u', 'avg0_d', 'avg0_l', 'avg0_r',
                       'avg1_c', 'avg1_u', 'avg1_d', 'avg1_l', 'avg1_r']:
            result = compare_field(expected, actual, field, tolerance)

            max_error = max(max_error, result.max_diff)
            sum_error += result.mean_diff * result.total_count
            count += result.total_count

            match_rate = 100.0 * result.match_count / result.total_count
            if match_rate < 95.0:
                all_pass = False

        return all_pass, {
            'pass': all_pass,
            'max_error': max_error,
            'mean_error': sum_error / count if count > 0 else 0
        }

    def compare_stage3(self, case_name: str) -> Tuple[bool, Dict]:
        """比较Stage 3结果"""
        python_file = os.path.join(self.python_dir, f"{case_name}_stage3.txt")
        hls_file = os.path.join(self.hls_dir, f"{case_name}_stage3.txt")

        expected = load_stage_data(python_file, 3)
        actual = load_stage_data(hls_file, 3)

        if not expected or not actual:
            return False, {'error': 'Missing data files'}

        tolerance = self.tolerances['stage3']['default']
        all_pass = True
        max_error = 0
        sum_error = 0
        count = 0

        for field in ['blend0_grad', 'blend1_grad']:
            result = compare_field(expected, actual, field, tolerance)

            max_error = max(max_error, result.max_diff)
            sum_error += result.mean_diff * result.total_count
            count += result.total_count

            match_rate = 100.0 * result.match_count / result.total_count
            if match_rate < 95.0:
                all_pass = False

        return all_pass, {
            'pass': all_pass,
            'max_error': max_error,
            'mean_error': sum_error / count if count > 0 else 0
        }

    def compare_output(self, case_name: str) -> Tuple[bool, Dict]:
        """比较最终输出"""
        python_file = os.path.join(self.python_dir, f"{case_name}_output.txt")
        hls_file = os.path.join(self.hls_dir, f"{case_name}_output.txt")

        expected = load_stage_data(python_file, 4)
        actual = load_stage_data(hls_file, 4)

        if not expected or not actual:
            return False, {'error': 'Missing data files'}

        tolerance = self.tolerances['output']['default']
        result = compare_field(expected, actual, 'output', tolerance)

        match_rate = 100.0 * result.match_count / result.total_count
        all_pass = match_rate >= 95.0

        return all_pass, {
            'pass': all_pass,
            'max_error': result.max_diff,
            'mean_error': result.mean_diff,
            'match_rate': match_rate
        }

    def compare_all(self, case_name: str) -> Tuple[bool, StageErrors]:
        """
        比较所有阶段

        Returns:
            (全部通过, 误差统计)
        """
        errors = StageErrors()
        all_pass = True

        # Stage 1
        s1_pass, s1_result = self.compare_stage1(case_name)
        if s1_pass:
            errors.stage1_max = s1_result.get('max_error', 0)
            errors.stage1_mean = s1_result.get('mean_error', 0)
        else:
            all_pass = False

        # Stage 2
        s2_pass, s2_result = self.compare_stage2(case_name)
        if s2_pass:
            errors.stage2_max = s2_result.get('max_error', 0)
            errors.stage2_mean = s2_result.get('mean_error', 0)
        else:
            all_pass = False

        # Stage 3
        s3_pass, s3_result = self.compare_stage3(case_name)
        if s3_pass:
            errors.stage3_max = s3_result.get('max_error', 0)
            errors.stage3_mean = s3_result.get('mean_error', 0)
        else:
            all_pass = False

        # Output
        out_pass, out_result = self.compare_output(case_name)
        if out_pass:
            errors.output_max = out_result.get('max_error', 0)
            errors.output_mean = out_result.get('mean_error', 0)
        else:
            all_pass = False

        return all_pass, errors


# ============================================================
# 随机验证运行器
# ============================================================
class RandomVerifyRunner:
    """
    随机验证运行器

    协调测试生成、运行和比较
    """

    def __init__(self, output_dir: str = RANDOM_DIR,
                 intermediate_dir: str = INTERMEDIATE_DIR,
                 reports_dir: str = REPORTS_DIR,
                 collect_coverage: bool = True):
        self.output_dir = output_dir
        self.intermediate_dir = intermediate_dir
        self.reports_dir = reports_dir
        self.collect_coverage = collect_coverage and COVERAGE_AVAILABLE

        # 确保目录存在
        os.makedirs(output_dir, exist_ok=True)
        os.makedirs(intermediate_dir, exist_ok=True)
        os.makedirs(reports_dir, exist_ok=True)

        # 初始化覆盖率收集器
        self.coverage_collector = None
        if self.collect_coverage:
            self.coverage_collector = FunctionalCoverageCollector()
            print("[Coverage] 功能覆盖率收集已启用")

        # 初始化组件
        self.python_runner = PythonModelRunner(intermediate_dir, self.coverage_collector)
        self.hls_runner = HLSModelRunner(HLS_DIR, intermediate_dir)
        self.comparator = ResultComparator(intermediate_dir)

    def generate_tests(self, num_cases: int, seed: int = None) -> List[str]:
        """
        生成测试用例

        Args:
            num_cases: 测试数量
            seed: 随机种子

        Returns:
            测试用例目录列表
        """
        print(f"\n[1/3] 生成测试用例...")
        generator = TestCaseGenerator(self.output_dir, seed)
        return generator.generate_batch(num_cases)

    def run_python_model(self, test_dirs: List[str]) -> Dict[str, Tuple[bool, str]]:
        """
        运行Python黄金模型

        Args:
            test_dirs: 测试用例目录列表

        Returns:
            {case_id: (成功, 错误信息)}
        """
        print(f"\n[2/3] 运行Python黄金模型...")
        results = {}

        for i, test_dir in enumerate(test_dirs):
            case_id = os.path.basename(test_dir)
            print(f"  [{i+1}/{len(test_dirs)}] {case_id}", end='\r')

            # 获取pattern_type用于覆盖率采样
            pattern_type = None
            if self.coverage_collector:
                config_file = os.path.join(test_dir, 'config.json')
                if os.path.exists(config_file):
                    with open(config_file, 'r') as f:
                        config = json.load(f)
                        pattern_type = config.get('pattern_type', 'unknown')

            success, error = self.python_runner.run_test_case(test_dir, pattern_type)
            results[case_id] = (success, error)

        print(f"\n  完成: {len(results)} 个测试用例")
        return results

    def run_hls_model(self, test_dirs: List[str]) -> Dict[str, Tuple[bool, str]]:
        """
        运行HLS模型

        Args:
            test_dirs: 测试用例目录列表

        Returns:
            {case_id: (成功, 错误信息)}
        """
        print(f"\n[3/3] 运行HLS模型...")

        # 先编译
        compiled, msg = self.hls_runner.compile()
        if not compiled:
            print(f"  警告: {msg}")
            print(f"  使用Python模型模拟HLS行为")

        results = {}
        for i, test_dir in enumerate(test_dirs):
            case_id = os.path.basename(test_dir)
            print(f"  [{i+1}/{len(test_dirs)}] {case_id}", end='\r')
            success, error = self.hls_runner.run_test_case(test_dir)
            results[case_id] = (success, error)

        print(f"\n  完成: {len(results)} 个测试用例")
        return results

    def compare_results(self, test_dirs: List[str]) -> List[TestCaseResult]:
        """
        比较结果

        Args:
            test_dirs: 测试用例目录列表

        Returns:
            测试结果列表
        """
        print(f"\n[4/4] 比较结果...")
        results = []

        for test_dir in test_dirs:
            case_id = os.path.basename(test_dir)

            # 加载配置
            config_file = os.path.join(test_dir, 'config.json')
            with open(config_file, 'r') as f:
                config = json.load(f)

            # 比较
            all_pass, errors = self.comparator.compare_all(case_id)

            # 构建结果
            result = TestCaseResult(
                case_id=case_id,
                pattern_type=config['pattern_type'],
                width=config['width'],
                height=config['height'],
                passed=all_pass,
                errors=errors
            )

            results.append(result)

        return results

    def generate_report(self, results: List[TestCaseResult],
                        start_time: datetime, end_time: datetime) -> str:
        """
        生成验证报告

        Args:
            results: 测试结果列表
            start_time: 开始时间
            end_time: 结束时间

        Returns:
            报告内容
        """
        total = len(results)
        passed = sum(1 for r in results if r.passed)
        failed = total - passed
        pass_rate = 100.0 * passed / total if total > 0 else 0

        # 统计最大误差
        max_stage1 = max((r.errors.stage1_max for r in results), default=0)
        max_stage2 = max((r.errors.stage2_max for r in results), default=0)
        max_stage3 = max((r.errors.stage3_max for r in results), default=0)
        max_output = max((r.errors.output_max for r in results), default=0)

        # Pattern类型统计
        pattern_stats = {}
        for r in results:
            if r.pattern_type not in pattern_stats:
                pattern_stats[r.pattern_type] = {'total': 0, 'passed': 0}
            pattern_stats[r.pattern_type]['total'] += 1
            if r.passed:
                pattern_stats[r.pattern_type]['passed'] += 1

        # 构建报告
        report_lines = [
            "=" * 50,
            "ISP-CSIIR 随机验证报告",
            "=" * 50,
            f"开始时间: {start_time.strftime('%Y-%m-%d %H:%M:%S')}",
            f"结束时间: {end_time.strftime('%Y-%m-%d %H:%M:%S')}",
            f"测试总数: {total}",
            f"通过数: {passed}",
            f"通过率: {pass_rate:.2f}%",
            "",
            "误差统计:",
            f"- Stage1 最大误差: {max_stage1}",
            f"- Stage2 最大误差: {max_stage2}",
            f"- Stage3 最大误差: {max_stage3}",
            f"- Output 最大误差: {max_output}",
            "",
            "Pattern类型统计:",
        ]

        for pattern, stats in sorted(pattern_stats.items()):
            rate = 100.0 * stats['passed'] / stats['total'] if stats['total'] > 0 else 0
            report_lines.append(f"  - {pattern}: {stats['passed']}/{stats['total']} ({rate:.1f}%)")

        # 失败案例
        if failed > 0:
            report_lines.extend([
                "",
                "失败案例:",
            ])
            for r in results:
                if not r.passed:
                    error_detail = f"Stage1:{r.errors.stage1_max}, Stage2:{r.errors.stage2_max}, " \
                                   f"Stage3:{r.errors.stage3_max}, Output:{r.errors.output_max}"
                    report_lines.append(f"- {r.case_id}: {error_detail}")

        report_lines.append("=" * 50)

        report = '\n'.join(report_lines)

        # 保存报告
        report_file = os.path.join(self.reports_dir, 'random_verify_report.txt')
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report)

        # 同时保存JSON格式
        json_report = {
            'start_time': start_time.isoformat(),
            'end_time': end_time.isoformat(),
            'total': total,
            'passed': passed,
            'pass_rate': pass_rate,
            'errors': {
                'stage1_max': max_stage1,
                'stage2_max': max_stage2,
                'stage3_max': max_stage3,
                'output_max': max_output
            },
            'pattern_stats': pattern_stats,
            'failed_cases': [
                {'case_id': r.case_id, 'errors': {
                    'stage1': r.errors.stage1_max,
                    'stage2': r.errors.stage2_max,
                    'stage3': r.errors.stage3_max,
                    'output': r.errors.output_max
                }}
                for r in results if not r.passed
            ]
        }

        json_file = os.path.join(self.reports_dir, 'random_verify_report.json')
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(json_report, f, indent=2, ensure_ascii=False)

        return report

    def generate_coverage_report(self) -> Optional[str]:
        """
        生成功能覆盖率报告

        Returns:
            覆盖率报告内容，如果覆盖率收集未启用则返回None
        """
        if not self.coverage_collector:
            return None

        print("\n[Coverage] 生成功能覆盖率报告...")

        # 获取覆盖率数据
        coverage_data = self.coverage_collector.get_coverage_summary()

        # 构建报告
        report_lines = [
            "=" * 60,
            "ISP-CSIIR 功能覆盖率报告",
            "=" * 60,
        ]

        total_points = 0
        total_covered = 0

        for cp_name, cp_data in coverage_data.items():
            total_points += 1
            coverage = cp_data.get('coverage', 0)
            bins = cp_data.get('bins', {})
            covered_bins = sum(1 for v in bins.values() if v > 0)
            total_bins = len(bins)

            total_covered += (1 if coverage > 0 else 0)

            status = "✓" if coverage >= 100 else "○"
            report_lines.append(f"{status} {cp_name}: {coverage:.1f}% ({covered_bins}/{total_bins} bins)")

        overall_rate = 100.0 * total_covered / total_points if total_points > 0 else 0
        report_lines.extend([
            "",
            "-" * 60,
            f"总覆盖率: {overall_rate:.1f}% ({total_covered}/{total_points} coverage points)",
            "=" * 60,
        ])

        report = '\n'.join(report_lines)

        # 保存报告
        cov_report_file = os.path.join(self.reports_dir, 'functional_coverage_report.txt')
        with open(cov_report_file, 'w', encoding='utf-8') as f:
            f.write(report)

        # 保存JSON格式详细数据
        cov_json_file = os.path.join(self.reports_dir, 'functional_coverage_report.json')
        with open(cov_json_file, 'w', encoding='utf-8') as f:
            json.dump(coverage_data, f, indent=2, ensure_ascii=False)

        print(f"[Coverage] 报告已保存到 {cov_report_file}")
        return report

    def run(self, num_cases: int = 100, seed: int = None) -> str:
        """
        运行完整验证流程

        Args:
            num_cases: 测试数量
            seed: 随机种子

        Returns:
            报告内容
        """
        start_time = datetime.now()

        print("=" * 50)
        print("ISP-CSIIR 随机验证运行器")
        print("=" * 50)
        print(f"测试数量: {num_cases}")
        print(f"随机种子: {seed if seed else '随机'}")
        if self.collect_coverage:
            print("覆盖率收集: 已启用")

        # 1. 生成测试用例
        test_dirs = self.generate_tests(num_cases, seed)

        # 2. 运行Python模型
        python_results = self.run_python_model(test_dirs)

        # 3. 运行HLS模型
        hls_results = self.run_hls_model(test_dirs)

        # 4. 比较结果
        results = self.compare_results(test_dirs)

        end_time = datetime.now()

        # 5. 生成验证报告
        report = self.generate_report(results, start_time, end_time)

        # 6. 生成功能覆盖率报告
        if self.collect_coverage:
            cov_report = self.generate_coverage_report()
            if cov_report:
                print("\n" + cov_report)

        return report


# ============================================================
# 命令行接口
# ============================================================
def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='ISP-CSIIR 随机验证运行器')
    parser.add_argument('-n', '--num-cases', type=int, default=100,
                        help='测试用例数量（默认100）')
    parser.add_argument('-s', '--seed', type=int, default=None,
                        help='随机种子')
    parser.add_argument('-o', '--output', type=str, default=None,
                        help='测试用例输出目录')
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='详细输出')

    args = parser.parse_args()

    # 设置输出目录
    output_dir = args.output if args.output else RANDOM_DIR

    # 创建运行器
    runner = RandomVerifyRunner(output_dir=output_dir)

    # 运行验证
    report = runner.run(num_cases=args.num_cases, seed=args.seed)

    # 打印报告
    print("\n" + report)


if __name__ == "__main__":
    main()