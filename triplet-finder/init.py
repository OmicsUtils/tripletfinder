"""
triplet_finder

Identify spatial cell triplets within a distance threshold.
"""

from importlib.metadata import version
from .tripletfinder import find_triplets_with_details

__version__ = version("triplet-finder")

__all__ = ["find_triplets_with_details", "__version__"]
