"""Analysis package. Importing it registers every rule."""

from app.analysis import rules as _rules  # noqa: F401  (import side effect: registration)
from app.analysis.base import REGISTRY, Finding, evaluate_all

__all__ = ["REGISTRY", "Finding", "evaluate_all"]
