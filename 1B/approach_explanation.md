# **Approach Explanation: Persona-Driven Document Intelligence**

Our solution for Round 1B is designed as a dynamic and scalable system to extract and rank relevant information from a collection of PDF documents based on a specific user persona and their job-to-be-done. The core principle of our approach is to avoid any hardcoding or document-specific logic, ensuring the system can generalize to any given set of documents, persona, and task.  
The methodology is implemented as a multi-stage pipeline:

### **1\. Dynamic Document Parsing and Sectioning**

The first stage of our pipeline is to process the raw PDF files. For this, we leverage the **pdfplumber** library to robustly extract text, character, and layout information from each document. Our script iterates through every page, reconstructing lines of text and identifying potential section breaks. We implemented a heuristic-based approach to identify titles and headings by analyzing visual cues such as font size, weight, and position. For each heading identified, we extract all subsequent text until the next heading, forming a complete, meaningful "section" that includes both a title and its corresponding body content. This process creates a structured representation of each document, which is essential for the subsequent analysis.

### **2\. Semantic Analysis and Relevance Ranking**

To understand the content semantically, we employ a lightweight yet powerful sentence transformer model, **intfloat/e5-base-v2**. This model was specifically chosen because it offers high accuracy while adhering to the hackathon's constraints (under 1GB and optimized for CPU execution).  
The process for ranking is as follows:

* **Query Embedding:** We first create a single, focused query by combining the user's persona and job\_to-be-done. This query is then converted into a high-dimensional vector (embedding) using the transformer model. This vector numerically represents the semantic meaning of the user's goal.  
* **Content Embedding:** Next, each of the extracted document sections is also converted into an embedding using the same model.  
* **Similarity Scoring:** We then calculate the **cosine similarity** between the query embedding and each of the section embeddings. This provides a quantitative score from \-1 to 1 that indicates how semantically related a section is to the user's task.

### **3\. Output Generation**

Finally, the sections are ranked in descending order based on their cosine similarity scores. The top-ranked sections are selected and formatted into the final JSON output, fulfilling the requirements for both the extracted\_sections and subsection\_analysis fields. This ensures that the most relevant information is prioritized and presented to the user in a clear and structured manner.