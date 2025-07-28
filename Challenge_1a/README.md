# Challenge 1A: PDF Outline Extractor (Enhanced Multilingual)

This repository contains an enhanced solution for extracting structured outlines from PDF documents with comprehensive multilingual support. The system extracts titles and headings (H1, H2, H3) with their page numbers and outputs them in JSON format, supporting languages including Japanese, Arabic, Chinese, and others.

## 🆕 Multilingual Enhancement

**NEW**: This system now includes advanced multilingual capabilities with:
- **NLP-Powered Semantic Validation** using `distiluse-base-multilingual-cased-v2` (120MB)
- **Language-Specific Pattern Recognition** for Japanese, Arabic, Chinese, and more
- **Font-Independent Detection** with contextual analysis
- **Performance Optimized** to maintain <10s processing for 50-page PDFs

📖 **[See detailed multilingual documentation →](README_MULTILINGUAL.md)**

## Approach

Our enhanced solution combines **PyMuPDF (fitz)** with **multilingual NLP models** for robust document structure identification:

1. **Text Extraction**: Extract text with font metadata (size, style, formatting)
2. **Language Detection**: Automatic identification of document language
3. **Multilingual Pattern Recognition**: Language-specific regex patterns and formatting rules
4. **Semantic Validation**: NLP embeddings to verify heading contextual appropriateness
5. **Title Detection**: Identify document title using largest fonts on first page
6. **Heading Classification**: Multi-method confidence scoring and hierarchy assignment

## Libraries Used

### Core Libraries
- **PyMuPDF (fitz)**: Lightweight PDF processing with font metadata
- **sentence-transformers**: Multilingual NLP embeddings (120MB model)
- **scikit-learn**: Similarity calculations and machine learning utilities
- **langdetect**: Automatic language detection

### Supporting Libraries  
- **re**: Pattern matching for heading detection
- **json**: JSON output formatting
- **pathlib**: File system operations
- **collections**: Data structure utilities
- **numpy**: Numerical computations
- **torch**: Deep learning framework

## Key Features

### Original Features
- **Font-based hierarchy**: Analyzes font sizes to determine heading levels
- **Multi-part title extraction**: Combines text blocks for complete titles
- **Pattern recognition**: Detects numbered headings (1., 2.1, etc.)
- **Robust heuristics**: Uses multiple criteria for heading identification
- **Error handling**: Graceful handling of malformed PDFs

### 🆕 Multilingual Enhancements
- **Language Detection**: Automatic identification of document language (50+ languages)
- **Multilingual Patterns**: Japanese (第1章), Arabic (الفصل الأول), Chinese (第一章) support
- **Semantic Validation**: NLP-powered contextual heading verification
- **Font-Independent Detection**: Works with uniform font sizes using semantic analysis
- **Performance Optimized**: Maintains <10s requirement with model caching
- **Fallback Mechanism**: Graceful degradation to original method if needed

## Build and Run

### Docker (Production) - Requirements Compliant

**Build Command (as specified in requirements):**
```bash
docker build --platform linux/amd64 -t mysolutionname:somerandomidentifier .
```

**Run Command (as specified in requirements):**
```bash
docker run --rm \
  -v $(pwd)/input:/app/input \
  -v $(pwd)/output:/app/output \
  --network none \
  mysolutionname:somerandomidentifier
```

**Automated Compliance Testing:**
```bash
./test_compliance.sh
```

### Local Testing

```bash
# Install all dependencies (including multilingual support)
pip install -r requirements.txt

# Run PDF processing (with automatic multilingual detection)
python process_pdfs.py

# Test multilingual functionality
python test_multilingual.py

# Performance validation
python performance_test.py
```

**Note**: The multilingual model (~120MB) will be downloaded automatically on first use.

## Output Format

JSON files with the following structure:

```json
{
  "title": "Document Title",
  "outline": [
    {
      "level": "H1",
      "text": "Chapter 1: Introduction", 
      "page": 5
    },
    {
      "level": "H2",
      "text": "1.1 Background",
      "page": 6
    }
  ]
}
```

## Performance Specifications

- **Execution time**: ≤ 10 seconds for 50-page PDFs
- **Model size**: ≤ 200MB (PyMuPDF ~20MB)
- **Architecture**: AMD64 (x86_64) CPU only
- **Memory**: Optimized for 16GB RAM systems
- **Network**: Fully offline operation

## Algorithm Details

1. **Font Analysis**: Extract all text with font sizes and styles
2. **Title Extraction**: 
   - Find largest font on first page
   - Combine adjacent blocks with similar positioning
3. **Hierarchy Mapping**:
   - Exclude title font size from heading analysis
   - Map remaining font sizes to H1/H2/H3 levels
4. **Heading Detection**:
   - Numbered patterns (1., 2.1, etc.)
   - Bold text formatting
   - Common heading keywords
   - Title case formatting
5. **Filtering**: Remove duplicates and non-headings

This solution prioritizes accuracy while maintaining performance constraints for the competition environment.