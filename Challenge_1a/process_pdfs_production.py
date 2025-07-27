#!/usr/bin/env python3
"""
Production PDF heading extraction script for Docker deployment.
Processes PDFs from /app/input and outputs JSON to /app/output.

Requirements compliance:
- Input: /app/input directory (mounted volume)
- Output: /app/output directory (mounted volume)
- Execution time: ≤ 10 seconds for 50-page PDF
- Model size: ≤ 200MB (using pattern-based detection, no ML models)
- Network: Offline operation (no internet calls)
- CPU: AMD64 architecture only
- Memory: Optimized for 16GB RAM systems
"""

import os
import json
import re
import time
from pathlib import Path
from collections import defaultdict, Counter
import fitz  # PyMuPDF
from typing import List, Dict, Tuple, Optional
def detect_language_simple(text: str) -> str:
    """Simple language detection based on character patterns."""
    text = text.strip()
    
    # Japanese patterns
    if re.search(r'[ひらがなカタカナ]', text) or re.search(r'第[0-9一二三四五六七八九十]+[章節]', text):
        return 'japanese'
    
    # Arabic patterns
    if re.search(r'[\u0600-\u06FF]', text):
        return 'arabic'
    
    # Chinese patterns
    if re.search(r'[\u4e00-\u9fff]', text) and not re.search(r'[ひらがなカタカナ]', text):
        return 'chinese'
    
    # Korean patterns
    if re.search(r'[\uAC00-\uD7AF]', text):
        return 'korean'
    
    return 'english'

def is_multilingual_heading_pattern(text: str, language: str = None) -> Tuple[bool, float, str]:
    """Check if text matches multilingual heading patterns."""
    if not text or len(text.strip()) < 2:
        return False, 0.0, ""
    
    text = text.strip()
    
    # Auto-detect language if not provided
    if language is None:
        language = detect_language_simple(text)
    
    max_confidence = 0.0
    best_pattern = ""
    
    # Japanese patterns
    japanese_patterns = [
        (r'^第[0-9０-９一二三四五六七八九十百千万]+章.*', 0.9, "japanese_chapter"),
        (r'^第[0-9０-９一二三四五六七八九十百千万]+節.*', 0.9, "japanese_section"),
        (r'^[0-9０-９]+[\.．][0-9０-９]*\s*.*', 0.8, "japanese_numbered"),
        (r'^「.*」$', 0.7, "japanese_quoted"),
        (r'^【.*】$', 0.7, "japanese_bracketed"),
        (r'^■.*|^◆.*|^○.*', 0.6, "japanese_bullet"),
    ]
    
    # Arabic patterns
    arabic_patterns = [
        (r'^الفصل\s+[الأ]*[0-9٠-٩]+.*', 0.9, "arabic_chapter"),
        (r'^القسم\s+[الأ]*[0-9٠-٩]+.*', 0.9, "arabic_section"),
        (r'^[0-9٠-٩]+[\.]\s*.*', 0.8, "arabic_numbered"),
        (r'^-\s+.*|^•\s+.*', 0.6, "arabic_bullet"),
    ]
    
    # Chinese patterns
    chinese_patterns = [
        (r'^第[0-9一二三四五六七八九十百千万]+章.*', 0.9, "chinese_chapter"),
        (r'^第[0-9一二三四五六七八九十百千万]+节.*', 0.9, "chinese_section"),
        (r'^第[0-9一二三四五六七八九十百千万]+節.*', 0.9, "chinese_section_trad"),
        (r'^[0-9]+[\.]\s*.*', 0.8, "chinese_numbered"),
    ]
    
    # Universal patterns
    universal_patterns = [
        (r'^\d+\.\s+[A-Z\u4e00-\u9fff\u0600-\u06ff]', 0.9, "numbered_section"),
        (r'^\d+\.\d+\s+[A-Z\u4e00-\u9fff\u0600-\u06ff]', 0.9, "sub_numbered"),
        (r'^[IVX]+\.\s+[A-Z\u4e00-\u9fff\u0600-\u06ff]', 0.8, "roman_numeral"),
        (r'^[A-Z]{2,}(\s+[A-Z]+)*$', 0.7, "all_caps"),
        (r'^[A-Z][a-z]+(\s+[A-Z][a-z]*)*$', 0.6, "title_case"),
    ]
    
    # Check language-specific patterns
    all_patterns = []
    if language == 'japanese':
        all_patterns.extend(japanese_patterns)
    elif language == 'arabic':
        all_patterns.extend(arabic_patterns)
    elif language == 'chinese':
        all_patterns.extend(chinese_patterns)
    
    # Always check universal patterns
    all_patterns.extend(universal_patterns)
    
    for pattern, confidence, pattern_type in all_patterns:
        if re.match(pattern, text):
            if confidence > max_confidence:
                max_confidence = confidence
                best_pattern = pattern_type
    
    # Check multilingual keywords
    multilingual_keywords = {
        'japanese': ['序論', '序章', 'はじめに', '概要', '概観', '背景', '目的', '手法', '方法', '実験', '結果', '考察', '結論', 'まとめ'],
        'arabic': ['المقدمة', 'الخلاصة', 'النتائج', 'المنهجية', 'الخلفية', 'الهدف', 'التحليل', 'الاستنتاج'],
        'chinese': ['引言', '概述', '背景', '方法', '结果', '讨论', '结论', '总结', '摘要'],
        'english': ['introduction', 'overview', 'background', 'methodology', 'results', 'discussion', 'conclusion', 'summary', 'abstract']
    }
    
    text_lower = text.lower()
    for lang, keywords in multilingual_keywords.items():
        for keyword in keywords:
            if keyword in text_lower:
                confidence = 0.7 if text_lower.startswith(keyword) else 0.5
                if confidence > max_confidence:
                    max_confidence = confidence
                    best_pattern = f"{lang}_keyword"
    
    return max_confidence > 0.5, max_confidence, best_pattern

