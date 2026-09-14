"""Datasets and the in-memory catalog abstraction."""

from .catalog import Catalog
from .synthetic import SyntheticDataset, make_synthetic

__all__ = ["Catalog", "SyntheticDataset", "make_synthetic"]
