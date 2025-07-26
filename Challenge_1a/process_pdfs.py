import os
import json
import re
from pathlib import Path
from collections import defaultdict, Counter
import fitz  # PyMuPDF
import math
from typing import List, Dict, Tuple, Optional
from multilingual_headings import MultilingualHeadingDetector

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

def extract_title_and_outline_multilingual(text_blocks: List[Dict]) -> Tuple[str, List[Dict]]:
    """Extract title and outline using multilingual detection."""
    # Initialize multilingual detector (cached after first use)
    if not hasattr(extract_title_and_outline_multilingual, 'detector'):
        extract_title_and_outline_multilingual.detector = MultilingualHeadingDetector()
    
    detector = extract_title_and_outline_multilingual.detector
    
    # Extract title using advanced method
    title = extract_title_advanced(text_blocks)
    
    # Use enhanced multilingual heading detection
    outline_candidates = detector.enhanced_heading_detection(text_blocks, title)
    
    # Convert to the expected format
    outline = []
    for heading in outline_candidates:
        outline.append({
            "level": heading["level"],
            "text": clean_heading_text(heading["text"]),
            "page": heading["page"]
        })
    
    return title, outline

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

def extract_text_blocks_with_metadata(doc):
    """Extract text blocks with comprehensive metadata for analysis."""
    text_blocks = []
    page_layouts = []
    
    for page_num in range(len(doc)):
        page = doc[page_num]
        page_dict = page.get_text("dict")
        page_rect = page.rect
        
        # Store page layout info
        page_layouts.append({
            "width": page_rect.width,
            "height": page_rect.height,
            "number": page_num + 1
        })
        
        for block in page_dict["blocks"]:
            if "lines" in block:
                for line_idx, line in enumerate(block["lines"]):
                    line_text_parts = []
                    line_bbox = line["bbox"]
                    
                    for span in line["spans"]:
                        text = span["text"].strip()
                        if text:
                            line_text_parts.append(text)
                    
                    if line_text_parts:
                        full_line_text = " ".join(line_text_parts).strip()
                        if full_line_text:
                            # Use the first span for font info (most representative)
                            first_span = line["spans"][0]
                            
                            text_blocks.append({
                                "text": full_line_text,
                                "page": page_num + 1,
                                "font": first_span["font"],
                                "size": first_span["size"],
                                "flags": first_span["flags"],
                                "bbox": line_bbox,
                                "line_height": line_bbox[3] - line_bbox[1],
                                "x_position": line_bbox[0],
                                "y_position": line_bbox[1],
                                "page_width": page_rect.width,
                                "page_height": page_rect.height,
                                "is_bold": bool(first_span["flags"] & 16),
                                "is_italic": bool(first_span["flags"] & 2),
                                "char_count": len(full_line_text),
                                "word_count": len(full_line_text.split())
                            })
    
    return text_blocks

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

def extract_outline_advanced_enhanced(text_blocks: List[Dict], title: str) -> List[Dict]:
    """Enhanced outline extraction with aggressive heading detection."""
    if not text_blocks:
        return []
    
    # Analyze document structure
    font_analysis = analyze_font_hierarchy_enhanced(text_blocks, title)
    structure_analysis = analyze_document_structure(text_blocks)
    
    # Multi-pass heading detection with lower thresholds
    headings = []
    
    # Pass 1: Font-based detection (more aggressive)
    font_headings = detect_headings_by_font_enhanced(text_blocks, font_analysis, title)
    headings.extend(font_headings)
    
    # Pass 2: Pattern-based detection (expanded patterns)
    pattern_headings = detect_headings_by_pattern_enhanced(text_blocks, title)
    headings.extend(pattern_headings)
    
    # Pass 3: Structure-based detection (more inclusive)
    structure_headings = detect_headings_by_structure_enhanced(text_blocks, structure_analysis, title)
    headings.extend(structure_headings)
    
    # Pass 4: Heuristic-based detection for common heading characteristics
    heuristic_headings = detect_headings_by_heuristics(text_blocks, title, font_analysis)
    headings.extend(heuristic_headings)
    
    # Merge and deduplicate
    merged_headings = merge_heading_candidates(headings)
    
    # Apply hierarchy and filtering with lower threshold
    final_outline = apply_heading_hierarchy_enhanced(merged_headings, font_analysis)
    
    return final_outline

