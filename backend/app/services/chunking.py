import re
from typing import List, Dict, Any

class ChunkingService:
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def split_text(self, text: str) -> List[Dict[str, Any]]:
        """
        Splits input text into overlapping chunks.
        Returns a list of dicts containing chunk index, content, and token estimate.
        """
        if not text or not text.strip():
            return []
            
        # Clean text basic whitespace normalization
        clean_text = re.sub(r'\r\n', '\n', text)
        
        chunks = []
        start = 0
        text_length = len(clean_text)
        index = 0

        while start < text_length:
            end = start + self.chunk_size
            
            # If not at the end of text, try to find a natural breakpoint (paragraph/sentence/space)
            if end < text_length:
                # Look for paragraph break near end
                paragraph_break = clean_text.rfind('\n\n', start + self.chunk_size // 2, end)
                if paragraph_break != -1:
                    end = paragraph_break + 2
                else:
                    # Look for sentence break
                    sentence_break = clean_text.rfind('. ', start + self.chunk_size // 2, end)
                    if sentence_break != -1:
                        end = sentence_break + 2
                    else:
                        # Look for space
                        space_break = clean_text.rfind(' ', start + self.chunk_size // 2, end)
                        if space_break != -1:
                            end = space_break + 1

            chunk_str = clean_text[start:end].strip()
            if chunk_str:
                # Rough token estimate: ~4 chars per token
                token_estimate = max(1, len(chunk_str) // 4)
                chunks.append({
                    "chunk_index": index,
                    "content": chunk_str,
                    "token_count": token_estimate
                })
                index += 1

            # Advance start position by step minus overlap
            start = max(start + 1, end - self.chunk_overlap)
            
        return chunks

chunking_service = ChunkingService()