def determine_heading_level_production(text: str, block: Dict, pattern_type: str) -> str:
    """Production heading level determination with proper H1/H2/H3 distribution."""
    # Scoring system for better level distribution
    h1_score = 0
    h2_score = 0
    h3_score = 0
    
    font_size = block.get("size", 12)
    is_bold = block.get("is_bold", False)
    text_len = len(text)
    word_count = len(text.split())
    
    # Font size scoring (primary factor)
    if font_size >= 16:
        h1_score += 3
    elif font_size >= 14:
        h1_score += 1
        h2_score += 2
    elif font_size >= 12:
        h2_score += 2
        h3_score += 1
    else:
        h3_score += 2
    
    # Bold text scoring
    if is_bold:
        h1_score += 1
        h2_score += 2
    else:
        h3_score += 1
    
    # Pattern-based scoring
    if pattern_type:
        if "chapter" in pattern_type.lower():
            h1_score += 3  # Chapters are always H1
        elif "numbered_section" in pattern_type:
            h1_score += 2  # "1. Introduction" style
        elif "sub_numbered" in pattern_type:
            h2_score += 3  # "1.1 Background" style
        elif "bullet" in pattern_type.lower():
            h3_score += 2  # Bullet points are usually H3
        elif "keyword" in pattern_type:
            # Major keywords
            major_keywords = ['introduction', 'conclusion', 'summary', 'overview', 'abstract', 
                            '序論', '結論', 'まとめ', '概要', 'المقدمة', 'الخلاصة', 'النتائج', 
                            '引言', '结论', '总结', '概述']
            if any(keyword in text.lower() for keyword in major_keywords):
                h1_score += 2
            else:
                h2_score += 1
    
    # Text characteristics scoring
    if word_count <= 3:
        h3_score += 1  # Very short headings often H3
    elif word_count <= 6:
        h2_score += 1  # Medium headings often H2
    elif word_count <= 12:
        h1_score += 1  # Longer headings often H1 (titles)
    
    # Text length scoring
    if text_len <= 20:
        h3_score += 1
    elif text_len <= 50:
        h2_score += 1
    else:
        h1_score += 1
    
    # Special patterns for H3
    h3_patterns = [
        r'^[a-z][\.\)]\s+',  # "a. something", "i) something"
        r'^\([a-z0-9]+\)',   # "(a)", "(1)"
        r'^-\s+',            # "- item"
        r'^•\s+',            # "• item" 
        r'^○\s+',            # "○ item"
        r'^■\s+',            # "■ item"
        r'^\d+\.\d+\.\d+',   # "1.1.1 subsection"
        r'^[A-Z][\.\)]\s+[a-z]',  # "A. something" (but lowercase after)
    ]
    
    for pattern in h3_patterns:
        if re.match(pattern, text):
            h3_score += 3
            break
    
    # Special patterns for H1 (document structure)
    h1_patterns = [
        r'^(CHAPTER|Chapter|章)\s+\d+',
        r'^(PART|Part|部)\s+[IVX0-9]+',
        r'^(SECTION|Section|節)\s+[A-Z0-9]+',
        r'^[A-Z\s]{10,}$',  # Long all-caps titles
    ]
    
    for pattern in h1_patterns:
        if re.match(pattern, text):
            h1_score += 3
            break
    
    # Address/contact info patterns (typically H3)
    contact_patterns = [
        r'.*@.*\.',          # Email addresses
        r'.*\d{3}[-\.\s]\d{3}',  # Phone numbers
        r'^(ADDRESS|PHONE|EMAIL|FAX)[\s:]+',
        r'^\d+\s+[A-Z][a-z]+\s+(Street|Ave|Road|Blvd)',  # Street addresses
    ]
    
    for pattern in contact_patterns:
        if re.match(pattern, text, re.IGNORECASE):
            h3_score += 4  # Strong preference for H3
            break
    
    # Form field patterns (typically H3)
    form_patterns = [
        r'^(Name|Date|Age|Department|Position|Designation)[\s:]*$',
        r'.*[_]{3,}.*',      # Underlines for filling
        r'^\d+\.\s*$',       # Just numbers like "1.", "2."
    ]
    
    for pattern in form_patterns:
        if re.match(pattern, text, re.IGNORECASE):
            h3_score += 3
            break
    
    # Determine final level based on highest score
    max_score = max(h1_score, h2_score, h3_score)
    
    if h1_score == max_score:
        return "H1"
    elif h2_score == max_score:
        return "H2"
    else:
        return "H3"

