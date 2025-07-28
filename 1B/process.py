import pdfplumber
import json
from pathlib import Path
from collections import Counter
import re
import time
from datetime import datetime
import os

# --- Round 1B Dependencies ---
# Note: These libraries must be installed in the Docker container.
# sentence-transformers, torch, pdfplumber
try:
    from sentence_transformers import SentenceTransformer, util
except ImportError:
    print("Error: sentence-transformers library not found.")
    print("Please install it using: pip install sentence-transformers")
    exit()

# ==============================================================================
#  COMBINED UTILITY FUNCTIONS
# ==============================================================================

# --- From parse_pdf.py ---
def extract_sections(path):
    result = []
    title_candidate = None

    with pdfplumber.open(path) as pdf:
        for i, page in enumerate(pdf.pages):
            text = page.extract_text()
            if not text:
                continue

            lines = text.split("\n")

            # Extract document-level title from page 1 (if possible)
            if i == 0:
                for line in lines:
                    clean = line.strip()
                    if (
                        len(clean.split()) >= 5 and
                        re.match(r'^[A-Z][A-Za-z\s\-:,]+$', clean) and
                        not clean.endswith(".")
                    ):
                        title_candidate = clean
                        break

            # Process lines into sections
            for line in lines:
                clean_line = line.strip()
                if len(clean_line) > 30:
                    result.append({
                        "page": i + 1,
                        "title": clean_line[:40],
                        "text": clean_line
                    })

    return result, title_candidate

# --- From embedder.py ---
def load_model():
    return SentenceTransformer("intfloat/e5-base-v2")

def get_embedding(model, text):
    if isinstance(text, str):
        text = f"query: {text}"
    return model.encode(text)

# --- From ranker.py ---
def rank_sections(query_emb, sections, model, top_k=5):
    texts = [sec["text"] for sec in sections]
    embeddings = model.encode(texts, convert_to_tensor=True)
    scores = util.pytorch_cos_sim(query_emb, embeddings)[0]
    top_results = scores.topk(k=min(top_k, len(sections)))
    ranked = []
    for score, idx in zip(top_results.values, top_results.indices):
        sec = sections[int(idx)]
        sec["score"] = float(score)
        ranked.append(sec)
    return ranked

# ==============================================================================
#  MAIN EXECUTION LOGIC (Adapted from main.ipynb)
# ==============================================================================

def process_document_intelligence_request():
    """
    Main entry point for the Round 1B solution.
    """
    # Use absolute paths for Docker compatibility
    input_dir = Path("/app/input")
    output_dir = Path("/app/output")
    output_dir.mkdir(parents=True, exist_ok=True)

    input_json_path = input_dir / "challenge1b_input.json"

    if not input_json_path.exists():
        print(f"Error: No JSON request file found at {input_json_path}.")
        return
        
    print("Loading AI model...")
    model = load_model()

    print(f"Processing request from: {input_json_path}")
    
    with open(input_json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    query = data["job_to_be_done"]["task"]
    documents = data["documents"]
    query_emb = get_embedding(model, query)

    all_ranked_sections = []
    input_filenames = [d["filename"] for d in documents]

    for doc_info in documents:
        fname = doc_info["filename"]
        pdf_path = input_dir / fname

        if not pdf_path.exists():
            print(f"🚫 Missing file: {pdf_path}")
            continue

        sections, doc_title = extract_sections(pdf_path)
        
        if sections:
            ranked = rank_sections(query_emb, sections, model)
            for section in ranked:
                section['document'] = fname # Add document name to each section
            all_ranked_sections.extend(ranked)

    # Sort all sections from all documents by their score
    all_ranked_sections.sort(key=lambda x: x['score'], reverse=True)

    # Prepare final output lists
    extracted_sections_output = []
    subsection_analysis_output = []

    for i, top_sec in enumerate(all_ranked_sections[:5]):
        extracted_sections_output.append({
            "document": top_sec['document'],
            "section_title": top_sec.get("title", top_sec["text"][:40]),
            "importance_rank": i + 1,
            "page_number": top_sec["page"]
        })

        subsection_analysis_output.append({
            "document": top_sec['document'],
            "refined_text": top_sec["text"],
            "page_number": top_sec["page"]
        })


    final_output = {
        "metadata": {
            "input_documents": input_filenames,
            "persona": data.get("persona", {}).get("role", "Unknown"),
            "job_to_be_done": query,
            "processing_timestamp": datetime.now().isoformat()
        },
        "extracted_sections": extracted_sections_output,
        "subsection_analysis": subsection_analysis_output
    }

    output_json_path = output_dir / "challenge1b_output.json"
    with open(output_json_path, "w", encoding="utf-8") as f:
        json.dump(final_output, f, indent=2, ensure_ascii=False)

    print(f"✅ Done: Saved output to {output_json_path}")


if __name__ == "__main__":
    process_document_intelligence_request()
    print("\nProcessing complete.")
