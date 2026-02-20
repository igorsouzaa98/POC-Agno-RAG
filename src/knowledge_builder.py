"""
Knowledge base builder using RAG with PDF documents.

Uses FastEmbedEmbedder (local ONNX-based) with multilingual support for
Portuguese documents, combined with LanceDB for vector storage.

No additional API keys required for embeddings - runs fully locally.
"""
import os
from pathlib import Path

from agno.knowledge.knowledge import Knowledge
from agno.knowledge.embedder.fastembed import FastEmbedEmbedder
from agno.knowledge.reader.pdf_reader import PDFReader
from agno.vectordb.lancedb import LanceDb, SearchType

from src.config import VECTOR_DB_PATH, KNOWLEDGE_BASE_DIR


def get_knowledge_base() -> Knowledge:
    """
    Build and return a Knowledge instance configured with PDF documents.

    Uses:
    - FastEmbedEmbedder with 'sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2'
      for multilingual (Portuguese) text support, runs locally (no API key needed).
    - LanceDB for vector storage with hybrid search (vector + keyword).
    - PDFReader for parsing PDF documents.

    Returns:
        Knowledge: Configured knowledge base instance ready for use.
    """
    embedder = FastEmbedEmbedder(
        id="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
        dimensions=384,
    )

    vector_db = LanceDb(
        table_name="steel_sales_knowledge",
        uri=VECTOR_DB_PATH,
        search_type=SearchType.hybrid,
        embedder=embedder,
    )

    knowledge_base = Knowledge(
        name="steel_sales_knowledge",
        description=(
            "Knowledge base containing product catalogs and sales processes "
            "for a Brazilian steel sales company. Includes: product dictionary "
            "(dicionario_produtos.pdf), lead qualification process "
            "(processo_classificacao.pdf), and prospecting strategy "
            "(estrategia_captacao.pdf)."
        ),
        vector_db=vector_db,
        readers={
            "pdf": PDFReader(split_on_pages=True, sanitize_content=True),
        },
        max_results=5,
    )

    return knowledge_base


def load_knowledge_base(recreate: bool = False) -> Knowledge:
    """
    Load and index all PDFs from the knowledge directory.

    Args:
        recreate: If True, drops and recreates the vector DB table before indexing.
                  Use True for first run or when PDFs change.

    Returns:
        Knowledge: The loaded knowledge base instance.
    """
    kb = get_knowledge_base()
    knowledge_dir = Path(KNOWLEDGE_BASE_DIR)

    if not knowledge_dir.exists():
        raise FileNotFoundError(
            f"Knowledge directory not found: {knowledge_dir.resolve()}"
        )

    pdf_files = list(knowledge_dir.glob("*.pdf"))
    if not pdf_files:
        raise FileNotFoundError(
            f"No PDF files found in: {knowledge_dir.resolve()}"
        )

    print(f"Found {len(pdf_files)} PDF file(s) to index:")
    for pdf in pdf_files:
        print(f"  - {pdf.name} ({pdf.stat().st_size / 1024:.1f} KB)")

    for pdf_path in pdf_files:
        print(f"\nIndexing: {pdf_path.name}...")
        kb.insert(
            path=str(pdf_path.resolve()),
            name=pdf_path.stem,
            upsert=True,
            skip_if_exists=(not recreate),
        )
        print(f"  Done: {pdf_path.name}")

    return kb
