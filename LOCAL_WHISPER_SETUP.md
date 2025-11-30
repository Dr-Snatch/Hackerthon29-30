# Local Whisper Setup Complete! 🎉

Your Adaptive Lecture Summarizer is now configured for **100% cost-free** audio transcription using local Whisper with Python 3.13.

## ✅ What's Been Configured

1. **Python 3.13 Installed** - via Homebrew at `/opt/homebrew/bin/python3.13`
2. **Virtual Environment Created** - Located at `venv/` with Python 3.13
3. **All Dependencies Installed** - Including:
   - openai-whisper (local transcription)
   - torch & torchaudio (ML framework)
   - FastAPI, Anthropic, and all other required packages
4. **Environment Configured** - `.env` set to `WHISPER_MODE=local`
5. **FFmpeg Ready** - Already installed (version 8.0.1)

## 🚀 How to Run

### Option 1: Using the Startup Script (Recommended)
```bash
./run.sh
```

### Option 2: Manual Start
```bash
source venv/bin/activate
python3 main.py
```

### Option 3: Using Uvicorn
```bash
source venv/bin/activate
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Then open: **http://localhost:8000**

## 📊 Performance Expectations (M4 Mac)

With your M4 Mac and the `base` Whisper model:

- **1 minute audio** → ~5-10 seconds transcription
- **10 minutes audio** → ~45-60 seconds transcription
- **30 minutes audio** → ~2-3 minutes transcription

Your M4's Metal GPU will provide 4-8x speedup compared to CPU-only transcription!

## 🎯 First Run - Model Download

On your **first audio transcription**, Whisper will:
- Download the `base` model (~74MB)
- Save it to: `~/.cache/whisper/base.pt`
- Takes ~30-60 seconds depending on internet speed
- **Subsequent transcriptions will be instant** (model is cached)

## 💰 Cost Comparison

### Local Mode (Your Setup) ✅
- **Cost:** $0.00 forever
- **Speed:** Excellent on M4 (45-60 sec for 10 min audio)
- **Privacy:** Complete - audio never leaves your machine
- **Internet:** Only needed for first model download

### API Mode (Alternative)
- **Cost:** $0.006/minute = $0.36/hour = $3.60/10 hours
- **Speed:** Similar to local mode
- **Privacy:** Audio sent to OpenAI
- **Internet:** Required for every transcription

## 🎨 Features Available

### PDF Upload
- ✅ Drag & drop or browse for PDF files
- ✅ Extract text from text-based PDFs
- ✅ Preview extracted content
- ✅ 50MB file size limit

### Audio Transcription
- ✅ Drag & drop or browse for audio files
- ✅ Supports MP3, WAV, M4A formats
- ✅ Transcribe with local Whisper (base model)
- ✅ 200MB file size limit
- ✅ 10 languages supported:
  - English, Spanish, French, German, Chinese
  - Japanese, Arabic, Hindi, Portuguese, Russian

### AI-Powered Features
- ✅ Adaptive summaries (5 knowledge levels)
- ✅ Interactive Q&A about content
- ✅ Personalized quizzes
- ✅ Multilingual interface

## 🔧 Whisper Model Options

You're currently using the **base** model (recommended for M4). To change:

1. Edit `.env`:
   ```bash
   WHISPER_MODEL_SIZE=small  # or tiny, medium, large
   ```

2. Restart the server

### Model Comparison:
- **tiny** (39MB) - Fastest, lower accuracy
- **base** (74MB) - ⭐ **RECOMMENDED** - Best balance
- **small** (244MB) - Better accuracy, ~2x slower
- **medium** (769MB) - High accuracy, ~4x slower
- **large** (1.5GB) - Best accuracy, ~8x slower

## 🐛 Troubleshooting

### "Module not found" errors
```bash
# Make sure virtual environment is activated
source venv/bin/activate
```

### Slow transcription
- Check that you're using the virtual environment (Python 3.13)
- Ensure WHISPER_MODE=local in .env
- Try a smaller model (tiny or base)

### "FFmpeg not found"
```bash
# Should not happen as FFmpeg is installed, but if needed:
brew install ffmpeg
ffmpeg -version
```

### Need to switch back to API mode
Edit `.env`:
```bash
WHISPER_MODE=api  # Uses OpenAI API (costs $0.006/min)
```

## 📝 Testing Your Setup

1. Start the server: `./run.sh`
2. Open: http://localhost:8000
3. Click "Upload Audio" tab
4. Upload a short audio file (MP3/WAV/M4A)
5. Wait for transcription (first time downloads model)
6. See transcribed text appear!
7. Click "Generate Summary" to test the full pipeline

## 🎓 Example Workflow

1. **Upload a lecture recording** (audio or PDF)
2. **Select your knowledge level** (beginner to expert)
3. **Generate an adaptive summary**
4. **Ask questions** about the content
5. **Take a quiz** to test your understanding

All powered by AI, all running locally (except Claude API for summarization), no transcription costs!

## 💡 Tips

- **Audio Quality:** Clear recordings transcribe better than noisy ones
- **PDF Quality:** Text-based PDFs work best (not scanned images)
- **Model Size:** Base model is perfect for lectures and educational content
- **Batch Processing:** Upload multiple files by switching between tabs
- **Language Selection:** Change language in top-right selector before uploading audio

## 🆘 Need Help?

- Check [SETUP.md](SETUP.md) for full documentation
- Review [requirements.txt](requirements.txt) for dependencies
- Verify `.env` configuration
- Check server logs for error messages

Enjoy your cost-free, privacy-focused lecture summarizer! 🚀
