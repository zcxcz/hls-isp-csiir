# ============================================================
# ISP-CSIIR Coverage Report Generator
# ============================================================
# Generates unified coverage reports (code + functional)
# ============================================================

import json
import os
from datetime import datetime
from typing import Dict, Optional
from dataclasses import dataclass

from .functional_coverage import FunctionalCoverageModel
from .code_coverage import CodeCoverageCollector, CodeCoverageSummary
from .config_consistency import ConfigConsistencyChecker

# ============================================================
# Coverage Report Generator
# ============================================================
class CoverageReportGenerator:
    """覆盖率报告生成器"""

    def __init__(self,
                 func_cov: FunctionalCoverageModel = None,
                 code_cov: CodeCoverageCollector = None,
                 config_checker: ConfigConsistencyChecker = None):
        """
        初始化报告生成器

        Args:
            func_cov: 功能覆盖率模型
            code_cov: 代码覆盖率收集器
            config_checker: 配置一致性检查器
        """
        self.func_cov = func_cov
        self.code_cov = code_cov
        self.config_checker = config_checker or ConfigConsistencyChecker()

    def generate_summary_report(self, output_dir: str) -> Dict:
        """
        生成摘要报告

        Args:
            output_dir: 输出目录

        Returns:
            报告数据
        """
        os.makedirs(output_dir, exist_ok=True)

        report = {
            "timestamp": datetime.now().isoformat(),
            "code_coverage": None,
            "functional_coverage": None,
            "config_consistency": None,
            "overall_status": "unknown"
        }

        # 代码覆盖率
        if self.code_cov:
            code_summary = self.code_cov.get_summary()
            report["code_coverage"] = code_summary.to_dict()

        # 功能覆盖率
        if self.func_cov:
            report["functional_coverage"] = self.func_cov.report()

        # 配置一致性
        report["config_consistency"] = self.config_checker.get_mismatch_summary()

        # 计算整体状态
        status = "pass"
        if report["code_coverage"]:
            if report["code_coverage"]["line_coverage"] < 80:
                status = "fail"
            elif report["code_coverage"]["line_coverage"] < 95:
                status = "warn"

        if report["functional_coverage"]:
            if report["functional_coverage"]["overall_coverage"] < 80:
                status = "fail"
            elif report["functional_coverage"]["overall_coverage"] < 95:
                status = "warn" if status != "fail" else "fail"

        if report["config_consistency"]["total_checks"] > 0:
            status = "fail"

        report["overall_status"] = status

        # 保存 JSON 报告
        json_path = os.path.join(output_dir, "coverage_report.json")
        with open(json_path, 'w') as f:
            json.dump(report, f, indent=2)

        # 生成文本报告
        txt_path = os.path.join(output_dir, "coverage_report.txt")
        self._generate_text_report(report, txt_path)

        return report

    def _generate_text_report(self, report: Dict, output_path: str):
        """生成文本格式报告"""
        lines = [
            "=" * 60,
            "ISP-CSIIR Coverage Report",
            "=" * 60,
            f"Generated: {report['timestamp']}",
            f"Overall Status: {report['overall_status'].upper()}",
            "",
        ]

        # 代码覆盖率
        if report["code_coverage"]:
            cc = report["code_coverage"]
            lines.extend([
                "-" * 40,
                "Code Coverage",
                "-" * 40,
                f"  Line Coverage:     {cc['line_coverage']:.1f}%",
                f"  Branch Coverage:   {cc['branch_coverage']:.1f}%",
                f"  Function Coverage: {cc['function_coverage']:.1f}%",
                "",
            ])

            if cc['files']:
                lines.append("  Files:")
                for f in cc['files']:
                    lines.append(f"    {f['filename']}: {f['line_coverage']:.1f}% lines, {f['branch_coverage']:.1f}% branches")
                lines.append("")

        # 功能覆盖率
        if report["functional_coverage"]:
            fc = report["functional_coverage"]
            lines.extend([
                "-" * 40,
                "Functional Coverage",
                "-" * 40,
                f"  Overall: {fc['overall_coverage']:.1f}%",
                "",
            ])

            # 按类别统计
            if fc.get("coverage_by_category"):
                lines.append("  By Category:")
                for cat, cov in fc["coverage_by_category"].items():
                    lines.append(f"    {cat}: {cov:.1f}%")
                lines.append("")

            # 未覆盖项
            if fc.get("uncovered_items"):
                lines.append("  Uncovered Items:")
                for item in fc["uncovered_items"][:10]:  # 只显示前10个
                    lines.append(f"    - {item['point']}/{item['bin']}")
                if len(fc["uncovered_items"]) > 10:
                    lines.append(f"    ... and {len(fc['uncovered_items']) - 10} more")
                lines.append("")

        # 配置一致性
        if report["config_consistency"]["total_checks"] > 0:
            lines.extend([
                "-" * 40,
                "Config Consistency Issues",
                "-" * 40,
            ])
            for mismatch in report["config_consistency"]["mismatches"]:
                lines.append(f"  {mismatch}")
            lines.append("")

        lines.append("=" * 60)

        with open(output_path, 'w') as f:
            f.write("\n".join(lines))

    def generate_html_report(self, output_dir: str) -> str:
        """
        生成 HTML 格式报告

        Args:
            output_dir: 输出目录

        Returns:
            HTML 文件路径
        """
        report = self.generate_summary_report(output_dir)

        html_path = os.path.join(output_dir, "coverage_report.html")

        html_content = self._generate_html_content(report)

        with open(html_path, 'w') as f:
            f.write(html_content)

        return html_path

    def _generate_html_content(self, report: Dict) -> str:
        """生成 HTML 内容"""
        status_color = {
            "pass": "#28a745",
            "warn": "#ffc107",
            "fail": "#dc3545",
            "unknown": "#6c757d"
        }.get(report["overall_status"], "#6c757d")

        html = f"""<!DOCTYPE html>
<html>
<head>
    <title>ISP-CSIIR Coverage Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        h1 {{ color: #333; }}
        .status {{ padding: 10px; border-radius: 5px; color: white; display: inline-block; }}
        .pass {{ background-color: #28a745; }}
        .warn {{ background-color: #ffc107; color: #333; }}
        .fail {{ background-color: #dc3545; }}
        .section {{ margin: 20px 0; padding: 15px; border: 1px solid #ddd; border-radius: 5px; }}
        .metric {{ margin: 10px 0; }}
        .progress {{ background-color: #e9ecef; border-radius: 5px; height: 20px; }}
        .progress-bar {{ height: 100%; border-radius: 5px; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 10px; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #f8f9fa; }}
    </style>
</head>
<body>
    <h1>ISP-CSIIR Coverage Report</h1>
    <p>Generated: {report['timestamp']}</p>

    <div class="status {report['overall_status']}">
        Status: {report['overall_status'].upper()}
    </div>

    {self._html_code_coverage(report)}
    {self._html_functional_coverage(report)}

</body>
</html>
"""
        return html

    def _html_code_coverage(self, report: Dict) -> str:
        """生成代码覆盖率 HTML 部分"""
        if not report.get("code_coverage"):
            return ""

        cc = report["code_coverage"]

        html = f"""
    <div class="section">
        <h2>Code Coverage</h2>

        <div class="metric">
            <strong>Line Coverage: {cc['line_coverage']:.1f}%</strong>
            <div class="progress">
                <div class="progress-bar" style="width: {cc['line_coverage']}%; background-color: {'#28a745' if cc['line_coverage'] >= 95 else '#ffc107' if cc['line_coverage'] >= 80 else '#dc3545'}"></div>
            </div>
        </div>

        <div class="metric">
            <strong>Branch Coverage: {cc['branch_coverage']:.1f}%</strong>
            <div class="progress">
                <div class="progress-bar" style="width: {cc['branch_coverage']}%; background-color: {'#28a745' if cc['branch_coverage'] >= 95 else '#ffc107' if cc['branch_coverage'] >= 80 else '#dc3545'}"></div>
            </div>
        </div>

        <div class="metric">
            <strong>Function Coverage: {cc['function_coverage']:.1f}%</strong>
            <div class="progress">
                <div class="progress-bar" style="width: {cc['function_coverage']}%; background-color: {'#28a745' if cc['function_coverage'] >= 95 else '#ffc107' if cc['function_coverage'] >= 80 else '#dc3545'}"></div>
            </div>
        </div>
    </div>
"""
        return html

    def _html_functional_coverage(self, report: Dict) -> str:
        """生成功能覆盖率 HTML 部分"""
        if not report.get("functional_coverage"):
            return ""

        fc = report["functional_coverage"]

        rows = ""
        for name, point in fc.get("points", {}).items():
            rows += f"""
            <tr>
                <td>{name}</td>
                <td>{point['covered_bins']}/{point['total_bins']}</td>
                <td>{point['coverage']:.1f}%</td>
            </tr>
            """

        html = f"""
    <div class="section">
        <h2>Functional Coverage</h2>

        <div class="metric">
            <strong>Overall: {fc['overall_coverage']:.1f}%</strong>
        </div>

        <table>
            <tr>
                <th>Coverage Point</th>
                <th>Bins Covered</th>
                <th>Coverage</th>
            </tr>
            {rows}
        </table>
    </div>
"""
        return html