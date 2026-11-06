"""Exact temporal range queries through local state windows."""

from .core import Interval, Result, compile_interval, solve_glucose, solve_intervals

__all__ = ["Interval", "Result", "compile_interval", "solve_glucose", "solve_intervals"]
__version__ = "0.1.0"
