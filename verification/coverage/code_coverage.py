# ============================================================
# ISP-CSIIR Code Coverage Collector
# ============================================================
# Wrapper for gcov/lcov code coverage collection
# ============================================================

import subprocess
import os
import re
import json
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path

# ============================================================
# Coverage Data Structures
# ============================================================
@dataclass
class FileCoverage:
    """单个文件的覆盖率数据"""
    filename: str
    line_coverage: float
    branch_coverage: float
    function_coverage: float
    lines_total: int
    lines_covered: int
    branches_total: int
    branches_covered: int

    def to_dict(self) -> Dict:
        return {
            "filename": self.filename,
            "line_coverage": round(self.line_coverage, 2),
            "branch_coverage": round(self.branch_coverage, 2),
            "function_coverage": round(self.function_coverage, 2),
            "lines_total": self.lines_total,
            "lines_covered": self.lines_covered,
            "branches_total": self.branches_total,
            "branches_covered": self.branches_covered
        }

@dataclass
class CodeCoverageSummary:
    """代码覆盖率摘要"""
    line_coverage: float
    branch_coverage: float
    function_coverage: float
    files: List[FileCoverage]

    def to_dict(self) -> Dict:
        return {
            "line_coverage": round(self.line_coverage, 2),
            "branch_coverage": round(self.branch_coverage, 2),
            "function_coverage": round(self.function_coverage, 2),
            "files": [f.to_dict() for f in self.files]
        }