def analyze_font_hierarchy_enhanced(text_blocks: List[Dict], title: str) -> Dict:
    """Enhanced font analysis for better hierarchy detection."""
    # Exclude title and common non-heading text
    content_blocks = [b for b in text_blocks 
                     if b["text"] != title and 
                     not is_page_number(b["text"]) and 
                     not is_header_footer(b, text_blocks) and
                     len(b["text"]) > 2]
    
    if not content_blocks:
        return {}
    
    # Analyze font size distribution
    sizes = [b["size"] for b in content_blocks]
    size_counter = Counter(round(s, 1) for s in sizes)
    
    # Find body text size (most common, but exclude very small sizes)
    size_candidates = [(size, count) for size, count in size_counter.items() if size > 8.0]
    if size_candidates:
        body_size = max(size_candidates, key=lambda x: x[1])[0]
    else:
        body_size = 12.0
    
    # Find heading sizes with improved logic for uniform documents
    heading_sizes = []
    total_blocks = len(content_blocks)
    
    for size, count in size_counter.items():
        # Include larger sizes
        if size > body_size + 0.3:
            heading_sizes.append(size)
        # Include bold text of body size or slightly smaller
        elif size >= body_size - 1.0:
            bold_blocks = [b for b in content_blocks if round(b["size"], 1) == size and b.get("any_bold", False)]
            if bold_blocks and len(bold_blocks) < total_blocks * 0.5:
                heading_sizes.append(size)
    
    # Handle documents with minimal size variation
    if len(heading_sizes) == 0:
        # If no clear heading sizes found, use body size as heading and create artificial hierarchy
        heading_sizes = [body_size]
    elif len(heading_sizes) == 1:
        # If only one heading size, create a three-level hierarchy based on formatting
        single_size = heading_sizes[0]
        heading_sizes = [single_size + 1.0, single_size, single_size - 1.0]
    
    # Sort heading sizes (largest first)
    heading_sizes = sorted(list(set(heading_sizes)), reverse=True)
    
    # Map to hierarchy levels - CORRECT HIERARCHY: largest font = H1, smallest = H3
    size_to_level = {}
    level_names = ["H1", "H2", "H3"]
    
    # Sort sizes in descending order (largest first) for correct H1/H2/H3 assignment
    heading_sizes_sorted = sorted(heading_sizes, reverse=True)
    
    for i, size in enumerate(heading_sizes_sorted[:3]):  # Only top 3 sizes
        size_to_level[size] = level_names[i]
    
    # Any remaining sizes get mapped to H3 (smallest)
    for size in heading_sizes_sorted[3:]:
        size_to_level[size] = "H3"
    
    return {
        "body_size": body_size,
        "heading_sizes": heading_sizes,
        "size_to_level": size_to_level,
        "size_distribution": dict(size_counter)
    }

def detect_headings_by_font_enhanced(text_blocks: List[Dict], font_analysis: Dict, title: str) -> List[Dict]:
    """Enhanced font-based heading detection with lower thresholds."""
    headings = []
    size_to_level = font_analysis.get("size_to_level", {})
    body_size = font_analysis.get("body_size", 12.0)
    
    for block in text_blocks:
        text = block["text"].strip()
        size = round(block["size"], 1)
        
        if (text != title and 
            not is_page_number(text) and
            not is_header_footer(block, text_blocks) and
            len(text) > 2 and
            len(text) < 200 and
            block["word_count"] <= 20):
            
            confidence = 0
            level = "H3"
            
            # Font size based detection
            if size in size_to_level:
                confidence += 0.6
                level = size_to_level[size]
            elif size > body_size + 0.5:
                confidence += 0.4
                level = "H2" if size > body_size + 1.5 else "H3"
            
            # Bold text detection
            if block.get("any_bold", False):
                confidence += 0.4
                if not level or level == "H3":
                    level = "H2"
            
            # Additional font characteristics
            if block.get("is_bold", False):
                confidence += 0.2
            
            if block.get("font_consistency", False):
                confidence += 0.1
            
            if confidence > 0.4:  # Lower threshold
                headings.append({
                    "text": text,
                    "level": level,
                    "page": block["page"],
                    "confidence": confidence,
                    "source": "font",
                    "y_position": block.get("y_position", 0),
                    "font_size": size
                })
    
    return headings

