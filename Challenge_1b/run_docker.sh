#!/bin/bash

# Build the Docker image
echo "Building Docker image..."
docker build -t document-intelligence .

echo "Processing Collection 1..."
docker run --rm -v "/Users/kabhatt/Downloads/ch_intern1b/Challenge_1b:/app/workspace" -w /app/workspace document-intelligence python main.py "Collection 1/challenge1b_input.json" "Collection 1/PDFs/" "Collection 1/challenge1b_output.json"

echo "Processing Collection 2..."
docker run --rm -v "/Users/kabhatt/Downloads/ch_intern1b/Challenge_1b:/app/workspace" -w /app/workspace document-intelligence python main.py "Collection 2/challenge1b_input.json" "Collection 2/PDFs/" "Collection 2/challenge1b_output.json"

echo "Processing Collection 3..."
docker run --rm -v "/Users/kabhatt/Downloads/ch_intern1b/Challenge_1b:/app/workspace" -w /app/workspace document-intelligence python main.py "Collection 3/challenge1b_input.json" "Collection 3/PDFs/" "Collection 3/challenge1b_output.json"

echo "All collections processed successfully!"