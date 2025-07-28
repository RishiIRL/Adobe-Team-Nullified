from sentence_transformers import SentenceTransformer

def load_model():
    return SentenceTransformer("intfloat/e5-base-v2")

def get_embedding(model, text):
    if isinstance(text, str):
        text = f"query: {text}"
    return model.encode(text)