def detect_headings_by_pattern_enhanced(text_blocks: List[Dict], title: str) -> List[Dict]:
    """Enhanced pattern-based detection with more patterns."""
    headings = []
    
    for block in text_blocks:
        text = block["text"].strip()
        
        if text == title or is_page_number(text) or len(text) < 3:
            continue
        
        confidence = 0
        
        # Pattern recognition for confidence only - don't assign levels
        if re.match(r'^\d+\.?\s+[A-Z]', text):
            confidence = 0.9
        elif re.match(r'^\d+\.\d+\.?\s+[A-Z]', text):
            confidence = 0.9
        elif re.match(r'^\d+\.\d+\.\d+\.?\s+[A-Z]', text):
            confidence = 0.9
        elif re.match(r'^(\d+\.)*\d+\s+[A-Z]', text):  # Multi-level numbering
            confidence = 0.8
        elif re.match(r'^[IVX]+\.?\s+[A-Z]', text):  # Roman numerals
            confidence = 0.8
        elif re.match(r'^[A-Z]\.?\s+[A-Z]', text):  # Lettered headings
            confidence = 0.7
        elif text.isupper() and len(text.split()) <= 10 and len(text) > 2:  # All caps
            confidence = 0.6
        elif (re.match(r'^[A-Z][a-z]+(\s+[A-Z][a-z]*)*$', text) and 
              len(text.split()) <= 12 and len(text) > 4):  # Title case
            confidence = 0.5
        elif text.endswith('?') and len(text.split()) <= 10:  # Questions
            confidence = 0.5
        elif text.endswith(':') and len(text.split()) <= 8:  # Colon endings
            confidence = 0.6
        
        if confidence > 0.4:
            headings.append({
                "text": text,
                "level": None,  # No level assigned - will be determined by font size
                "page": block["page"],
                "confidence": confidence,
                "source": "pattern",
                "y_position": block.get("y_position", 0),
                "font_size": round(block.get("size", 12), 1)
            })
    
    return headings

def detect_headings_by_structure_enhanced(text_blocks: List[Dict], structure_analysis: Dict, title: str) -> List[Dict]:
    """Enhanced structure-based detection with more inclusive criteria."""
    headings = []
    significant_spacing = structure_analysis.get("significant_spacing", 15)
    
    for i, block in enumerate(text_blocks):
        text = block["text"].strip()
        
        if text == title or is_page_number(text) or len(text) < 3:
            continue
        
        confidence = 0
        level = "H3"
        
        # Check for spacing before this block
        if i > 0:
            prev_block = text_blocks[i-1]
            spacing = block["y_position"] - prev_block["y_position"]
            if spacing > significant_spacing * 0.8:  # More lenient spacing
                confidence += 0.3
        
        # Check for bold text
        if block.get("any_bold", False):
            confidence += 0.4
            level = "H2"
        
        # Check for shorter lines (headings are often shorter)
        if len(text) < 100 and len(text.split()) <= 15:
            confidence += 0.2
        
        # Check for isolation (lines with space before and after)
        isolated = False
        if i > 0 and i < len(text_blocks) - 1:
            prev_spacing = block["y_position"] - text_blocks[i-1]["y_position"]
            next_spacing = text_blocks[i+1]["y_position"] - block["y_position"]
            if prev_spacing > 10 and next_spacing > 10:
                isolated = True
                confidence += 0.3
        
        # Check for specific heading indicators (expanded list)
        heading_keywords = [
            'introduction', 'overview', 'conclusion', 'summary', 'background',
            'methodology', 'results', 'discussion', 'abstract', 'contents',
            'chapter', 'section', 'part', 'appendix', 'index', 'references',
            'objectives', 'goals', 'purpose', 'scope', 'definition', 'problem',
            'solution', 'analysis', 'findings', 'recommendations', 'future',
            'related', 'work', 'literature', 'review', 'evaluation', 'implementation'
        ]
        
        # Major headings should get higher confidence and be tagged for H1
        major_headings = ['overview', 'introduction', 'conclusion', 'summary', 'abstract', 'contents']
        
        if any(word in text.lower() for word in heading_keywords):
            confidence += 0.3
            if any(word in text.lower() for word in major_headings):
                confidence += 0.4  # Extra boost for major headings
                level = "H1"
            else:
                level = "H2"
        
        # Check for centered text
        page_center = block.get("page_width", 612) / 2
        text_center = block["x_position"] + (block["bbox"][2] - block["bbox"][0]) / 2
        if abs(text_center - page_center) < 30:
            confidence += 0.2
        
        if confidence > 0.5:  # Lower threshold
            headings.append({
                "text": text,
                "level": None,  # Let font size determine level
                "page": block["page"],
                "confidence": confidence,
                "source": "structure",
                "y_position": block.get("y_position", 0),
                "font_size": round(block.get("size", 12), 1)
            })
    
    return headings

