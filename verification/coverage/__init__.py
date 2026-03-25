# ============================================================
# ISP-CSIIR Coverage Package
# ============================================================
# Unified coverage collection for HLS verification
# ============================================================

from .coverage_config import (
    CoverageType,
    CoverageGoal,
    CodeCoverageConfig,
    CoverageBinConfig,
    CoveragePointConfig,
    CoverageConfig,
    FUNCTIONAL_COVERAGE_POINTS,
    ReportConfig
)

from .functional_coverage import (
    CoverageBin,
    CoveragePoint,
    FunctionalCoverageModel,
    FunctionalCoverageCollector
)

from .code_coverage import (
    FileCoverage,
    CodeCoverageSummary,
    CodeCoverageCollector,
    collect_code_coverage
)

from .hls_code_coverage import (
    HLSFileCoverage,
    HLSCodeCoverageSummary,
    HLSCodeCoverageCollector,
    collect_hls_coverage
)

from .unified_reporter import (
    CoverageMetadata,
    CoverageSummaryStats,
    UnifiedCoverageReport,
    UnifiedReportConfig,
    UnifiedCoverageReporter,
    generate_unified_report,
    merge_coverage_reports
)

from .config_consistency import (
    ISPConfig,
    ConfigConsistencyChecker,
    HLSOutputConfigValidator,
    verify_config_consistency
)

__all__ = [
    # Configuration
    'CoverageType',
    'CoverageGoal',
    'CodeCoverageConfig',
    'CoverageBinConfig',
    'CoveragePointConfig',
    'CoverageConfig',
    'FUNCTIONAL_COVERAGE_POINTS',
    'ReportConfig',

    # Functional Coverage
    'CoverageBin',
    'CoveragePoint',
    'FunctionalCoverageModel',
    'FunctionalCoverageCollector',

    # Code Coverage
    'FileCoverage',
    'CodeCoverageSummary',
    'CodeCoverageCollector',
    'collect_code_coverage',

    # HLS Code Coverage
    'HLSFileCoverage',
    'HLSCodeCoverageSummary',
    'HLSCodeCoverageCollector',
    'collect_hls_coverage',

    # Unified Reporter
    'CoverageMetadata',
    'CoverageSummaryStats',
    'UnifiedCoverageReport',
    'UnifiedReportConfig',
    'UnifiedCoverageReporter',
    'generate_unified_report',
    'merge_coverage_reports',

    # Config Consistency
    'ISPConfig',
    'ConfigConsistencyChecker',
    'HLSOutputConfigValidator',
    'verify_config_consistency'
]