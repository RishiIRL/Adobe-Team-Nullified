from sentence_transformers import util

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