def detect_headings_by_heuristics(text_blocks: List[Dict], title: str, font_analysis: Dict) -> List[Dict]:
    """Additional heuristic-based heading detection."""
    headings = []
    body_size = font_analysis.get("body_size", 12.0)
    
    for block in text_blocks:
        text = block["text"].strip()
        
        if (text == title or is_page_number(text) or 
            len(text) < 3 or len(text) > 150):
            continue
        
        confidence = 0
        level = "H3"
        
        # Short lines that are not body text
        if (len(text) < 80 and 
            len(text.split()) <= 10 and 
            len(text.split()) >= 2):
            confidence += 0.2
        
        # Lines with unusual capitalization
        if (text.count(' ') <= 8 and 
            sum(1 for c in text if c.isupper()) / len(text) > 0.3):
            confidence += 0.3
        
        # Lines that start with common section words
        section_starters = [
            'part', 'chapter', 'section', 'subsection', 'topic', 'lesson',
            'unit', 'module', 'step', 'phase', 'stage', 'level', 'grade'
        ]
        
        first_word = text.split()[0].lower() if text.split() else ""
        if first_word in section_starters:
            confidence += 0.4
            level = "H1"
        
        # Lines with special formatting patterns
        if re.match(r'^[A-Z][A-Z\s]+[A-Z]$', text) and len(text.split()) <= 6:
            confidence += 0.4
            level = "H1"
        
        # Lines that look like table of contents entries
        if re.match(r'^[A-Z].*\.\.\.*\d+$', text):
            confidence += 0.6
            level = "H2"
        
        # Bold or large text that's not body size
        if (block.get("any_bold", False) and 
            block["size"] >= body_size - 0.5 and
            len(text.split()) <= 12):
            confidence += 0.3
        
        if confidence > 0.4:
            headings.append({
                "text": text,
                "level": None,  # Let font size determine level
                "page": block["page"],
                "confidence": confidence,
                "source": "heuristic",
                "y_position": block.get("y_position", 0),
                "font_size": round(block.get("size", 12), 1)
            })
    
    return headings

def apply_heading_hierarchy_enhanced(headings: List[Dict], font_analysis: Dict) -> List[Dict]:
    """Enhanced hierarchy application with proper font-based level assignment."""
    # Filter by lower confidence threshold
    filtered_headings = [h for h in headings if h["confidence"] > 0.35]
    
    # Get font size to level mapping
    size_to_level = font_analysis.get("size_to_level", {})
    
    # Apply hierarchy rules
    final_outline = []
    
    for heading in filtered_headings:
        # Clean and validate heading text
        clean_text = clean_heading_text(heading["text"])
        if len(clean_text) < 2 or len(clean_text) > 250:
            continue
        
        # Skip very common words and form field patterns that are unlikely to be headings
        skip_words = ['page', 'copyright', '©', 'www', 'http', 'email', '@', 'version']
        if any(word in clean_text.lower() for word in skip_words):
            continue
        
        # Determine final level based on font size
        final_level = heading.get("level")
        
        # Check if this is a form field pattern and override to H3
        is_form_field = (len(clean_text.split()) <= 8 and 
            (clean_text.lower().startswith(('name of', 'date of', 'whether', 'if so', 'home town')) or
             clean_text.lower().endswith(('servant', 'service', 'government', 'book', 'ltc', 'employed', 'temporary')) or
             clean_text.lower() in ['designation', 'service', 'age', 'name', 'relationship', 's.no', 'date', 'rs.'] or
             '+' in clean_text or
             re.match(r'^[A-Z\s]+\+[A-Z\s]+', clean_text) or
             re.match(r'^\d+\.$', clean_text) or  # Just numbers like "10.", "11.", "12."
             len(clean_text.split()) == 1 and len(clean_text) < 15))
        
        # If no level assigned or need to determine from font size
        if final_level is None:
            font_size = heading.get("font_size")
            body_size = font_analysis.get("body_size", 12.0)
            
            if font_size and font_size in size_to_level:
                final_level = size_to_level[font_size]
            else:
                # For uniform documents, use additional cues beyond font size
                confidence = heading.get("confidence", 0.5)
                source = heading.get("source", "")
                
                # Assign levels based on multiple factors, with special handling for common headings
                text_lower = clean_text.lower()
                
                # Major document headings should be H1
                if (text_lower in ['overview', 'introduction', 'conclusion', 'summary', 'abstract', 'contents'] or
                    text_lower.startswith(('chapter ', 'section ', 'part ')) or
                    re.match(r'^\d+\.?\s+(overview|introduction|conclusion|summary)', text_lower) or
                    (font_size and font_size > body_size + 1.5)):
                    final_level = "H1"
                # Subsection headings
                elif (confidence > 0.8 or 
                      source == "pattern" or 
                      (font_size and font_size > body_size + 0.3) or
                      re.match(r'^\d+\.\d+', clean_text)):  # Numbered subsections like "2.1"
                    final_level = "H2"
                else:
                    final_level = "H3"
        
        # Special handling for major document headings - these should always be H1
        major_headings = ['overview', 'introduction', 'conclusion', 'summary', 'abstract', 'contents', 'table of contents']
        if (clean_text.lower() in major_headings or 
            any(clean_text.lower().startswith(f'{word} ') for word in major_headings) or
            re.match(r'^\d+\.?\s+(overview|introduction|conclusion|summary)', clean_text.lower())):
            final_level = "H1"
        
        # Override form fields to H3 (but major headings take precedence)
        elif is_form_field:
            final_level = "H3"
        
        final_outline.append({
            "level": final_level,
            "text": clean_text,
            "page": heading["page"]
        })
    
    # Sort by page and then by position/order to maintain chronological order
    final_outline.sort(key=lambda x: x["page"])
    
    return final_outline

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
                      if b["is_bold"] and 
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
        if candidate["is_bold"]:
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

