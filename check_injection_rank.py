from config import FAISS_INDEX_DIR
from vectorstore import get_vectorstore, Love2DRetriever

vs = get_vectorstore(persist_dir=FAISS_INDEX_DIR, only_current=True)
retriever = Love2DRetriever(vectorstore=vs, k=20, mode="dense", only_current=True)

queries = [
    "what is love.graphics.drawCyberPortal",
    "drawCyberPortal",
    "cyber portal pulsing particle rings",
    "CyberFX",
]

print("=" * 70)
print("DIAGNOSTIC: Searching for injection.pdf in FAISS Index")
print("=" * 70)

# Check if injection.pdf is in docstore
found_in_store = [d for d in retriever.chunks if d.metadata.get("source") == "injection.pdf"]
print(f"Chunks from 'injection.pdf' in index: {len(found_in_store)}")
if found_in_store:
    print(f"Content: {found_in_store[0].page_content[:100]}...")

print("-" * 70)
for q in queries:
    results = retriever.retrieve(q, k=10)
    inj_ranks = [i for i, d in enumerate(results, start=1) if d.metadata.get("source") == "injection.pdf"]
    print(f"\nQuery: '{q}'")
    if inj_ranks:
        print(f"  🎯 FOUND at Rank: #{inj_ranks[0]} out of top {len(results)}!")
    else:
        print(f"  ❌ Not in top {len(results)}. Top 3 hits were:")
        for r_idx, d in enumerate(results[:3], start=1):
            src = d.metadata.get("source")
            page = d.metadata.get("page")
            snip = d.page_content.replace("\n", " ")[:60]
            print(f"     #{r_idx}: {src} p.{page} -> {snip}")