# ============================================================
# Code Coverage Collector
# ============================================================
class CodeCoverageCollector:
    """代码覆盖率收集器"""

    def __init__(self, source_dir: str, build_dir: str):
        """
        初始化代码覆盖率收集器

        Args:
            source_dir: 源代码目录
            build_dir: 构建目录（.gcda/.gcno 文件位置）
        """
        self.source_dir = Path(source_dir)
        self.build_dir = Path(build_dir)
        self.coverage_files: List[FileCoverage] = []

        # 覆盖率编译选项
        self.coverage_flags = [
            "-fprofile-arcs",
            "-ftest-coverage",
            "-O0",
            "-g"
        ]

    def get_compile_command(self, source_files: List[str],
                            output: str,
                            cxxflags: List[str] = None) -> List[str]:
        """
        获取带覆盖率选项的编译命令

        Args:
            source_files: 源文件列表
            output: 输出文件名
            cxxflags: 额外的编译选项

        Returns:
            完整的编译命令
        """
        cmd = ["g++", "-std=c++17"]
        cmd.extend(self.coverage_flags)
        if cxxflags:
            cmd.extend(cxxflags)
        cmd.extend(["-o", output])
        cmd.extend(source_files)
        return cmd

    def compile_with_coverage(self, source_files: List[str],
                               output: str,
                               cwd: str = None) -> Tuple[bool, str]:
        """
        使用覆盖率选项编译

        Args:
            source_files: 源文件列表
            output: 输出文件名
            cwd: 工作目录

        Returns:
            (成功, 错误信息)
        """
        cmd = self.get_compile_command(source_files, output)

        try:
            result = subprocess.run(
                cmd,
                cwd=cwd or self.build_dir,
                capture_output=True,
                text=True,
                timeout=120
            )

            if result.returncode != 0:
                return False, result.stderr

            return True, ""

        except subprocess.TimeoutExpired:
            return False, "Compilation timeout"
        except Exception as e:
            return False, str(e)

    def run_with_coverage(self, executable: str, args: List[str],
                          cwd: str = None) -> Tuple[bool, str]:
        """
        运行可执行文件并收集覆盖率数据

        Args:
            executable: 可执行文件路径
            args: 命令行参数
            cwd: 工作目录

        Returns:
            (成功, 错误信息)
        """
        cmd = [executable] + args

        try:
            result = subprocess.run(
                cmd,
                cwd=cwd or self.build_dir,
                capture_output=True,
                text=True,
                timeout=300
            )

            if result.returncode != 0:
                return False, result.stderr

            return True, ""

        except subprocess.TimeoutExpired:
            return False, "Execution timeout"
        except Exception as e:
            return False, str(e)

    def run_gcov(self, source_files: List[str],
                 cwd: str = None) -> Tuple[bool, str]:
        """
        运行 gcov 生成覆盖率数据

        Args:
            source_files: 源文件列表
            cwd: 工作目录

        Returns:
            (成功, 错误信息)
        """
        cmd = ["gcov"] + source_files

        try:
            result = subprocess.run(
                cmd,
                cwd=cwd or self.build_dir,
                capture_output=True,
                text=True,
                timeout=60
            )

            # gcov 可能返回非零但仍生成数据
            return True, result.stdout

        except Exception as e:
            return False, str(e)

    def run_lcov(self, output_file: str,
                 cwd: str = None) -> Tuple[bool, str]:
        """
        运行 lcov 收集覆盖率数据

        Args:
            output_file: 输出 .info 文件路径
            cwd: 工作目录

        Returns:
            (成功, 错误信息)
        """
        cmd = [
            "lcov",
            "--capture",
            "--directory", ".",
            "--output-file", output_file
        ]

        try:
            result = subprocess.run(
                cmd,
                cwd=cwd or self.build_dir,
                capture_output=True,
                text=True,
                timeout=60
            )

            if result.returncode != 0:
                return False, result.stderr

            return True, ""

        except FileNotFoundError:
            return False, "lcov not found. Install with: sudo apt-get install lcov"
        except Exception as e:
            return False, str(e)

    def run_genhtml(self, info_file: str,
                    output_dir: str) -> Tuple[bool, str]:
        """
        运行 genhtml 生成 HTML 报告

        Args:
            info_file: .info 文件路径
            output_dir: HTML 输出目录

        Returns:
            (成功, 错误信息)
        """
        cmd = [
            "genhtml",
            info_file,
            "--output-directory", output_dir,
            "--title", "ISP-CSIIR Code Coverage"
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60
            )

            if result.returncode != 0:
                return False, result.stderr

            return True, ""

        except FileNotFoundError:
            return False, "genhtml not found. Install with: sudo apt-get install lcov"
        except Exception as e:
            return False, str(e)

    def parse_gcov_output(self, gcov_output: str) -> Dict[str, Dict]:
        """
        解析 gcov 输出

        Args:
            gcov_output: gcov 命令输出

        Returns:
            文件覆盖率数据
        """
        results = {}
        current_file = None

        for line in gcov_output.split('\n'):
            # 匹配文件名
            if line.startswith("File '"):
                match = re.search(r"File '(.+)'", line)
                if match:
                    current_file = match.group(1)
                    results[current_file] = {
                        "lines_total": 0,
                        "lines_covered": 0,
                        "branches_total": 0,
                        "branches_covered": 0
                    }

            # 匹配行覆盖率
            elif current_file and "Lines executed:" in line:
                match = re.search(r"Lines executed:(\d+\.?\d*)%", line)
                if match:
                    results[current_file]["line_coverage"] = float(match.group(1))

            # 匹配分支覆盖率
            elif current_file and "Branches executed:" in line:
                match = re.search(r"Branches executed:(\d+\.?\d*)%", line)
                if match:
                    results[current_file]["branch_coverage"] = float(match.group(1))

            # 匹配函数覆盖率
            elif current_file and "Functions executed:" in line:
                match = re.search(r"Functions executed:(\d+\.?\d*)%", line)
                if match:
                    results[current_file]["function_coverage"] = float(match.group(1))
                    current_file = None  # 重置当前文件

        return results

    def get_summary(self) -> CodeCoverageSummary:
        """
        获取覆盖率摘要

        Returns:
            覆盖率摘要数据
        """
        if not self.coverage_files:
            return CodeCoverageSummary(
                line_coverage=0.0,
                branch_coverage=0.0,
                function_coverage=0.0,
                files=[]
            )

        total_lines = sum(f.lines_total for f in self.coverage_files)
        covered_lines = sum(f.lines_covered for f in self.coverage_files)
        total_branches = sum(f.branches_total for f in self.coverage_files)
        covered_branches = sum(f.branches_covered for f in self.coverage_files)

        line_cov = 100.0 * covered_lines / total_lines if total_lines > 0 else 0.0
        branch_cov = 100.0 * covered_branches / total_branches if total_branches > 0 else 0.0
        func_cov = sum(f.function_coverage for f in self.coverage_files) / len(self.coverage_files)

        return CodeCoverageSummary(
            line_coverage=line_cov,
            branch_coverage=branch_cov,
            function_coverage=func_cov,
            files=self.coverage_files
        )

    def generate_report(self, output_dir: str,
                        source_files: List[str] = None) -> Tuple[bool, Dict]:
        """
        生成完整的覆盖率报告

        Args:
            output_dir: 报告输出目录
            source_files: 要分析的源文件列表

        Returns:
            (成功, 报告数据)
        """
        os.makedirs(output_dir, exist_ok=True)

        # 默认分析所有 HLS 源文件
        if source_files is None:
            source_files = [
                "stage1_gradient.cpp",
                "stage2_average.cpp",
                "stage3_blend.cpp",
                "stage4_output.cpp",
                "div_utils.cpp"
            ]

        # 运行 gcov
        success, output = self.run_gcov(source_files)
        if not success:
            return False, {"error": output}

        # 解析结果
        parsed = self.parse_gcov_output(output)

        # 转换为 FileCoverage 对象
        for filename, data in parsed.items():
            self.coverage_files.append(FileCoverage(
                filename=filename,
                line_coverage=data.get("line_coverage", 0.0),
                branch_coverage=data.get("branch_coverage", 0.0),
                function_coverage=data.get("function_coverage", 0.0),
                lines_total=data.get("lines_total", 0),
                lines_covered=data.get("lines_covered", 0),
                branches_total=data.get("branches_total", 0),
                branches_covered=data.get("branches_covered", 0)
            ))

        # 运行 lcov 和 genhtml (如果可用)
        info_file = os.path.join(output_dir, "coverage.info")
        html_dir = os.path.join(output_dir, "html")

        lcov_success, _ = self.run_lcov(info_file)
        if lcov_success:
            self.run_genhtml(info_file, html_dir)

        # 保存 JSON 报告
        summary = self.get_summary()
        json_file = os.path.join(output_dir, "code_coverage.json")
        with open(json_file, 'w') as f:
            json.dump(summary.to_dict(), f, indent=2)

        return True, summary.to_dict()

# ============================================================
# Convenience Functions
# ============================================================
def collect_code_coverage(hls_dir: str,
                          test_executable: str,
                          test_args: List[str],
                          output_dir: str) -> Tuple[bool, Dict]:
    """
    便捷函数：一站式代码覆盖率收集

    Args:
        hls_dir: HLS 源代码目录
        test_executable: 测试可执行文件
        test_args: 测试参数
        output_dir: 报告输出目录

    Returns:
        (成功, 报告数据)
    """
    collector = CodeCoverageCollector(
        source_dir=hls_dir,
        build_dir=hls_dir
    )

    # 运行测试
    success, error = collector.run_with_coverage(test_executable, test_args)
    if not success:
        return False, {"error": f"Test execution failed: {error}"}

    # 生成报告
    return collector.generate_report(output_dir)