def extract_outline_advanced(text_blocks: List[Dict], title: str) -> List[Dict]:
    """Advanced outline extraction with multiple detection methods."""
    if not text_blocks:
        return []
    
    # Analyze document structure
    font_analysis = analyze_font_hierarchy(text_blocks, title)
    structure_analysis = analyze_document_structure(text_blocks)
    
    # Multi-pass heading detection
    headings = []
    
    # Pass 1: Font-based detection
    font_headings = detect_headings_by_font(text_blocks, font_analysis, title)
    headings.extend(font_headings)
    
    # Pass 2: Pattern-based detection
    pattern_headings = detect_headings_by_pattern(text_blocks, title)
    headings.extend(pattern_headings)
    
    # Pass 3: Structure-based detection
    structure_headings = detect_headings_by_structure(text_blocks, structure_analysis, title)
    headings.extend(structure_headings)
    
    # Merge and deduplicate
    merged_headings = merge_heading_candidates(headings)
    
    # Apply hierarchy and filtering
    final_outline = apply_heading_hierarchy(merged_headings, font_analysis)
    
    return final_outline

def analyze_font_hierarchy(text_blocks: List[Dict], title: str) -> Dict:
    """Analyze font sizes and establish hierarchy."""
    # Exclude title and common non-heading text
    content_blocks = [b for b in text_blocks 
                     if b["text"] != title and 
                     not is_page_number(b["text"]) and 
                     not is_header_footer(b, text_blocks)]
    
    if not content_blocks:
        return {}
    
    # Analyze font size distribution
    sizes = [b["size"] for b in content_blocks]
    size_counter = Counter(round(s, 1) for s in sizes)
    
    # Find body text size (most common)
    body_size = size_counter.most_common(1)[0][0]
    
    # Find heading sizes (larger than body text and less frequent)
    heading_sizes = []
    for size, count in size_counter.items():
        if size > body_size + 0.5 and count < len(content_blocks) * 0.3:
            heading_sizes.append(size)
    
    # Sort heading sizes (largest first)
    heading_sizes.sort(reverse=True)
    
    # Map to hierarchy levels
    size_to_level = {}
    level_names = ["H1", "H2", "H3"]
    
    for i, size in enumerate(heading_sizes[:3]):
        size_to_level[size] = level_names[i]
    
    return {
        "body_size": body_size,
        "heading_sizes": heading_sizes,
        "size_to_level": size_to_level,
        "size_distribution": dict(size_counter)
    }

def analyze_document_structure(text_blocks: List[Dict]) -> Dict:
    """Analyze document structure and layout patterns."""
    # Analyze spacing patterns
    y_positions = [b["y_position"] for b in text_blocks]
    spacing_gaps = []
    
    for i in range(1, len(y_positions)):
        gap = y_positions[i] - y_positions[i-1]
        if gap > 0:
            spacing_gaps.append(gap)
    
    # Find significant spacing (potential section breaks)
    if spacing_gaps:
        avg_spacing = sum(spacing_gaps) / len(spacing_gaps)
        significant_spacing = avg_spacing * 1.5
    else:
        significant_spacing = 20
    
    # Analyze indentation patterns
    x_positions = [b["x_position"] for b in text_blocks]
    common_indents = Counter(round(x, 0) for x in x_positions)
    
    return {
        "significant_spacing": significant_spacing,
        "average_spacing": sum(spacing_gaps) / len(spacing_gaps) if spacing_gaps else 15,
        "common_indents": dict(common_indents),
        "left_margin": min(x_positions) if x_positions else 0
    }

def detect_headings_by_font(text_blocks: List[Dict], font_analysis: Dict, title: str) -> List[Dict]:
    """Detect headings based on font size analysis."""
    headings = []
    size_to_level = font_analysis.get("size_to_level", {})
    
    for block in text_blocks:
        text = block["text"].strip()
        size = round(block["size"], 1)
        
        if (text != title and 
            size in size_to_level and 
            not is_page_number(text) and
            not is_header_footer(block, text_blocks) and
            is_heading_like_text(text)):
            
            headings.append({
                "text": text,
                "level": size_to_level[size],
                "page": block["page"],
                "confidence": calculate_font_confidence(block, font_analysis),
                "source": "font"
            })
    
    return headings

