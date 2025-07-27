# Platform Compatibility Fix

## Issue Analysis

The error you encountered has two components:

1. **Platform Mismatch**: 
   - Your Mac: ARM64 (Apple Silicon)
   - Docker Image: AMD64 (as required by specifications)
   - Warning: `requested image's platform (linux/amd64) does not match detected host platform (linux/arm64/v8)`

2. **Permission Error**:
   - Docker couldn't create mount directories
   - Error: `chown /Users/kabhatt/Downloads/undefined/Challenge_1a/input: permission denied`

## Solutions

### Solution 1: Fix Directory Permissions (Required)

```bash
# Create directories first
mkdir -p input output

# Copy sample data
cp sample_dataset/pdfs/*.pdf input/

# Ensure proper permissions
chmod 755 input output
```

### Solution 2: Platform Specification (Recommended)

Use explicit platform specification to suppress the warning:

```bash
# Build with platform specification
docker build --platform linux/amd64 -t mysolutionname:somerandomidentifier .

# Run with platform specification
docker run --rm \
  --platform linux/amd64 \
  -v $(pwd)/input:/app/input \
  -v $(pwd)/output:/app/output \
  --network none \
  mysolutionname:somerandomidentifier
```

### Solution 3: ARM64 Development Version (Optional)

For local development on Apple Silicon, I can create an ARM64 compatible version:

```bash
# Create ARM64 Dockerfile for development
FROM --platform=linux/arm64 python:3.11-slim
# ... rest of Dockerfile
```

## Updated Test Script

Create and run this test script:

```bash
#!/bin/bash
# test_docker.sh - Fixed version for Apple Silicon Macs

echo "🔧 Setting up directories..."
mkdir -p input output
cp sample_dataset/pdfs/*.pdf input/
chmod 755 input output

echo "🐳 Building Docker image with platform specification..."
docker build --platform linux/amd64 -t pdf-extractor:test .

echo "🚀 Running Docker container with platform specification..."
docker run --rm \
  --platform linux/amd64 \
  -v $(pwd)/input:/app/input \
  -v $(pwd)/output:/app/output \
  --network none \
  pdf-extractor:test

echo "✅ Checking results..."
ls -la output/
echo "Files processed: $(ls output/*.json | wc -l)"
```

## Expected Behavior

### Platform Warning (Safe to Ignore)
```
WARNING: The requested image's platform (linux/amd64) does not match the detected host platform (linux/arm64/v8) and no specific platform was requested
```

**This warning is EXPECTED and SAFE to ignore because:**
- The requirements specify AMD64 architecture
- Docker will run the AMD64 image using emulation
- Performance may be slightly slower but functionality is preserved
- The evaluators will use AMD64 machines where this warning won't appear

### Successful Output
```
PDF Outline Extractor - Production Version
==========================================
Processing 6 PDF files...
✓ file01.pdf -> file01.json (4 headings, 0.05s)
✓ file02.pdf -> file02.json (37 headings, 0.12s)
...
Processing complete!
```

## Production Deployment Note

**For the actual evaluation environment (AMD64 machines), use the original commands without platform specification:**

```bash
# Build (evaluators will use this exact command)
docker build --platform linux/amd64 -t mysolutionname:somerandomidentifier .

# Run (evaluators will use this exact command)
docker run --rm \
  -v $(pwd)/input:/app/input \
  -v $(pwd)/output:/app/output \
  --network none \
  mysolutionname:somerandomidentifier
```

The evaluators won't see the platform warning because they'll be on AMD64 machines.

## Quick Fix Commands

```bash
# 1. Fix permissions
mkdir -p input output
cp sample_dataset/pdfs/*.pdf input/

# 2. Build with platform specification  
docker build --platform linux/amd64 -t mysolutionname:somerandomidentifier .

# 3. Run with platform specification
docker run --rm \
  --platform linux/amd64 \
  -v $(pwd)/input:/app/input \
  -v $(pwd)/output:/app/output \
  --network none \
  mysolutionname:somerandomidentifier
```

## Troubleshooting

### If Docker Performance is Too Slow
```bash
# Enable Docker Rosetta emulation for better ARM64->AMD64 performance
# In Docker Desktop: Settings > General > "Use Rosetta for x86/amd64 emulation"
```

### If Permission Issues Persist
```bash
# Check Docker Desktop settings
# Settings > Resources > File Sharing > Add your project directory
```

### If Mount Issues Continue
```bash
# Use absolute paths
docker run --rm \
  --platform linux/amd64 \
  -v /Users/kabhatt/Downloads/undefined/Challenge_1a/input:/app/input \
  -v /Users/kabhatt/Downloads/undefined/Challenge_1a/output:/app/output \
  --network none \
  mysolutionname:somerandomidentifier
```

## Verification

After running successfully, verify:

```bash
# Check output files exist
ls output/

# Verify JSON format
cat output/file01.json

# Count heading levels
grep -o '"level":"H[123]"' output/*.json | sort | uniq -c
```

The solution remains **100% compliant** with requirements - the platform warning is expected when testing on Apple Silicon but won't occur in the evaluation environment.