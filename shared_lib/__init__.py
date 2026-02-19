"""Shared library for multi-agent powerplant monitoring system."""

from .models import (
    Telemetry,
    AlertEvent,
    AlertDetail,
    DiagnosisReport,
    DiagnosisEvidence,
    Ticket,
    Feedback,
    VisionDescription,
    VisionImageReady,
)
from .config import Settings, get_settings
from .utils import (
    get_current_timestamp,
    generate_id,
    append_jsonl,
    ensure_log_dir,
)

# RAG / Vector search (optional)
try:
    from .embeddings import EmbeddingModel, get_embedding_model
    from .vector_db import (
        init_vector_table,
        insert_vector,
        search_similar,
        delete_vector,
        add_text_to_vector_db,
        search_text_in_vector_db,
    )
    from .vector_indexing import (
        index_diagnosis,
        index_alert,
        index_feedback,
        index_ticket,
        index_chat_message,
        index_vision_analysis,
        index_rules,
    )
    _HAS_RAG = True
except ImportError:
    _HAS_RAG = False

__all__ = [
    "Telemetry",
    "AlertEvent",
    "AlertDetail",
    "DiagnosisReport",
    "DiagnosisEvidence",
    "Ticket",
    "Feedback",
    "VisionDescription",
    "VisionImageReady",
    "Settings",
    "get_settings",
    "get_current_timestamp",
    "generate_id",
    "append_jsonl",
    "ensure_log_dir",
]

if _HAS_RAG:
    __all__.extend([
        "EmbeddingModel",
        "get_embedding_model",
        "init_vector_table",
        "insert_vector",
        "search_similar",
        "delete_vector",
        "add_text_to_vector_db",
        "search_text_in_vector_db",
        "index_diagnosis",
        "index_alert",
        "index_feedback",
        "index_ticket",
        "index_chat_message",
        "index_vision_analysis",
        "index_rules",
    ])
