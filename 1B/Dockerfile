FROM --platform=linux/amd64 python:3.11-slim

WORKDIR /app

COPY process.py .

RUN pip install --no-cache-dir pdfplumber==0.10.3 sentence-transformers==2.2.2 torch==2.1.0

CMD ["python", "process.py"]
