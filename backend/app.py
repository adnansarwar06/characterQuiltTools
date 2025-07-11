"""
FastAPI backend for deep research agent project.

This module provides the main application with a streaming chat endpoint
that accepts user messages and configuration, returning dummy streaming responses.
"""

import json
import asyncio
import logging
from typing import List, Dict, Any, AsyncGenerator
from dataclasses import dataclass

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware

from config import AppConfig


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@dataclass
class Message:
    """Represents a chat message with role and content."""
    role: str
    content: str


@dataclass
class ChatRequest:
    """Request model for the chat endpoint."""
    messages: List[Dict[str, str]]
    tools: List[str]
    deep_research_mode: bool


@dataclass
class ChatResponse:
    """Response model for the chat endpoint."""
    status: str
    message: str


def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application.
    
    Returns:
        FastAPI: Configured FastAPI application instance.
    """
    config = AppConfig()
    
    app = FastAPI(
        title="Deep Research Agent API",
        description="API for streaming chat responses with research capabilities",
        version="1.0.0",
        debug=config.debug_mode
    )
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    @app.post("/chat")
    async def chat_endpoint(request_data: Dict[str, Any]) -> StreamingResponse:
        """
        Stream a dummy response for chat messages.
        
        Args:
            request_data: Dictionary containing messages, tools, and research mode.
            
        Returns:
            StreamingResponse: Character-by-character streaming response.
            
        Raises:
            HTTPException: If request validation fails.
        """
        try:
            # Validate required fields
            if not isinstance(request_data, dict):
                raise HTTPException(status_code=400, detail="Request must be a JSON object")
            
            if "messages" not in request_data:
                raise HTTPException(status_code=400, detail="Missing required field: messages")
            
            if "tools" not in request_data:
                raise HTTPException(status_code=400, detail="Missing required field: tools")
            
            if "deep_research_mode" not in request_data:
                raise HTTPException(status_code=400, detail="Missing required field: deep_research_mode")
            
            # Create ChatRequest object
            request = ChatRequest(
                messages=request_data["messages"],
                tools=request_data["tools"],
                deep_research_mode=request_data["deep_research_mode"]
            )
            
            logger.info(f"Received chat request with {len(request.messages)} messages")
            logger.info(f"Tools enabled: {request.tools}")
            logger.info(f"Deep research mode: {request.deep_research_mode}")
            
            # Validate messages format
            for i, message in enumerate(request.messages):
                if not isinstance(message, dict) or "role" not in message or "content" not in message:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Invalid message format at index {i}. Expected {{role, content}}"
                    )
            
            # Generate streaming response
            return StreamingResponse(
                generate_streaming_response(request),
                media_type="text/plain"
            )
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")
    
    @app.get("/health")
    async def health_check() -> Dict[str, str]:
        """
        Health check endpoint.
        
        Returns:
            Dict[str, str]: Health status.
        """
        return {"status": "healthy"}
    
    return app


async def generate_streaming_response(request: ChatRequest) -> AsyncGenerator[str, None]:
    """
    Generate a streaming dummy response character by character.
    
    Args:
        request: ChatRequest containing the user's message and configuration.
        
    Yields:
        str: Individual characters of the response message.
    """
    # Get the last user message
    user_messages = [msg for msg in request.messages if msg.get("role") == "user"]
    last_message = user_messages[-1]["content"] if user_messages else "Hello"
    
    # Create dummy response
    response_parts = [
        "Thank you for your message: ",
        f'"{last_message}"',
        "\n\nI understand you have ",
        f"{len(request.tools)} tools enabled" if request.tools else "no tools enabled",
        " and deep research mode is ",
        "ON" if request.deep_research_mode else "OFF",
        ".\n\nThis is a streaming dummy response that will help test the real-time communication between the frontend and backend. ",
        "In the actual implementation, this would be replaced with calls to language models and research tools."
    ]
    
    full_response = "".join(response_parts)
    
    # Stream character by character with small delays
    for char in full_response:
        yield char
        await asyncio.sleep(0.05)  # Small delay between characters


# Create the app instance
app = create_app()

if __name__ == "__main__":
    import uvicorn
    
    config = AppConfig()
    uvicorn.run(
        "app:app",
        host=config.host,
        port=config.port,
        reload=config.debug_mode,
        log_level="info"
    )

# Test payload for verification:
# curl -X POST "http://localhost:8000/chat" \
#      -H "Content-Type: application/json" \
#      -d '{
#        "messages": [
#          {"role": "user", "content": "Hello, how are you?"},
#          {"role": "assistant", "content": "I am doing well, thank you!"},
#          {"role": "user", "content": "Can you help me with research?"}
#        ],
#        "tools": ["web_search", "code_analysis"],
#        "deep_research_mode": true
#      }' 