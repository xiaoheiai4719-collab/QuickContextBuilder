"""QuickContextBuilder: offline, bounded, explainable code context."""
from .core import Builder, ContextError, estimate_tokens

__all__ = ["Builder", "ContextError", "estimate_tokens"]
__version__ = "0.1.0"
