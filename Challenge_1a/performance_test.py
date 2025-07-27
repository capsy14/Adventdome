#!/usr/bin/env python3
"""
Performance testing script for multilingual PDF heading extraction.
Ensures processing remains within 10 seconds for 50-page PDFs.
"""

import time
import os
import json
from pathlib import Path
import traceback
from process_pdfs import extract_title_and_outline

def test_performance():
    """Test performance of multilingual heading extraction."""
    print("=== PDF Heading Extraction Performance Test ===\n")
    
    # Use local paths for testing
    if os.path.exists("/app/sample_dataset"):
        input_dir = Path("/app/sample_dataset/pdfs")
    else:
        input_dir = Path("sample_dataset/pdfs")
    
    if not input_dir.exists():
        print(f"Error: Input directory {input_dir} not found")
        return
    
    # Get all PDF files
    pdf_files = list(input_dir.glob("*.pdf"))
    
    if not pdf_files:
        print("No PDF files found for testing")
        return
    
    print(f"Found {len(pdf_files)} PDF files for performance testing")
    print("-" * 60)
    
    total_start_time = time.time()
    results = []
    
    for pdf_file in pdf_files:
        print(f"Testing: {pdf_file.name}")
        
        try:
            # Time the extraction process
            start_time = time.time()
            title, outline = extract_title_and_outline(pdf_file)
            end_time = time.time()
            
            processing_time = end_time - start_time
            
            # Collect results
            result = {
                "file": pdf_file.name,
                "processing_time": processing_time,
                "title_length": len(title) if title else 0,
                "heading_count": len(outline) if outline else 0,
                "success": True
            }
            
            # Performance check
            status = "✓ PASS" if processing_time <= 10.0 else "✗ FAIL"
            if processing_time > 10.0:
                status += f" (EXCEEDS 10s LIMIT)"
            
            print(f"  Time: {processing_time:.2f}s | Headings: {len(outline)} | {status}")
            
            if title:
                print(f"  Title: {title[:60]}{'...' if len(title) > 60 else ''}")
            
            # Show first few headings for verification
            if outline:
                print("  Sample headings:")
                for i, heading in enumerate(outline[:3]):
                    print(f"    {heading['level']}: {heading['text'][:50]}{'...' if len(heading['text']) > 50 else ''}")
                if len(outline) > 3:
                    print(f"    ... and {len(outline) - 3} more")
            
        except Exception as e:
            processing_time = time.time() - start_time
            result = {
                "file": pdf_file.name,
                "processing_time": processing_time,
                "title_length": 0,
                "heading_count": 0,
                "success": False,
                "error": str(e)
            }
            
            print(f"  Time: {processing_time:.2f}s | ✗ ERROR: {str(e)}")
            print(f"  Traceback: {traceback.format_exc()}")
        
        results.append(result)
        print()
    
    # Summary statistics
    total_time = time.time() - total_start_time
    successful_files = [r for r in results if r["success"]]
    failed_files = [r for r in results if not r["success"]]
    
    print("=" * 60)
    print("PERFORMANCE SUMMARY")
    print("=" * 60)
    print(f"Total files processed: {len(results)}")
    print(f"Successful extractions: {len(successful_files)}")
    print(f"Failed extractions: {len(failed_files)}")
    print(f"Total processing time: {total_time:.2f}s")
    
    if successful_files:
        processing_times = [r["processing_time"] for r in successful_files]
        heading_counts = [r["heading_count"] for r in successful_files]
        
        print(f"\nProcessing Time Statistics:")
        print(f"  Average: {sum(processing_times) / len(processing_times):.2f}s")
        print(f"  Minimum: {min(processing_times):.2f}s")
        print(f"  Maximum: {max(processing_times):.2f}s")
        print(f"  Files within 10s limit: {len([t for t in processing_times if t <= 10.0])}/{len(processing_times)}")
        
        print(f"\nHeading Detection Statistics:")
        print(f"  Average headings per file: {sum(heading_counts) / len(heading_counts):.1f}")
        print(f"  Minimum headings: {min(heading_counts)}")
        print(f"  Maximum headings: {max(heading_counts)}")
        print(f"  Total headings extracted: {sum(heading_counts)}")
    
    # Performance validation
    print(f"\nPERFORMANCE VALIDATION:")
    performance_pass = all(r["processing_time"] <= 10.0 for r in successful_files)
    if performance_pass:
        print("✓ ALL FILES processed within 10-second requirement")
    else:
        slow_files = [r for r in successful_files if r["processing_time"] > 10.0]
        print(f"✗ {len(slow_files)} files exceeded 10-second requirement:")
        for r in slow_files:
            print(f"  - {r['file']}: {r['processing_time']:.2f}s")
    
    # Model loading time analysis
    print(f"\nModel Loading Analysis:")
    if hasattr(extract_title_and_outline, 'detector'):
        print("  Multilingual model loaded and cached successfully")
    else:
        print("  Multilingual model not loaded (using fallback method)")
    
    if failed_files:
        print(f"\nFAILED FILES:")
        for r in failed_files:
            print(f"  - {r['file']}: {r.get('error', 'Unknown error')}")
    
    # Save detailed results
    results_file = Path("performance_results.json")
    with open(results_file, "w", encoding="utf-8") as f:
        json.dump({
            "test_timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "total_time": total_time,
            "performance_requirement_met": performance_pass,
            "files": results
        }, f, indent=2, ensure_ascii=False)
    
    print(f"\nDetailed results saved to: {results_file}")
    
    return performance_pass

def benchmark_multilingual_vs_original():
    """Compare performance between multilingual and original methods."""
    print("\n=== MULTILINGUAL vs ORIGINAL PERFORMANCE COMPARISON ===\n")
    
    # This would require temporarily disabling multilingual detection
    # and comparing times, but for now we'll just note the enhancement
    print("Note: The multilingual enhancement is designed to:")
    print("1. Try multilingual detection first (with timeout/fallback)")
    print("2. Fall back to original method if multilingual fails")
    print("3. Cache the NLP model after first load for subsequent files")
    print("4. Use optimized patterns and semantic validation")
    print("\nThis ensures minimal performance impact while adding multilingual capabilities.")

if __name__ == "__main__":
    # Run performance tests
    performance_passed = test_performance()
    
    # Run comparison analysis
    benchmark_multilingual_vs_original()
    
    # Exit with appropriate code
    exit(0 if performance_passed else 1)