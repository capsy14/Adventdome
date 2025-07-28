#!/bin/bash

# Check if collection number is provided
if [ $# -eq 0 ]; then
    echo "Usage: ./run_collection.sh [1|2|3|all]"
    echo "Example: ./run_collection.sh 1"
    echo "Example: ./run_collection.sh all"
    exit 1
fi

# Build Docker image if it doesn't exist
echo "Ensuring Docker image is built..."
docker build -t document-intelligence . > /dev/null 2>&1

if [ "$1" == "1" ] || [ "$1" == "all" ]; then
    echo "Processing Collection 1 (Travel Planning)..."
    docker run --rm \
        -v "/Users/kabhatt/Downloads/ch_intern1b/Challenge_1b:/app/workspace" \
        -w /app/workspace \
        document-intelligence \
        python main.py \
        "Collection 1/challenge1b_input.json" \
        "Collection 1/PDFs/" \
        "Collection 1/challenge1b_output.json"
fi

if [ "$1" == "2" ] || [ "$1" == "all" ]; then
    echo "Processing Collection 2 (Adobe Acrobat Learning)..."
    docker run --rm \
        -v "/Users/kabhatt/Downloads/ch_intern1b/Challenge_1b:/app/workspace" \
        -w /app/workspace \
        document-intelligence \
        python main.py \
        "Collection 2/challenge1b_input.json" \
        "Collection 2/PDFs/" \
        "Collection 2/challenge1b_output.json"
fi

if [ "$1" == "3" ] || [ "$1" == "all" ]; then
    echo "Processing Collection 3 (Recipe Collection)..."
    docker run --rm \
        -v "/Users/kabhatt/Downloads/ch_intern1b/Challenge_1b:/app/workspace" \
        -w /app/workspace \
        document-intelligence \
        python main.py \
        "Collection 3/challenge1b_input.json" \
        "Collection 3/PDFs/" \
        "Collection 3/challenge1b_output.json"
fi

echo "Processing completed successfully!"