"""
FastAPI backend for deep research agent project.

This module provides the main application with clean separation of concerns,
using the modular deep research agent from llm.py for all LLM operations.
"""

import json
import logging
from datetime import datetime
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
    async def chat_endpoint(
        request: Request, request_data: Dict[str, Any]
    ) -> StreamingResponse:
        """
        Chat endpoint that handles both simple chat and deep research mode.

        Args:
            request: FastAPI request object to check for client disconnection.
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

            # Validate tool names against available tools
            available_tools = list(tool_registry.tool_schemas.keys())
            invalid_tools = [tool for tool in tools if tool not in available_tools]
            if invalid_tools:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid tools: {invalid_tools}. Available tools: {available_tools}",
                )

            # Validate deep_research_mode
            if not isinstance(deep_research_mode, bool):
                raise HTTPException(
                    status_code=400, detail="deep_research_mode must be a boolean"
                )

            # Validate message content length
            max_content_length = (
                config.max_request_size // 4
            )  # Reserve space for other data
            for i, message in enumerate(messages):
                if (
                    message.get("content")
                    and len(message["content"]) > max_content_length
                ):
                    raise HTTPException(
                        status_code=400,
                        detail=f"Message {i} content exceeds maximum length of {max_content_length} characters",
                    )

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
                        request=request,  # Pass request for cancellation checking
                    ):
                        # Check if client has disconnected before yielding chunk
                        if await request.is_disconnected():
                            logger.info(
                                "Client disconnected, stopping response generation"
                            )
                            break
                        yield chunk
                except Exception as e:
                    logger.error(f"Error in chat generation: {str(e)}")
                    # Only yield error if client is still connected
                    if not await request.is_disconnected():
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
    async def health_check() -> Dict[str, Any]:
        """
        Health check endpoint with enhanced diagnostics.

        Returns:
            Dict[str, Any]: Health status with diagnostics.
        """
        try:
            # Check if tool registry is accessible
            available_tools = list(tool_registry.tool_schemas.keys())

            # Check if configuration is valid
            config.validate_config()

            # Return healthy status with diagnostics
            return {
                "status": "healthy",
                "service": "deep-research-agent",
                "version": "1.0.0",
                "tools_available": len(available_tools),
                "model": config.llm_model,
                "timestamp": datetime.now().isoformat(),
            }
        except Exception as e:
            logger.error(f"Health check failed: {str(e)}", exc_info=True)
            return {
                "status": "unhealthy",
                "service": "deep-research-agent",
                "version": "1.0.0",
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            }

    @app.get("/tools")
    async def list_tools() -> Dict[str, Any]:
        """
        List available tools.

        Returns:
            Dict[str, Any]: Available tools and their descriptions.
        """
        try:
            available_tools = list(tool_registry.tool_schemas.keys())
            return {
                "available_tools": available_tools,
                "total_count": len(available_tools),
                "timestamp": datetime.now().isoformat(),
            }
        except Exception as e:
            logger.error(f"Failed to list tools: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=500, detail=f"Failed to retrieve tool information: {str(e)}"
            )

    @app.get("/config")
    async def get_config() -> Dict[str, Any]:
        """
        Get application configuration for the frontend.

        Returns:
            Dict[str, Any]: Configuration data including API key and model settings.
        """
        try:
            return {
                "status": "ok",
                "config": {
                    "api_key": config.api_key,
                    "model": config.llm_model,
                    "temperature": config.llm_temperature,
                    "max_tokens": config.llm_max_tokens,
                    "available_tools": list(tool_registry.tool_schemas.keys()),
                },
                "timestamp": datetime.now().isoformat(),
            }
        except Exception as e:
            logger.error(f"Error getting config: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to get configuration")

    @app.get("/api-key")
    async def get_api_key() -> Dict[str, str]:
        """
        Get OpenAI API key for frontend direct streaming.

        Returns:
            Dict[str, str]: API key for OpenAI.
        """
        try:
            return {
                "api_key": config.api_key,
                "model": config.llm_model,
            }
        except Exception as e:
            logger.error(f"Error getting API key: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to get API key")

    @app.exception_handler(Exception)
    async def global_exception_handler(
        request: Request, exc: Exception
    ) -> HTTPException:
        """
        Global exception handler for unhandled exceptions.

        Args:
            request: FastAPI request object.
            exc: The exception that occurred.

        Returns:
            HTTPException: Error response.
        """
        error_id = f"error_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        logger.error(
            f"Unhandled exception [{error_id}]: {str(exc)}",
            exc_info=True,
            extra={
                "error_id": error_id,
                "request_url": str(request.url),
                "request_method": request.method,
                "exception_type": type(exc).__name__,
            },
        )

        # Return different error messages based on debug mode
        if config.debug_mode:
            detail = f"Internal server error [{error_id}]: {str(exc)}"
        else:
            detail = f"Internal server error [{error_id}]. Please contact support."

        return HTTPException(status_code=500, detail=detail)

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
