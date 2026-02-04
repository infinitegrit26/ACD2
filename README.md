# PDF Chatbot with Google ADK

A professional, production-ready PDF chatbot built with Google Agent Development Kit (ADK), OpenAI models, ChromaDB, and Streamlit. Upload PDFs and interact with them using an intelligent agent that knows when to search documents and when to respond directly.

## 🏗️ Architecture Overview

### System Components

```
┌─────────────────────────────────────────────────────────────┐
│                     Streamlit Frontend                      │
│  • File Upload UI    • Chat Interface    • Stats Display   │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────┐
│                    Google ADK Agent                         │
│  • LiteLlm Connector (OpenAI Bridge)                       │
│  • Smart Routing Logic                                      │
│  • Tool Decision Making                                     │
└────────┬────────────────────────────────┬───────────────────┘
         │                                │
         │ (General Questions)            │ (Document Questions)
         │                                │
         ▼                                ▼
    Direct Response              ┌──────────────────┐
    (No Tool Call)               │  Vector DB Tool  │
                                 └────────┬─────────┘
                                          │
                                          ▼
                            ┌──────────────────────────┐
                            │    ChromaDB (Persistent) │
                            │  • OpenAI Embeddings     │
                            │  • Semantic Search       │
                            │  • Duplicate Detection   │
                            └──────────────────────────┘
```

### Data Flow

#### 1. PDF Upload Flow
```
User Upload PDF
    ↓
Validate PDF (pypdf)
    ↓
Extract Text (pypdf)
    ↓
Chunk Text (RecursiveCharacterTextSplitter)
    ├── chunk_size: 1000 chars
    └── overlap: 200 chars
    ↓
Generate Embeddings (OpenAI text-embedding-3-large)
    ↓
Check for Duplicates (SHA-256 hash)
    ↓
Store in ChromaDB (./chroma_data/)
```

#### 2. Chat Query Flow
```
User Input
    ↓
Google ADK Agent Analyzes Query
    ↓
Decision Point:
    ├─── General Question? ──→ Direct Response (No Tool)
    │    (e.g., "Hello", "What is AI?")
    │
    └─── Document Question? ──→ Use query_vector_db Tool
         (e.g., "What does the doc say about X?")
              ↓
         Generate Query Embedding
              ↓
         Semantic Search in ChromaDB
              ↓
         Retrieve Top-K Chunks
              ↓
         Format Context for Agent
              ↓
         Agent Generates Response
              ↓
         Cites Document Source
```

## 🚀 Features

### Smart Agent Routing
The Google ADK agent is configured with intelligent routing logic:
- **Handles internally**: Greetings, general AI questions, casual conversation
- **Invokes tool**: Questions about uploaded document content only
- **Decision transparency**: User sees "Thinking..." spinner during tool decisions

### Robust PDF Processing
- **Text Extraction**: Uses `pypdf` for reliable PDF parsing
- **Smart Chunking**: Recursive character-based splitting with semantic boundaries
- **Overlap Strategy**: 200-character overlap prevents context loss

### Persistent Vector Storage
- **ChromaDB**: Persistent storage in `./chroma_data/`
- **Duplicate Detection**: SHA-256 hashing prevents re-processing
- **OpenAI Embeddings**: High-quality `text-embedding-3-large` model

### Production Standards
- ✅ Type hints throughout
- ✅ Structured logging (no print statements)
- ✅ Pydantic-based configuration
- ✅ Error handling and validation
- ✅ Modular, testable architecture

## 📁 Project Structure

```
.
├── .env                          # Environment variables
├── .gitignore                    # Git ignore patterns
├── pyproject.toml                # UV package configuration
├── README.md                     # This file
│
└── src/
    ├── main.py                   # Streamlit application entry point
    ├── config.py                 # Pydantic Settings configuration
    │
    ├── agent/
    │   ├── core.py              # Google ADK Agent setup with LiteLlm
    │   └── tools.py             # Vector DB query tool implementation
    │
    ├── database/
    │   └── chroma.py            # ChromaDB client and operations
    │
    └── utils/
        └── pdf_helper.py        # PDF processing and text chunking
```

## 🛠️ Setup Instructions

