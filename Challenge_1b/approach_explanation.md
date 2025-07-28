# Persona-Driven Document Intelligence System

## Methodology Overview

Our solution implements a modular pipeline that processes PDF documents and extracts the most relevant sections based on a specific persona and their job requirements. The system uses semantic similarity matching combined with intelligent text processing to deliver personalized document analysis.

## Core Architecture

### 1. Document Preprocessing (`preprocessing.py`)
- **PDF Text Extraction**: Uses PyMuPDF for robust text extraction while preserving document structure
- **Section Identification**: Employs regex patterns and heuristics to identify document sections based on headings, formatting, and structural indicators
- **Fallback Strategy**: When clear sections aren't detected, creates page-based sections to ensure comprehensive coverage

### 2. Semantic Embedding Engine (`embedding.py`)
- **Model Selection**: Utilizes `all-MiniLM-L6-v2` from sentence-transformers for lightweight, efficient embeddings (~90MB)
- **Query Construction**: Combines persona description and job requirements into a unified query vector
- **Relevance Scoring**: Employs cosine similarity to measure semantic alignment between query and document sections
- **CPU Optimization**: Configured for CPU-only execution to meet deployment constraints

### 3. Section Retrieval and Ranking (`retrieval.py`)
- **Document Collection Processing**: Batch processes all PDFs in the input directory
- **Relevance Ranking**: Scores and ranks all sections based on semantic similarity to persona+job query
- **Top-K Selection**: Returns the most relevant sections with importance rankings

### 4. Intelligent Summarization (`summarization.py`)
- **Extractive Approach**: Uses extractive summarization for efficiency and reliability without requiring large language models
- **Persona-Aware Refinement**: Filters and prioritizes content based on keywords relevant to the persona and job requirements
- **Content Optimization**: Balances relevance, length, and coherence to produce concise, actionable summaries

## Technical Design Decisions

**Lightweight Model Choice**: Selected sentence-transformers with MiniLM to stay well under the 1GB constraint while maintaining semantic understanding quality.

**Extractive Over Abstractive**: Chose extractive summarization to avoid large transformer models and ensure factual accuracy.

**Modular Architecture**: Separated concerns into distinct modules for maintainability and testability.

**Error Handling**: Implemented robust error handling for PDF processing failures and graceful degradation.

## Performance Optimizations

- **CPU-Only Execution**: All models configured for CPU inference
- **Efficient Text Processing**: Optimized section identification and text chunking
- **Memory Management**: Careful handling of embeddings and document processing to minimize memory footprint
- **Batch Processing**: Efficient handling of multiple documents in a single pipeline

## Output Structure

The system produces JSON output with:
- **Metadata**: Input documents, persona, job description, and processing timestamp
- **Extracted Sections**: Top-ranked sections with importance rankings and page references
- **Subsection Analysis**: Refined, persona-specific content summaries for detailed insights

This approach ensures high relevance scoring while maintaining processing efficiency within the specified constraints.