"""
Async LLM API call utility using OpenRouter
"""

import asyncio
import os
import httpx
from typing import List, Dict
from loguru import logger

# Configure logger (only if not already configured)
if not any("api_calls.log" in str(handler._sink) for handler in logger._core.handlers.values()):
    logger.add("logs/api_calls.log", rotation="50 MB", retention="3 days")

async def llm_call(model_name: str, messages: List[Dict[str, str]], call_type: str = "general") -> str:
    """
    Make an async API call to OpenRouter
    
    Args:
        model_name: The model to use (e.g., "openai/gpt-4o-mini")
        messages: List of message dicts with "role" and "content"
        call_type: Type of call for logging ("main_response", "evaluation", "prompt_analysis", etc.)
        
    Returns:
        The response content as a string
        
    Raises:
        Exception: If API call fails or returns empty response
    """
    
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise Exception("OPENROUTER_API_KEY not found in environment variables")
    
    if call_type == "main_response":
        system_prompt = next((msg["content"] for msg in messages if msg["role"] == "system"), "")
        user_query = next((msg["content"] for msg in messages if msg["role"] == "user"), "")
        logger.info(f"MAIN_CALL | Model: {model_name}")
        logger.info(f"SYSTEM_PROMPT: {system_prompt}")
        logger.info(f"USER_QUERY: {user_query}")
    elif call_type == "evaluation":
        eval_content = next((msg["content"] for msg in messages if msg["role"] == "user"), "")
        logger.info(f"EVAL_CALL | Model: {model_name}")
        logger.info(f"EVALUATION_PROMPT: {eval_content}")
    else:
        system_prompt = next((msg["content"] for msg in messages if msg["role"] == "system"), "")
        user_query = next((msg["content"] for msg in messages if msg["role"] == "user"), "")
        logger.info(f"API_CALL | Type: {call_type} | Model: {model_name} | System: {system_prompt[:100]}... | User: {user_query[:100]}...")
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": model_name,
        "messages": messages
    }
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            response = await client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                json=payload
            )
            response.raise_for_status()
            
            data = response.json()
            
            # Extract content
            if "choices" not in data or len(data["choices"]) == 0:
                raise Exception("No choices in API response")
            
            content = data["choices"][0]["message"]["content"]
            
            if not content or content.strip() == "":
                raise Exception("Empty response from API")
            
            # Structured response logging
            if call_type == "main_response":
                logger.info(f"MAIN_RESPONSE: {content}")
            elif call_type == "evaluation":
                logger.info(f"EVALUATION_RESULT: {content}")
            else:
                logger.info(f"API_RESPONSE | Type: {call_type}: {content}")
            
            return content.strip()
            
        except httpx.HTTPStatusError as e:
            error_msg = f"HTTP error {e.response.status_code}: {e.response.text}"
            logger.error(f"API_ERROR | {error_msg}")
            raise Exception(error_msg)
        except Exception as e:
            logger.error(f"API_ERROR | {str(e)}")
            raise Exception(f"API call failed: {str(e)}")