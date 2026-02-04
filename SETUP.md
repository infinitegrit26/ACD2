# Installation & Setup Guide

## Table of Contents
1. [Prerequisites](#prerequisites)
2. [Installation Methods](#installation-methods)
3. [Configuration](#configuration)
4. [Running the Application](#running-the-application)
5. [Verification](#verification)

---

## Prerequisites

### Required
- **Python 3.10 or higher**
  ```bash
  python --version  # Should show 3.10+
  ```

- **OpenAI API Key**
  - Sign up at https://platform.openai.com/
  - Generate an API key from the dashboard
  - Ensure you have credits available

### Optional but Recommended
- **uv package manager** (faster than pip)
  ```bash
  # Install uv
  pip install uv
  ```

---

## Installation Methods

### Method 1: Using UV (Recommended)

1. **Navigate to project directory:**
   ```bash
   cd c:\ACD\ACD2
   ```

2. **Install dependencies:**
   ```bash
   uv pip install -e .
   ```

3. **Configure environment:**
   - Edit `.env` file with your OpenAI API key (see Configuration section)

4. **Run application:**
   ```bash
   streamlit run src\main.py
   ```

### Method 2: Using pip

1. **Create virtual environment:**
   ```bash
   python -m venv .venv
   ```

2. **Activate virtual environment:**
   
   **Windows:**
   ```bash
   .venv\Scripts\activate
   ```
   
   **Linux/Mac:**
   ```bash
   source .venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
   or 
   
    ```bash
   uv pip install -e
   ```

4. **Configure environment:**
   - Edit `.env` file with your OpenAI API key

5. **Run application:**
   ```bash
   streamlit run src\main.py
   ```

---

## Configuration

### 1. OpenAI API Key Setup

Edit the `.env` file in the project root:

```env
# Required: Your OpenAI API key
OPENAI_API_KEY=sk-proj-xxxxxxxxxxxxxxxxxxxxx

# Optional: Customize models
LLM_MODEL=gpt-4o-mini
EMBEDDING_MODEL=text-embedding-3-large

# Optional: Customize paths
CHROMA_PERSIST_DIRECTORY=./chroma_data

# Optional: Logging
LOG_LEVEL=INFO
```

### 2. Verify Configuration

Run a quick check:
```bash
python -c "from src.config import get_config; c = get_config(); print('✅ Config loaded successfully')"
```

---

## Running the Application

### Standard Launch
```bash
streamlit run src\main.py
```

### Custom Port
```bash
streamlit run src\main.py --server.port 8502
```

### Headless Mode (Server)
```bash
streamlit run src\main.py --server.headless true
```

### Development Mode (Auto-reload)
```bash
streamlit run src\main.py --server.runOnSave true
```

---

## Verification

### 1. Check Browser Access
After running, open:
```
http://localhost:8501
```

### 2. Test Basic Functionality

**Test 1: General Question (No Tool)**
```
User: "Hello, how are you?"
Expected: Direct greeting response without tool usage
```

**Test 2: Upload PDF**
- Click "Browse files" in sidebar
- Upload a sample PDF
- Verify: "✅ Successfully processed [filename] (X chunks)"

**Test 3: Document Query (With Tool)**
```
User: "What is this document about?"
Expected: "Thinking..." spinner, then response citing the document
```

### 3. Verify Database Persistence

1. Upload a PDF file
2. Close the application
3. Restart the application
4. Check sidebar stats - uploaded file should still be there
5. Try uploading the same file - should see "already processed" message

---

## Troubleshooting

### Issue: "No module named 'google.adk'"

**Solution:**
```bash
pip install google-adk
```

### Issue: "OpenAI API key not found"

**Solution:**
1. Verify `.env` file exists in project root
2. Check no spaces around `=` in `.env`
3. Ensure key starts with `sk-`
4. Restart the application

### Issue: "ChromaDB directory not writable"

**Solution:**
```bash
# Windows
mkdir chroma_data
icacls chroma_data /grant %username%:F

# Linux/Mac
mkdir -p chroma_data
chmod 755 chroma_data
```

### Issue: "Port 8501 already in use"

**Solution:**
```bash
# Kill existing Streamlit processes
# Windows:
taskkill /F /IM streamlit.exe

# Linux/Mac:
pkill -f streamlit

# Or use a different port:
streamlit run src\main.py --server.port 8502
```

### Issue: Import errors with relative imports

**Solution:**
Make sure you're running from the project root:
```bash
cd c:\ACD\ACD2
streamlit run src\main.py
```

Or set PYTHONPATH:
```bash
# Windows
set PYTHONPATH=%CD%

# Linux/Mac
export PYTHONPATH=$(pwd)
```

---

## Development Setup

### Install Development Dependencies

```bash
pip install pytest black ruff
```

### Run Code Formatting

```bash
black src/
```

### Run Linting

```bash
ruff check src/
```

### Run Tests (when available)

```bash
pytest tests/
```

---

## Environment Variables Reference

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `OPENAI_API_KEY` | Yes | - | Your OpenAI API key |
| `LLM_MODEL` | No | `gpt-4o-mini` | OpenAI model for the agent |
| `EMBEDDING_MODEL` | No | `text-embedding-3-large` | OpenAI embedding model |
| `CHROMA_PERSIST_DIRECTORY` | No | `./chroma_data` | ChromaDB storage location |
| `LOG_LEVEL` | No | `INFO` | Logging verbosity (DEBUG/INFO/WARNING/ERROR) |

---

## Next Steps

After successful installation:

1. **Upload a test PDF** - Try a simple document first
2. **Test general questions** - Verify smart routing works
3. **Test document queries** - Ensure tool invocation works
4. **Check persistence** - Restart app and verify data remains
5. **Review logs** - Check console for any warnings

---

## Getting Help

If you encounter issues:

1. Check this guide's troubleshooting section
2. Review the main [README.md](README.md)
3. Check application logs in the console
4. Verify all prerequisites are met
5. Ensure `.env` is properly configured

---

**Ready to start? Run:** `streamlit run src\main.py`
