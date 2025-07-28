import fitz
import re
from typing import List, Dict, Tuple

class PDFProcessor:
    def __init__(self):
        self.section_patterns = [
            r'^[A-Z][A-Za-z\s]+:',  # Title with colon
            r'^Chapter \d+',         # Chapter X
            r'^Section \d+',         # Section X
            r'^\d+\.\s+[A-Z]',      # 1. Title
            r'^[A-Z][A-Z\s]+$',     # ALL CAPS titles
        ]
    
    def extract_text_from_pdf(self, pdf_path: str) -> Dict[int, str]:
        """Extract text from PDF, organized by page number."""
        doc = fitz.open(pdf_path)
        text_by_page = {}
        
        for page_num in range(doc.page_count):
            page = doc.load_page(page_num)
            text = page.get_text()
            if text.strip():
                text_by_page[page_num + 1] = text.strip()
        
        doc.close()
        return text_by_page
    
    def identify_sections(self, text_by_page: Dict[int, str]) -> List[Dict]:
        """Identify sections within the document text."""
        sections = []
        
        for page_num, text in text_by_page.items():
            # Split text into paragraphs
            paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
            
            if not paragraphs:
                continue
            
            # Try to identify meaningful sections
            current_section = None
            section_content = []
            
            for paragraph in paragraphs:
                lines = paragraph.split('\n')
                first_line = lines[0].strip()
                
                # Check if this looks like a section header
                is_section_header = False
                
                # Check against patterns
                if any(re.match(pattern, first_line) for pattern in self.section_patterns):
                    is_section_header = True
                
                # Check for short title-like lines
                elif (len(first_line) < 80 and 
                      len(first_line.split()) <= 10 and 
                      first_line[0].isupper() and
                      not first_line.endswith('.') and
                      ':' not in first_line):
                    is_section_header = True
                
                # Check for bullet points or numbered lists as section breaks
                elif re.match(r'^[•·\-\*]\s+[A-Z]', first_line) or re.match(r'^\d+\.\s+[A-Z]', first_line):
                    if len(section_content) > 0:  # Only if we have existing content
                        is_section_header = True
                
                if is_section_header and len(first_line) > 5:  # Minimum title length
                    # Save previous section if it exists
                    if current_section and section_content:
                        content = '\n\n'.join(section_content).strip()
                        if len(content) > 20:  # Minimum content length
                            sections.append({
                                'title': current_section,
                                'content': content,
                                'page_number': page_num
                            })
                    
                    # Start new section
                    current_section = first_line
                    section_content = [paragraph] if len(lines) > 1 else []
                else:
                    section_content.append(paragraph)
            
            # Don't forget the last section
            if current_section and section_content:
                content = '\n\n'.join(section_content).strip()
                if len(content) > 20:
                    sections.append({
                        'title': current_section,
                        'content': content,
                        'page_number': page_num
                    })
        
        # If no clear sections found, create meaningful chunks
        if not sections:
            for page_num, text in text_by_page.items():
                paragraphs = [p.strip() for p in text.split('\n\n') if p.strip() and len(p) > 50]
                
                for i, paragraph in enumerate(paragraphs):
                    lines = paragraph.split('\n')
                    title = lines[0][:60] + "..." if len(lines[0]) > 60 else lines[0]
                    
                    if not title.strip():
                        title = f"Page {page_num} Section {i+1}"
                    
                    sections.append({
                        'title': title.strip(),
                        'content': paragraph,
                        'page_number': page_num
                    })
        
        return sections
    
    def process_document(self, pdf_path: str) -> List[Dict]:
        """Complete processing pipeline for a single PDF."""
        text_by_page = self.extract_text_from_pdf(pdf_path)
        sections = self.identify_sections(text_by_page)
        return sections