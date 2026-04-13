"""
tripletfinder

Identify spatial cell triplets within a distance threshold.
"""

from .tripletfinder import find_triplets_with_details

# Optional version (safe fallback)
try:
    from importlib.metadata import version
    __version__ = version("tripletfinder")
except Exception:
    __version__ = "unknown"

__all__ = ["find_triplets_with_details", "__version__"]