import re
from typing import List, Dict, Any

class TokenOptimizer:
    """
    Simulates token optimization strategies like 'Headroom' and 'Toonify'.
    Reduces token usage by compressing context and removing redundancy.
    """

    @staticmethod
    def compress_context(context: str, aggressive: bool = False) -> str:
        """
        Compresses text context by removing stop words (heuristic) and redundant whitespace.
        In a real implementation, this would use semantic compression or a smaller model.
        """
        if not context:
            return ""

        # Basic whitespace normalization
        compressed = re.sub(r'\s+', ' ', context).strip()

        if aggressive:
            # Remove common stop words for aggressive compression (simulated)
            stop_words = {'the', 'is', 'at', 'which', 'on', 'a', 'an', 'and', 'or', 'but'}
            words = compressed.split()
            compressed = ' '.join([w for w in words if w.lower() not in stop_words])

        return compressed

    @staticmethod
    def optimize_message_history(messages: List[Dict[str, str]], max_tokens: int = 1000) -> List[Dict[str, str]]:
        """
        Truncates or summarizes message history to fit within a token limit.
        Simple FIFO approach for now, but could be enhanced with summarization.
        """
        optimized = []
        current_tokens = 0
        
        # Reverse to keep most recent
        for msg in reversed(messages):
            content = msg.get('content', '')
            # Rough token estimate: 1 token ~= 4 chars
            tokens = len(content) // 4
            
            if current_tokens + tokens > max_tokens:
                break
            
            optimized.insert(0, msg)
            current_tokens += tokens
            
        return optimized

    @staticmethod
    def toonify_format(prompt: str) -> str:
        """
        Formats prompt in a 'TOON' style (simulated) which is a concise,
        structured format that some models process more efficiently.
        """
        # Example simulation: Convert verbose sentences to bullet points or JSON-like structure
        return f"TASK: {prompt}\nMODE: Concise\nOUTPUT: JSON"
