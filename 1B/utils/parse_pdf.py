import pdfplumber
import re

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
