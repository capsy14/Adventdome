import os
import json
from pathlib import Path

def process_pdfs():
    # Get input and output directories
    input_dir = Path("/app/input")
    output_dir = Path("/app/output")
    
    # Create output directory if it doesn't exist
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Get all PDF files
    pdf_files = list(input_dir.glob("*.pdf"))
    
    for pdf_file in pdf_files:
        # Create dummy JSON data
        dummy_data = {
            "title": "Understanding AI",
            "outline": [
                {
                    "level": "H1",
                    "text": "Introduction",
                    "page": 1
                },
                {
                    "level": "H2",
                    "text": "What is AI?",
                    "page": 2
                },
                {
                    "level": "H3",
                    "text": "History of AI",
                    "page": 3
                }
            ]
        }
        
        # Create output JSON file
        output_file = output_dir / f"{pdf_file.stem}.json"
        with open(output_file, "w") as f:
            json.dump(dummy_data, f, indent=2)
        
        print(f"Processed {pdf_file.name} -> {output_file.name}")


def extract_title_and_outline(pdf_path):
    """Extract title and outline from PDF with enhanced multilingual support."""
    doc = fitz.open(pdf_path)
    
    try:
        # SPEED HEURISTIC 1: Check PDF bookmarks first (fastest method)
        pdf_outline = extract_pdf_outline(doc)
        if pdf_outline["outline"] and len(pdf_outline["outline"]) > 3:
            return pdf_outline["title"], pdf_outline["outline"]
        
        # SPEED HEURISTIC 2: Minimal font analysis on first few pages only
        quick_sample_pages = min(len(doc), 3)  # Analyze only first 3 pages initially
        sample_blocks = extract_text_blocks_optimized(doc, quick_sample_pages)
        
        if sample_blocks:
            # Quick pattern check - if we find clear headings in first 3 pages, continue with limited analysis
            quick_headings = detect_quick_patterns(sample_blocks)
            if len(quick_headings) >= 2:  # If we found some headings, do limited full analysis
                max_pages = min(len(doc), 20)  # Reduced from 50 to 20 pages
                text_blocks = extract_text_blocks_optimized(doc, max_pages)
            else:
                # SPEED HEURISTIC 3: Fall back to intensive analysis only if needed
                max_pages = min(len(doc), 50)  # Full analysis as fallback
                text_blocks = extract_text_blocks_with_metadata_enhanced(doc, max_pages)
        else:
            return "", []
        
        if not text_blocks:
            return "", []
        
        # NEW: Try multilingual enhanced detection first
        try:
            title, outline = extract_title_and_outline_multilingual(text_blocks)
            if outline and len(outline) >= 2:  # If multilingual detection finds good results
                return title, outline
        except Exception as e:
            print(f"Warning: Multilingual detection failed, falling back to original method: {e}")
        
        # Fallback to original method
        title = extract_title_fast(text_blocks) if len(quick_headings) >= 2 else extract_title_advanced(text_blocks)
        outline = extract_outline_fast_enhanced(text_blocks, title) if len(quick_headings) >= 2 else extract_outline_advanced_enhanced(text_blocks, title)
        
        return title, outline
        
    finally:
        doc.close()


if __name__ == "__main__":
    print("Starting processing pdfs")
    process_pdfs() 
    print("completed processing pdfs")