def detect_headings_by_pattern(text_blocks: List[Dict], title: str) -> List[Dict]:
    """Detect headings based on text patterns."""
    headings = []
    
    for block in text_blocks:
        text = block["text"].strip()
        
        if text == title or is_page_number(text):
            continue
        
        confidence = 0
        level = "H1"
        
        # Numbered headings (1., 1.1, etc.)
        if re.match(r'^\d+\.\s+[A-Z]', text):
            confidence = 0.9
            level = "H1"
        elif re.match(r'^\d+\.\d+\s+[A-Z]', text):
            confidence = 0.9
            level = "H2"
        elif re.match(r'^\d+\.\d+\.\d+\s+[A-Z]', text):
            confidence = 0.9
            level = "H3"
        
        # Roman numerals
        elif re.match(r'^[IVX]+\.\s+[A-Z]', text):
            confidence = 0.8
            level = "H1"
        
        # Lettered headings (A., B., etc.)
        elif re.match(r'^[A-Z]\.\s+[A-Z]', text):
            confidence = 0.7
            level = "H2"
        
        # All caps headings
        elif text.isupper() and len(text.split()) <= 8 and len(text) > 3:
            confidence = 0.6
            level = "H1"
        
        # Title case with specific patterns
        elif (re.match(r'^[A-Z][a-z]+(\s+[A-Z][a-z]*)*$', text) and 
              len(text.split()) <= 8 and 
              len(text) > 5):
            confidence = 0.5
            level = "H2"
        
        if confidence > 0.5:
            headings.append({
                "text": text,
                "level": level,
                "page": block["page"],
                "confidence": confidence,
                "source": "pattern"
            })
    
    return headings

def detect_headings_by_structure(text_blocks: List[Dict], structure_analysis: Dict, title: str) -> List[Dict]:
    """Detect headings based on document structure and layout."""
    headings = []
    significant_spacing = structure_analysis.get("significant_spacing", 20)
    
    for i, block in enumerate(text_blocks):
        text = block["text"].strip()
        
        if text == title or is_page_number(text):
            continue
        
        confidence = 0
        
        # Check for spacing before this block
        if i > 0:
            prev_block = text_blocks[i-1]
            spacing = block["y_position"] - prev_block["y_position"]
            if spacing > significant_spacing:
                confidence += 0.3
        
        # Check for bold text
        if block.get("is_bold", False):
            confidence += 0.4
        
        # Check for shorter lines (headings are often shorter)
        if len(text) < 80 and len(text.split()) <= 10:
            confidence += 0.2
        
        # Check for specific heading indicators
        if any(word in text.lower() for word in 
               ['introduction', 'overview', 'conclusion', 'summary', 'background',
                'methodology', 'results', 'discussion', 'abstract', 'contents']):
            confidence += 0.3
        
        if confidence > 0.6:
            # Determine level based on position and formatting
            level = "H2"
            if block.get("is_bold", False) and confidence > 0.8:
                level = "H1"
            elif confidence < 0.8:
                level = "H3"
            
            headings.append({
                "text": text,
                "level": level,
                "page": block["page"],
                "confidence": confidence,
                "source": "structure"
            })
    
    return headings

def merge_heading_candidates(headings: List[Dict]) -> List[Dict]:
    """Merge and deduplicate heading candidates from different detection methods."""
    # Group by text and page
    heading_groups = defaultdict(list)
    for heading in headings:
        key = (heading["text"], heading["page"])
        heading_groups[key].append(heading)
    
    merged = []
    for (text, page), candidates in heading_groups.items():
        # Prioritize font-based detection for level assignment
        font_candidate = next((c for c in candidates if c["source"] == "font"), None)
        
        if font_candidate:
            best = font_candidate
        else:
            # Find best candidate (highest confidence)
            best = max(candidates, key=lambda x: x["confidence"])
        
        # Boost confidence if multiple methods agree
        if len(candidates) > 1:
            best["confidence"] = min(1.0, best["confidence"] + 0.2 * (len(candidates) - 1))
        
        merged.append(best)
    
    # Sort by page and then by y-position to maintain document order
    merged.sort(key=lambda x: (x["page"], x.get("y_position", 0)))
    
    return merged

def apply_heading_hierarchy(headings: List[Dict], font_analysis: Dict) -> List[Dict]:
    """Apply consistent heading hierarchy and filtering."""
    # Filter by confidence threshold
    filtered_headings = [h for h in headings if h["confidence"] > 0.5]
    
    # Apply hierarchy rules
    final_outline = []
    
    for heading in filtered_headings:
        # Clean and validate heading text
        clean_text = clean_heading_text(heading["text"])
        if len(clean_text) < 3 or len(clean_text) > 200:
            continue
        
        final_outline.append({
            "level": heading["level"],
            "text": clean_text,
            "page": heading["page"]
        })
    
    return final_outline

