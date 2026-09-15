import json
import os
import random
import urllib.request
import urllib.error
import time
import base64
import boto3

from common.config import (
    AWS_REGION, 
    GEMINI_API_KEY_SSM_PARAM, 
    MAX_REQUEST_SIZE, 
    GEMINI_ANSWER_MODEL, 
    ANSWER_MAX_RETRIES
)
# Note: Since models was imported but standard validation is handled inline, we assume basic structure if not explicitly needed
# from common.models import QueryRequest, QueryResponse, SourceReference
from common.logger import get_logger
from common.embeddings import GeminiEmbeddingClient
from common.vector_store import VectorStore

from query.retriever import Retriever
from query.prompt_builder import (
    build_context, 
    build_prompt, 
    build_insufficient_evidence_response, 
    format_sources, 
    SYSTEM_PROMPT
)

logger = get_logger('query')

# SSM + cached keys
_ssm = None
_gemini_key = None

def _get_ssm():
    global _ssm
    if _ssm is None:
        _ssm = boto3.client('ssm', region_name=AWS_REGION)
    return _ssm

def _get_gemini_key():
    global _gemini_key
    if _gemini_key is None:
        resp = _get_ssm().get_parameter(Name=GEMINI_API_KEY_SSM_PARAM, WithDecryption=True)
        _gemini_key = resp['Parameter']['Value']
    return _gemini_key

def call_gemini_answer(api_key: str, messages: list) -> str:
    """Call Gemini answer model."""
    url = f'https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_ANSWER_MODEL}:generateContent?key={api_key}'
    
    payload = json.dumps({'contents': messages}).encode('utf-8')
    
    for attempt in range(ANSWER_MAX_RETRIES + 1):
        try:
            req = urllib.request.Request(url, data=payload, headers={'Content-Type': 'application/json'}, method='POST')
            with urllib.request.urlopen(req, timeout=60) as resp:
                result = json.loads(resp.read().decode('utf-8'))
                candidates = result.get('candidates', [])
                if candidates:
                    parts = candidates[0].get('content', {}).get('parts', [])
                    if parts:
                        return parts[0].get('text', 'No answer generated.')
                return 'No answer generated.'
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < ANSWER_MAX_RETRIES:
                retry_after = int(e.headers.get('Retry-After', 2 ** attempt))
                time.sleep(retry_after + random.uniform(0, 1))
                continue
            if e.code >= 500 and attempt < ANSWER_MAX_RETRIES:
                time.sleep(2 ** attempt)
                continue
            raise
    return 'Failed to generate answer after retries.'

def cors_response(status_code: int, body) -> dict:
    """Return a response with CORS headers."""
    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'POST, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type',
        },
        'body': json.dumps(body) if isinstance(body, dict) else body,
    }

def handler(event, context):
    """Lambda Function URL handler."""
    # Handle CORS preflight
    if event.get('requestContext', {}).get('http', {}).get('method') == 'OPTIONS':
        return cors_response(200, '')
    
    try:
        # Parse and validate request
        body = event.get('body', '')
        if event.get('isBase64Encoded'):
            body = base64.b64decode(body).decode('utf-8')
        
        if len(body) > MAX_REQUEST_SIZE:
            return cors_response(413, {'error': 'Request too large'})
        
        try:
            data = json.loads(body)
        except (json.JSONDecodeError, TypeError):
            return cors_response(400, {'error': 'Invalid JSON'})
        
        # Validate required fields
        repo = data.get('repo', '').strip()
        question = data.get('question', '').strip()
        
        if not repo:
            return cors_response(400, {'error': 'Missing required field: repo'})
        if not question:
            return cors_response(400, {'error': 'Missing required field: question'})
        if len(question) > 2000:
            return cors_response(400, {'error': 'Question too long (max 2000 chars)'})
        
        # Validate repo format (owner/name)
        if '/' not in repo or len(repo.split('/')) != 2:
            return cors_response(400, {'error': 'Invalid repo format. Use owner/name'})
        
        # Initialize clients
        gemini_key = _get_gemini_key()
        embedding_client = GeminiEmbeddingClient(api_key=gemini_key)
        vector_store = VectorStore()
        retriever = Retriever(vector_store, embedding_client)
        
        # Retrieve relevant chunks
        results = retriever.retrieve(repo, question)
        
        if not results:
            answer = build_insufficient_evidence_response(question, repo)
            return cors_response(200, {'answer': answer, 'sources': [], 'repo': repo, 'question': question})
        
        # Build context and call Gemini for answer
        context_str = build_context(results)
        messages = build_prompt(question, context_str)
        
        answer = call_gemini_answer(gemini_key, messages)
        sources = format_sources(results)
        
        return cors_response(200, {
            'answer': answer,
            'sources': sources,
            'repo': repo,
            'question': question
        })
    
    except Exception as e:
        logger.error(f'Query failed: {type(e).__name__}: {e}', exc_info=True)
        return cors_response(500, {'error': 'Internal server error'})
