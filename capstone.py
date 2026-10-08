import sys
from config import DOCUMENTS_DIR, RETRIEVER_K
from loader import get_document_chunks
from vectorstore import get_retriever, get_vectorstore
from chain import create_rag_chain
from aip_core import cost
from run_gate import format_metrics_report, run_regression_gate


def main():
    print("=" * 75)
    print("  Love2D Documentation RAG Assistant (Plaksha AIP Upgraded)")
    print("  Live Commands: `/metrics` | `/gate` | `/break` | `exit`")
    print("=" * 75)

    try:
        # 1. Load or build vector store (600-char recursive chunks, status='current')
        try:
            vs = get_vectorstore()
        except ValueError:
            chunks = get_document_chunks(DOCUMENTS_DIR, only_current=True)
            vs = get_vectorstore(chunks, only_current=True)

        # 2. Setup Hybrid Retriever (Dense FAISS + Sparse BM25 via Reciprocal Rank Fusion)
        retriever = get_retriever(vs, k=RETRIEVER_K, mode="hybrid")

        # 3. Create Grounded RAG chain (v2 Adaptive Prompt + 5-Layer Guards)
        print("Initializing Grounded RAG chain (v2 + 5 Security Layers)...")
        rag_chain = create_rag_chain(retriever, version="v2", enable_guards=True)
        print("System is ready!\n")

        # 4. Query interaction loop
        while True:
            try:
                query = input("Ask a Love2D question (or type `/metrics`, `/gate`, `/break`, `exit`): \n\n").strip()
                if not query:
                    continue
                if query.lower() in {"exit", "quit", "q"}:
                    print("\nSession Budget Summary:")
                    print("  " + cost.global_budget().report())
                    print("Goodbye!")
                    break
                if query.lower() == "/metrics":
                    print("\n" + format_metrics_report() + "\n")
                    continue
                if query.lower() == "/gate":
                    _, gate_report = run_regression_gate(deliberate_break=False)
                    print("\n" + gate_report + "\n")
                    continue
                if query.lower() in {"/break", "/deliberate-break"}:
                    _, gate_report = run_regression_gate(deliberate_break=True)
                    print("\n" + gate_report + "\n")
                    continue

                print("\nRunning guardrails, searching FAISS, and generating grounded response...")
                response = rag_chain.invoke(query)

                print("\n" + "-" * 75)
                if response and response.answers:
                    for ans in response.answers:
                        ans_text = ans.get("text", "")
                        print(ans_text)

                    if not response.is_refusal and response.cited_chunks:
                        print("\n📚 Cited Reference Chunks (`faiss_index/`):")
                        for ch in response.cited_chunks:
                            idx = ch.get("index", "?")
                            src = ch.get("source", "Unknown.pdf")
                            page = ch.get("page", "?")
                            sec = ch.get("section", "")
                            body = ch.get("content", "").strip()
                            sec_str = f" | Section: {sec}" if sec else ""
                            print(f"\n  [{idx}] {src} (Page {page}{sec_str}):")
                            for ln in body.splitlines():
                                print(f"      {ln}")

                    print("\n" + "." * 75)
                    print(
                        f"Citations: {response.cited_indices} | "
                        f"Refusal: {response.is_refusal} | "
                        f"Latency: {response.latency_ms:.0f}ms | "
                        f"Cost: ${response.cost_usd:.5f} | "
                        f"Cached: {response.cached} | "
                        f"Guard: {response.guard_triggered or 'Passed'}"
                    )
                else:
                    print("No answer returned.")
                print("-" * 65 + "\n")

            except (KeyboardInterrupt, EOFError):
                print("\nSession Budget Summary:")
                print("  " + cost.global_budget().report())
                print("Exiting. Goodbye!")
                break
            except Exception as e:
                print(f"\nError processing query: {e}\n")

    except Exception as e:
        print(f"\nInitialization failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()