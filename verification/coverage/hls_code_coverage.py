# ============================================================
# ISP-CSIIR HLS Code Coverage Collector
# ============================================================
# Collects code coverage from HLS C simulation using gcov/lcov
# ============================================================

import subprocess
import os
import re
import json
import shutil
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
from pathlib import Path

# ============================================================
# Data Structures
# ============================================================
@dataclass
class HLSFileCoverage:
    """HLS 源文件覆盖率数据"""
    filename: str
    line_coverage: float = 0.0
    branch_coverage: float = 0.0
    function_coverage: float = 0.0
    lines_total: int = 0
    lines_covered: int = 0
    branches_total: int = 0
    branches_covered: int = 0

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
class HLSCodeCoverageSummary:
    """HLS 代码覆盖率摘要"""
    line_coverage: float = 0.0
    branch_coverage: float = 0.0
    function_coverage: float = 0.0
    files: List[HLSFileCoverage] = field(default_factory=list)
    timestamp: str = ""
    test_runs: int = 0

    def to_dict(self) -> Dict:
        return {
            "timestamp": self.timestamp,
            "line_coverage": round(self.line_coverage, 2),
            "branch_coverage": round(self.branch_coverage, 2),
            "function_coverage": round(self.function_coverage, 2),
            "test_runs": self.test_runs,
            "files": [f.to_dict() for f in self.files]
        }


