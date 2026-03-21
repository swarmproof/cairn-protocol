"""
CAIRN Pipeline - Bonfires Integration

Data pipeline for writing failure/resolution records to Bonfires knowledge graph.
"""

from pipeline.adapter import BonfiresAdapter
from pipeline.bonfires import BonfiresClient
from pipeline.config import PipelineConfig
from pipeline.listener import EventListener
from pipeline.patterns import PatternDetector
from pipeline.records import FailureRecord, ResolutionRecord

__all__ = [
    "BonfiresAdapter",
    "BonfiresClient",
    "PipelineConfig",
    "EventListener",
    "PatternDetector",
    "FailureRecord",
    "ResolutionRecord",
]

__version__ = "0.1.0"
