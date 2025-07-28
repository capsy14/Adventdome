# 🎯 Persona-Driven Document Intelligence System

**Adobe India Hackathon 2025 - Challenge 1B Solution**

An intelligent document analysis system that extracts and ranks the most relevant content from PDF collections based on specific personas and their job requirements. Perfect for travel planning, learning materials, recipes, and more!

## ✨ Key Features

- 🚀 **Lightning Fast**: Processes 3-5 documents in under 60 seconds
- 💻 **CPU-Only**: No GPU required, works on any machine
- 🔒 **Offline Ready**: No internet connection needed during execution
- 🎯 **Persona-Aware**: Tailors content extraction to specific user roles
- 📊 **Smart Ranking**: Uses TF-IDF similarity for relevance scoring
- 🐳 **Docker Ready**: Containerized for easy deployment

## 🚀 Quick Start

### Method 1: Local Python (Fastest)

```bash
# 1. Navigate to the project directory
cd Challenge_1b

# 2. Install dependencies (only 3 packages!)
pip3 install -r requirements.txt

# 3. Run on sample data
python3 main.py "Collection 1/challenge1b_input.json" "Collection 1/PDFs/" "Collection 1/challenge1b_output.json"
```

### Method 2: Docker (Recommended for Production)

```bash
# 1. Build the image
docker build -t document-intelligence .

# 2. Run all collections automatically
./run_collection.sh all

# Or run individual collections
./run_collection.sh 1    # Travel Planning
./run_collection.sh 2    # Adobe Acrobat Learning
./run_collection.sh 3    # Recipe Collection
```

## 📁 Ready-to-Test Collections

The system comes with **3 pre-configured test cases**:

| Collection | Persona | Task | Documents |
|------------|---------|------|-----------|
| **Collection 1** | Travel Planner | Plan 4-day trip for 10 college friends | 7 South of France guides |
| **Collection 2** | HR Professional | Create fillable forms for onboarding | 15 Adobe Acrobat tutorials |
| **Collection 3** | Food Contractor | Prepare vegetarian buffet menu | 9 cooking guides |

### 🎮 Interactive Demo Commands

```bash
# Test Collection 1: Travel Planning
python3 main.py "Collection 1/challenge1b_input.json" "Collection 1/PDFs/" "Collection 1/challenge1b_output.json"

# Test Collection 2: Adobe Acrobat Learning  
python3 main.py "Collection 2/challenge1b_input.json" "Collection 2/PDFs/" "Collection 2/challenge1b_output.json"

# Test Collection 3: Recipe Collection
python3 main.py "Collection 3/challenge1b_input.json" "Collection 3/PDFs/" "Collection 3/challenge1b_output.json"
```

**Expected Output**: Each command generates a `challenge1b_output.json` file in the respective Collection folder with ranked sections and persona-specific analysis.

### 🔍 Sample Output Preview

```json
{
  "metadata": {
    "persona": "Travel Planner",
    "job_to_be_done": "Plan a trip of 4 days for a group of 10 college friends",
    "processing_timestamp": "2025-07-20T..."
  },
  "extracted_sections": [
    {
      "document": "South of France - Tips and Tricks.pdf",
      "section_title": "General Packing Tips and Tricks",
      "importance_rank": 1,
      "page_number": 2
    }
  ],
  "subsection_analysis": [
    {
      "document": "South of France - Tips and Tricks.pdf", 
      "refined_text": "Planning a trip to the South of France requires thoughtful preparation...",
      "page_number": 1
    }
  ]
}
```

## 📁 Project Structure
```
Challenge_1b/
├── main.py                         # Main application entry point
├── preprocessing.py                # PDF text extraction and section identification
├── embedding.py                    # Semantic similarity using sentence-transformers
├── retrieval.py                    # Document processing and section ranking
├── summarization.py                # Intelligent content refinement
├── requirements.txt                # Python dependencies
├── Dockerfile                      # Container configuration
├── approach_explanation.md         # Technical methodology
├── Collection 1/                   # Travel Planning test case
│   ├── PDFs/                      # South of France guides
│   ├── challenge1b_input.json     # Input configuration
│   └── challenge1b_output.json    # Expected results
├── Collection 2/                   # Adobe Acrobat Learning test case
│   ├── PDFs/                      # Acrobat tutorials
│   ├── challenge1b_input.json     # Input configuration
│   └── challenge1b_output.json    # Expected results
├── Collection 3/                   # Recipe Collection test case
│   ├── PDFs/                      # Cooking guides
│   ├── challenge1b_input.json     # Input configuration
│   └── challenge1b_output.json    # Expected results
└── README.md
```

## Sample Test Cases

### Collection 1: Travel Planning
- **Challenge ID**: round_1b_002
- **Persona**: Travel Planner
- **Task**: Plan a 4-day trip for 10 college friends to South of France
- **Documents**: 7 travel guides

### Collection 2: Adobe Acrobat Learning
- **Challenge ID**: round_1b_003
- **Persona**: HR Professional
- **Task**: Create and manage fillable forms for onboarding and compliance
- **Documents**: 15 Acrobat guides

