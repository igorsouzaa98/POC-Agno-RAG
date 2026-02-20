"""
Script para indexar documentos PDF na knowledge base.

Executar uma vez (ou quando os PDFs mudarem):
    python scripts/build_knowledge.py

Para recriar do zero (apagar e reindexar):
    python scripts/build_knowledge.py --recreate
"""
import sys
import argparse

sys.path.insert(0, ".")

from src.knowledge_builder import load_knowledge_base


def main():
    parser = argparse.ArgumentParser(
        description="Indexa PDFs na knowledge base para RAG"
    )
    parser.add_argument(
        "--recreate",
        action="store_true",
        default=False,
        help="Recriar a tabela do vector DB do zero (reindexar tudo)",
    )
    args = parser.parse_args()

    print("=" * 60)
    print("Iniciando indexacao da knowledge base...")
    print(f"Modo: {'RECRIAR (drop + reindex)' if args.recreate else 'INCREMENTAL (skip se existir)'}")
    print("=" * 60)

    try:
        kb = load_knowledge_base(recreate=args.recreate)
        print("\n" + "=" * 60)
        print("Knowledge base criada com sucesso!")
        print("Embedder: FastEmbed (paraphrase-multilingual-MiniLM-L12-v2)")
        print("Vector DB: LanceDB (hybrid search)")
        print("Pronta para uso pelos agentes.")
        print("=" * 60)
    except FileNotFoundError as e:
        print(f"\nERRO: {e}")
        print("Certifique-se de que os PDFs estao em knowledge/")
        sys.exit(1)
    except Exception as e:
        print(f"\nERRO inesperado: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
