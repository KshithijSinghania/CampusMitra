import os
from pathlib import Path
from django.conf import settings
from langchain_text_splitters import RecursiveCharacterTextSplitter
import chromadb
import cohere

FAQ_DIR = Path(__file__).resolve().parent / "data" / "faqs"

def embed_query(text):
    co = cohere.Client(settings.COHERE_API_KEY)
    return co.embed(texts=[text], model="embed-english-v3.0", input_type="search_query").embeddings[0]


def ingest_handbook_docs():
    co = cohere.Client(settings.COHERE_API_KEY)
    chroma_client = chromadb.PersistentClient(path="vectorstore")
    collection = chroma_client.get_or_create_collection(name="institutional_knowledge")

    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)

    md_files = list(FAQ_DIR.glob("*.md"))
    print(f"Found {len(md_files)} FAQ documents to ingest.")

    all_ids, all_embeddings, all_documents, all_metadatas = [], [], [], []

    for filepath in md_files:
        text = filepath.read_text(encoding="utf-8")
        doc_title = filepath.stem.replace("_", " ").title()
        chunks = splitter.split_text(text)

        if not chunks:
            continue

        embeddings = co.embed(texts=chunks, model="embed-english-v3.0", input_type="search_document").embeddings

        for idx, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            all_ids.append(f"{filepath.stem}_{idx}")
            all_embeddings.append(embedding)
            all_documents.append(chunk)
            all_metadatas.append({
                "source": "handbook",
                "doc_title": doc_title,
                "filename": filepath.name,
                "chunk_index": idx,
            })

    if all_ids:
        collection.upsert(
            ids=all_ids,
            embeddings=all_embeddings,
            documents=all_documents,
            metadatas=all_metadatas,
        )
        print(f"Ingested {len(all_ids)} chunks from {len(md_files)} documents into 'institutional_knowledge'.")
    else:
        print("No chunks generated — check that .md files exist in assistant/data/faqs/")
