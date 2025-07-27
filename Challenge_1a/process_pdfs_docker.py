import os
import json
import re
from pathlib import Path
from collections import defaultdict, Counter
import fitz  # PyMuPDF
import math
from typing import List, Dict, Tuple, Optional

# Docker-optimized version without heavy ML dependencies
# Falls back to pattern-based multilingual detection

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

def extract_title_and_outline_multilingual_docker(text_blocks: List[Dict]) -> Tuple[str, List[Dict]]:
    """Docker-optimized multilingual heading detection without heavy ML dependencies."""
    if not text_blocks:
        return "", []
    
    # Extract title using existing method
    title = extract_title_advanced(text_blocks)
    
    # Enhanced heading detection with multilingual patterns
    headings = []
    
    for block in text_blocks:
        text = block["text"].strip()
        
        # Skip obvious non-headings
        if (text == title or len(text) < 3 or len(text) > 200 or 
            is_page_number(text) or is_header_footer(block, text_blocks)):
            continue
        
        confidence_scores = {}
        
        # 1. Multilingual pattern detection
        is_pattern_heading, pattern_conf, pattern_type = is_multilingual_heading_pattern(text)
        if is_pattern_heading:
            confidence_scores['pattern'] = pattern_conf
        
        # 2. Font-based detection
        font_conf = calculate_font_confidence_simple(block, text_blocks, title)
        if font_conf > 0.3:
            confidence_scores['font'] = font_conf
        
        # 3. Structure-based detection
        structure_conf = calculate_structure_confidence_simple(block, text_blocks)
        if structure_conf > 0.3:
            confidence_scores['structure'] = structure_conf
        
        # Combine confidence scores
        if confidence_scores:
            weights = {'pattern': 0.5, 'font': 0.35, 'structure': 0.15}
            total_confidence = sum(
                confidence_scores.get(method, 0) * weight 
                for method, weight in weights.items()
            )
            
            # Determine heading level
            level = determine_heading_level_simple(text, block, pattern_type)
            
            # Apply threshold
            if total_confidence > 0.45:
                headings.append({
                    "text": clean_heading_text(text),
                    "level": level,
                    "page": block["page"],
                    "confidence": total_confidence,
                    "detection_method": "multilingual_pattern"
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
    
    # Convert to expected format
    outline = []
    for heading in unique_headings:
        outline.append({
            "level": heading["level"],
            "text": heading["text"],
            "page": heading["page"]
        })
    
    return title, outline

def calculate_font_confidence_simple(block: Dict, all_blocks: List[Dict], title: str) -> float:
    """Simplified font confidence calculation."""
    confidence = 0.0
    
    # Font size analysis
    content_blocks = [b for b in all_blocks if b["text"] != title and len(b["text"]) > 2]
    
    if content_blocks:
        sizes = [b["size"] for b in content_blocks]
        avg_size = sum(sizes) / len(sizes)
        size_diff = block["size"] - avg_size
        
        if size_diff > 2:
            confidence += 0.6
        elif size_diff > 1:
            confidence += 0.4
        elif size_diff > 0.5:
            confidence += 0.2
    
    # Bold text bonus
    if block.get("is_bold", False):
        confidence += 0.3
    
    # Text length consideration
    text_len = len(block["text"])
    if 5 <= text_len <= 100:
        confidence += 0.2
    
    return min(1.0, confidence)

def calculate_structure_confidence_simple(block: Dict, all_blocks: List[Dict]) -> float:
    """Simplified structure confidence calculation."""
    confidence = 0.0
    
    # Check for bold text
    if block.get("is_bold", False):
        confidence += 0.4
    
    # Check for shorter lines
    if len(block["text"]) < 100 and len(block["text"].split()) <= 12:
        confidence += 0.3
    
    # Check for centering (simplified)
    page_width = block.get("page_width", 612)
    x_pos = block.get("x_position", 0)
    if abs(x_pos - page_width/4) < 50:  # Roughly centered or indented
        confidence += 0.2
    
    return min(1.0, confidence)

def determine_heading_level_simple(text: str, block: Dict, pattern_type: str) -> str:
    """Improved heading level determination with proper H1/H2/H3 distribution."""
    # Start with base scoring system
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

def extract_title_and_outline(pdf_path):
    """Enhanced extraction with Docker-compatible multilingual support."""
    doc = fitz.open(pdf_path)
    
    try:
        # Check PDF bookmarks first
        pdf_outline = extract_pdf_outline(doc)
        if pdf_outline["outline"] and len(pdf_outline["outline"]) > 3:
            return pdf_outline["title"], pdf_outline["outline"]
        
        # Extract text blocks
        quick_sample_pages = min(len(doc), 3)
        sample_blocks = extract_text_blocks_optimized(doc, quick_sample_pages)
        
        if sample_blocks:
            quick_headings = detect_quick_patterns(sample_blocks)
            if len(quick_headings) >= 2:
                max_pages = min(len(doc), 20)
                text_blocks = extract_text_blocks_optimized(doc, max_pages)
            else:
                max_pages = min(len(doc), 50)
                text_blocks = extract_text_blocks_with_metadata_enhanced(doc, max_pages)
        else:
            return "", []
        
        if not text_blocks:
            return "", []
        
        # Try Docker-optimized multilingual detection first
        try:
            title, outline = extract_title_and_outline_multilingual_docker(text_blocks)
            if outline and len(outline) >= 2:
                print(f"Multilingual detection found {len(outline)} headings")
                return title, outline
        except Exception as e:
            print(f"Warning: Multilingual detection failed, using fallback: {e}")
        
        # Fallback to original method
        title = extract_title_fast(text_blocks) if len(quick_headings) >= 2 else extract_title_advanced(text_blocks)
        outline = extract_outline_fast_enhanced(text_blocks, title) if len(quick_headings) >= 2 else extract_outline_advanced_enhanced(text_blocks, title)
        
        return title, outline
        
    finally:
        doc.close()

# Include all original functions from process_pdfs.py
def extract_pdf_outline(doc):
    """Extract outline from PDF bookmarks/table of contents."""
    title = ""
    outline = []
    
    try:
        # Get PDF metadata title
        metadata = doc.metadata
        if metadata and metadata.get("title"):
            title = metadata["title"].strip()
        
        # Get outline/bookmarks
        toc = doc.get_toc(simple=False)
        if toc:
            for item in toc:
                level = item[0]  # Level (1=H1, 2=H2, etc.)
                text = item[1].strip()  # Title text
                page = item[2]  # Page number
                
                if text and len(text) > 2:
                    # Map level to H1, H2, H3 format
                    level_map = {1: "H1", 2: "H2", 3: "H3"}
                    level_str = level_map.get(min(level, 3), "H3")
                    
                    outline.append({
                        "level": level_str,
                        "text": clean_heading_text(text),
                        "page": page
                    })
    except Exception:
        pass
    
    return {"title": title, "outline": outline}

def extract_text_blocks_optimized(doc, max_pages):
    """Optimized text extraction with limited scope."""
    text_blocks = []
    
    for page_num in range(max_pages):
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
                            if len(text_blocks) > 500:  # Global limit for performance
                                return text_blocks
    
    return text_blocks

# Include other necessary functions...
def extract_text_blocks_with_metadata_enhanced(doc, max_pages):
    """Enhanced text extraction for maximum heading detection."""
    text_blocks = []
    
    for page_num in range(max_pages):
        page = doc[page_num]
        page_dict = page.get_text("dict")
        page_rect = page.rect
        
        for block in page_dict["blocks"]:
            if "lines" in block:
                for line_idx, line in enumerate(block["lines"]):
                    line_text_parts = []
                    line_bbox = line["bbox"]
                    
                    # Collect all spans in the line
                    spans_info = []
                    for span in line["spans"]:
                        text = span["text"].strip()
                        if text:
                            line_text_parts.append(text)
                            spans_info.append(span)
                    
                    if line_text_parts and spans_info:
                        full_line_text = " ".join(line_text_parts).strip()
                        if full_line_text:
                            # Use the first span for primary font info
                            first_span = spans_info[0]
                            
                            # Calculate average font size for the line
                            avg_size = sum(s["size"] for s in spans_info) / len(spans_info)
                            
                            # Check if all spans are bold/italic
                            all_bold = all(bool(s["flags"] & 16) for s in spans_info)
                            all_italic = all(bool(s["flags"] & 2) for s in spans_info)
                            any_bold = any(bool(s["flags"] & 16) for s in spans_info)
                            
                            text_blocks.append({
                                "text": full_line_text,
                                "page": page_num + 1,
                                "font": first_span["font"],
                                "size": avg_size,
                                "flags": first_span["flags"],
                                "bbox": line_bbox,
                                "line_height": line_bbox[3] - line_bbox[1],
                                "x_position": line_bbox[0],
                                "y_position": line_bbox[1],
                                "page_width": page_rect.width,
                                "page_height": page_rect.height,
                                "is_bold": all_bold,
                                "any_bold": any_bold,
                                "is_italic": all_italic,
                                "char_count": len(full_line_text),
                                "word_count": len(full_line_text.split()),
                                "span_count": len(spans_info),
                                "font_consistency": len(set(s["font"] for s in spans_info)) == 1
                            })
    
    return text_blocks

def extract_title_advanced(text_blocks: List[Dict]) -> str:
    """Advanced title extraction using multiple heuristics."""
    if not text_blocks:
        return ""
    
    # Filter to first page
    first_page_blocks = [b for b in text_blocks if b["page"] == 1]
    if not first_page_blocks:
        return ""
    
    # Multiple title detection strategies
    title_candidates = []
    
    # Strategy 1: Largest font size on first page
    max_size = max(b["size"] for b in first_page_blocks)
    size_candidates = [b for b in first_page_blocks 
                      if abs(b["size"] - max_size) < 0.5 and 
                      len(b["text"]) > 3 and 
                      not is_page_number(b["text"]) and
                      not is_header_footer(b, first_page_blocks)]
    
    # Strategy 2: Bold text in upper portion
    upper_third = min(b["y_position"] for b in first_page_blocks) + \
                 (max(b["y_position"] for b in first_page_blocks) - 
                  min(b["y_position"] for b in first_page_blocks)) / 3
    
    bold_candidates = [b for b in first_page_blocks
                      if b.get("is_bold", False) and 
                      b["y_position"] < upper_third and
                      len(b["text"]) > 5 and
                      not is_page_number(b["text"])]
    
    # Strategy 3: Centered text
    page_center = first_page_blocks[0]["page_width"] / 2
    centered_candidates = [b for b in first_page_blocks
                          if abs(b["x_position"] + (b["bbox"][2] - b["bbox"][0])/2 - page_center) < 50 and
                          len(b["text"]) > 5 and
                          not is_page_number(b["text"])]
    
    # Combine and score candidates
    all_candidates = size_candidates + bold_candidates + centered_candidates
    candidate_scores = {}
    
    for candidate in all_candidates:
        text = candidate["text"]
        score = 0
        
        # Size score
        score += candidate["size"] * 2
        
        # Position score (higher for top of page)
        position_score = (1 - candidate["y_position"] / candidate["page_height"]) * 10
        score += position_score
        
        # Bold score
        if candidate.get("is_bold", False):
            score += 5
        
        # Length score (prefer moderate length)
        length_score = min(len(text) / 10, 5)
        score += length_score
        
        # Centering score
        page_center = candidate["page_width"] / 2
        text_center = candidate["x_position"] + (candidate["bbox"][2] - candidate["bbox"][0])/2
        centering_score = max(0, 5 - abs(text_center - page_center) / 20)
        score += centering_score
        
        # Pattern bonus
        if re.match(r'^[A-Z][A-Za-z\s\-–:]+$', text):
            score += 3
        
        candidate_scores[text] = score
    
    if candidate_scores:
        best_title = max(candidate_scores, key=candidate_scores.get)
        return clean_title_text(best_title)
    
    return ""

def extract_title_fast(text_blocks: List[Dict]) -> str:
    """Fast title extraction with streamlined logic."""
    if not text_blocks:
        return ""
    
    first_page_blocks = [b for b in text_blocks if b["page"] == 1][:50]  # Limit scope
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
        return best_title.strip()[:150]  # Limit length
    
    return ""

def extract_outline_fast_enhanced(text_blocks: List[Dict], title: str) -> List[Dict]:
    """Enhanced fast outline extraction combining speed with accuracy."""
    if not text_blocks:
        return []
    
    # Quick font size analysis with caching
    content_blocks = [b for b in text_blocks 
                     if b["text"] != title and 
                     not is_page_number_fast(b["text"]) and 
                     len(b["text"]) > 2]
    
    if not content_blocks:
        return []
    
    # Simplified font hierarchy analysis
    sizes = [b["size"] for b in content_blocks]
    size_counter = Counter(round(s, 1) for s in sizes)
    body_size = size_counter.most_common(1)[0][0] if size_counter else 12.0
    
    # Find heading sizes efficiently
    heading_sizes = [size for size, count in size_counter.items() 
                    if size > body_size + 0.3 or 
                    (size >= body_size - 1.0 and 
                     any(b.get("is_bold", False) for b in content_blocks if round(b["size"], 1) == size))]
    
    # Sort sizes for hierarchy (largest = H1, smallest = H3)
    heading_sizes_sorted = sorted(list(set(heading_sizes)), reverse=True)
    size_to_level = {}
    level_names = ["H1", "H2", "H3"]
    
    for i, size in enumerate(heading_sizes_sorted[:3]):
        size_to_level[size] = level_names[i]
    
    # Fast heading detection with multiple passes
    headings = []
    
    for block in content_blocks:
        text = block["text"].strip()
        
        if (len(text) > 3 and len(text) < 200 and
            block.get("word_count", 1) <= 20):
            
            confidence = 0
            level = "H3"
            size = round(block["size"], 1)
            
            # Font-based detection
            if size in size_to_level:
                confidence += 0.6
                level = size_to_level[size]
            elif size > body_size + 0.5:
                confidence += 0.4
                level = "H2" if size > body_size + 1.5 else "H3"
            
            # Bold detection
            if block.get("is_bold", False):
                confidence += 0.4
                if level == "H3":
                    level = "H2"
            
            # Pattern detection (fast)
            if re.match(r'^\d+\.?\s+[A-Z]', text):
                confidence += 0.5
                level = "H1"
            elif re.match(r'^\d+\.\d+\s+[A-Z]', text):
                confidence += 0.5
                level = "H2"
            elif text.isupper() and len(text.split()) <= 8:
                confidence += 0.4
            
            # Common heading keywords (fast check)
            major_words = ['overview', 'introduction', 'conclusion', 'summary', 'abstract', 'contents']
            if any(word in text.lower() for word in major_words):
                confidence += 0.4
                level = "H1"
            
            if confidence > 0.4:  # Lower threshold for fast mode
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
    
    # Sort by page to maintain chronological order
    unique_headings.sort(key=lambda x: x["page"])
    
    return unique_headings

def detect_quick_patterns(text_blocks: List[Dict]) -> List[Dict]:
    """Ultra-fast pattern detection to determine if we should use fast or comprehensive analysis."""
    quick_headings = []
    
    for block in text_blocks[:50]:  # Only check first 50 blocks for speed
        text = block["text"].strip()
        
        if (len(text) > 3 and len(text) < 100 and 
            not is_page_number_fast(text) and
            block.get("word_count", 1) <= 10):
            
            confidence = 0
            
            # Quick pattern checks (most obvious heading patterns)
            if re.match(r'^\d+\.?\s+[A-Z]', text):  # "1. Introduction"
                confidence = 0.9
            elif re.match(r'^\d+\.\d+\s+[A-Z]', text):  # "2.1 Something"
                confidence = 0.8
            elif text.isupper() and len(text.split()) <= 6:  # All caps
                confidence = 0.7
            elif block.get("is_bold", False) and block.get("size", 12) > 12:  # Bold + larger
                confidence = 0.6
            elif any(word in text.lower() for word in ['overview', 'introduction', 'summary']):
                confidence = 0.7
            
            if confidence > 0.6:
                quick_headings.append({
                    "text": text,
                    "confidence": confidence,
                    "page": block["page"]
                })
    
    return quick_headings

def is_page_number(text):
    """Check if text is likely a page number."""
    text = text.strip()
    if text.isdigit() and len(text) <= 3:
        return True
    if re.match(r'^(page\s*)?\d+$', text.lower()):
        return True
    if re.match(r'^\d+\s*$', text):
        return True
    return False

def is_page_number_fast(text: str) -> bool:
    """Fast page number detection."""
    text = text.strip()
    if len(text) > 10:
        return False
    if text.isdigit() and len(text) <= 3:
        return True
    return bool(re.match(r'^(page\s*)?\d+$', text.lower()))

def is_header_footer(block: Dict, all_blocks: List[Dict]) -> bool:
    """Check if block is likely a header or footer."""
    page_height = block.get("page_height", 1000)
    y_pos = block.get("y_position", 0)
    
    # Check if in header area (top 10% of page)
    if y_pos < page_height * 0.1:
        return True
    
    # Check if in footer area (bottom 10% of page)
    if y_pos > page_height * 0.9:
        return True
    
    return False

def clean_heading_text(text):
    """Clean and normalize heading text."""
    # Remove trailing dots and whitespace
    text = text.strip()
    
    # Don't remove leading numbers for numbered headings - keep them as they appear
    return text

def clean_title_text(text: str) -> str:
    """Clean and normalize title text."""
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text.strip())
    
    # Remove trailing punctuation except for appropriate cases
    text = re.sub(r'[\.]+$', '', text)
    
    return text

def process_pdfs():
    """Process all PDFs in input directory and generate JSON outlines with optimized performance."""
    import time
    start_time = time.time()
    
    # Use local paths for testing, Docker paths for production
    if os.path.exists("/app/sample_dataset"):
        input_dir = Path("/app/sample_dataset/pdfs")
        output_dir = Path("/app/sample_dataset/outputs")
    else:
        input_dir = Path("sample_dataset/pdfs")
        output_dir = Path("sample_dataset/outputs")
    
    # Create output directory if it doesn't exist
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Get all PDF files
    pdf_files = list(input_dir.glob("*.pdf"))
    
    if not pdf_files:
        print("No PDF files found in input directory")
        return
    
    print(f"Found {len(pdf_files)} PDF files to process")
    print("Using Docker-optimized multilingual detection")
    
    successful_count = 0
    total_headings = 0
    
    for pdf_file in pdf_files:
        file_start_time = time.time()
        try:
            print(f"Processing {pdf_file.name}...")
            
            # Extract title and outline with multilingual support
            title, outline = extract_title_and_outline(pdf_file)
            
            # Create output data
            output_data = {
                "title": title,
                "outline": outline
            }
            
            # Create output JSON file with minimal indentation for size optimization
            output_file = output_dir / f"{pdf_file.stem}.json"
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(output_data, f, indent=2, ensure_ascii=False, separators=(',', ':'))
            
            file_time = time.time() - file_start_time
            successful_count += 1
            total_headings += len(outline)
            
            print(f"Completed {pdf_file.name} -> {output_file.name} "
                  f"(Title: '{title[:50]}{'...' if len(title) > 50 else ''}', "
                  f"{len(outline)} headings, {file_time:.2f}s)")
            
        except Exception as e:
            print(f"Error processing {pdf_file.name}: {str(e)}")
            # Create empty output for failed files
            output_data = {
                "title": "",
                "outline": []
            }
            output_file = output_dir / f"{pdf_file.stem}.json"
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(output_data, f, indent=2, separators=(',', ':'))
    
    total_time = time.time() - start_time
    print(f"\nProcessing Summary:")
    print(f"Successfully processed: {successful_count}/{len(pdf_files)} files")
    print(f"Total headings extracted: {total_headings}")
    print(f"Total processing time: {total_time:.2f} seconds")
    print(f"Average time per file: {total_time/len(pdf_files):.2f} seconds")

if __name__ == "__main__":
    print("Starting PDF outline extraction with Docker-optimized multilingual support...")
    process_pdfs()
    print("Completed PDF outline extraction.")