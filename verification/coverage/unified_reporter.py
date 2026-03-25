# ============================================================
# ISP-CSIIR Unified Coverage Reporter
# ============================================================
# Generates unified coverage reports (functional + code coverage)
# ============================================================

import json
import os
from datetime import datetime
from typing import Dict, Optional, List, Any
from dataclasses import dataclass, field, asdict
from pathlib import Path

from .functional_coverage import FunctionalCoverageModel, FunctionalCoverageCollector
from .hls_code_coverage import HLSCodeCoverageSummary, HLSCodeCoverageCollector
from .config_consistency import ConfigConsistencyChecker

# ============================================================
# Report Data Structures
# ============================================================
@dataclass
class CoverageMetadata:
    """报告元数据"""
    timestamp: str
    version: str = "1.0.0"
    project: str = "ISP-CSIIR"

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class CoverageSummaryStats:
    """覆盖率摘要统计"""
    overall_score: float
    status: str  # "pass", "warn", "fail"

    # 功能覆盖率
    func_point_coverage: float
    func_bin_coverage: float
    func_points_covered: int
    func_points_total: int
    func_bins_covered: int
    func_bins_total: int

    # 代码覆盖率
    code_line_coverage: float
    code_branch_coverage: float
    code_function_coverage: float

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class UnifiedCoverageReport:
    """统一覆盖率报告"""
    metadata: CoverageMetadata
    summary: CoverageSummaryStats
    functional_coverage: Dict
    code_coverage: Optional[Dict] = None
    config_consistency: Dict = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            "metadata": self.metadata.to_dict(),
            "summary": self.summary.to_dict(),
            "functional_coverage": self.functional_coverage,
            "code_coverage": self.code_coverage,
            "config_consistency": self.config_consistency
        }


# ============================================================
# Report Configuration
# ============================================================
@dataclass
class UnifiedReportConfig:
    """统一报告配置"""
    # 输出目录
    output_dir: str = "reports/coverage"

    # 覆盖率阈值
    pass_threshold: float = 80.0    # 低于此值为 fail
    warn_threshold: float = 95.0    # 低于此值为 warn

    # 包含内容
    include_uncovered: bool = True
    include_source: bool = False
    include_trends: bool = False

    # 导出格式
    export_json: bool = True
    export_html: bool = True
    export_text: bool = True


