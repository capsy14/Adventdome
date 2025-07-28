#!/usr/bin/env python3
"""
Persona-Driven Document Intelligence System
Main entry point for processing documents based on persona and job requirements.
"""

import json
import os
import sys
import time
from datetime import datetime
from typing import Dict, List

from retrieval import DocumentRetrieval
from summarization import TextSummarizer

class DocumentIntelligenceSystem:
    def __init__(self):
        self.retrieval_engine = DocumentRetrieval()
        self.summarizer = TextSummarizer()
    
    def load_input_config(self, input_file: str) -> Dict:
        """Load input configuration from JSON file."""
        try:
            with open(input_file, 'r') as f:
                config = json.load(f)
            return config
        except Exception as e:
            print(f"Error loading input config: {str(e)}")
            return {}
    
    def process_documents(self, pdf_directory: str, persona: str, 
                         job_to_be_done: str) -> Dict:
        """Main processing pipeline."""
        start_time = time.time()
        
        # Step 1: Retrieve and rank relevant sections
        print("Extracting and ranking document sections...")
        ranked_sections = self.retrieval_engine.retrieve_relevant_sections(
            pdf_directory, persona, job_to_be_done, top_k=10
        )
        
        if not ranked_sections:
            print("No sections found or processed successfully.")
            return self.create_empty_output(pdf_directory, persona, job_to_be_done)
        
        # Step 2: Format extracted sections for output
        extracted_sections = self.retrieval_engine.format_extracted_sections(
            ranked_sections[:5]  # Take top 5 for output
        )
        
        # Step 3: Create subsection analysis
        print("Creating subsection analysis...")
        subsection_analysis = self.summarizer.create_subsection_analysis(
            ranked_sections, persona, job_to_be_done
        )
        
        # Step 4: Get list of input documents
        input_documents = [f for f in os.listdir(pdf_directory) 
                          if f.lower().endswith('.pdf')]
        
        # Step 5: Create output JSON
        output = {
            "metadata": {
                "input_documents": input_documents,
                "persona": persona,
                "job_to_be_done": job_to_be_done,
                "processing_timestamp": datetime.now().isoformat()
            },
            "extracted_sections": extracted_sections,
            "subsection_analysis": subsection_analysis
        }
        
        processing_time = time.time() - start_time
        print(f"Processing completed in {processing_time:.2f} seconds")
        
        return output
    
    def create_empty_output(self, pdf_directory: str, persona: str, 
                           job_to_be_done: str) -> Dict:
        """Create empty output structure when no sections are found."""
        input_documents = [f for f in os.listdir(pdf_directory) 
                          if f.lower().endswith('.pdf')]
        
        return {
            "metadata": {
                "input_documents": input_documents,
                "persona": persona,
                "job_to_be_done": job_to_be_done,
                "processing_timestamp": datetime.now().isoformat()
            },
            "extracted_sections": [],
            "subsection_analysis": []
        }
    
    def save_output(self, output: Dict, output_file: str):
        """Save output to JSON file."""
        try:
            with open(output_file, 'w') as f:
                json.dump(output, f, indent=4, ensure_ascii=False)
            print(f"Output saved to {output_file}")
        except Exception as e:
            print(f"Error saving output: {str(e)}")

def main():
    """Main function to run the document intelligence system."""
    if len(sys.argv) != 4:
        print("Usage: python main.py <input_json> <pdf_directory> <output_json>")
        print("Example: python main.py 'Collection 1/challenge1b_input.json' 'Collection 1/PDFs/' 'Collection 1/challenge1b_output.json'")
        sys.exit(1)
    
    input_file = sys.argv[1]
    pdf_directory = sys.argv[2]
    output_file = sys.argv[3]
    
    # Validate inputs
    if not os.path.exists(input_file):
        print(f"Error: Input file {input_file} not found")
        sys.exit(1)
    
    if not os.path.exists(pdf_directory):
        print(f"Error: PDF directory {pdf_directory} not found")
        sys.exit(1)
    
    # Initialize system
    system = DocumentIntelligenceSystem()
    
    # Load input configuration
    config = system.load_input_config(input_file)
    if not config:
        print("Failed to load input configuration")
        sys.exit(1)
    
    # Extract persona and job from config
    persona = config.get('persona', {}).get('role', '')
    job_to_be_done = config.get('job_to_be_done', {}).get('task', '')
    
    if not persona or not job_to_be_done:
        print("Error: Persona role and job_to_be_done task are required in input JSON")
        sys.exit(1)
    
    print(f"Processing documents for persona: {persona}")
    print(f"Job to be done: {job_to_be_done}")
    print(f"PDF directory: {pdf_directory}")
    
    # Process documents
    try:
        output = system.process_documents(pdf_directory, persona, job_to_be_done)
        system.save_output(output, output_file)
        print("Processing completed successfully!")
    except Exception as e:
        print(f"Error during processing: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()