# Filename: generic_document_analyzer.py
# A single, self-contained and generic script for document analysis.

import json
import os
import re
import time
from datetime import datetime
import fitz  # PyMuPDF
from sentence_transformers import SentenceTransformer, util

# --- Configuration ---
# Set the name of the collection folder you want to process.
COLLECTION_FOLDER_NAME = 'Collection_1'
# --------------------


class PDFSectionExtractor:
    """
    Parses PDF documents by intelligently identifying and extracting distinct sections
    based on formatting cues like titles.
    """

    def _get_dominant_font_info(self, page):
        """Calculates the most common font size and name on a page."""
        styles = {}
        page_dict = page.get_text("dict")
        for block in page_dict.get("blocks", []):
            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    style_key = (round(span["size"]), span["font"])
                    styles[style_key] = styles.get(style_key, 0) + len(span["text"])

        if not styles:
            return 10, "default"  # Fallback values

        dominant_style = max(styles, key=styles.get)
        return dominant_style[0], dominant_style[1]

    def _is_title(self, block, dominant_size, dominant_font):
        """
        Determines if a text block is likely a title based on its styling.
        A title is typically larger, bold, or uses a different font than the body text.
        """
        if not block.get('lines') or len(block['lines']) > 2:
            return False, ""

        line = block['lines'][0]
        if not line.get('spans'):
            return False, ""

        full_title_text = " ".join([s['text'].strip() for s in line['spans']]).strip()
        if not full_title_text or len(full_title_text.split()) > 10:
            return False, ""

        span = line['spans'][0]
        is_larger = span['size'] > dominant_size + 0.5
        is_distinct_style = "bold" in span['font'].lower() and "bold" not in dominant_font.lower()

        if is_larger or is_distinct_style:
            return True, full_title_text

        return False, ""

    def extract_sections(self, pdf_path):
        """Extracts structured sections from a given PDF file."""
        doc = fitz.open(pdf_path)
        sections = []
        current_section = None

        for page_num, page in enumerate(doc, 1):
            dominant_size, dominant_font = self._get_dominant_font_info(page)
            blocks = page.get_text("dict").get("blocks", [])

            for block in blocks:
                is_a_title, title_text = self._is_title(block, dominant_size, dominant_font)

                if is_a_title:
                    if current_section:
                        sections.append(current_section)
                    current_section = {"title": title_text, "content": "", "page_number": page_num}
                elif current_section:
                    block_text = "".join(span['text'] for line in block.get('lines', []) for span in line.get('spans', []))
                    current_section["content"] += block_text + " "
            
            if page_num == len(doc) and current_section and current_section not in sections:
                 sections.append(current_section)

        doc.close()
        for section in sections:
            section['content'] = re.sub(r'\s+', ' ', section['content']).strip()
        return sections


class RelevanceAnalyzer:
    """Analyzes and ranks document sections based on relevance and defined constraints."""
    def _init_(self, model_name='all-MiniLM-L6-v2'):
        self.model = SentenceTransformer(model_name)

    def _is_compliant(self, section, constraints):
        """Checks if a section complies with the job's constraints (e.g., keyword inclusion/exclusion)."""
        content = (section['title'] + ' ' + section['content']).lower()
        
        # Check for keywords to exclude
        for keyword in constraints.get('exclude_keywords', []):
            if re.search(r'\b' + re.escape(keyword.lower()) + r'\b', content):
                return False

        # Check for keywords that must be included
        include_keywords = constraints.get('include_keywords', [])
        if include_keywords:
            if not any(re.search(r'\b' + re.escape(kw.lower()) + r'\b', content) for kw in include_keywords):
                return False
                
        return True

    def rank_sections(self, sections, persona, job_to_be_done):
        """Filters sections based on constraints and ranks them by relevance."""
        if not sections:
            return []
        
        constraints = job_to_be_done.get('constraints', {})
        compliant_sections = [s for s in sections if self._is_compliant(s, constraints)]

        if not compliant_sections:
            return []

        focus_query = f"{persona['role']}: {job_to_be_done['task']}"
        query_embedding = self.model.encode(focus_query, convert_to_tensor=True)
        
        section_texts = [f"{s['title']}. {s['content']}" for s in compliant_sections]
        section_embeddings = self.model.encode(section_texts, convert_to_tensor=True)
        
        cosine_scores = util.cos_sim(query_embedding, section_embeddings)[0]

        for i, section in enumerate(compliant_sections):
            section['score'] = cosine_scores[i].item()
            
        ranked_sections = sorted(compliant_sections, key=lambda x: x['score'], reverse=True)
        
        for rank, section in enumerate(ranked_sections):
            section['importance_rank'] = rank + 1
            
        return ranked_sections

    def analyze_subsection(self, section):
        """Provides the most useful refined text from a section, which is its full content."""
        return section['content'].strip()