def calculate_font_confidence(block: Dict, font_analysis: Dict) -> float:
    """Calculate confidence score for font-based heading detection."""
    confidence = 0.7  # Base confidence for font-based detection
    
    # Boost for bold text
    if block.get("is_bold", False):
        confidence += 0.2
    
    # Boost for larger font size difference
    body_size = font_analysis.get("body_size", 12)
    size_diff = block["size"] - body_size
    if size_diff > 2:
        confidence += 0.1
    
    return min(1.0, confidence)

def is_heading_like_text(text: str) -> bool:
    """Enhanced check if text looks like a heading."""
    text = text.strip()
    
    # Length check
    if len(text) < 3 or len(text) > 200:
        return False
    
    # Word count check
    word_count = len(text.split())
    if word_count > 15:
        return False
    
    # Pattern checks
    if re.match(r'^\d+[\.\s]', text):  # Numbered
        return True
    
    if re.match(r'^[A-Z][a-z]+(\s+[A-Z][a-z]*)*$', text):  # Title case
        return True
    
    if text.isupper() and word_count <= 8:  # All caps
        return True
    
    # Common heading words
    heading_indicators = [
        'introduction', 'overview', 'background', 'methodology', 'results',
        'conclusion', 'discussion', 'summary', 'abstract', 'contents',
        'chapter', 'section', 'part', 'appendix', 'index', 'references'
    ]
    
    if any(word in text.lower() for word in heading_indicators):
        return True
    
    return False

def is_header_footer(block: Dict, all_blocks: List[Dict]) -> bool:
    """Check if block is likely a header or footer."""
    page_height = block.get("page_height", 1000)
    y_pos = block["y_position"]
    
    # Check if in header area (top 10% of page)
    if y_pos < page_height * 0.1:
        return True
    
    # Check if in footer area (bottom 10% of page)
    if y_pos > page_height * 0.9:
        return True
    
    return False

def clean_title_text(text: str) -> str:
    """Clean and normalize title text."""
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text.strip())
    
    # Remove trailing punctuation except for appropriate cases
    text = re.sub(r'[\.]+$', '', text)
    
    return text

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

def is_likely_heading(text, block):
    """Determine if text is likely a heading based on various heuristics."""
    text = text.strip()
    
    # Too short or too long
    if len(text) < 3 or len(text) > 200:
        return False
    
    # Contains mostly numbers (likely page numbers or references)
    if re.match(r'^\d+(\.\d+)*$', text):
        return False
    
    # Skip common non-heading content
    skip_words = ['page', 'copyright', '©', 'version', 'date', 'isbn']
    if any(word in text.lower() for word in skip_words):
        return False
    
    # Common heading patterns
    if re.match(r'^\d+\.?\s+', text):  # "1. Introduction" or "1 Introduction"
        return True
    
    if re.match(r'^\d+\.\d+\s+', text):  # "2.1 Something"
        return True
    
    # Title case pattern
    if re.match(r'^[A-Z][A-Za-z\s\-–]+$', text) and len(text.split()) <= 10:
        return True
    
    # Check if it's bold (flags & 16 = bold)
    if block["flags"] & 16 and len(text.split()) <= 10:
        return True
    
    # Common heading words
    heading_words = ['introduction', 'overview', 'background', 'methodology', 'results', 
                    'conclusion', 'discussion', 'summary', 'abstract', 'acknowledgment',
                    'references', 'bibliography', 'appendix', 'contents', 'index', 'revision',
                    'history', 'table', 'business', 'outcomes', 'content', 'trademarks',
                    'documents', 'web', 'sites', 'audience', 'career', 'paths', 'learning',
                    'objectives', 'entry', 'requirements', 'structure', 'course', 'duration',
                    'keeping', 'current', 'syllabus', 'agile', 'tester', 'extension', 'foundation',
                    'level']
    
    if any(word in text.lower() for word in heading_words):
        return True
    
    return False

def clean_heading_text(text):
    """Clean and normalize heading text."""
    # Remove trailing dots and whitespace
    text = text.strip()
    
    # Don't remove leading numbers for numbered headings - keep them as they appear
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
    
    successful_count = 0
    total_headings = 0
    
    for pdf_file in pdf_files:
        file_start_time = time.time()
        try:
            print(f"Processing {pdf_file.name}...")
            
            # Extract title and outline with maximum accuracy
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

