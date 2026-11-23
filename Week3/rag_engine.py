import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from google import genai
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue

sys.path.append(str(Path(__file__).resolve().parent.parent))
load_dotenv()

client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
qdrant_client = QdrantClient(url="http://localhost:6333", check_compatibility=False)

SYSTEM_INSTRUCTION = """
You are an AI People Operations Assistant. Your task is to answer employee leave policy questions STRICTLY and SOLELY based on the provided policy context snippets.

STRICT RULES:
1. Cite your sources for every factual assertion using the exact format: [Chunk: <chunk_id>, Policy: <policy_id>, Section: <section>, Region: <region>].
   - <chunk_id> must be the exact Chunk ID provided in the context header (e.g. struct_HR-207_APAC_3).
   - <policy_id> must be the policy identifier (e.g. HR-207).
   - <section> must be the specific section number (e.g. 3.2).
   - <region> must be the jurisdiction (e.g. APAC).
2. If the question cannot be directly and fully answered using ONLY the provided context, or if the context does not contain the answer, you MUST refuse gracefully by stating EXACTLY:
   "I do not have sufficient information in the provided leave policy documents to answer this question."
3. Never use outside knowledge or make assumptions beyond the text provided. Do not invent policies, sections, or chunk IDs.
"""

def get_embedding(text: str) -> list[float]:
    response = client.models.embed_content(
        model="gemini-embedding-001",
        contents=text,
    )
    return response.embeddings[0].values

def retrieve_context(query: str, collection_name: str = "structure_chunks", region: str = None, top_k: int = 4) -> list[dict]:
    """Retrieve relevant chunks from Qdrant with optional region metadata filtering."""
    query_emb = get_embedding(query)
    
    query_filter = None
    if region:
        query_filter = Filter(
            must=[FieldCondition(key="region", match=MatchValue(value=region))]
        )
        
    points = qdrant_client.query_points(
        collection_name=collection_name,
        query=query_emb,
        query_filter=query_filter,
        limit=top_k
    ).points
    
    contexts = []
    for p in points:
        contexts.append({
            "chunk_id": p.payload.get("chunk_id", "UNKNOWN"),
            "text": p.payload.get("text", ""),
            "policy_id": p.payload.get("policy_id", "UNKNOWN"),
            "region": p.payload.get("region", "UNKNOWN"),
            "effective_date": p.payload.get("effective_date", "UNKNOWN"),
            "source_file": p.payload.get("source_file", "UNKNOWN"),
            "score": p.score
        })
    return contexts

def answer_query(question: str, collection_name: str = "structure_chunks", region: str = None) -> dict:
    """End-to-end RAG pipeline: Retrieve -> Construct Prompt -> Generate with Grounding & Refusal."""
    contexts = retrieve_context(question, collection_name=collection_name, region=region, top_k=3)
    
    # Format retrieved contexts into prompt with Chunk ID clearly demarcated
    context_str = "\n\n---\n\n".join([
        f"[Chunk ID: {c['chunk_id']} | File: {c['source_file']} | Policy: {c['policy_id']} | Region: {c['region']} | Effective: {c['effective_date']}]\n{c['text']}"
        for c in contexts
    ])
    
    prompt = f"""CONTEXT POLICY DOCUMENTS:
{context_str}

USER QUESTION:
{question}
"""
    
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config={"system_instruction": SYSTEM_INSTRUCTION, "temperature": 0.0}
    )
    
    return {
        "question": question,
        "region_filter": region,
        "retrieved_count": len(contexts),
        "contexts": contexts,
        "top_sources": [(c["chunk_id"], c["policy_id"], c["region"]) for c in contexts],
        "answer": response.text.strip()
    }

GROUNDED_TEST_QUESTIONS = [
    {
        "id": "G1",
        "question": "What is the annual leave carry-over cap for Tier 1 probationary staff in APAC?",
        "region": "APAC",
        "expected_policy": "HR-207",
        "expected_section": "3.2"
    },
    {
        "id": "G2",
        "question": "What is the paid leave duration for a primary caregiver with 24 months of service in North America?",
        "region": "NA",
        "expected_policy": "HR-208",
        "expected_section": "2.1"
    },
    {
        "id": "G3",
        "question": "What documentation is required for medical absences exceeding 8 days in the UK?",
        "region": "UK",
        "expected_policy": "HR-209",
        "expected_section": "2.1"
    }
]

REFUSAL_TEST_QUESTIONS = [
    {
        "id": "R1",
        "question": "What is the company policy on remote work stipends for APAC engineers?",
        "region": "APAC",
        "reason": "Remote work stipend policy is outside the leave addenda corpus."
    },
    {
        "id": "R2",
        "question": "How many months of paid sabbatical leave are employees entitled to take after 5 years of service?",
        "region": None,
        "reason": "Sabbatical policy is not defined in any regional leave addendum."
    },
    {
        "id": "R3",
        "question": "Can employees cash out unused pet bereavement leave under HR-208?",
        "region": None,
        "reason": "Pet bereavement leave cash-out does not exist in HR-208 or any other addendum."
    }
]

def run_evaluation_suite():
    print("\n" + "="*70)
    print("RUNNING 3 GROUNDED GENERATION EVALUATIONS (WITH RESOLVABLE CITATIONS)")
    print("="*70)
    grounded_results = []
    for g in GROUNDED_TEST_QUESTIONS:
        res = answer_query(g["question"], region=g["region"])
        print(f"\n[{g['id']}] Question: {g['question']}")
        print(f"Region Filter: {g['region']}")
        print(f"Answer:\n{res['answer']}\n")
        print(f"Retrieved Chunks: {[c['chunk_id'] for c in res['contexts']]}")
        grounded_results.append({**g, **res})

    print("\n" + "="*70)
    print("RUNNING 3 OUT-OF-CORPUS REFUSAL EVALUATIONS (HONEST REFUSAL TRANSCRIPTS)")
    print("="*70)
    refusal_results = []
    for r in REFUSAL_TEST_QUESTIONS:
        res = answer_query(r["question"], region=r["region"])
        print(f"\n[{r['id']}] Out-of-Corpus Query: {r['question']}")
        print(f"Refusal Response: {res['answer']}")
        refusal_results.append({**r, **res})

    return grounded_results, refusal_results

if __name__ == "__main__":
    run_evaluation_suite()