def run_pipeline(base_dir, collection_name):
    """Main function to run the entire document processing and analysis pipeline."""
    start_time = time.time()
    input_dir = os.path.join(base_dir, collection_name)
    input_json_path = os.path.join(input_dir, 'challenge1b_input.json')
    pdf_dir = os.path.join(input_dir, 'PDFs')

    print(f"🚀 Starting analysis for: {collection_name}")
    try:
        with open(input_json_path, 'r') as f:
            input_data = json.load(f)
        print("✅ Loaded input data.")
    except FileNotFoundError:
        print(f"❌ Error: Input JSON not found at {input_json_path}")
        return

    section_extractor = PDFSectionExtractor()
    relevance_analyzer = RelevanceAnalyzer()
    print("✅ Initialized processors and analyzers.")

    all_sections = []
    for doc_info in input_data.get('documents', []):
        pdf_path = os.path.join(pdf_dir, doc_info['filename'])
        if os.path.exists(pdf_path):
            print(f"  - Parsing sections from: {doc_info['filename']}")
            extracted = section_extractor.extract_sections(pdf_path)
            for section in extracted:
                section['document'] = doc_info['filename']
            all_sections.extend(extracted)
        else:
            print(f"  - Warning: PDF file not found: {doc_info['filename']}")

    print("\n🔬 Applying constraints and ranking sections by relevance...")
    ranked_sections = relevance_analyzer.rank_sections(
        all_sections,
        input_data['persona'],
        input_data['job_to_be_done']
    )
    top_5_sections = ranked_sections[:5]
    print(f"✅ Ranking complete. Found {len(ranked_sections)} compliant sections.")

    print("✍ Generating final output...")
    subsection_analyses = [
        {"document": s['document'], "refined_text": relevance_analyzer.analyze_subsection(s), "page_number": s['page_number']}
        for s in top_5_sections
    ]
    extracted_sections_output = [
        {"document": s['document'], "section_title": s['title'], "importance_rank": s['importance_rank'], "page_number": s['page_number']}
        for s in top_5_sections
    ]

    output_data = {
        "metadata": {
            "input_documents": [doc['filename'] for doc in input_data.get('documents', [])],
            "persona": input_data.get('persona', {}).get('role', 'N/A'),
            "job_to_be_done": input_data.get('job_to_be_done', {}).get('task', 'N/A'),
            "processing_timestamp": datetime.now().isoformat()
        },
        "extracted_sections": extracted_sections_output,
        "subsection_analysis": subsection_analyses
    }

    output_json_path = os.path.join(input_dir, 'challenge1b_output.json')
    with open(output_json_path, 'w') as f:
        json.dump(output_data, f, indent=4)

    end_time = time.time()
    print(f"\n🎉 Success! Processing complete in {end_time - start_time:.2f} seconds.")
    print(f"Output saved to: {output_json_path}")


if _name_ == "_main_":
    current_script_dir = os.path.dirname(os.path.abspath(_file_))
    run_pipeline(base_dir=current_script_dir, collection_name=COLLECTION_FOLDER_NAME)