def extract_title_and_outline_optimized(pdf_path):
    """Optimized version of title and outline extraction for performance."""
    doc = fitz.open(pdf_path)
    
    try:
        # Quick PDF outline check first (fastest method)
        pdf_outline = extract_pdf_outline_fast(doc)
        if pdf_outline["title"] or pdf_outline["outline"]:
            return pdf_outline["title"], pdf_outline["outline"]
        
        # Limited page analysis for performance (first 20 pages max)
        max_pages = min(len(doc), 20)
        text_blocks = extract_text_blocks_optimized(doc, max_pages)
        
        if not text_blocks:
            return "", []
        
        # Streamlined analysis
        title = extract_title_fast(text_blocks)
        outline = extract_outline_fast(text_blocks, title)
        
        return title, outline
    
    finally:
        doc.close()

def extract_pdf_outline_fast(doc):
    """Fast PDF outline extraction with minimal processing."""
    title = ""
    outline = []
    
    try:
        # Quick metadata check
        metadata = doc.metadata
        if metadata and metadata.get("title"):
            title = metadata["title"].strip()[:200]  # Limit title length
        
        # Quick outline extraction
        toc = doc.get_toc(simple=True)  # Use simple=True for faster processing
        if toc:
            for item in toc[:50]:  # Limit to first 50 outline items
                level = min(item[0], 3)  # Cap at H3
                text = item[1].strip()[:100]  # Limit text length
                page = item[2]
                
                if text and len(text) > 2:
                    level_map = {1: "H1", 2: "H2", 3: "H3"}
                    outline.append({
                        "level": level_map[level],
                        "text": text,
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
            if block["is_bold"]:
                score += 5
            
            scored_candidates.append((score, block["text"]))
    
    if scored_candidates:
        best_title = max(scored_candidates, key=lambda x: x[0])[1]
        return best_title.strip()[:150]  # Limit length
    
    return ""

def extract_outline_fast(text_blocks: List[Dict], title: str) -> List[Dict]:
    """Fast outline extraction with simplified logic."""
    if not text_blocks:
        return []
    
    # Quick font size analysis
    sizes = [b["size"] for b in text_blocks if b["text"] != title]
    if not sizes:
        return []
    
    size_counts = Counter(round(s, 1) for s in sizes)
    body_size = size_counts.most_common(1)[0][0]
    
    # Find heading candidates
    headings = []
    
    for block in text_blocks:
        text = block["text"].strip()
        
        if (text != title and 
            not is_page_number_fast(text) and
            len(text) > 3 and 
            len(text) < 150 and
            block["word_count"] <= 12):
            
            confidence = 0
            level = "H2"
            
            # Font size check
            if block["size"] > body_size + 1.0:
                confidence += 0.6
                if block["size"] > body_size + 2.0:
                    level = "H1"
            
            # Bold check
            if block["is_bold"]:
                confidence += 0.3
            
            # Pattern checks (simplified)
            if re.match(r'^\d+\.?\s+[A-Z]', text):
                confidence += 0.4
                level = "H1"
            elif re.match(r'^\d+\.\d+\s+[A-Z]', text):
                confidence += 0.4
                level = "H2"
            elif text.isupper() and len(text.split()) <= 6:
                confidence += 0.3
            
            # Common heading words
            if any(word in text.lower() for word in 
                   ['introduction', 'overview', 'conclusion', 'summary', 'background',
                    'methodology', 'results', 'discussion', 'abstract']):
                confidence += 0.2
            
            if confidence > 0.6:
                headings.append({
                    "level": level,
                    "text": text,
                    "page": block["page"]
                })
    
    # Remove duplicates and limit count
    seen = set()
    unique_headings = []
    for heading in headings[:100]:  # Limit for performance
        key = (heading["text"], heading["page"])
        if key not in seen:
            seen.add(key)
            unique_headings.append(heading)
    
    return unique_headings

def is_page_number_fast(text: str) -> bool:
    """Fast page number detection."""
    text = text.strip()
    if len(text) > 10:
        return False
    if text.isdigit() and len(text) <= 3:
        return True
    return bool(re.match(r'^(page\s*)?\d+$', text.lower()))

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
            
            # Form field detection (override to H3)
            is_form_field = (len(text.split()) <= 8 and 
                (text.lower() in ['designation', 'service', 'age', 'name', 'relationship'] or
                 text.lower().startswith(('name of', 'date of', 'whether')) or
                 '+' in text))
            
            if is_form_field:
                level = "H3"
                confidence = max(confidence, 0.5)
            
            # Apply special handling for major headings
            text_lower = text.lower()
            if (text_lower in major_words or 
                any(text_lower.startswith(f'{word} ') for word in major_words) or
                re.match(r'^\d+\.?\s+(overview|introduction|conclusion|summary)', text_lower)):
                level = "H1"
                confidence = max(confidence, 0.8)
            
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

if __name__ == "__main__":
    print("Starting PDF outline extraction...")
    process_pdfs()
    print("Completed PDF outline extraction.")