### Prerequisites
- Python 3.10+
- [uv](https://github.com/astral-sh/uv) package manager
- OpenAI API key

### Installation

1. **Clone and navigate to the project:**
   ```bash
   cd c:\ACD\ACD2
   ```

2. **Install dependencies with uv:**
   ```bash
   uv pip install -e .
   ```

3. **Configure environment variables:**
   Edit `.env` file with your OpenAI API key:
   ```env
   OPENAI_API_KEY=sk-your-actual-key-here
   LLM_MODEL=gpt-4o-mini
   EMBEDDING_MODEL=text-embedding-3-large
   CHROMA_PERSIST_DIRECTORY=./chroma_data
   LOG_LEVEL=INFO
   ```

4. **Run the application:**
   ```bash
   streamlit run src/main.py
   ```

5. **Access the UI:**
   Open your browser to `http://localhost:8501`

## 📖 Usage Guide

### Uploading PDFs
1. Click **"Browse files"** in the sidebar
2. Select one or more PDF files
3. Wait for processing (you'll see chunk count)
4. Files are automatically deduplicated

### Chatting with Documents
**The agent intelligently routes your questions:**

**General questions (no tool call):**
- "Hello!" → Direct greeting
- "What is machine learning?" → Direct explanation
- "Tell me about yourself" → Direct response

**Document questions (uses query_vector_db tool):**
- "What does this document say about X?"
- "Summarize the uploaded PDF"
- "Find information about Y in the documents"

### Understanding Agent Behavior

#### Smart Routing Configuration
In [src/agent/core.py](src/agent/core.py), the agent is configured with:

```python
system_prompt = """You are a helpful AI assistant with access to uploaded PDF documents.

IMPORTANT ROUTING RULES:
1. For general questions, greetings, or conversations about AI/technology 
   that are NOT about the uploaded documents, respond directly WITHOUT using any tools.
2. ONLY use the query_vector_db tool when the user asks questions specifically 
   about content in the uploaded PDFs.
"""
```

#### LiteLlm Integration
The agent uses **Google ADK with LiteLlm** to bridge OpenAI models:

```python
from google.adk.models import LiteLlm

model = LiteLlm(
    model_name=f"openai/{self.config.llm_model}",
    api_key=self.config.openai_api_key
)

agent = Agent(
    model=model,
    system_instruction=system_prompt,
    tools=[query_vector_db_tool]
)
```

This allows seamless use of OpenAI's `gpt-4o-mini` within the Google ADK framework.

## 🔧 Configuration Options

### config.py Settings
| Parameter | Default | Description |
|-----------|---------|-------------|
| `llm_model` | `gpt-4o-mini` | OpenAI model for agent |
| `embedding_model` | `text-embedding-3-large` | OpenAI embedding model |
| `chunk_size` | `1000` | Characters per chunk |
| `chunk_overlap` | `200` | Overlap between chunks |
| `chroma_persist_directory` | `./chroma_data` | Vector DB storage path |

### Customizing Chunking
Edit in [src/utils/pdf_helper.py](src/utils/pdf_helper.py):
```python
self.text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,      # Adjust for your documents
    chunk_overlap=200,    # Adjust for context preservation
    separators=["\n\n", "\n", ". ", " ", ""]  # Customize split priority
)
```

## 🧪 Testing the System

### Test Smart Routing
1. **General Question**: "Hello, how are you?"
   - Expected: Direct response, no tool call
   
2. **Document Question**: "What is the main topic of the document?"
   - Expected: "Thinking..." spinner, uses `query_vector_db`, cites source

### Test Duplicate Detection
1. Upload a PDF file
2. Upload the same file again
3. Expected: "Already processed" message

### Test Edge Cases
- Upload an empty PDF
- Ask questions before uploading any documents
- Upload corrupted files

## 🔍 Logging and Debugging

### View Logs
Logs are output to console with timestamps:
```
2026-02-04 10:30:15 - database.chroma - INFO - ChromaDB initialized with 0 documents
2026-02-04 10:30:20 - agent.core - INFO - PDF Chat Agent initialized successfully
```

### Adjust Log Level
In `.env`:
```env
LOG_LEVEL=DEBUG  # For detailed debugging
LOG_LEVEL=INFO   # For production
```

## 🔐 Security Considerations

- **API Keys**: Never commit `.env` to version control
- **File Validation**: All PDFs are validated before processing
- **Error Handling**: Graceful fallbacks for all operations
- **Input Sanitization**: User inputs are safely handled

## 🚧 Troubleshooting

### Common Issues

**"No module named 'google.adk'"**
```bash
uv pip install google-adk
```

**"OpenAI API key not found"**
- Check `.env` file exists and contains `OPENAI_API_KEY`
- Ensure no spaces around the `=` in `.env`

**"ChromaDB permission error"**
- Ensure `./chroma_data` directory is writable
- Check disk space availability

**"PDF extraction failed"**
- Verify PDF is not password-protected
- Some scanned PDFs may have no extractable text

## 📊 Performance Considerations

### Scaling Recommendations
- **Large PDFs**: Consider increasing `chunk_size` to reduce chunk count
- **Many Files**: ChromaDB scales to millions of vectors
- **Query Speed**: Adjust `n_results` parameter (default: 5)

### Resource Usage
- **Memory**: ~100-500MB depending on loaded documents
- **Disk**: Varies with document count (embeddings stored on disk)
- **API Costs**: 
  - Embeddings: ~$0.13 per 1M tokens
  - LLM queries: ~$0.15-0.60 per 1M tokens (GPT-4o-mini)

## 🤝 Contributing

### Code Standards
- Follow PEP 8 style guidelines
- Add type hints to all functions
- Use structured logging (not print)
- Write docstrings for public APIs

### Testing
```bash
# Run with pytest (once tests are added)
pytest tests/
```

## 📝 License

This project is provided as-is for educational and commercial use.

## 🙏 Acknowledgments

- **Google ADK**: Agent development framework
- **OpenAI**: LLM and embedding models
- **ChromaDB**: Vector database
- **Streamlit**: UI framework
- **pypdf**: PDF processing library

## 📞 Support

For issues or questions:
1. Check the troubleshooting section above
2. Review logs in the console
3. Verify `.env` configuration
4. Ensure all dependencies are installed

---

**Built with ❤️ using Google ADK, OpenAI, and ChromaDB**
