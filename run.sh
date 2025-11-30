#!/bin/bash
# Startup script for Adaptive Lecture Summarizer with Local Whisper

echo "🎓 Starting Adaptive Lecture Summarizer..."
echo "📦 Using Python 3.13 virtual environment with local Whisper"
echo ""

# Activate virtual environment
source venv/bin/activate

# Start the application
echo "🚀 Starting server on http://localhost:8000"
echo "💡 Note: First audio transcription will download the Whisper base model (~74MB)"
echo ""

python3 main.py
