"""
SQLite-vec integration for RAG (vector storage and similarity search).
Works with existing SQLite database - adds vec0 virtual tables.
"""

import json
import sqlite3
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from .config import get_settings
from .embeddings import get_embedding_model

_lock = threading.Lock()


def _db_path() -> Path:
    p = get_settings().sqlite_path
    return Path(p) if Path(p).is_absolute() else Path(__file__).resolve().parent.parent / p


def _ensure_dir():
    _db_path().parent.mkdir(parents=True, exist_ok=True)


def _get_connection() -> sqlite3.Connection:
    """Get SQLite connection with sqlite-vec extension loaded."""
    _ensure_dir()
    conn = sqlite3.connect(str(_db_path()))
    
    # Load sqlite-vec extension
    try:
        import sqlite_vec
        conn.enable_load_extension(True)
        sqlite_vec.load(conn)
        conn.enable_load_extension(False)
    except ImportError:
        raise ImportError(
            "sqlite-vec not installed. Run: pip install sqlite-vec"
        )
    except Exception as e:
        raise RuntimeError(f"Failed to load sqlite-vec extension: {e}")
    
    return conn


def init_vector_table(table_name: str = "vec_memory", dimension: int = 384) -> None:
    """
    Initialize vec0 virtual table for vector storage.
    
    Args:
        table_name: Name of the virtual table
        dimension: Embedding dimension (must match your embedding model)
    """
    with _lock:
        conn = _get_connection()
        try:
            conn.execute(f"""
                create virtual table if not exists {table_name} using vec0(
                    embedding float[{dimension}],
                    metadata text  -- JSON metadata: {"type": "diagnosis|alert|feedback", "id": int, ...}
                );
            """)
            conn.commit()
        finally:
            conn.close()


def insert_vector(
    embedding: np.ndarray,
    metadata: Dict[str, Any],
    table_name: str = "vec_memory",
    rowid: Optional[int] = None,
) -> int:
    """
    Insert a vector with metadata into vec0 table.
    
    Args:
        embedding: numpy array of shape (dimension,)
        metadata: Dict with keys like {"type": "diagnosis", "id": 123, "text": "..."}
        table_name: vec0 table name
        rowid: Optional rowid (if None, auto-increment)
    
    Returns:
        rowid of inserted row
    """
    from sqlite_vec import serialize_float32
    
    with _lock:
        conn = _get_connection()
        try:
            # Convert embedding to BLOB format
            embedding_blob = serialize_float32(embedding.tolist())
            metadata_json = json.dumps(metadata)
            
            if rowid is None:
                cursor = conn.execute(
                    f"insert into {table_name}(embedding, metadata) values (?, ?)",
                    (embedding_blob, metadata_json),
                )
                rowid = cursor.lastrowid
            else:
                conn.execute(
                    f"insert into {table_name}(rowid, embedding, metadata) values (?, ?, ?)",
                    (rowid, embedding_blob, metadata_json),
                )
            conn.commit()
            return rowid
        finally:
            conn.close()


def search_similar(
    query_embedding: np.ndarray,
    table_name: str = "vec_memory",
    limit: int = 5,
    filter_metadata: Optional[Dict[str, Any]] = None,
) -> List[Tuple[int, float, Dict[str, Any]]]:
    """
    Search for similar vectors using KNN.
    
    Args:
        query_embedding: Query vector (numpy array)
        table_name: vec0 table name
        limit: Number of results to return
        filter_metadata: Optional filter on metadata (e.g., {"type": "diagnosis"})
                        Note: sqlite-vec doesn't support WHERE filters yet, so this is post-filter
    
    Returns:
        List of (rowid, distance, metadata_dict) tuples, sorted by distance (ascending)
    """
    from sqlite_vec import serialize_float32
    
    with _lock:
        conn = _get_connection()
        try:
            query_blob = serialize_float32(query_embedding.tolist())
            
            # KNN search using MATCH operator
            rows = conn.execute(
                f"""
                select rowid, distance, metadata
                from {table_name}
                where embedding match ?
                order by distance
                limit ?
                """,
                (query_blob, limit * 3 if filter_metadata else limit),  # Fetch more if filtering
            ).fetchall()
            
            results = []
            for rowid, distance, metadata_json in rows:
                metadata = json.loads(metadata_json)
                
                # Apply metadata filter if provided
                if filter_metadata:
                    match = all(
                        metadata.get(k) == v for k, v in filter_metadata.items()
                    )
                    if not match:
                        continue
                
                results.append((rowid, distance, metadata))
                
                if len(results) >= limit:
                    break
            
            return results
        finally:
            conn.close()


def delete_vector(rowid: int, table_name: str = "vec_memory") -> None:
    """Delete a vector by rowid."""
    with _lock:
        conn = _get_connection()
        try:
            conn.execute(f"delete from {table_name} where rowid = ?", (rowid,))
            conn.commit()
        finally:
            conn.close()


def add_text_to_vector_db(
    text: str,
    doc_type: str,
    doc_id: int,
    extra_metadata: Optional[Dict[str, Any]] = None,
    table_name: str = "vec_memory",
    embedding_model_name: str = "all-MiniLM-L6-v2",
) -> int:
    """
    Convenience function: encode text and insert into vector DB.
    
    Args:
        text: Text to embed
        doc_type: Type of document ("diagnosis", "alert", "feedback", etc.)
        doc_id: ID of the document in the original table
        extra_metadata: Additional metadata to store
        table_name: vec0 table name
        embedding_model_name: Model name for embeddings
    
    Returns:
        rowid in vec0 table
    """
    model = get_embedding_model(embedding_model_name)
    
    # Ensure table exists with correct dimension
    try:
        init_vector_table(table_name, dimension=model.dimension)
    except sqlite3.OperationalError:
        # Table might already exist, that's ok
        pass
    
    # Generate embedding
    embedding = model.encode_single(text)
    
    # Prepare metadata
    metadata = {
        "type": doc_type,
        "id": doc_id,
        "text": text[:500],  # Store first 500 chars for reference
    }
    if extra_metadata:
        metadata.update(extra_metadata)
    
    # Insert
    return insert_vector(embedding, metadata, table_name, rowid=doc_id)


def search_text_in_vector_db(
    query_text: str,
    table_name: str = "vec_memory",
    limit: int = 5,
    filter_type: Optional[str] = None,
    embedding_model_name: str = "all-MiniLM-L6-v2",
) -> List[Tuple[int, float, Dict[str, Any]]]:
    """
    Convenience function: encode query text and search vector DB.
    
    Args:
        query_text: Query text
        table_name: vec0 table name
        limit: Number of results
        filter_type: Optional filter by doc_type (e.g., "diagnosis")
        embedding_model_name: Model name for embeddings
    
    Returns:
        List of (rowid, distance, metadata_dict) tuples
    """
    model = get_embedding_model(embedding_model_name)
    
    # Generate query embedding
    query_embedding = model.encode_single(query_text)
    
    # Build filter
    filter_metadata = {"type": filter_type} if filter_type else None
    
    # Search
    return search_similar(query_embedding, table_name, limit, filter_metadata)