### Collection 3: Recipe Collection
- **Challenge ID**: round_1b_001
- **Persona**: Food Contractor
- **Task**: Prepare vegetarian buffet-style dinner menu for corporate gathering
- **Documents**: 9 cooking guides

## Usage

### Input Format

Create an input JSON file with the following structure:

```json
{
    "challenge_info": {
        "challenge_id": "your_id",
        "test_case_name": "your_test_case",
        "description": "Brief description"
    },
    "documents": [
        {
            "filename": "document1.pdf",
            "title": "Document 1 Title"
        }
    ],
    "persona": {
        "role": "Travel Planner"
    },
    "job_to_be_done": {
        "task": "Plan a trip of 4 days for a group of 10 college friends."
    }
}
```

### Example Usage

```bash
# Test with provided sample data
python main.py "Collection 1/challenge1b_input.json" "Collection 1/PDFs/" "output.json"

# Custom usage
python main.py my_input.json ./my_pdfs/ my_output.json
```

### Output Format

The system generates a JSON file with:

```json
{
    "metadata": {
        "input_documents": ["doc1.pdf", "doc2.pdf"],
        "persona": "Travel Planner",
        "job_to_be_done": "Plan a trip...",
        "processing_timestamp": "2025-07-20T..."
    },
    "extracted_sections": [
        {
            "document": "doc1.pdf",
            "section_title": "Section Title",
            "importance_rank": 1,
            "page_number": 5
        }
    ],
    "subsection_analysis": [
        {
            "document": "doc1.pdf",
            "refined_text": "Summarized content...",
            "page_number": 5
        }
    ]
}
```

## System Architecture

```
PDF Collection → Text Extraction → Section Identification → Embedding Generation → 
Relevance Ranking → Subsection Analysis → JSON Output
```

### Key Components

1. **preprocessing.py**: PDF text extraction and section identification
2. **embedding.py**: Semantic similarity using sentence-transformers
3. **retrieval.py**: Document processing and section ranking
4. **summarization.py**: Intelligent content refinement
5. **main.py**: Main application orchestrator

## ⚡ Performance Specifications

- **Model Size**: <100MB (TF-IDF vectorizer)
- **Processing Time**: ~0.1 seconds for 7 documents
- **Memory Usage**: <500MB RAM
- **CPU Only**: No GPU dependencies
- **Network**: No internet required during execution

## 🧪 Testing & Validation

### Quick Validation
```bash
# Verify installation
pip3 list | grep -E "(PyMuPDF|scikit-learn|numpy)"

# Test single collection (fastest)
python3 main.py "Collection 1/challenge1b_input.json" "Collection 1/PDFs/" "Collection 1/challenge1b_output.json"

# Verify output file was created
ls -la "Collection 1/challenge1b_output.json"
```

### Full Test Suite
```bash
# Test all collections
for i in {1..3}; do
  python3 main.py "Collection $i/challenge1b_input.json" "Collection $i/PDFs/" "Collection $i/challenge1b_output.json"
  echo "Collection $i: ✅ $(ls -la "Collection $i/challenge1b_output.json" | awk '{print $5}') bytes"
done
```

## Dependencies (Minimal & Offline)

- **PyMuPDF**: PDF text extraction
- **numpy**: Numerical computations  
- **scikit-learn**: TF-IDF vectorization and similarity calculations

*No internet connection required during execution!*

## 🆘 Troubleshooting

| Issue | Solution |
|-------|----------|
| `ModuleNotFoundError` | Run `pip3 install -r requirements.txt` |
| `Permission denied` | Use `chmod +x run_collection.sh` |
| `Docker build fails` | Try `docker build --no-cache -t document-intelligence .` |
| `PDF not found` | Check file paths have correct spaces: `"Collection 1/..."` |
| `Empty output` | Verify PDF files are not password-protected |

### Common Docker Issues
```bash
# Fix Docker permission issues
sudo chmod 666 /var/run/docker.sock

# Clean Docker cache if build fails
docker system prune -f

# Check Docker is running
docker --version
```

## 🎯 For Judges & Evaluators

### One-Command Demo
```bash
# Install and test everything in one go
pip3 install -r requirements.txt && python3 main.py "Collection 1/challenge1b_input.json" "Collection 1/PDFs/" "Collection 1/challenge1b_output.json" && echo "✅ Demo completed! Check Collection 1/challenge1b_output.json"
```

### Key Evaluation Points
- ✅ **CPU-only execution** (no GPU required)
- ✅ **Model size <1GB** (TF-IDF is ~100MB)
- ✅ **Processing time <60s** (actual: ~0.1s for 7 docs)
- ✅ **No internet access** needed during execution
- ✅ **Persona-aware relevance ranking** with importance scores
- ✅ **Structured JSON output** with metadata and analysis

## 📜 License

**Adobe India Hackathon 2025 - Challenge 1B Submission**

Created by Team for intelligent document analysis and persona-driven content extraction. 