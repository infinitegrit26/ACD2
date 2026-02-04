"""PDF processing and text chunking utilities."""
import logging
from typing import List, Dict
from io import BytesIO

from pypdf import PdfReader

from src.config import get_config

logger = logging.getLogger(__name__)


class RecursiveCharacterTextSplitter:
    """Splits text recursively by different characters to create semantic chunks."""
    
    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        separators: List[str] = None
    ):
        """Initialize the text splitter.
        
        Args:
            chunk_size: Maximum size of each chunk
            chunk_overlap: Number of characters to overlap between chunks
            separators: List of separators to split on, in order of priority
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.separators = separators or ["\n\n", "\n", ". ", " ", ""]
    
    def split_text(self, text: str) -> List[str]:
        """Split text into chunks recursively.
        
        Args:
            text: The text to split
            
        Returns:
            List of text chunks
        """
        return self._split_text(text, self.separators)
    
    def _split_text(self, text: str, separators: List[str]) -> List[str]:
        """Recursively split text using available separators."""
        final_chunks = []
        
        # Get the separator to use
        separator = separators[-1]
        new_separators = []
        
        for i, sep in enumerate(separators):
            if sep == "":
                separator = sep
                break
            if sep in text:
                separator = sep
                new_separators = separators[i + 1:]
                break
        
        # Split the text
        splits = text.split(separator) if separator else list(text)
        
        # Merge splits into chunks
        good_splits = []
        for split in splits:
            if len(split) < self.chunk_size:
                good_splits.append(split)
            else:
                if good_splits:
                    merged = self._merge_splits(good_splits, separator)
                    final_chunks.extend(merged)
                    good_splits = []
                
                # If we have more separators, recursively split
                if new_separators:
                    other_chunks = self._split_text(split, new_separators)
                    final_chunks.extend(other_chunks)
                else:
                    # Just chunk by size
                    final_chunks.extend(self._chunk_by_size(split))
        
        # Handle remaining splits
        if good_splits:
            merged = self._merge_splits(good_splits, separator)
            final_chunks.extend(merged)
        
        return final_chunks
    
    def _merge_splits(self, splits: List[str], separator: str) -> List[str]:
        """Merge splits into chunks of appropriate size."""
        chunks = []
        current_chunk = []
        current_length = 0
        
        for split in splits:
            split_len = len(split)
            
            if current_length + split_len + len(separator) <= self.chunk_size:
                current_chunk.append(split)
                current_length += split_len + len(separator)
            else:
                if current_chunk:
                    chunk_text = separator.join(current_chunk)
                    if chunk_text:
                        chunks.append(chunk_text)
                
                current_chunk = [split]
                current_length = split_len
        
        # Add the last chunk
        if current_chunk:
            chunk_text = separator.join(current_chunk)
            if chunk_text:
                chunks.append(chunk_text)
        
        return self._add_overlap(chunks, separator)
    
    def _add_overlap(self, chunks: List[str], separator: str) -> List[str]:
        """Add overlap between chunks."""
        if len(chunks) <= 1 or self.chunk_overlap == 0:
            return chunks
        
        overlapped_chunks = []
        for i, chunk in enumerate(chunks):
            if i == 0:
                overlapped_chunks.append(chunk)
            else:
                # Get overlap from previous chunk
                prev_chunk = chunks[i - 1]
                overlap_text = prev_chunk[-self.chunk_overlap:]
                overlapped_chunk = overlap_text + separator + chunk
                overlapped_chunks.append(overlapped_chunk)
        
        return overlapped_chunks
    
    def _chunk_by_size(self, text: str) -> List[str]:
        """Chunk text by size when no separators work."""
        chunks = []
        for i in range(0, len(text), self.chunk_size - self.chunk_overlap):
            chunk = text[i:i + self.chunk_size]
            if chunk:
                chunks.append(chunk)
        return chunks


class PDFProcessor:
    """Processes PDF files and extracts text."""
    
    def __init__(self):
        """Initialize PDF processor with config."""
        self.config = get_config()
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.config.chunk_size,
            chunk_overlap=self.config.chunk_overlap
        )
    
    def extract_text_from_pdf(self, pdf_file: BytesIO, filename: str) -> str:
        """Extract text from a PDF file.
        
        Args:
            pdf_file: PDF file as BytesIO object
            filename: Name of the PDF file
            
        Returns:
            Extracted text as a single string
        """
        try:
            reader = PdfReader(pdf_file)
            text_parts = []
            
            for page_num, page in enumerate(reader.pages, 1):
                text = page.extract_text()
                if text.strip():
                    text_parts.append(text)
                    logger.debug(f"Extracted text from page {page_num} of {filename}")
            
            full_text = "\n\n".join(text_parts)
            logger.info(
                f"Extracted {len(full_text)} characters from {len(reader.pages)} pages"
            )
            
            return full_text
            
        except Exception as e:
            logger.error(f"Error extracting text from PDF {filename}: {e}")
            raise
    
    def process_pdf(
        self,
        pdf_file: BytesIO,
        filename: str
    ) -> tuple[List[str], List[Dict]]:
        """Process a PDF file into chunks with metadata.
        
        Args:
            pdf_file: PDF file as BytesIO object
            filename: Name of the PDF file
            
        Returns:
            Tuple of (text_chunks, metadata_list)
        """
        try:
            # Extract text
            full_text = self.extract_text_from_pdf(pdf_file, filename)
            
            if not full_text.strip():
                logger.warning(f"No text extracted from {filename}")
                return [], []
            
            # Split into chunks
            chunks = self.text_splitter.split_text(full_text)
            logger.info(f"Split {filename} into {len(chunks)} chunks")
            
            # Create metadata for each chunk
            metadatas = [
                {
                    "source": filename,
                    "chunk_index": i,
                    "total_chunks": len(chunks),
                    "chunk_size": len(chunk)
                }
                for i, chunk in enumerate(chunks)
            ]
            
            return chunks, metadatas
            
        except Exception as e:
            logger.error(f"Error processing PDF {filename}: {e}")
            raise
    
    def validate_pdf(self, pdf_file: BytesIO) -> bool:
        """Validate if the file is a valid PDF.
        
        Args:
            pdf_file: PDF file as BytesIO object
            
        Returns:
            True if valid, False otherwise
        """
        try:
            reader = PdfReader(pdf_file)
            # Try to access pages to validate
            _ = len(reader.pages)
            pdf_file.seek(0)  # Reset file pointer
            return True
        except Exception as e:
            logger.error(f"Invalid PDF file: {e}")
            return False
