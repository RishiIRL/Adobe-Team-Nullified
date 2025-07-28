FROM --platform=linux/amd64 python:3.10-slim

WORKDIR /app

COPY process_pdfs.py .

RUN pip install --no-cache-dir pdfplumber

# Run the script when the container starts
CMD ["python", "process_pdfs.py"]