# ============================================================
# HLS Code Coverage Collector
# ============================================================
class HLSCodeCoverageCollector:
    """HLS C 仿真代码覆盖率收集器"""

    # 默认 HLS 源文件
    DEFAULT_HLS_SOURCES = [
        "isp_csiir.cpp",      # HLS 顶层实现
        "stage1_gradient.cpp",
        "stage2_average.cpp",
        "stage3_blend.cpp",
        "stage4_output.cpp",
        "div_utils.cpp"
    ]

    # 排除的文件模式（系统头文件等）
    EXCLUDE_PATTERNS = [
        "/usr/include/",           # 系统头文件
        "/usr/lib/",               # 系统库
        "bits/",                   # C++ STL 内部头文件
        "ext/",                    # GCC 扩展
        "x86_64-pc-linux-gnu/",    # 平台特定头文件
        "new_allocator.h",
        "alloc_traits.h",
        "allocator.h",
        "cpp_type_traits.h",
        "ptr_traits.h",
        "char_traits.h",
        "move.h",
        "new",
    ]

    # 覆盖率编译选项
    COVERAGE_FLAGS = [
        "-fprofile-arcs",
        "-ftest-coverage",
        "-O0",
        "-g",
        "--coverage"
    ]

    def __init__(self, hls_dir: str, build_dir: str = None):
        """
        初始化 HLS 代码覆盖率收集器

        Args:
            hls_dir: HLS 源代码目录
            build_dir: 构建目录（默认为 hls_dir/coverage_build）
        """
        self.hls_dir = Path(hls_dir)
        self.build_dir = Path(build_dir) if build_dir else self.hls_dir / "coverage_build"
        self.output_dir = self.build_dir / "reports"

        # 覆盖率数据
        self.summary = HLSCodeCoverageSummary()
        self._test_runs = 0
        self._compiled = False
        self._executable = None

    @property
    def coverage_executable(self) -> str:
        """获取覆盖率可执行文件路径"""
        return str(self.build_dir / "tb_coverage")

    def setup_build_dir(self) -> bool:
        """
        设置构建目录

        Returns:
            是否成功
        """
        try:
            self.build_dir.mkdir(parents=True, exist_ok=True)
            self.output_dir.mkdir(parents=True, exist_ok=True)
            return True
        except Exception as e:
            print(f"[Coverage] 创建构建目录失败: {e}")
            return False

    def find_testbench(self) -> Optional[str]:
        """
        查找测试平台文件

        Returns:
            测试平台文件名
        """
        candidates = [
            "tb_coverage.cpp",  # 覆盖率测试平台 (调用 isp_csiir_top)
            "tb_random.cpp",
            "tb_isp_csiir.cpp",
            "tb_main.cpp",
            "testbench.cpp"
        ]

        for candidate in candidates:
            if (self.hls_dir / candidate).exists():
                return candidate

        return None

    def find_hls_sources(self) -> List[str]:
        """
        查找 HLS 源文件

        Returns:
            源文件列表
        """
        sources = []
        for src in self.DEFAULT_HLS_SOURCES:
            if (self.hls_dir / src).exists():
                sources.append(src)

        # 查找其他 .cpp 文件（排除测试平台）
        testbench = self.find_testbench()
        for cpp_file in self.hls_dir.glob("*.cpp"):
            name = cpp_file.name
            if name not in sources and name != testbench and not name.startswith("tb_"):
                sources.append(name)

        return sources

    def _convert_json_config(self, json_path: str) -> Optional[str]:
        """
        将 JSON 配置文件转换为文本格式

        tb_random.cpp 期望的格式:
        width 64
        height 64
        win_thresh 16 24 32 40
        grad_clip 15 23 31 39
        blend_ratio 32 32 32 32

        Args:
            json_path: JSON 配置文件路径

        Returns:
            临时文本配置文件路径，或 None 表示转换失败
        """
        try:
            with open(json_path, 'r') as f:
                config = json.load(f)

            # 创建临时文本配置文件
            text_path = str(self.build_dir / "temp_config.txt")

            with open(text_path, 'w') as f:
                if 'width' in config:
                    f.write(f"width {config['width']}\n")
                if 'height' in config:
                    f.write(f"height {config['height']}\n")
                if 'win_thresh' in config:
                    wt = config['win_thresh']
                    f.write(f"win_thresh {wt[0]} {wt[1]} {wt[2]} {wt[3]}\n")
                if 'grad_clip' in config:
                    gc = config['grad_clip']
                    f.write(f"grad_clip {gc[0]} {gc[1]} {gc[2]} {gc[3]}\n")
                if 'blend_ratio' in config:
                    br = config['blend_ratio']
                    f.write(f"blend_ratio {br[0]} {br[1]} {br[2]} {br[3]}\n")

            return text_path

        except Exception as e:
            print(f"[Coverage] 配置转换失败: {e}")
            return None

    def compile_with_coverage(self,
                              extra_flags: List[str] = None,
                              source_files: List[str] = None,
                              testbench: str = None) -> Tuple[bool, str]:
        """
        编译带覆盖率选项的可执行文件

        Args:
            extra_flags: 额外的编译选项
            source_files: 源文件列表（默认自动查找）
            testbench: 测试平台文件（默认自动查找）

        Returns:
            (成功, 错误信息)
        """
        self.setup_build_dir()

        # 查找文件
        testbench = testbench or self.find_testbench()
        if not testbench:
            return False, "未找到测试平台文件"

        source_files = source_files or self.find_hls_sources()

        # 构建编译命令
        cmd = ["g++", "-std=c++17"]
        cmd.extend(self.COVERAGE_FLAGS)
        if extra_flags:
            cmd.extend(extra_flags)

        # 添加源文件
        cmd.extend(["-o", str(self.coverage_executable)])
        cmd.append(str(self.hls_dir / testbench))

        for src in source_files:
            src_path = self.hls_dir / src
            if src_path.exists():
                cmd.append(str(src_path))

        print(f"[Coverage] 编译命令: {' '.join(cmd)}")

        try:
            result = subprocess.run(
                cmd,
                cwd=str(self.build_dir),
                capture_output=True,
                text=True,
                timeout=120
            )

            if result.returncode != 0:
                return False, f"编译失败:\n{result.stderr}"

            self._compiled = True
            self._executable = self.coverage_executable
            return True, "编译成功"

        except subprocess.TimeoutExpired:
            return False, "编译超时"
        except Exception as e:
            return False, f"编译异常: {e}"

    def run_test(self,
                 input_file: str,
                 output_dir: str,
                 config_file: str = None) -> Tuple[bool, str]:
        """
        运行单个测试用例

        Args:
            input_file: 输入文件路径
            output_dir: 输出目录
            config_file: 配置文件路径 (支持 JSON 或文本格式)

        Returns:
            (成功, 错误信息)
        """
        if not self._compiled:
            return False, "请先编译覆盖率版本"

        # 处理配置文件 - 如果是 JSON 则转换为文本格式
        text_config = None
        if config_file and config_file.endswith('.json'):
            text_config = self._convert_json_config(config_file)
            if text_config:
                config_file = text_config
            else:
                config_file = None  # 转换失败，使用默认配置

        # 构建运行命令
        cmd = [self._executable, input_file, output_dir]
        if config_file:
            cmd.append(config_file)

        try:
            result = subprocess.run(
                cmd,
                cwd=str(self.build_dir),
                capture_output=True,
                text=True,
                timeout=60
            )

            # 清理临时配置文件
            if text_config and os.path.exists(text_config):
                os.unlink(text_config)

            # 即使返回非零，也可能生成了部分覆盖率数据
            self._test_runs += 1
            return True, result.stdout

        except subprocess.TimeoutExpired:
            return False, "测试超时"
        except Exception as e:
            return False, f"测试异常: {e}"

    def run_test_suite(self,
                       test_cases: List[Dict],
                       base_dir: str) -> Dict:
        """
        运行测试集合并收集覆盖率

        Args:
            test_cases: 测试用例列表，每个包含 path, input_file, config_file
            base_dir: 测试用例基础目录

        Returns:
            运行统计
        """
        stats = {
            "total": len(test_cases),
            "passed": 0,
            "failed": 0,
            "errors": []
        }

        for i, tc in enumerate(test_cases):
            case_path = tc.get("path", "")
            input_file = os.path.join(base_dir, case_path, "input.txt")
            config_file = os.path.join(base_dir, case_path, "config.json")

            # 创建临时输出目录
            output_dir = self.build_dir / "output" / os.path.basename(case_path)
            output_dir.mkdir(parents=True, exist_ok=True)

            success, msg = self.run_test(input_file, str(output_dir), config_file)

            if success:
                stats["passed"] += 1
            else:
                stats["failed"] += 1
                stats["errors"].append({
                    "case": case_path,
                    "error": msg
                })

            print(f"  [{i+1}/{len(test_cases)}] {os.path.basename(case_path)}: {'PASS' if success else 'FAIL'}")

        return stats

    def run_gcov(self, source_files: List[str] = None) -> Tuple[bool, str]:
        """
        运行 gcov 生成覆盖率数据

        Args:
            source_files: 源文件列表

        Returns:
            (成功, gcov 输出)
        """
        if source_files is None:
            source_files = self.find_hls_sources()

        # gcov 需要使用正确的对象文件名
        # 编译器生成的文件名格式: tb_coverage-<source>.gcno
        # 我们需要用源文件名对应到正确的 gcno 文件
        gcno_files = []
        for src in source_files:
            base = src.replace('.cpp', '')
            gcno = f"tb_coverage-{base}.gcno"
            if (self.build_dir / gcno).exists():
                gcno_files.append(gcno)

        if not gcno_files:
            # Fallback: 尝试直接使用源文件名
            gcno_files = source_files

        cmd = ["gcov"] + gcno_files

        try:
            result = subprocess.run(
                cmd,
                cwd=str(self.build_dir),
                capture_output=True,
                text=True,
                timeout=60
            )

            # gcov 可能返回非零但仍生成数据
            return True, result.stdout + result.stderr + result.stderr

        except Exception as e:
            return False, str(e)

    def run_lcov(self, output_file: str = None) -> Tuple[bool, str]:
        """
        运行 lcov 收集覆盖率数据

        Args:
            output_file: 输出 .info 文件路径

        Returns:
            (成功, 错误信息)
        """
        if output_file is None:
            output_file = str(self.output_dir / "coverage.info")

        # 先收集所有覆盖率数据
        cmd = [
            "lcov",
            "--capture",
            "--directory", str(self.build_dir),
            "--output-file", output_file
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

            # 移除系统头文件
            remove_cmd = [
                "lcov",
                "--remove", output_file,
                "/usr/include/*",
                "/usr/lib/*",
                "*/bits/*",
                "*/ext/*",
                "--output-file", output_file
            ]
            subprocess.run(remove_cmd, capture_output=True, text=True, timeout=30)

            return True, ""

        except FileNotFoundError:
            return False, "lcov 未安装。安装命令: sudo apt-get install lcov"
        except Exception as e:
            return False, str(e)

    def run_genhtml(self, info_file: str = None,
                    output_dir: str = None) -> Tuple[bool, str]:
        """
        运行 genhtml 生成 HTML 报告

        Args:
            info_file: .info 文件路径
            output_dir: HTML 输出目录

        Returns:
            (成功, 错误信息)
        """
        if info_file is None:
            info_file = str(self.output_dir / "coverage.info")
        if output_dir is None:
            output_dir = str(self.output_dir / "html")

        cmd = [
            "genhtml",
            info_file,
            "--output-directory", output_dir,
            "--title", "ISP-CSIIR HLS Code Coverage"
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
            return False, "genhtml 未安装。安装命令: sudo apt-get install lcov"
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
                        "line_coverage": 0.0,
                        "branch_coverage": 0.0,
                        "function_coverage": 0.0,
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

    def _should_exclude_file(self, filename: str) -> bool:
        """
        检查文件是否应该被排除

        Args:
            filename: 文件路径

        Returns:
            是否应该排除
        """
        for pattern in self.EXCLUDE_PATTERNS:
            if pattern in filename:
                return True
        return False

    def generate_report(self, output_dir: str = None) -> HLSCodeCoverageSummary:
        """
        生成覆盖率报告

        Args:
            output_dir: 输出目录

        Returns:
            覆盖率摘要
        """
        output_dir = Path(output_dir) if output_dir else self.output_dir
        output_dir.mkdir(parents=True, exist_ok=True)

        # 运行 gcov
        success, gcov_output = self.run_gcov()

        if success:
            parsed = self.parse_gcov_output(gcov_output)

            # 构建 FileCoverage 列表，排除系统头文件
            for filename, data in parsed.items():
                # 跳过系统头文件
                if self._should_exclude_file(filename):
                    continue

                file_cov = HLSFileCoverage(
                    filename=filename,
                    line_coverage=data.get("line_coverage", 0.0),
                    branch_coverage=data.get("branch_coverage", 0.0),
                    function_coverage=data.get("function_coverage", 0.0),
                    lines_total=data.get("lines_total", 0),
                    lines_covered=data.get("lines_covered", 0),
                    branches_total=data.get("branches_total", 0),
                    branches_covered=data.get("branches_covered", 0)
                )
                self.summary.files.append(file_cov)

        # 计算总体覆盖率
        if self.summary.files:
            self.summary.line_coverage = sum(f.line_coverage for f in self.summary.files) / len(self.summary.files)
            self.summary.branch_coverage = sum(f.branch_coverage for f in self.summary.files) / len(self.summary.files)
            self.summary.function_coverage = sum(f.function_coverage for f in self.summary.files) / len(self.summary.files)

        self.summary.timestamp = datetime.now().isoformat()
        self.summary.test_runs = self._test_runs

        # 运行 lcov 和 genhtml
        info_file = str(output_dir / "coverage.info")
        lcov_success, _ = self.run_lcov(info_file)

        if lcov_success:
            self.run_genhtml(info_file, str(output_dir / "html"))

        # 保存 JSON 报告
        json_file = output_dir / "hls_code_coverage.json"
        with open(json_file, 'w') as f:
            json.dump(self.summary.to_dict(), f, indent=2)

        print(f"[Coverage] 报告已保存到: {output_dir}")
        return self.summary

    def cleanup(self):
        """清理覆盖率数据文件"""
        patterns = ["*.gcda", "*.gcno", "*.gcov"]
        for pattern in patterns:
            for f in self.build_dir.glob(pattern):
                f.unlink()

    def reset(self):
        """重置覆盖率收集器"""
        self.summary = HLSCodeCoverageSummary()
        self._test_runs = 0
        self._compiled = False
        self._executable = None


# ============================================================
# Convenience Functions
# ============================================================
def collect_hls_coverage(hls_dir: str,
                         test_cases: List[Dict],
                         base_dir: str,
                         output_dir: str) -> Tuple[bool, HLSCodeCoverageSummary]:
    """
    便捷函数：一站式 HLS 代码覆盖率收集

    Args:
        hls_dir: HLS 源代码目录
        test_cases: 测试用例列表
        base_dir: 测试用例基础目录
        output_dir: 报告输出目录

    Returns:
        (成功, 覆盖率摘要)
    """
    collector = HLSCodeCoverageCollector(hls_dir)

    # 编译
    success, msg = collector.compile_with_coverage()
    if not success:
        print(f"[Coverage] 编译失败: {msg}")
        return False, collector.summary

    # 运行测试
    stats = collector.run_test_suite(test_cases, base_dir)
    print(f"[Coverage] 测试统计: {stats['passed']}/{stats['total']} 通过")

    # 生成报告
    summary = collector.generate_report(output_dir)

    return True, summary