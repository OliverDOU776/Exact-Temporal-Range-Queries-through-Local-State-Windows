"""LocalWindows: exact range-count envelopes under total-variation drift budgets."""

from .core import Interval, Result, compile_interval, solve_glucose, solve_intervals

__all__ = ["Interval", "Result", "compile_interval", "solve_glucose", "solve_intervals"]
__version__ = "0.1.0"
