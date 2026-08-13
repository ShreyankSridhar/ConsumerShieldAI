from rag.chroma_service import chroma_service


if __name__ == "__main__":
    count = chroma_service.seed(force=True)
    print(f"Seeded {count} ChromaDB chunks.")
