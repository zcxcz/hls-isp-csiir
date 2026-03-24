#!/usr/bin/env python3
# ============================================================
# ISP-CSIIR Coverage Runner
# ============================================================
# Unified entry point for coverage collection
# ============================================================

import argparse
import os
import sys
import json
from datetime import datetime

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from coverage import (
    FunctionalCoverageCollector,
    FunctionalCoverageModel,
    CodeCoverageCollector,
    ConfigConsistencyChecker,
    ISPConfig,
    CoverageConfig
)

# ============================================================
# Coverage Runner
# ============================================================
class CoverageRunner:
    """覆盖率运行器"""

    def __init__(self, hls_dir: str, verification_dir: str):
        self.hls_dir = hls_dir
        self.verification_dir = verification_dir
        self.output_dir = os.path.join(verification_dir, "reports", "coverage")

        # 初始化收集器
        self.func_cov = FunctionalCoverageCollector()
        self.code_cov = CodeCoverageCollector(hls_dir, hls_dir)
        self.config_checker = ConfigConsistencyChecker()

    def run_with_coverage(self, test_args: dict) -> dict:
        """
        运行测试并收集覆盖率

        Args:
            test_args: 测试参数

        Returns:
            覆盖率报告
        """
        results = {
            "timestamp": datetime.now().isoformat(),
            "code_coverage": None,
            "functional_coverage": None,
            "config_consistency": None,
            "tests_passed": 0,
            "tests_total": 0
        }

        # 启动功能覆盖率收集
        self.func_cov.model.start()

        return results

    def collect_code_coverage(self, source_files: list = None) -> dict:
        """
        收集代码覆盖率

        Args:
            source_files: 源文件列表

        Returns:
            代码覆盖率数据
        """
        if source_files is None:
            source_files = [
                "stage1_gradient.cpp",
                "stage2_average.cpp",
                "stage3_blend.cpp",
                "stage4_output.cpp",
                "div_utils.cpp"
            ]

        # 运行 gcov
        success, output = self.code_cov.run_gcov(source_files)
        if not success:
            return {"error": output}

        # 解析结果
        parsed = self.code_cov.parse_gcov_output(output)

        return parsed

    def generate_report(self) -> str:
        """
        生成覆盖率报告

        Returns:
            报告目录
        """
        from coverage.coverage_report import CoverageReportGenerator

        generator = CoverageReportGenerator(
            func_cov=self.func_cov.model,
            code_cov=self.code_cov,
            config_checker=self.config_checker
        )

        os.makedirs(self.output_dir, exist_ok=True)
        generator.generate_summary_report(self.output_dir)
        generator.generate_html_report(self.output_dir)

        return self.output_dir

# ============================================================
# Integration with compute_expected.py
# ============================================================
def patch_compute_expected_for_coverage():
    """
    为 compute_expected.py 添加覆盖率收集支持

    使用方式：
    from coverage.run_coverage import get_coverage_collector

    cov = get_coverage_collector()
    cov.sample_pixel_processing(...)
    """
    _collector = None

    def get_coverage_collector() -> FunctionalCoverageCollector:
        nonlocal _collector
        if _collector is None:
            _collector = FunctionalCoverageCollector()
        return _collector

    return get_coverage_collector

# 导出单例获取函数
get_coverage_collector = patch_compute_expected_for_coverage()

# ============================================================
# Main Entry Point
# ============================================================
def main():
    parser = argparse.ArgumentParser(
        description="ISP-CSIIR Coverage Collection Runner"
    )

    parser.add_argument(
        "--hls-dir",
        default="../hls",
        help="HLS source directory"
    )

    parser.add_argument(
        "--output-dir",
        default="../verification/reports/coverage",
        help="Output directory for reports"
    )

    parser.add_argument(
        "--collect-code",
        action="store_true",
        help="Collect code coverage"
    )

    parser.add_argument(
        "--collect-functional",
        action="store_true",
        help="Collect functional coverage"
    )

    parser.add_argument(
        "--run-tests",
        type=int,
        default=0,
        help="Run N random tests with coverage"
    )

    args = parser.parse_args()

    # 确定要收集的覆盖率类型
    if not args.collect_code and not args.collect_functional:
        args.collect_code = True
        args.collect_functional = True

    runner = CoverageRunner(
        hls_dir=args.hls_dir,
        verification_dir=os.path.dirname(args.output_dir)
    )
    runner.output_dir = args.output_dir

    print("=" * 60)
    print("ISP-CSIIR Coverage Collection")
    print("=" * 60)

    # 收集代码覆盖率
    if args.collect_code:
        print("\n[Code Coverage]")
        print("  Running gcov...")

        source_files = [
            "stage1_gradient.cpp",
            "stage2_average.cpp",
            "stage3_blend.cpp",
            "stage4_output.cpp",
            "div_utils.cpp"
        ]

        success, output = runner.code_cov.run_gcov(source_files, cwd=args.hls_dir)

        if success:
            parsed = runner.code_cov.parse_gcov_output(output)
            print(f"  Parsed {len(parsed)} files")

            for filename, data in parsed.items():
                print(f"    {filename}: {data.get('line_coverage', 0):.1f}% lines")
        else:
            print(f"  Error: {output}")

    # 生成报告
    print("\n[Generating Reports]")
    report_dir = runner.generate_report()
    print(f"  Reports saved to: {report_dir}")

    print("\n" + "=" * 60)

if __name__ == "__main__":
    main()