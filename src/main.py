"""Streamlit UI for PDF Chatbot with Google ADK Agent."""
import logging
from io import BytesIO

import streamlit as st

from src.config import get_config
from src.database.chroma import ChromaDBClient
from src.agent.core import create_agent
from src.utils.pdf_helper import PDFProcessor

# Configure logging
logger = logging.getLogger(__name__)


def initialize_session_state():
    """Initialize Streamlit session state variables."""
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    if "chroma_client" not in st.session_state:
        with st.spinner("Initializing vector database..."):
            st.session_state.chroma_client = ChromaDBClient()
    
    if "agent" not in st.session_state:
        with st.spinner("Loading AI agent..."):
            st.session_state.agent = create_agent(st.session_state.chroma_client)
    
    if "pdf_processor" not in st.session_state:
        st.session_state.pdf_processor = PDFProcessor()
    
    if "uploaded_files" not in st.session_state:
        st.session_state.uploaded_files = set()


def render_sidebar():
    """Render the sidebar with file upload and statistics."""
    with st.sidebar:
        st.title("📚 PDF Chatbot")
        st.markdown("---")
        
        # File upload section
        st.subheader("Upload PDF Documents")
        uploaded_file = st.file_uploader(
            "Choose a PDF file",
            type=["pdf"],
            help="Upload a PDF document to chat with"
        )
        
        if uploaded_file is not None:
            handle_pdf_upload(uploaded_file)
        
        st.markdown("---")
        
        # Database statistics
        st.subheader("📊 Database Stats")
        stats = st.session_state.chroma_client.get_stats()
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Total Chunks", stats.get("total_chunks", 0))
        with col2:
            st.metric("Unique Files", stats.get("unique_files", 0))
        
        # Agent information
        st.markdown("---")
        st.subheader("🤖 Agent Info")
        agent_stats = st.session_state.agent.get_stats()
        st.info(f"**Model:** {agent_stats['model']}")
        st.info(f"**Embeddings:** {agent_stats['embedding_model']}")
        
        # Clear conversation button
        st.markdown("---")
        if st.button("🗑️ Clear Conversation", use_container_width=True):
            st.session_state.messages = []
            st.rerun()
        
        # Reset database button (with confirmation)
        with st.expander("⚠️ Danger Zone"):
            st.warning("This will delete all uploaded documents!")
            if st.button("Reset Database", type="secondary"):
                st.session_state.chroma_client.reset_database()
                st.session_state.uploaded_files = set()
                st.session_state.messages = []
                st.success("Database reset successfully!")
                st.rerun()


def handle_pdf_upload(uploaded_file):
    """Handle PDF file upload and processing.
    
    Args:
        uploaded_file: Streamlit UploadedFile object
    """
    filename = uploaded_file.name
    
    # Check if already processed
    if filename in st.session_state.uploaded_files:
        st.info(f"ℹ️ {filename} is already uploaded")
        return
    
    with st.spinner(f"Processing {filename}..."):
        try:
            # Read file content
            file_content = uploaded_file.read()
            pdf_file = BytesIO(file_content)
            
            # Validate PDF
            if not st.session_state.pdf_processor.validate_pdf(pdf_file):
                st.error(f"❌ Invalid PDF file: {filename}")
                return
            
            # Reset file pointer
            pdf_file.seek(0)
            
            # Check if already in database
            if st.session_state.chroma_client.is_file_processed(filename, file_content):
                st.warning(f"⚠️ {filename} has already been processed")
                st.session_state.uploaded_files.add(filename)
                return
            
            # Process PDF
            pdf_file.seek(0)
            chunks, metadatas = st.session_state.pdf_processor.process_pdf(
                pdf_file, filename
            )
            
            if not chunks:
                st.error(f"❌ No text could be extracted from {filename}")
                return
            
            # Add to vector database
            num_chunks = st.session_state.chroma_client.add_documents(
                texts=chunks,
                metadatas=metadatas,
                filename=filename,
                file_content=file_content
            )
            
            if num_chunks > 0:
                st.success(f"✅ Successfully processed {filename} ({num_chunks} chunks)")
                st.session_state.uploaded_files.add(filename)
                
                # Add system message
                st.session_state.messages.append({
                    "role": "system",
                    "content": f"📄 Uploaded: {filename} ({num_chunks} chunks)"
                })
                st.rerun()
            else:
                st.warning(f"⚠️ {filename} was already in the database")
                
        except Exception as e:
            st.error(f"❌ Error processing {filename}: {str(e)}")
            logger.error(f"Error processing PDF: {e}", exc_info=True)


def render_chat_interface():
    """Render the main chat interface."""
    st.title("💬 Chat with Your PDFs")
    
    # Display chat messages
    for message in st.session_state.messages:
        if message["role"] == "system":
            with st.chat_message("assistant", avatar="📄"):
                st.info(message["content"])
        else:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
    
    # Chat input
    if prompt := st.chat_input("Ask a question about your documents..."):
        # Add user message
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Get agent response
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                try:
                    response = st.session_state.agent.chat(prompt)
                    st.markdown(response)
                    
                    # Add to message history
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": response
                    })
                    
                except Exception as e:
                    error_msg = f"I apologize, but I encountered an error: {str(e)}"
                    st.error(error_msg)
                    logger.error(f"Error in chat: {e}", exc_info=True)


def main():
    """Main application entry point."""
    # Page configuration
    st.set_page_config(
        page_title="PDF Chatbot - Google ADK",
        page_icon="📚",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Custom CSS
    st.markdown("""
        <style>
        .stChatMessage {
            padding: 1rem;
            border-radius: 0.5rem;
        }
        .stSpinner > div {
            text-align: center;
            color: #1f77b4;
        }
        </style>
    """, unsafe_allow_html=True)
    
    try:
        # Initialize configuration
        config = get_config()
        logger.info("Application started")
        
        # Initialize session state
        initialize_session_state()
        
        # Render UI components
        render_sidebar()
        render_chat_interface()
        
    except Exception as e:
        st.error(f"❌ Failed to initialize application: {str(e)}")
        logger.error(f"Application initialization error: {e}", exc_info=True)
        st.stop()


if __name__ == "__main__":
    main()
