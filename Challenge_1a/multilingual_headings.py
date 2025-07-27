import re
import numpy as np
from typing import List, Dict, Tuple, Optional
from collections import Counter
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import langdetect
import warnings
warnings.filterwarnings("ignore")

class MultilingualHeadingDetector:
    """Enhanced multilingual heading detection with NLP semantic validation."""
    
    def __init__(self, model_name: str = "distiluse-base-multilingual-cased-v2"):
        """Initialize the multilingual heading detector.
        
        Args:
            model_name: Name of the sentence transformer model to use
        """
        print(f"Loading multilingual model: {model_name}")
        self.model = SentenceTransformer(model_name)
        
        # Precompute heading prototype embeddings for semantic validation
        self.heading_prototypes = self._create_heading_prototypes()
        
        # Language-specific patterns
        self.language_patterns = self._initialize_language_patterns()
        
        # Heading keywords in multiple languages
        self.multilingual_keywords = self._initialize_multilingual_keywords()
    
    def _create_heading_prototypes(self) -> np.ndarray:
        """Create prototype embeddings for typical headings."""
        prototype_headings = [
            # English
            "Introduction", "Overview", "Background", "Methodology", "Results",
            "Discussion", "Conclusion", "Summary", "Chapter 1", "Section 2.1",
            
            # Japanese
            "第1章", "第2節", "概要", "序論", "方法論", "結果", "考察", "結論",
            "まとめ", "背景", "目的", "手法", "実験", "分析",
            
            # Arabic
            "المقدمة", "الخلاصة", "النتائج", "المنهجية", "الخلفية", "الهدف",
            "الفصل الأول", "القسم الثاني", "التحليل", "الاستنتاج",
            
            # Spanish
            "Introducción", "Resumen", "Metodología", "Resultados", "Conclusión",
            "Capítulo 1", "Sección 2", "Análisis", "Discusión",
            
            # French
            "Introduction", "Résumé", "Méthodologie", "Résultats", "Conclusion",
            "Chapitre 1", "Section 2", "Analyse", "Discussion",
            
            # German
            "Einführung", "Zusammenfassung", "Methodologie", "Ergebnisse", "Schlussfolgerung",
            "Kapitel 1", "Abschnitt 2", "Analyse", "Diskussion",
            
            # Chinese
            "引言", "概述", "方法", "结果", "讨论", "结论", "第一章", "第二节"
        ]
        
        embeddings = self.model.encode(prototype_headings, convert_to_numpy=True)
        return embeddings
    
    def _initialize_language_patterns(self) -> Dict[str, List[str]]:
        """Initialize language-specific regex patterns for heading detection."""
        return {
            'japanese': [
                r'^第[0-9０-９一二三四五六七八九十百千万]+章.*',  # Chapter patterns
                r'^第[0-9０-９一二三四五六七八九十百千万]+節.*',  # Section patterns
                r'^[0-9０-９]+[\.．][0-9０-９]*\s*.*',  # Numbered sections
                r'^[０-９0-9]+[　\s]*[\.．][　\s]*.*',  # Spaced numbering
                r'^[一二三四五六七八九十百千万]+[\.．、]\s*.*',  # Japanese numerals
                r'^「.*」$',  # Quoted headings
                r'^【.*】$',  # Bracketed headings
                r'^■.*',     # Bullet point headings
                r'^◆.*',     # Diamond bullet headings
                r'^○.*',     # Circle bullet headings
                r'^序章|序論|はじめに|概要|概観|背景|目的|手法|方法|実験|結果|考察|検討|結論|まとめ|おわりに',
            ],
            'arabic': [
                r'^الفصل\s+[الأ]*[0-9٠-٩]+.*',  # Chapter patterns
                r'^القسم\s+[الأ]*[0-9٠-٩]+.*',  # Section patterns
                r'^[0-9٠-٩]+[\.]\s*.*',  # Numbered sections
                r'^[0-9٠-٩]+[\.][0-9٠-٩]+\s*.*',  # Sub-numbered sections
                r'^[أ-ي]+[\.]\s*.*',  # Arabic letter numbering
                r'^-\s+.*',  # Dash headings
                r'^•\s+.*',  # Bullet headings
                r'^المقدمة|الخلاصة|النتائج|المنهجية|الخلفية|الهدف|التحليل|الاستنتاج|المراجع|الملاحق',
            ],
            'chinese': [
                r'^第[0-9一二三四五六七八九十百千万]+章.*',  # Chapter patterns
                r'^第[0-9一二三四五六七八九十百千万]+节.*',  # Section patterns (simplified)
                r'^第[0-9一二三四五六七八九十百千万]+節.*',  # Section patterns (traditional)
                r'^[0-9]+[\.]\s*.*',  # Numbered sections
                r'^[0-9]+[\.][0-9]+\s*.*',  # Sub-numbered sections
                r'^[一二三四五六七八九十百千万]+[、．\.]\s*.*',  # Chinese numerals
                r'^引言|概述|背景|方法|结果|讨论|结论|总结|参考文献|附录',
            ],
            'korean': [
                r'^제[0-9]+장.*',  # Chapter patterns
                r'^제[0-9]+절.*',  # Section patterns
                r'^[0-9]+[\.]\s*.*',  # Numbered sections
                r'^[0-9]+[\.][0-9]+\s*.*',  # Sub-numbered sections
                r'^서론|개요|배경|방법|결과|논의|결론|요약|참고문헌|부록',
            ]
        }
    
    def _initialize_multilingual_keywords(self) -> Dict[str, List[str]]:
        """Initialize heading keywords in multiple languages."""
        return {
            'english': [
                'introduction', 'overview', 'background', 'methodology', 'methods',
                'results', 'discussion', 'conclusion', 'summary', 'abstract',
                'contents', 'chapter', 'section', 'part', 'appendix', 'references',
                'index', 'acknowledgments', 'preface', 'foreword'
            ],
            'japanese': [
                '序論', '序章', 'はじめに', '概要', '概観', '背景', '目的', '手法',
                '方法', '方法論', '実験', '結果', '考察', '検討', '結論', 'まとめ',
                'おわりに', '謝辞', '参考文献', '付録', '目次', '索引'
            ],
            'arabic': [
                'المقدمة', 'الخلاصة', 'النتائج', 'المنهجية', 'الخلفية', 'الهدف',
                'التحليل', 'الاستنتاج', 'المراجع', 'الملاحق', 'الفهرس', 'المحتويات'
            ],
            'chinese': [
                '引言', '概述', '背景', '方法', '方法论', '结果', '讨论', '结论',
                '总结', '摘要', '目录', '参考文献', '附录', '索引', '前言'
            ],
            'spanish': [
                'introducción', 'resumen', 'metodología', 'resultados', 'conclusión',
                'capítulo', 'sección', 'análisis', 'discusión', 'referencias'
            ],
            'french': [
                'introduction', 'résumé', 'méthodologie', 'résultats', 'conclusion',
                'chapitre', 'section', 'analyse', 'discussion', 'références'
            ],
            'german': [
                'einführung', 'zusammenfassung', 'methodologie', 'ergebnisse',
                'schlussfolgerung', 'kapitel', 'abschnitt', 'analyse', 'diskussion'
            ]
        }
    
    def detect_language(self, text: str) -> str:
        """Detect the language of the given text."""
        try:
            # Clean text for language detection
            clean_text = re.sub(r'[0-9\.\[\](){}「」【】]', '', text)
            if len(clean_text.strip()) < 3:
                return 'unknown'
            
            detected = langdetect.detect(clean_text)
            return detected
        except:
            return 'unknown'
    
    def is_heading_by_pattern(self, text: str, language: str = None) -> Tuple[bool, float, str]:
        """Check if text matches language-specific heading patterns.
        
        Returns:
            Tuple of (is_heading, confidence, pattern_type)
        """
        if not text or len(text.strip()) < 2:
            return False, 0.0, ""
        
        text = text.strip()
        
        # Auto-detect language if not provided
        if language is None:
            language = self.detect_language(text)
        
        max_confidence = 0.0
        best_pattern = ""
        
        # Check language-specific patterns
        if language in self.language_patterns:
            for pattern in self.language_patterns[language]:
                if re.search(pattern, text, re.IGNORECASE):
                    confidence = 0.8 if re.match(pattern, text, re.IGNORECASE) else 0.6
                    if confidence > max_confidence:
                        max_confidence = confidence
                        best_pattern = f"{language}_pattern"
        
        # Check multilingual keywords
        text_lower = text.lower()
        for lang, keywords in self.multilingual_keywords.items():
            for keyword in keywords:
                if keyword in text_lower:
                    confidence = 0.7 if text_lower.startswith(keyword) else 0.5
                    if confidence > max_confidence:
                        max_confidence = confidence
                        best_pattern = f"{lang}_keyword"
        
        # Universal patterns (numbers, formatting)
        universal_patterns = [
            (r'^\d+\.\s+[A-Z\u4e00-\u9fff\u0600-\u06ff]', 0.9, "numbered_section"),
            (r'^\d+\.\d+\s+[A-Z\u4e00-\u9fff\u0600-\u06ff]', 0.9, "sub_numbered"),
            (r'^[IVX]+\.\s+[A-Z\u4e00-\u9fff\u0600-\u06ff]', 0.8, "roman_numeral"),
            (r'^[A-Z]{2,}(\s+[A-Z]+)*$', 0.7, "all_caps"),
            (r'^[A-Z][a-z]+(\s+[A-Z][a-z]*)*$', 0.6, "title_case"),
        ]
        
        for pattern, confidence, pattern_type in universal_patterns:
            if re.match(pattern, text):
                if confidence > max_confidence:
                    max_confidence = confidence
                    best_pattern = pattern_type
        
        return max_confidence > 0.5, max_confidence, best_pattern
    
    def calculate_semantic_confidence(self, text: str, context_texts: List[str] = None) -> float:
        """Calculate semantic confidence that text is a heading using NLP embeddings."""
        try:
            # Get embedding for the candidate text
            text_embedding = self.model.encode([text], convert_to_numpy=True)
            
            # Calculate similarity with heading prototypes
            similarities = cosine_similarity(text_embedding, self.heading_prototypes)[0]
            max_similarity = np.max(similarities)
            avg_similarity = np.mean(similarities)
            
            # Base confidence from prototype similarity
            semantic_confidence = (max_similarity * 0.7 + avg_similarity * 0.3)
            
            # Boost confidence if text appears in typical heading positions/contexts
            if context_texts:
                # Check if surrounded by non-heading text (typical for headings)
                context_embeddings = self.model.encode(context_texts, convert_to_numpy=True)
                context_similarities = cosine_similarity(text_embedding, context_embeddings)[0]
                
                # Headings should be somewhat distinct from surrounding text
                avg_context_similarity = np.mean(context_similarities)
                if avg_context_similarity < 0.7:  # Distinct from context
                    semantic_confidence += 0.1
            
            return min(1.0, semantic_confidence)
            
        except Exception as e:
            print(f"Warning: Semantic analysis failed: {e}")
            return 0.5  # Neutral confidence if embeddings fail
    
    def enhanced_heading_detection(self, text_blocks: List[Dict], title: str = "") -> List[Dict]:
        """Enhanced heading detection with multilingual support and semantic validation."""
        if not text_blocks:
            return []
        
        headings = []
        
        # Group text blocks by language for better context
        language_groups = {}
        for i, block in enumerate(text_blocks):
            text = block["text"].strip()
            if len(text) > 2 and text != title:
                lang = self.detect_language(text)
                if lang not in language_groups:
                    language_groups[lang] = []
                language_groups[lang].append((i, block))
        
        # Process each language group
        for language, blocks in language_groups.items():
            for i, (original_index, block) in enumerate(blocks):
                text = block["text"].strip()
                
                # Skip obvious non-headings
                if (len(text) < 3 or len(text) > 200 or 
                    self._is_page_number(text) or 
                    self._is_header_footer(block, text_blocks)):
                    continue
                
                confidence_scores = {}
                
                # 1. Pattern-based detection
                is_pattern_heading, pattern_conf, pattern_type = self.is_heading_by_pattern(text, language)
                if is_pattern_heading:
                    confidence_scores['pattern'] = pattern_conf
                
                # 2. Font-based detection (from original system)
                font_conf = self._calculate_font_confidence(block, text_blocks, title)
                if font_conf > 0.3:
                    confidence_scores['font'] = font_conf
                
                # 3. Semantic validation using NLP embeddings
                context_texts = []
                if i > 0:
                    context_texts.append(blocks[i-1][1]["text"])
                if i < len(blocks) - 1:
                    context_texts.append(blocks[i+1][1]["text"])
                
                semantic_conf = self.calculate_semantic_confidence(text, context_texts)
                confidence_scores['semantic'] = semantic_conf
                
                # 4. Structure-based detection
                structure_conf = self._calculate_structure_confidence(block, text_blocks, original_index)
                if structure_conf > 0.3:
                    confidence_scores['structure'] = structure_conf
                
                # Combine confidence scores with weights
                if confidence_scores:
                    weights = {
                        'pattern': 0.35,
                        'semantic': 0.30,
                        'font': 0.25,
                        'structure': 0.10
                    }
                    
                    total_confidence = sum(
                        confidence_scores.get(method, 0) * weight 
                        for method, weight in weights.items()
                    )
                    
                    # Determine heading level based on multiple factors
                    level = self._determine_heading_level(
                        text, block, confidence_scores, language, pattern_type
                    )
                    
                    # Apply threshold for heading detection
                    if total_confidence > 0.45:  # Adjust threshold as needed
                        headings.append({
                            "text": text,
                            "level": level,
                            "page": block["page"],
                            "confidence": total_confidence,
                            "language": language,
                            "detection_methods": list(confidence_scores.keys()),
                            "y_position": block.get("y_position", 0)
                        })
        
        # Sort and deduplicate
        headings = self._deduplicate_headings(headings)
        headings.sort(key=lambda x: (x["page"], x.get("y_position", 0)))
        
        return headings
    
    def _determine_heading_level(self, text: str, block: Dict, confidence_scores: Dict, 
                                language: str, pattern_type: str) -> str:
        """Determine the appropriate heading level (H1, H2, H3) with improved distribution."""
        # Use scoring system for better level distribution
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
                major_keywords = {
                    'english': ['introduction', 'conclusion', 'summary', 'overview', 'abstract'],
                    'japanese': ['序論', '結論', 'まとめ', '概要'],
                    'arabic': ['المقدمة', 'الخلاصة', 'النتائج'],
                    'chinese': ['引言', '结论', '总结', '概述']
                }
                
                text_lower = text.lower()
                if language in major_keywords:
                    if any(keyword in text_lower for keyword in major_keywords[language]):
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
    
    def _calculate_font_confidence(self, block: Dict, all_blocks: List[Dict], title: str) -> float:
        """Calculate confidence based on font characteristics."""
        confidence = 0.0
        
        # Font size analysis
        content_blocks = [b for b in all_blocks 
                         if b["text"] != title and len(b["text"]) > 2]
        
        if content_blocks:
            sizes = [b["size"] for b in content_blocks]
            avg_size = np.mean(sizes)
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
        
        # Text length consideration (headings are usually shorter)
        text_len = len(block["text"])
        if 5 <= text_len <= 100:
            confidence += 0.2
        elif text_len <= 150:
            confidence += 0.1
        
        return min(1.0, confidence)
    
    def _calculate_structure_confidence(self, block: Dict, all_blocks: List[Dict], index: int) -> float:
        """Calculate confidence based on document structure."""
        confidence = 0.0
        
        # Check spacing around the block
        if index > 0 and index < len(all_blocks) - 1:
            prev_block = all_blocks[index - 1]
            next_block = all_blocks[index + 1]
            
            # Calculate vertical spacing
            spacing_before = block["y_position"] - prev_block["y_position"]
            spacing_after = next_block["y_position"] - block["y_position"]
            
            # Headings often have more spacing around them
            if spacing_before > 15 or spacing_after > 15:
                confidence += 0.3
            
            # Isolation (standalone lines often headings)
            if spacing_before > 10 and spacing_after > 10:
                confidence += 0.2
        
        # Check horizontal position (centered text often headings)
        page_width = block.get("page_width", 612)
        x_pos = block.get("x_position", 0)
        bbox = block.get("bbox", [0, 0, 100, 0])
        text_width = bbox[2] - bbox[0]
        text_center = x_pos + text_width / 2
        page_center = page_width / 2
        
        if abs(text_center - page_center) < 50:  # Reasonably centered
            confidence += 0.2
        
        return min(1.0, confidence)
    
    def _deduplicate_headings(self, headings: List[Dict]) -> List[Dict]:
        """Remove duplicate headings based on text and page."""
        seen = set()
        unique_headings = []
        
        for heading in headings:
            key = (heading["text"].strip(), heading["page"])
            if key not in seen:
                seen.add(key)
                unique_headings.append(heading)
        
        return unique_headings
    
    def _is_page_number(self, text: str) -> bool:
        """Check if text is likely a page number."""
        text = text.strip()
        if len(text) > 10:
            return False
        return bool(re.match(r'^\d+$', text) or re.match(r'^page\s*\d+$', text.lower()))
    
    def _is_header_footer(self, block: Dict, all_blocks: List[Dict]) -> bool:
        """Check if block is likely a header or footer."""
        page_height = block.get("page_height", 1000)
        y_pos = block.get("y_position", 0)
        
        # Top 8% or bottom 8% of page
        return y_pos < page_height * 0.08 or y_pos > page_height * 0.92