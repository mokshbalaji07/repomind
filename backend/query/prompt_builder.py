"""Prompt building and formatting for the RAG (Retrieval-Augmented Generation) pipeline."""
import json
from typing import List, Tuple, Dict, Any

SYSTEM_PROMPT = """You are RepoMind, a code-aware repository assistant. You answer questions about source code repositories.

CRITICAL RULES:
1. You may ONLY answer using the repository context provided below.
2. If the provided context does not contain sufficient evidence to answer the question, you MUST explicitly state: "The available repository context does not contain sufficient evidence to answer this question."
3. NEVER fabricate or invent:
   - File paths that are not in the provided context
   - Function names that are not in the provided context
   - Class names that are not in the provided context
   - Variable names that are not in the provided context
   - Line numbers that are not in the provided context
4. Always cite your sources using the file path, symbol name, and line numbers from the provided context.
5. Clearly distinguish between what the code evidence shows and any inferences you draw.
6. If you can only partially answer the question, state what the evidence shows and what information is missing."""

def build_context(chunks: List[Tuple[Dict[str, Any], float]]) -> str:
    """Build the repository context string from retrieved chunks."""
    context_parts = []
    for i, (metadata, score) in enumerate(chunks, 1):
        file_path = metadata.get('file_path', 'unknown')
        symbol = metadata.get('symbol', 'unknown')
        symbol_type = metadata.get('symbol_type', 'unknown')
        start_line = metadata.get('start_line', '?')
        end_line = metadata.get('end_line', '?')
        language = metadata.get('language', 'text')
        content = metadata.get('content', '')
        
        chunk_str = f"--- Source {i} ---\n"
        chunk_str += f"File: {file_path}\n"
        chunk_str += f"Symbol: {symbol} ({symbol_type})\n"
        chunk_str += f"Lines: {start_line}-{end_line}\n"
        chunk_str += f"Language: {language}\n"
        chunk_str += f"Relevance: {score:.4f}\n\n"
        chunk_str += f"```{language}\n{content}\n```\n"
        
        context_parts.append(chunk_str)
        
    return "\n".join(context_parts)

def build_prompt(question: str, context: str) -> List[Dict[str, Any]]:
    """Build the prompt messages for the Gemini API."""
    text_content = f"{SYSTEM_PROMPT}\n\nREPOSITORY CONTEXT:\n{context}\n\nQUESTION: {question}"
    return [{"role": "user", "parts": [{"text": text_content}]}]

def build_insufficient_evidence_response(question: str, repo: str) -> str:
    """Return a response stating insufficient evidence."""
    return "The available repository context does not contain sufficient evidence to answer this question."

def format_sources(chunks: List[Tuple[Dict[str, Any], float]]) -> List[Dict[str, Any]]:
    """Format the sources for the API response."""
    sources = []
    for metadata, score in chunks:
        source = {
            'file_path': metadata.get('file_path', ''),
            'symbol': metadata.get('symbol', ''),
            'symbol_type': metadata.get('symbol_type', ''),
            'start_line': metadata.get('start_line'),
            'end_line': metadata.get('end_line'),
            'repo': metadata.get('repo', ''),
            'commit_sha': metadata.get('commit_sha', ''),
            'relevance_score': score
        }
        sources.append(source)
    return sources
