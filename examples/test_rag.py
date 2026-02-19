#!/usr/bin/env python3
"""
Test RAG functionality with sqlite-vec + sentence-transformers.
Run from project root: python examples/test_rag.py
"""

import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from shared_lib.vector_db import (
    init_vector_table,
    add_text_to_vector_db,
    search_text_in_vector_db,
)
from shared_lib.embeddings import get_embedding_model


def main():
    print("🔍 Testing RAG with sqlite-vec + sentence-transformers\n")
    
    # 1. Check embedding model
    print("1. Loading embedding model...")
    model = get_embedding_model("all-MiniLM-L6-v2")
    print(f"   ✓ Model: {model.model_name}")
    print(f"   ✓ Dimension: {model.dimension}\n")
    
    # 2. Initialize vector table
    print("2. Initializing vector table...")
    init_vector_table("vec_memory", dimension=model.dimension)
    print("   ✓ Table 'vec_memory' created\n")
    
    # 3. Add sample documents
    print("3. Adding sample documents...")
    documents = [
        {
            "text": "Root cause: bearing wear. Evidence: vibration_rms=8.5, bearing_temp_c=85.2. Recommended: replace bearing.",
            "type": "diagnosis",
            "id": 1,
            "asset_id": "pump01",
        },
        {
            "text": "Root cause: clogging. Evidence: flow_m3h=12.3 (normal 25), pressure_bar=15.5 (high). Recommended: clean filter.",
            "type": "diagnosis",
            "id": 2,
            "asset_id": "pump02",
        },
        {
            "text": "Alert: vibration_rms exceeded threshold (8.2 > 7.0). Asset: pump01.",
            "type": "alert",
            "id": 101,
            "asset_id": "pump01",
        },
        {
            "text": "Root cause: valve stuck. Evidence: valve_open_pct=50% but flow unchanged. Recommended: inspect valve mechanism.",
            "type": "diagnosis",
            "id": 3,
            "asset_id": "pump03",
        },
    ]
    
    for doc in documents:
        rowid = add_text_to_vector_db(
            text=doc["text"],
            doc_type=doc["type"],
            doc_id=doc["id"],
            extra_metadata={"asset_id": doc["asset_id"]},
        )
        print(f"   ✓ Added {doc['type']} #{doc['id']} (rowid={rowid})")
    print()
    
    # 4. Search queries
    print("4. Testing similarity search:\n")
    
    queries = [
        "bearing temperature high",
        "flow rate low pressure high",
        "vibration sensor alert",
    ]
    
    for query in queries:
        print(f"   Query: '{query}'")
        results = search_text_in_vector_db(
            query_text=query,
            limit=3,
        )
        
        for i, (rowid, distance, metadata) in enumerate(results, 1):
            similarity = 1.0 - distance  # Convert distance to similarity
            print(f"      {i}. [{metadata['type']}] ID={metadata['id']}, "
                  f"Similarity={similarity:.3f}")
            print(f"         Text: {metadata['text'][:80]}...")
        print()
    
    # 5. Filtered search (only diagnoses)
    print("5. Filtered search (diagnosis only):\n")
    results = search_text_in_vector_db(
        query_text="pump problem flow",
        limit=2,
        filter_type="diagnosis",
    )
    
    for rowid, distance, metadata in results:
        similarity = 1.0 - distance
        print(f"   [{metadata['type']}] ID={metadata['id']}, "
              f"Similarity={similarity:.3f}")
        print(f"   {metadata['text']}\n")
    
    print("✅ RAG test completed successfully!")


if __name__ == "__main__":
    try:
        main()
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("\nPlease install dependencies:")
        print("  pip install sqlite-vec sentence-transformers")
        sys.exit(1)
    except Exception as e:
        import traceback
        print(f"❌ Error: {e}")
        traceback.print_exc()
        sys.exit(1)