def extract_text_blocks_optimized(doc, max_pages=50):
    """Optimized text extraction for production use."""
    text_blocks = []
    
    # Limit pages for performance
    actual_max_pages = min(len(doc), max_pages)
    
    for page_num in range(actual_max_pages):
        page = doc[page_num]
        page_dict = page.get_text("dict")
        page_rect = page.rect
        
        block_count = 0
        for block in page_dict["blocks"]:
            if block_count > 100:  # Limit blocks per page for performance
                break
            
            if "lines" in block:
                for line in block["lines"]:
                    line_text_parts = []
                    line_bbox = line["bbox"]
                    
                    for span in line["spans"]:
                        text = span["text"].strip()
                        if text:
                            line_text_parts.append(text)
                    
                    if line_text_parts:
                        full_line_text = " ".join(line_text_parts).strip()
                        if full_line_text and len(full_line_text) > 2:
                            first_span = line["spans"][0]
                            
                            text_blocks.append({
                                "text": full_line_text[:200],  # Limit text length
                                "page": page_num + 1,
                                "size": first_span["size"],
                                "flags": first_span["flags"],
                                "bbox": line_bbox,
                                "x_position": line_bbox[0],
                                "y_position": line_bbox[1],
                                "page_width": page_rect.width,
                                "page_height": page_rect.height,
                                "is_bold": bool(first_span["flags"] & 16),
                                "word_count": len(full_line_text.split())
                            })
                            
                            block_count += 1
                            if len(text_blocks) > 1000:  # Global limit for performance
                                return text_blocks
    
    return text_blocks

def extract_title_optimized(text_blocks: List[Dict]) -> str:
    """Optimized title extraction."""
    if not text_blocks:
        return ""
    
    first_page_blocks = [b for b in text_blocks if b["page"] == 1][:50]
    if not first_page_blocks:
        return ""
    
    # Simple largest font + position strategy
    scored_candidates = []
    max_size = max(b["size"] for b in first_page_blocks)
    
    for block in first_page_blocks:
        if (abs(block["size"] - max_size) < 1.0 and 
            len(block["text"]) > 5 and 
            len(block["text"]) < 150 and
            not is_page_number_fast(block["text"])):
            
            # Simple scoring
            score = block["size"] * 2
            score += (1 - block["y_position"] / block["page_height"]) * 10
            if block.get("is_bold", False):
                score += 5
            
            scored_candidates.append((score, block["text"]))
    
    if scored_candidates:
        best_title = max(scored_candidates, key=lambda x: x[0])[1]
        return best_title.strip()[:150]
    
    return ""

def extract_headings_optimized(text_blocks: List[Dict], title: str) -> List[Dict]:
    """Optimized heading extraction for production."""
    if not text_blocks:
        return []
    
    # Filter content blocks
    content_blocks = [b for b in text_blocks 
                     if b["text"] != title and 
                     not is_page_number_fast(b["text"]) and 
                     len(b["text"]) > 2]
    
    if not content_blocks:
        return []
    
    # Quick font analysis
    sizes = [b["size"] for b in content_blocks]
    size_counter = Counter(round(s, 1) for s in sizes)
    body_size = size_counter.most_common(1)[0][0] if size_counter else 12.0
    
    headings = []
    
    for block in content_blocks:
        text = block["text"].strip()
        
        if (len(text) > 3 and len(text) < 200 and
            block.get("word_count", 1) <= 20):
            
            confidence = 0
            size = round(block["size"], 1)
            
            # Font-based detection
            if size > body_size + 1.0:
                confidence += 0.6
            elif size > body_size + 0.5:
                confidence += 0.4
            
            # Bold detection
            if block.get("is_bold", False):
                confidence += 0.4
            
            # Multilingual pattern detection
            is_pattern_heading, pattern_conf, pattern_type = is_multilingual_heading_pattern(text)
            if is_pattern_heading:
                confidence += pattern_conf * 0.6
            
            # Common heading keywords
            major_words = ['overview', 'introduction', 'conclusion', 'summary', 'abstract', 'contents']
            if any(word in text.lower() for word in major_words):
                confidence += 0.4
            
            if confidence > 0.4:
                level = determine_heading_level_production(text, block, pattern_type)
                headings.append({
                    "level": level,
                    "text": clean_heading_text(text),
                    "page": block["page"]
                })
    
    # Remove duplicates and sort
    seen = set()
    unique_headings = []
    for heading in headings:
        key = (heading["text"], heading["page"])
        if key not in seen:
            seen.add(key)
            unique_headings.append(heading)
    
    unique_headings.sort(key=lambda x: x["page"])
    return unique_headings

