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

    # Config Consistency
    'ISPConfig',
    'ConfigConsistencyChecker',
    'HLSOutputConfigValidator',
    'verify_config_consistency'
]