from .dataset import EVALUATION_DATASET
from .metrics import compute_keyword_coverage, compute_memory_precision, compute_memory_recall, aggregate_system_metrics

def __getattr__(name):
    if name in ('EvaluationRunner', 'run_cli_benchmark'):
        from .runner import EvaluationRunner, run_cli_benchmark
        return locals()[name]
    raise AttributeError(f"module {__name__} has no attribute {name}")

__all__ = [
    'EVALUATION_DATASET',
    'compute_keyword_coverage',
    'compute_memory_precision',
    'compute_memory_recall',
    'aggregate_system_metrics',
    'EvaluationRunner',
    'run_cli_benchmark',
]
