from typing import List, Dict
import os
from preprocessing import PDFProcessor
from embedding import EmbeddingEngine

class DocumentRetrieval:
    def __init__(self):
        self.pdf_processor = PDFProcessor()
        self.embedding_engine = EmbeddingEngine()
    
    def process_document_collection(self, pdf_directory: str) -> List[Dict]:
        """Process all PDFs in a directory and extract sections."""
        all_sections = []
        
        for filename in os.listdir(pdf_directory):
            if filename.lower().endswith('.pdf'):
                pdf_path = os.path.join(pdf_directory, filename)
                try:
                    sections = self.pdf_processor.process_document(pdf_path)
                    # Add document filename to each section
                    for section in sections:
                        section['document'] = filename
                    all_sections.extend(sections)
                except Exception as e:
                    print(f"Error processing {filename}: {str(e)}")
                    continue
        
        return all_sections
    
    def retrieve_relevant_sections(self, pdf_directory: str, persona: str, 
                                 job_to_be_done: str, top_k: int = 5) -> List[Dict]:
        """Main retrieval function that processes documents and ranks sections."""
        # Process all documents
        all_sections = self.process_document_collection(pdf_directory)
        
        if not all_sections:
            return []
        
        # Rank sections by relevance
        ranked_sections = self.embedding_engine.rank_sections_by_relevance(
            all_sections, persona, job_to_be_done, top_k
        )
        
        return ranked_sections
    
    def format_extracted_sections(self, ranked_sections: List[Dict]) -> List[Dict]:
        """Format sections for the output JSON structure."""
        extracted_sections = []
        
        for section in ranked_sections:
            extracted_sections.append({
                "document": section['document'],
                "section_title": section['title'],
                "importance_rank": section['importance_rank'],
                "page_number": section['page_number']
            })
        
        return extracted_sections