# ============================================================
# Unified Coverage Reporter
# ============================================================
class UnifiedCoverageReporter:
    """统一覆盖率报告生成器"""

    def __init__(self, config: UnifiedReportConfig = None):
        """
        初始化报告生成器

        Args:
            config: 报告配置
        """
        self.config = config or UnifiedReportConfig()

        # 覆盖率收集器
        self.func_collector: Optional[FunctionalCoverageCollector] = None
        self.code_collector: Optional[HLSCodeCoverageCollector] = None
        self.config_checker: Optional[ConfigConsistencyChecker] = None

        # 报告数据
        self._report: Optional[UnifiedCoverageReport] = None

    # ========== 数据附加 API ==========

    def attach_functional_coverage(self,
                                    collector: FunctionalCoverageCollector) -> 'UnifiedCoverageReporter':
        """
        附加功能覆盖率收集器

        Args:
            collector: 功能覆盖率收集器

        Returns:
            self (支持链式调用)
        """
        self.func_collector = collector
        return self

    def attach_code_coverage(self,
                             collector: HLSCodeCoverageCollector) -> 'UnifiedCoverageReporter':
        """
        附加代码覆盖率收集器

        Args:
            collector: HLS 代码覆盖率收集器

        Returns:
            self (支持链式调用)
        """
        self.code_collector = collector
        return self

    def attach_config_checker(self,
                               checker: ConfigConsistencyChecker) -> 'UnifiedCoverageReporter':
        """
        附加配置检查器

        Args:
            checker: 配置一致性检查器

        Returns:
            self (支持链式调用)
        """
        self.config_checker = checker
        return self

    def load_from_files(self,
                        func_report_path: str = None,
                        code_report_path: str = None) -> 'UnifiedCoverageReporter':
        """
        从现有报告文件加载数据

        Args:
            func_report_path: 功能覆盖率报告路径
            code_report_path: 代码覆盖率报告路径

        Returns:
            self (支持链式调用)
        """
        if func_report_path and os.path.exists(func_report_path):
            with open(func_report_path, 'r') as f:
                self._func_data = json.load(f)

        if code_report_path and os.path.exists(code_report_path):
            with open(code_report_path, 'r') as f:
                self._code_data = json.load(f)

        return self

    # ========== 报告生成 API ==========

    def generate(self,
                 output_dir: str = None,
                 formats: List[str] = None) -> Dict[str, str]:
        """
        生成统一报告

        Args:
            output_dir: 输出目录
            formats: 输出格式列表 ['json', 'html', 'text']

        Returns:
            生成的文件路径映射
        """
        output_dir = Path(output_dir or self.config.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        formats = formats or ['json', 'html', 'text']
        paths = {}

        # 构建报告数据
        self._report = self._build_report()

        # 按格式导出
        if 'json' in formats:
            paths['json'] = self._export_json(output_dir)
        if 'html' in formats:
            paths['html'] = self._export_html(output_dir)
        if 'text' in formats:
            paths['text'] = self._export_text(output_dir)

        return paths

    def generate_json(self, output_path: str) -> str:
        """仅生成 JSON 报告"""
        self._report = self._build_report()
        with open(output_path, 'w') as f:
            json.dump(self._report.to_dict(), f, indent=2, ensure_ascii=False)
        return output_path

    def generate_html(self, output_path: str) -> str:
        """仅生成 HTML 报告"""
        self._report = self._build_report()
        html_content = self._generate_html_content()
        with open(output_path, 'w') as f:
            f.write(html_content)
        return output_path

    # ========== 内部方法 ==========

    def _build_report(self) -> UnifiedCoverageReport:
        """构建报告数据"""
        # 元数据
        metadata = CoverageMetadata(
            timestamp=datetime.now().isoformat(),
            version="1.0.0",
            project="ISP-CSIIR"
        )

        # 功能覆盖率
        func_data = self._get_functional_data()

        # 代码覆盖率
        code_data = self._get_code_data()

        # 配置一致性
        config_data = self._get_config_data()

        # 计算摘要
        summary = self._calculate_summary(func_data, code_data)

        return UnifiedCoverageReport(
            metadata=metadata,
            summary=summary,
            functional_coverage=func_data,
            code_coverage=code_data,
            config_consistency=config_data
        )

    def _get_functional_data(self) -> Dict:
        """获取功能覆盖率数据"""
        if self.func_collector:
            return self.func_collector.get_coverage_summary()
        elif hasattr(self, '_func_data'):
            return self._func_data
        else:
            return {
                "coverage": 0.0,
                "points": {}
            }

    def _get_code_data(self) -> Optional[Dict]:
        """获取代码覆盖率数据"""
        if self.code_collector and self.code_collector.summary:
            return self.code_collector.summary.to_dict()
        elif hasattr(self, '_code_data'):
            return self._code_data
        else:
            return None

    def _get_config_data(self) -> Dict:
        """获取配置一致性数据"""
        if self.config_checker:
            return self.config_checker.get_mismatch_summary()
        else:
            return {
                "total_checks": 0,
                "mismatches": []
            }

    def _calculate_summary(self,
                           func_data: Dict,
                           code_data: Optional[Dict]) -> CoverageSummaryStats:
        """计算覆盖率摘要"""

        # 功能覆盖率统计
        if isinstance(func_data, dict) and 'summary' in func_data:
            # 来自 comprehensive_coverage_report.json
            summary_data = func_data['summary']
            func_point_cov = summary_data.get('point_coverage', 0.0)
            func_bin_cov = summary_data.get('bin_coverage', 0.0)
            func_points_covered = summary_data.get('fully_covered_points', 0)
            func_points_total = summary_data.get('total_points', 0)
            func_bins_covered = summary_data.get('covered_bins', 0)
            func_bins_total = summary_data.get('total_bins', 0)
        else:
            # 来自 func_collector
            func_point_cov = func_data.get('overall_coverage', 0.0)
            func_bin_cov = func_data.get('overall_coverage', 0.0)
            func_points_covered = 0
            func_points_total = 0
            func_bins_covered = 0
            func_bins_total = 0
            for point_name, point_data in func_data.items():
                if isinstance(point_data, dict):
                    func_points_total += 1
                    if point_data.get('coverage', 0) >= 100:
                        func_points_covered += 1
                    func_bins_covered += point_data.get('covered_bins', 0)
                    func_bins_total += point_data.get('total_bins', 0)

        # 代码覆盖率统计
        if code_data:
            code_line_cov = code_data.get('line_coverage', 0.0)
            code_branch_cov = code_data.get('branch_coverage', 0.0)
            code_func_cov = code_data.get('function_coverage', 0.0)
        else:
            code_line_cov = 0.0
            code_branch_cov = 0.0
            code_func_cov = 0.0

        # 计算综合评分
        if code_data:
            overall_score = (func_point_cov * 0.5 + code_line_cov * 0.5)
        else:
            overall_score = func_point_cov

        # 判断状态
        if overall_score >= self.config.warn_threshold:
            status = "pass"
        elif overall_score >= self.config.pass_threshold:
            status = "warn"
        else:
            status = "fail"

        return CoverageSummaryStats(
            overall_score=round(overall_score, 2),
            status=status,
            func_point_coverage=round(func_point_cov, 2),
            func_bin_coverage=round(func_bin_cov, 2),
            func_points_covered=func_points_covered,
            func_points_total=func_points_total,
            func_bins_covered=func_bins_covered,
            func_bins_total=func_bins_total,
            code_line_coverage=round(code_line_cov, 2),
            code_branch_coverage=round(code_branch_cov, 2),
            code_function_coverage=round(code_func_cov, 2)
        )

    def _export_json(self, output_dir: Path) -> str:
        """导出 JSON 报告"""
        path = output_dir / "unified_coverage_report.json"
        with open(path, 'w') as f:
            json.dump(self._report.to_dict(), f, indent=2, ensure_ascii=False)
        return str(path)

    def _export_html(self, output_dir: Path) -> str:
        """导出 HTML 报告"""
        path = output_dir / "unified_coverage_report.html"
        html_content = self._generate_html_content()
        with open(path, 'w') as f:
            f.write(html_content)
        return str(path)

    def _export_text(self, output_dir: Path) -> str:
        """导出文本报告"""
        path = output_dir / "unified_coverage_report.txt"
        text_content = self._generate_text_content()
        with open(path, 'w') as f:
            f.write(text_content)
        return str(path)

    def _generate_html_content(self) -> str:
        """生成 HTML 内容"""
        report = self._report
        summary = report.summary

        # 状态颜色映射
        status_colors = {
            "pass": "#28a745",
            "warn": "#ffc107",
            "fail": "#dc3545"
        }
        status_color = status_colors.get(summary.status, "#6c757d")

        # 功能覆盖率详情
        func_rows = ""
        func_data = report.functional_coverage
        if 'details' in func_data:
            for cp_name, cp_data in func_data['details'].items():
                coverage = cp_data.get('coverage', 0)
                bar_color = "#28a745" if coverage >= 95 else "#ffc107" if coverage >= 80 else "#dc3545"
                func_rows += f"""
                <tr>
                    <td>{cp_name}</td>
                    <td>{cp_data.get('covered_bins', 0)}/{cp_data.get('total_bins', 0)}</td>
                    <td>
                        <div class="progress-bar-container">
                            <div class="progress-bar" style="width: {coverage}%; background-color: {bar_color};"></div>
                            <span class="progress-text">{coverage:.1f}%</span>
                        </div>
                    </td>
                </tr>
                """
        elif isinstance(func_data, dict):
            for cp_name, cp_data in func_data.items():
                if isinstance(cp_data, dict) and 'coverage' in cp_data:
                    coverage = cp_data.get('coverage', 0)
                    bar_color = "#28a745" if coverage >= 95 else "#ffc107" if coverage >= 80 else "#dc3545"
                    func_rows += f"""
                    <tr>
                        <td>{cp_name}</td>
                        <td>{cp_data.get('covered_bins', 0)}/{cp_data.get('total_bins', 0)}</td>
                        <td>
                            <div class="progress-bar-container">
                                <div class="progress-bar" style="width: {coverage}%; background-color: {bar_color};"></div>
                                <span class="progress-text">{coverage:.1f}%</span>
                            </div>
                        </td>
                    </tr>
                    """

        # 代码覆盖率详情
        code_section = ""
        if report.code_coverage:
            cc = report.code_coverage
            code_section = f"""
            <div class="section">
                <h2>Code Coverage</h2>
                <div class="metric-row">
                    <div class="metric">
                        <span class="metric-label">Line Coverage</span>
                        <div class="progress-bar-container">
                            <div class="progress-bar" style="width: {cc['line_coverage']}%;"></div>
                            <span class="progress-text">{cc['line_coverage']:.1f}%</span>
                        </div>
                    </div>
                    <div class="metric">
                        <span class="metric-label">Branch Coverage</span>
                        <div class="progress-bar-container">
                            <div class="progress-bar" style="width: {cc['branch_coverage']}%;"></div>
                            <span class="progress-text">{cc['branch_coverage']:.1f}%</span>
                        </div>
                    </div>
                    <div class="metric">
                        <span class="metric-label">Function Coverage</span>
                        <div class="progress-bar-container">
                            <div class="progress-bar" style="width: {cc['function_coverage']}%;"></div>
                            <span class="progress-text">{cc['function_coverage']:.1f}%</span>
                        </div>
                    </div>
                </div>
            </div>
            """

        html = f"""<!DOCTYPE html>
<html>
<head>
    <title>ISP-CSIIR Unified Coverage Report</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
            color: #333;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background-color: white;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            padding: 20px;
        }}
        .header {{
            text-align: center;
            border-bottom: 1px solid #eee;
            padding-bottom: 20px;
            margin-bottom: 20px;
        }}
        .header h1 {{
            margin: 0;
            color: #333;
        }}
        .header .timestamp {{
            color: #666;
            font-size: 0.9em;
        }}
        .status-badge {{
            display: inline-block;
            padding: 8px 16px;
            border-radius: 20px;
            color: white;
            font-weight: bold;
            margin-top: 10px;
        }}
        .summary-cards {{
            display: flex;
            gap: 20px;
            margin-bottom: 30px;
        }}
        .summary-card {{
            flex: 1;
            padding: 20px;
            border-radius: 8px;
            text-align: center;
            background-color: #f8f9fa;
        }}
        .summary-card h3 {{
            margin: 0 0 10px 0;
            color: #666;
            font-size: 0.9em;
        }}
        .summary-card .value {{
            font-size: 2em;
            font-weight: bold;
        }}
        .section {{
            margin-bottom: 30px;
        }}
        .section h2 {{
            margin: 0 0 15px 0;
            padding-bottom: 10px;
            border-bottom: 2px solid #007bff;
            color: #007bff;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
        }}
        th, td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #eee;
        }}
        th {{
            background-color: #f8f9fa;
            font-weight: 600;
        }}
        .progress-bar-container {{
            position: relative;
            background-color: #e9ecef;
            border-radius: 4px;
            height: 24px;
            overflow: hidden;
        }}
        .progress-bar {{
            height: 100%;
            border-radius: 4px;
            background-color: #007bff;
            transition: width 0.3s ease;
        }}
        .progress-text {{
            position: absolute;
            right: 8px;
            top: 50%;
            transform: translateY(-50%);
            font-size: 0.85em;
            font-weight: 600;
        }}
        .metric-row {{
            display: flex;
            gap: 20px;
        }}
        .metric {{
            flex: 1;
        }}
        .metric-label {{
            display: block;
            margin-bottom: 8px;
            font-weight: 600;
        }}
        .footer {{
            text-align: center;
            margin-top: 30px;
            padding-top: 20px;
            border-top: 1px solid #eee;
            color: #666;
            font-size: 0.85em;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>ISP-CSIIR Unified Coverage Report</h1>
            <div class="timestamp">Generated: {report.metadata.timestamp}</div>
            <div class="status-badge" style="background-color: {status_color};">
                Status: {summary.status.upper()}
            </div>
        </div>

        <div class="summary-cards">
            <div class="summary-card">
                <h3>Overall Score</h3>
                <div class="value">{summary.overall_score:.1f}%</div>
            </div>
            <div class="summary-card">
                <h3>Functional Coverage</h3>
                <div class="value">{summary.func_point_coverage:.1f}%</div>
                <small>{summary.func_points_covered}/{summary.func_points_total} points, {summary.func_bins_covered}/{summary.func_bins_total} bins</small>
            </div>
            <div class="summary-card">
                <h3>Code Coverage</h3>
                <div class="value">{summary.code_line_coverage:.1f}%</div>
                <small>Lines: {summary.code_line_coverage:.1f}%, Branches: {summary.code_branch_coverage:.1f}%</small>
            </div>
        </div>

        <div class="section">
            <h2>Functional Coverage Details</h2>
            <table>
                <thead>
                    <tr>
                        <th>Coverage Point</th>
                        <th>Bins</th>
                        <th>Coverage</th>
                    </tr>
                </thead>
                <tbody>
                    {func_rows}
                </tbody>
            </table>
        </div>

        {code_section}

        <div class="footer">
            ISP-CSIIR Verification Framework | Report generated by UnifiedCoverageReporter
        </div>
    </div>
</body>
</html>
"""
        return html

    def _generate_text_content(self) -> str:
        """生成文本内容"""
        report = self._report
        summary = report.summary

        lines = [
            "=" * 70,
            "ISP-CSIIR Unified Coverage Report",
            "=" * 70,
            f"Generated: {report.metadata.timestamp}",
            f"Status: {summary.status.upper()}",
            f"Overall Score: {summary.overall_score:.1f}%",
            "",
            "-" * 70,
            "Summary",
            "-" * 70,
            f"  Functional Coverage: {summary.func_point_coverage:.1f}%",
            f"    Points: {summary.func_points_covered}/{summary.func_points_total}",
            f"    Bins:   {summary.func_bins_covered}/{summary.func_bins_total}",
            "",
            f"  Code Coverage:",
            f"    Line:     {summary.code_line_coverage:.1f}%",
            f"    Branch:   {summary.code_branch_coverage:.1f}%",
            f"    Function: {summary.code_function_coverage:.1f}%",
            "",
        ]

        # 功能覆盖率详情
        lines.extend([
            "-" * 70,
            "Functional Coverage Details",
            "-" * 70,
        ])

        func_data = report.functional_coverage
        if 'details' in func_data:
            for cp_name, cp_data in func_data['details'].items():
                coverage = cp_data.get('coverage', 0)
                status = "✓" if coverage >= 100 else "○"
                lines.append(f"  {status} {cp_name}: {coverage:.1f}% ({cp_data.get('covered_bins', 0)}/{cp_data.get('total_bins', 0)} bins)")

        # 代码覆盖率详情
        if report.code_coverage:
            lines.extend([
                "",
                "-" * 70,
                "Code Coverage Details",
                "-" * 70,
            ])

            for file_data in report.code_coverage.get('files', []):
                lines.append(f"  {file_data['filename']}:")
                lines.append(f"    Lines: {file_data['line_coverage']:.1f}%")
                lines.append(f"    Branches: {file_data['branch_coverage']:.1f}%")

        lines.append("")
        lines.append("=" * 70)

        return "\n".join(lines)

    # ========== 便捷方法 ==========

    def get_summary(self) -> CoverageSummaryStats:
        """获取覆盖率摘要"""
        if not self._report:
            self._report = self._build_report()
        return self._report.summary

    def get_uncovered_items(self) -> List[Dict]:
        """获取所有未覆盖项"""
        items = []

        func_data = self._get_functional_data()

        if 'details' in func_data:
            for cp_name, cp_data in func_data['details'].items():
                for bin_name, hit_count in cp_data.get('bins', {}).items():
                    if hit_count == 0:
                        items.append({
                            "type": "functional_bin",
                            "point": cp_name,
                            "bin": bin_name,
                            "hit_count": 0
                        })

        return items


# ============================================================
# Convenience Functions
# ============================================================
def generate_unified_report(
    output_dir: str,
    func_collector: FunctionalCoverageCollector = None,
    code_collector: HLSCodeCoverageCollector = None,
    config: UnifiedReportConfig = None,
    formats: List[str] = None
) -> Dict[str, str]:
    """
    便捷函数：一站式生成统一覆盖率报告

    Args:
        output_dir: 输出目录
        func_collector: 功能覆盖率收集器
        code_collector: 代码覆盖率收集器
        config: 报告配置
        formats: 输出格式列表

    Returns:
        生成的文件路径映射
    """
    reporter = UnifiedCoverageReporter(config)

    if func_collector:
        reporter.attach_functional_coverage(func_collector)
    if code_collector:
        reporter.attach_code_coverage(code_collector)

    return reporter.generate(output_dir, formats)


def merge_coverage_reports(
    func_report_path: str,
    code_report_path: str,
    output_dir: str
) -> Dict[str, str]:
    """
    合并功能覆盖率和代码覆盖率报告

    Args:
        func_report_path: 功能覆盖率报告路径
        code_report_path: 代码覆盖率报告路径
        output_dir: 输出目录

    Returns:
        生成的文件路径映射
    """
    reporter = UnifiedCoverageReporter()
    reporter.load_from_files(func_report_path, code_report_path)
    return reporter.generate(output_dir)