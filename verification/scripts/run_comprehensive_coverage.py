#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ISP-CSIIR 综合覆盖率测试运行器

运行随机测试 + 定向测试，收集完整覆盖率

作者: rtl-verf
日期: 2026-03-25
"""

import os
import sys
import json
import glob
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
VERIFICATION_DIR = os.path.dirname(SCRIPT_DIR)
PROJECT_DIR = os.path.dirname(VERIFICATION_DIR)

sys.path.insert(0, SCRIPT_DIR)
sys.path.insert(0, VERIFICATION_DIR)

from run_random_verify import (
    PythonModelRunner, HLSModelRunner, ResultComparator,
    VerificationReport, TestCaseResult, StageErrors
)
from coverage import (
    FunctionalCoverageCollector,
    HLSCodeCoverageCollector,
    UnifiedCoverageReporter,
    generate_unified_report
)


def run_comprehensive_coverage(collect_code_coverage: bool = True):
    """运行综合覆盖率测试

    Args:
        collect_code_coverage: 是否收集代码覆盖率
    """
    print("=" * 60)
    print("ISP-CSIIR 综合覆盖率测试")
    print("=" * 60)

    # 创建运行器
    intermediate_dir = os.path.join(VERIFICATION_DIR, 'intermediate')
    reports_dir = os.path.join(VERIFICATION_DIR, 'reports')
    os.makedirs(reports_dir, exist_ok=True)

    hls_dir = os.path.join(os.path.dirname(PROJECT_DIR), 'isp-csiir', 'hls')
    if not os.path.exists(hls_dir):
        hls_dir = os.path.join(PROJECT_DIR, 'isp-csiir', 'hls')

    # 创建覆盖率收集器
    coverage_collector = FunctionalCoverageCollector()
    print("[Coverage] 功能覆盖率收集已启用")

    # 创建代码覆盖率收集器
    hls_code_collector = None
    if collect_code_coverage:
        hls_code_collector = HLSCodeCoverageCollector(hls_dir)
        print("[Coverage] 代码覆盖率收集已启用")

        # 编译带覆盖率的 HLS 测试程序
        success, msg = hls_code_collector.compile_with_coverage()
        if success:
            print(f"[Coverage] HLS 覆盖率编译成功")
        else:
            print(f"[Coverage] HLS 覆盖率编译失败: {msg}")
            hls_code_collector = None

    python_runner = PythonModelRunner(intermediate_dir, coverage_collector)
    hls_runner = HLSModelRunner(hls_dir, intermediate_dir)
    comparator = ResultComparator(intermediate_dir)

    # 编译HLS
    compiled, msg = hls_runner.compile()
    if not compiled:
        print(f"警告: HLS编译失败 - {msg}")

    # 收集所有测试用例
    all_test_cases = []

    # 1. 随机测试用例
    random_dir = os.path.join(VERIFICATION_DIR, 'test_vectors', 'random')
    print(f"检查随机测试目录: {random_dir}")
    if os.path.exists(random_dir):
        random_cases = sorted([
            d for d in glob.glob(os.path.join(random_dir, 'case_*'))
            if os.path.isdir(d) and os.path.exists(os.path.join(d, 'config.json'))
        ])
        all_test_cases.extend(random_cases)
        print(f"[随机测试] 找到 {len(random_cases)} 个测试用例")

    # 2. 定向测试用例 (targeted_cov)
    targeted_dir = os.path.join(VERIFICATION_DIR, 'test_vectors', 'targeted_cov')
    print(f"检查定向测试目录: {targeted_dir}")
    if os.path.exists(targeted_dir):
        targeted_cases = sorted([
            d for d in glob.glob(os.path.join(targeted_dir, '*'))
            if os.path.isdir(d) and os.path.exists(os.path.join(d, 'config.json'))
        ])
        all_test_cases.extend(targeted_cases)
        print(f"[定向测试] 找到 {len(targeted_cases)} 个测试用例")

    print(f"\n总计: {len(all_test_cases)} 个测试用例")

    if not all_test_cases:
        print("错误: 未找到测试用例")
        return

    start_time = datetime.now()

    # 运行Python模型
    print("\n[1/3] 运行Python模型...")
    for i, test_case in enumerate(all_test_cases):
        case_id = os.path.basename(test_case)
        print(f"  [{i+1}/{len(all_test_cases)}] {case_id}", end='\r')

        config_file = os.path.join(test_case, 'config.json')
        with open(config_file, 'r') as f:
            config = json.load(f)
        pattern_type = config.get('pattern_type', 'unknown')

        python_runner.run_test_case(test_case, pattern_type)

    print(f"\n  完成: {len(all_test_cases)} 个测试用例")

    # 运行HLS模型
    print("\n[2/3] 运行HLS模型...")
    for i, test_case in enumerate(all_test_cases):
        case_id = os.path.basename(test_case)
        print(f"  [{i+1}/{len(all_test_cases)}] {case_id}", end='\r')
        hls_runner.run_test_case(test_case)

        # 收集代码覆盖率
        if hls_code_collector:
            input_file = os.path.join(test_case, 'input.txt')
            config_file = os.path.join(test_case, 'config.json')
            output_dir = os.path.join(intermediate_dir, case_id)
            os.makedirs(output_dir, exist_ok=True)
            hls_code_collector.run_test(input_file, output_dir, config_file)

    print(f"\n  完成: {len(all_test_cases)} 个测试用例")

    # 比较结果
    print("\n[3/3] 比较结果...")
    results = []
    for test_case in all_test_cases:
        case_id = os.path.basename(test_case)
        config_file = os.path.join(test_case, 'config.json')
        with open(config_file, 'r') as f:
            config = json.load(f)

        all_pass, errors = comparator.compare_all(case_id)
        result = TestCaseResult(
            case_id=case_id,
            pattern_type=config.get('pattern_type', 'unknown'),
            width=config['width'],
            height=config['height'],
            passed=all_pass,
            errors=errors
        )
        results.append(result)

    end_time = datetime.now()

    # 统计结果
    passed = sum(1 for r in results if r.passed)
    pass_rate = 100.0 * passed / len(results) if results else 0

    print(f"\n验证结果: {passed}/{len(results)} 通过 ({pass_rate:.1f}%)")

    # 生成覆盖率报告
    print("\n[Coverage] 生成功能覆盖率报告...")
    cov_summary = coverage_collector.get_coverage_summary()

    # 计算覆盖率统计
    total_points = len(cov_summary)
    fully_covered_points = 0
    total_bins = 0
    covered_bins = 0

    print("\n" + "=" * 60)
    print("ISP-CSIIR 功能覆盖率报告")
    print("=" * 60)

    for cp_name, cp_data in sorted(cov_summary.items()):
        cp_total_bins = cp_data['total_bins']
        cp_covered_bins = cp_data['covered_bins']
        coverage = cp_data['coverage']

        total_bins += cp_total_bins
        covered_bins += cp_covered_bins

        if coverage >= 100:
            fully_covered_points += 1
            status = "✓"
        else:
            status = "○"

        # 显示每个bin的状态
        bins_detail = []
        for bin_name, hit_count in cp_data['bins'].items():
            bins_detail.append(f"{bin_name}:{hit_count}")

        print(f"{status} {cp_name}: {coverage:.1f}% ({cp_covered_bins}/{cp_total_bins} bins)")
        if coverage < 100:
            print(f"    缺失: {[b for b in cp_data['bins'].keys() if cp_data['bins'][b] == 0]}")

    print("-" * 60)
    point_coverage = 100.0 * fully_covered_points / total_points if total_points else 0
    bin_coverage = 100.0 * covered_bins / total_bins if total_bins else 0
    print(f"覆盖点覆盖率: {point_coverage:.1f}% ({fully_covered_points}/{total_points})")
    print(f"Bin覆盖率: {bin_coverage:.1f}% ({covered_bins}/{total_bins})")
    print("=" * 60)

    # 保存报告
    cov_report_file = os.path.join(reports_dir, 'comprehensive_coverage_report.json')
    with open(cov_report_file, 'w') as f:
        json.dump({
            'summary': {
                'point_coverage': point_coverage,
                'bin_coverage': bin_coverage,
                'fully_covered_points': fully_covered_points,
                'total_points': total_points,
                'covered_bins': covered_bins,
                'total_bins': total_bins
            },
            'details': cov_summary
        }, f, indent=2)
    print(f"\n覆盖率报告已保存到: {cov_report_file}")

    # 生成代码覆盖率报告
    code_cov_report = None
    if hls_code_collector:
        print("\n[Coverage] 生成代码覆盖率报告...")
        code_cov_summary = hls_code_collector.generate_report(reports_dir)
        print(f"  代码覆盖率: {code_cov_summary.line_coverage:.1f}% lines, {code_cov_summary.branch_coverage:.1f}% branches")
        code_cov_report = code_cov_summary.to_dict()

    # 生成统一报告
    print("\n[Coverage] 生成统一覆盖率报告...")
    reporter = UnifiedCoverageReporter()
    reporter.attach_functional_coverage(coverage_collector)
    if hls_code_collector:
        reporter.attach_code_coverage(hls_code_collector)

    unified_paths = reporter.generate(reports_dir, formats=['json', 'html', 'text'])
    print(f"  统一报告已保存:")
    for fmt, path in unified_paths.items():
        print(f"    [{fmt}] {path}")

    # 保存验证报告
    verify_report = {
        'start_time': start_time.isoformat(),
        'end_time': end_time.isoformat(),
        'total': len(results),
        'passed': passed,
        'pass_rate': pass_rate,
        'coverage': {
            'point_coverage': point_coverage,
            'bin_coverage': bin_coverage,
            'code_line_coverage': code_cov_report.get('line_coverage', 0) if code_cov_report else 0,
            'code_branch_coverage': code_cov_report.get('branch_coverage', 0) if code_cov_report else 0
        }
    }
    verify_file = os.path.join(reports_dir, 'comprehensive_verify_report.json')
    with open(verify_file, 'w') as f:
        json.dump(verify_report, f, indent=2)

    return results, cov_summary


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='ISP-CSIIR 综合覆盖率测试')
    parser.add_argument('--no-code-coverage', action='store_true',
                        help='禁用代码覆盖率收集')
    args = parser.parse_args()

    run_comprehensive_coverage(collect_code_coverage=not args.no_code_coverage)