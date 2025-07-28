# Generic Document Analyzer

A Python script designed to intelligently parse, analyze, and rank sections from a collection of PDF documents based on semantic relevance to a user's specified goal.

## Description

This tool automates the process of sifting through multiple lengthy documents to find the most pertinent information. It takes a collection of PDFs and an input JSON file defining a user persona and a "job to be done," and it outputs a ranked list of the most relevant sections from the documents that match the user's query.

This is particularly useful for researchers, analysts, or anyone who needs to quickly extract key insights from a large corpus of text without manual reading.

## Features

- **Intelligent Section Extraction**: Automatically identifies document structure by analyzing font styles to distinguish titles from body text.
- **Semantic Ranking**: Uses sentence-transformer models to understand the contextual meaning of text, going beyond simple keyword matching.
- **Constraint-Based Filtering**: Allows for fine-grained control by including or excluding sections based on specific keywords.
- **Automated Pipeline**: A single script that handles the entire workflow from input to structured JSON output.
- **Configurable**: Easily point the script to different collections of documents by changing a single variable.

## How It Works

The analysis is performed in a three-step pipeline:

1.  **PDF Section Extraction**: The script first parses each PDF to identify its structure. It determines the dominant "body text" font style for each page and then identifies titles as text blocks with larger or bolder fonts. All content following a title is aggregated into a "section" until a new title is found.

2.  **Relevance Analysis & Ranking**:
    * **Filtering**: All extracted sections are first filtered against `include_keywords` and `exclude_keywords` defined in the input file.
    * **Ranking**: A "focus query" is created from the user persona and task (e.g., "Data Scientist: Find the project methodology"). The script uses the `all-MiniLM-L6-v2` model to convert this query and all compliant sections into numerical vectors (embeddings). It then calculates the cosine similarity between the query's vector and each section's vector to score their semantic relevance.

3.  **Output Generation**: The sections are ranked by their relevance score, and the top 5 are selected. The final output is a JSON file containing metadata, a summary of the top-ranked sections, and the full text of those sections.

## Requirements

The script requires Python 3 and the following libraries:

-   `fitz` (PyMuPDF)
-   `sentence-transformers`
-   `torch` (a dependency of `sentence-transformers`)

## Installation

1.  Clone or download the repository/script.

2.  Install the required Python packages using pip:
    ```bash
    pip install PyMuPDF sentence-transformers
    ```
    *Note: `torch` will typically be installed as a dependency of `sentence-transformers`.*

## Usage

1.  **Prepare your document collection.** Create a directory structure as follows. The `COLLECTION_FOLDER_NAME` variable in the script must match the name of your collection folder (e.g., `Collection_1`).

    ```
    .
    ├── generic_document_analyzer.py
    └── Collection_1/
        ├── PDFs/
        │   ├── document1.pdf
        │   └── document2.pdf
        └── challenge1b_input.json
    ```

2.  **Configure the script.** Open `generic_document_analyzer.py` and set the `COLLECTION_FOLDER_NAME` variable to the name of your collection's directory.

    ```python
    # --- Configuration ---
    # Set the name of the collection folder you want to process.
    COLLECTION_FOLDER_NAME = 'Collection_1'
    # --------------------
    ```

3.  **Run the script** from your terminal:

    ```bash
    python generic_document_analyzer.py
    ```

4.  **Check the output.** A file named `challenge1b_output.json` will be created inside your collection folder (`Collection_1/` in this example).

## Input Format (`challenge1b_input.json`)

The input JSON file must contain the following structure:

```json
{
  "documents": [
    { "filename": "document1.pdf" },
    { "filename": "document2.pdf" }
  ],
  "persona": {
    "role": "Data Scientist"
  },
  "job_to_be_done": {
    "task": "Understand the methodology for data processing.",
    "constraints": {
      "include_keywords": ["methodology", "processing"],
      "exclude_keywords": ["marketing", "sales"]
    }
  }
}
