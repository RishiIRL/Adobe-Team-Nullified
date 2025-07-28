# **PDF Structure Extractor \- Adobe Hackathon Round 1A**

This project is a solution for Round 1A of the Adobe India Hackathon. It provides a Python script that accepts PDF files as input and outputs a structured JSON file containing the document's title and a hierarchical outline of its headings (H1, H2, etc.).

## **Approach Explained**

The solution uses a multi-pass, heuristic-based approach to analyze the visual properties of the text within a PDF, rather than relying on any single attribute like font size. This makes the extraction process robust across a wide variety of document layouts.  
The core logic is implemented in the analyze\_pdf\_structure function, which follows these steps:

1. **Text Extraction and Grouping**: The script first reads the PDF page by page using pdfplumber. It groups individual characters into lines based on their vertical position (y0 coordinate). This accurately reconstructs the text flow.  
2. **Initial Filtering and Cleaning**: Each reconstructed line undergoes several cleaning steps:  
   * **Style Consistency**: Lines with mixed font sizes or styles (e.g., starting bold and transitioning to non-bold) are discarded.  
   * **Character Deduplication**: A custom function (deduplicate\_repeating\_chars) handles cases where characters are overprinted to create a bold effect, which can cause text to be misread.  
3. **Baseline Font Size Determination**: The script calculates the frequency of all font sizes in the document. The most common size is designated as the "body text size," which serves as a crucial baseline for identifying headings.  
4. **Heading Candidate Identification**: A line of text is identified as a potential heading if it meets one of two conditions:  
   * **Size-Based Rule**: Its font size is strictly greater than the body text size.  
   * **Style-Based Rule**: It is a left-aligned, bolded line that starts with a number and is less than 100 characters long. This rule is designed to catch numbered headings that might not be larger than the body text.  
   * Candidates that are likely URLs or do not contain any alphabetical characters are filtered out.  
5. **Title Identification**: The title is identified as the first heading candidate on the first page with the largest font size, located within the top 75% of the page. This prevents large headings at the bottom of the page from being mistaken for the title.  
6. **Advanced Filtering (Post-Title)**: After the title is secured, the remaining candidates are filtered further:  
   * Headings in the header/footer regions are removed.  
   * Headings inside the content area of tables are removed.  
   * Sequences of more than two centered headings are reduced to only the two largest, removing decorative text.  
7. **Multi-Line Heading Merging**: The script merges consecutive heading candidates that are on the same page and are physically close to each other, correctly combining multi-line headings into a single entry.  
8. **Hierarchical Classification**: Finally, the script groups the remaining heading candidates by font size (clustering sizes that are within 1pt of each other). It then assigns levels (H1, H2, etc.) to these clusters, from largest to smallest, creating the final hierarchical outline.

## **Models and Libraries Used**

This solution is lightweight and does not use any pre-trained machine learning models. It relies on the following Python library:

* **pdfplumber**: For robustly extracting text, characters, and their properties (like font size, name, and position) from PDF files.

## **How to Build and Run**

The solution is containerized using Docker and is designed to run according to the "Expected Execution" section of the challenge document.

### **Build the Docker Image**

Navigate to the root directory of the project (where the Dockerfile is located) and run the following command:  
docker build \--platform linux/amd64 \-t mysolutionname:somerandomidentifier .

### **Run the Container**

Place your input PDF files in a local directory named input. Create an empty local directory named output. Then, run the solution using the following command, which mounts the local directories into the container:  
docker run \--rm \-v $(pwd)/input:/app/input \-v $(pwd)/output:/app/output \--network none mysolutionname:somerandomidentifier

The container will automatically process all PDF files in the /app/input directory and generate a corresponding JSON file for each in the /app/output directory.