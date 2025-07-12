"""
FastAPI backend for deep research agent project.

This module provides the main application with clean separation of concerns,
using the modular deep research agent from llm.py for all LLM operations.
"""

import json
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware

from config import AppConfig
from tools import get_tool_registry
from llm import deep_research_agent

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


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
        FastAPI: Configured application instance.
    """
    config = AppConfig()

    # Validate configuration
    try:
        config.validate_config()
    except ValueError as e:
        logger.error(f"Configuration validation failed: {e}")
        raise

    # Initialize tool registry
    tool_registry = get_tool_registry(config)

    # Create FastAPI app
    app = FastAPI(
        title="Deep Research Agent API",
        description="Production-ready API for deep research agent with modular LLM integration",
        version="1.0.0",
        debug=config.debug_mode,
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
        Chat endpoint that handles both simple chat and deep research mode.

        Args:
            request_data: Request data containing messages, tools, and mode.

        Returns:
            StreamingResponse: Streaming response with chat content.
        """
        try:
            # Validate request data
            if not isinstance(request_data, dict):
                raise HTTPException(
                    status_code=400, detail="Request must be a JSON object"
                )

            messages = request_data.get("messages", [])
            tools = request_data.get("tools", [])
            deep_research_mode = request_data.get("deep_research_mode", False)

            # Validate messages
            if not isinstance(messages, list) or not messages:
                raise HTTPException(
                    status_code=400, detail="Messages must be a non-empty list"
                )

            # Validate message format
            for i, message in enumerate(messages):
                if not isinstance(message, dict):
                    raise HTTPException(
                        status_code=400, detail=f"Message {i} must be an object"
                    )
                if "role" not in message or "content" not in message:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Message {i} must have 'role' and 'content' fields",
                    )
                if message["role"] not in ["user", "assistant", "system"]:
                    raise HTTPException(
                        status_code=400, detail=f"Message {i} has invalid role"
                    )

            # Validate tools
            if not isinstance(tools, list):
                raise HTTPException(status_code=400, detail="Tools must be a list")

            # Convert messages to the format expected by the agent
            formatted_messages = []
            for msg in messages:
                formatted_messages.append(
                    {"role": msg["role"], "content": msg["content"]}
                )

            # Create streaming response
            async def generate_response():
                """Generate streaming response using the deep research agent."""
                try:
                    async for chunk in deep_research_agent(
                        messages=formatted_messages,
                        enabled_tools=tools,
                        deep_research_mode=deep_research_mode,
                        config=config,
                        tool_registry=tool_registry,
                    ):
                        yield chunk
                except Exception as e:
                    logger.error(f"Error in chat generation: {str(e)}")
                    yield f"\n\n❌ **Error:** {str(e)}"

            return StreamingResponse(
                generate_response(),
                media_type="text/plain",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no",  # Disable nginx buffering
                },
            )

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Unexpected error in chat endpoint: {str(e)}")
            raise HTTPException(status_code=500, detail="Internal server error")

    @app.get("/health")
    async def health_check() -> Dict[str, str]:
        """
        Health check endpoint.

        Returns:
            Dict[str, str]: Health status.
        """
        return {
            "status": "healthy",
            "service": "deep-research-agent",
            "version": "1.0.0",
        }

    @app.get("/tools")
    async def list_tools() -> Dict[str, List[str]]:
        """
        List available tools.

        Returns:
            Dict[str, List[str]]: Available tools and their descriptions.
        """
        available_tools = list(tool_registry.tool_schemas.keys())
        return {"available_tools": available_tools, "total_count": len(available_tools)}

    @app.get("/config")
    async def get_config() -> Dict[str, Any]:
        """
        Get current configuration (excluding sensitive data).

        Returns:
            Dict[str, Any]: Configuration details.
        """
        return {
            "model": config.llm_model,
            "max_tokens": config.llm_max_tokens,
            "temperature": config.llm_temperature,
            "max_iterations": config.max_research_iterations,
            "available_tools": config.available_tools,
            "debug_mode": config.debug_mode,
        }

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        """
        Global exception handler for unhandled exceptions.

        Args:
            request: FastAPI request object.
            exc: The exception that occurred.

        Returns:
            JSONResponse: Error response.
        """
        logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
        return HTTPException(status_code=500, detail="Internal server error")

    return app


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
        log_level=config.log_level.lower(),
    )


# Test payloads for verification:
#
# Simple Chat Test:
# curl -X POST "http://localhost:8000/chat" \
#      -H "Content-Type: application/json" \
#      -d '{
#        "messages": [{"role": "user", "content": "Hello, how are you?"}],
#        "tools": [],
#        "deep_research_mode": false
#      }'
#
# Deep Research with Web Search:
# curl -X POST "http://localhost:8000/chat" \
#      -H "Content-Type: application/json" \
#      -d '{
#        "messages": [{"role": "user", "content": "Research the latest developments in AI and write a summary to a file"}],
#        "tools": ["web_search", "file_write"],
#        "deep_research_mode": true
#      }'
#
# Weather Query (using Open-Meteo - free, no API key needed):
# curl -X POST "http://localhost:8000/chat" \
#      -H "Content-Type: application/json" \
#      -d '{
#        "messages": [{"role": "user", "content": "What is the weather like in London?"}],
#        "tools": ["weather"],
#        "deep_research_mode": true
#      }'
#
# Multi-tool Research:
# curl -X POST "http://localhost:8000/chat" \
#      -H "Content-Type: application/json" \
#      -d '{
#        "messages": [{"role": "user", "content": "Search for information about climate change, get the weather for 3 major cities, and write a report"}],
#        "tools": ["web_search", "weather", "file_write"],
#        "deep_research_mode": true
#      }'