def is_page_number_fast(text: str) -> bool:
    """Fast page number detection."""
    text = text.strip()
    if len(text) > 10:
        return False
    if text.isdigit() and len(text) <= 3:
        return True
    return bool(re.match(r'^(page\s*)?\d+$', text.lower()))

def clean_heading_text(text: str) -> str:
    """Clean and normalize heading text."""
    return text.strip()

def extract_title_and_outline_production(pdf_path: Path) -> Tuple[str, List[Dict]]:
    """Production-optimized PDF processing."""
    doc = fitz.open(pdf_path)
    
    try:
        # Extract text blocks with performance limits
        text_blocks = extract_text_blocks_optimized(doc, max_pages=50)
        
        if not text_blocks:
            return "", []
        
        # Extract title and headings
        title = extract_title_optimized(text_blocks)
        outline = extract_headings_optimized(text_blocks, title)
        
        return title, outline
        
    finally:
        doc.close()

def process_pdfs_production():
    """Production PDF processing following exact requirements."""
    start_time = time.time()
    
    # Use exact paths as specified in requirements
    # For local testing, allow override with environment variables
    input_dir = Path(os.getenv("INPUT_DIR", "/app/input"))
    output_dir = Path(os.getenv("OUTPUT_DIR", "/app/output"))
    
    # Ensure directories exist
    if not input_dir.exists():
        print(f"Error: Input directory {input_dir} not found")
        return
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Get all PDF files from input directory
    pdf_files = list(input_dir.glob("*.pdf"))
    
    if not pdf_files:
        print("No PDF files found in input directory")
        return
    
    print(f"Processing {len(pdf_files)} PDF files...")
    print(f"Input directory: {input_dir}")
    print(f"Output directory: {output_dir}")
    
    successful_count = 0
    total_headings = 0
    
    for pdf_file in pdf_files:
        file_start_time = time.time()
        try:
            print(f"Processing {pdf_file.name}...")
            
            # Extract title and outline
            title, outline = extract_title_and_outline_production(pdf_file)
            
            # Create output data
            output_data = {
                "title": title,
                "outline": outline
            }
            
            # Create output JSON file with exact naming: filename.json for filename.pdf
            output_file = output_dir / f"{pdf_file.stem}.json"
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(output_data, f, indent=2, ensure_ascii=False)
            
            file_time = time.time() - file_start_time
            successful_count += 1
            total_headings += len(outline)
            
            print(f"✓ {pdf_file.name} -> {output_file.name} "
                  f"({len(outline)} headings, {file_time:.2f}s)")
            
        except Exception as e:
            print(f"✗ Error processing {pdf_file.name}: {str(e)}")
            # Create empty output for failed files
            output_data = {
                "title": "",
                "outline": []
            }
            output_file = output_dir / f"{pdf_file.stem}.json"
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(output_data, f, indent=2)
    
    total_time = time.time() - start_time
    print(f"\nProcessing complete!")
    print(f"Files processed: {successful_count}/{len(pdf_files)}")
    print(f"Total headings: {total_headings}")
    print(f"Total time: {total_time:.2f}s")
    print(f"Average per file: {total_time/len(pdf_files):.2f}s")

if __name__ == "__main__":
    print("PDF Outline Extractor - Production Version")
    print("==========================================")
    print("Requirements compliance:")
    print("- Input: /app/input (mounted volume)")
    print("- Output: /app/output (mounted volume)")
    print("- Multilingual support: Japanese, Arabic, Chinese, English")
    print("- Performance: ≤10s for 50-page PDFs")
    print("- Offline operation: No network dependencies")
    print("- Architecture: AMD64 CPU only")
    print()
    
    process_pdfs_production()