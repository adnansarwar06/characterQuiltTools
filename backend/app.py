"""
FastAPI backend for deep research agent project.

This module provides the main application with OpenAI integration,
function calling capabilities, and deep research mode with streaming responses.
"""

import json
import asyncio
import logging
from typing import List, Dict, Any, AsyncGenerator, Optional
from dataclasses import dataclass

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from openai import AsyncOpenAI

from config import AppConfig
from tools import get_tool_registry, ToolResult

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@dataclass
class Message:
    """Represents a chat message with role and content."""

    role: str
    content: str
    tool_calls: Optional[List[Dict[str, Any]]] = None
    tool_call_id: Optional[str] = None


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


class ResearchAgent:
    """
    Deep research agent that uses OpenAI function calling with tools.

    Handles the research loop, tool execution, and streaming responses.
    """

    def __init__(self, config: AppConfig):
        """
        Initialize the research agent.

        Args:
            config: Application configuration.
        """
        self.config = config
        self.client = AsyncOpenAI(
            api_key=config.openai_api_key, base_url=config.openai_base_url
        )
        self.tool_registry = get_tool_registry(config)

    async def process_chat(self, request: ChatRequest) -> AsyncGenerator[str, None]:
        """
        Process a chat request with optional deep research mode.

        Args:
            request: Chat request containing messages and configuration.

        Yields:
            str: Streaming response chunks.
        """
        try:
            # Convert request messages to OpenAI format
            messages = self._convert_messages(request.messages)

            if request.deep_research_mode and request.tools:
                # Use deep research mode with function calling
                async for chunk in self._deep_research_mode(messages, request.tools):
                    yield chunk
            else:
                # Simple chat without tools
                async for chunk in self._simple_chat(messages):
                    yield chunk

        except Exception as e:
            logger.error(f"Error processing chat: {str(e)}")
            yield f"Error: {str(e)}"

    def _convert_messages(self, messages: List[Dict[str, str]]) -> List[Dict[str, Any]]:
        """
        Convert request messages to OpenAI format.

        Args:
            messages: List of message dictionaries.

        Returns:
            List[Dict[str, Any]]: OpenAI-formatted messages.
        """
        converted = []
        for msg in messages:
            converted.append({"role": msg["role"], "content": msg["content"]})
        return converted

    async def _simple_chat(
        self, messages: List[Dict[str, Any]]
    ) -> AsyncGenerator[str, None]:
        """
        Process a simple chat without tools.

        Args:
            messages: List of OpenAI-formatted messages.

        Yields:
            str: Streaming response chunks.
        """
        try:
            stream = await self.client.chat.completions.create(
                model=self.config.llm_model,
                messages=messages,
                temperature=self.config.llm_temperature,
                max_tokens=self.config.llm_max_tokens,
                stream=True,
            )

            async for chunk in stream:
                if chunk.choices[0].delta.content is not None:
                    yield chunk.choices[0].delta.content

        except Exception as e:
            logger.error(f"Error in simple chat: {str(e)}")
            yield f"Error: {str(e)}"

    async def _deep_research_mode(
        self, messages: List[Dict[str, Any]], enabled_tools: List[str]
    ) -> AsyncGenerator[str, None]:
        """
        Process chat with deep research mode and function calling.

        Args:
            messages: List of OpenAI-formatted messages.
            enabled_tools: List of enabled tool names.

        Yields:
            str: Streaming response chunks.
        """
        try:
            # Get tool schemas for enabled tools
            tool_schemas = self.tool_registry.get_tool_schemas(enabled_tools)

            if not tool_schemas:
                yield "No valid tools available. Falling back to simple chat mode.\n\n"
                async for chunk in self._simple_chat(messages):
                    yield chunk
                return

            current_messages = messages.copy()
            iterations = 0

            while iterations < self.config.max_research_iterations:
                iterations += 1

                # Send request to OpenAI with tools
                response = await self.client.chat.completions.create(
                    model=self.config.llm_model,
                    messages=current_messages,
                    tools=tool_schemas,
                    tool_choice="auto",
                    temperature=self.config.llm_temperature,
                    max_tokens=self.config.llm_max_tokens,
                )

                choice = response.choices[0]
                message = choice.message

                # Add assistant message to conversation
                current_messages.append(
                    {
                        "role": "assistant",
                        "content": message.content or "",
                        "tool_calls": (
                            [tc.dict() for tc in message.tool_calls]
                            if message.tool_calls
                            else None
                        ),
                    }
                )

                # Stream the assistant's response
                if message.content:
                    for char in message.content:
                        yield char
                        await asyncio.sleep(0.01)  # Small delay for streaming effect

                # Check if there are tool calls to execute
                if message.tool_calls:
                    yield "\n\n🔧 **Tool Calls:**\n"

                    for tool_call in message.tool_calls:
                        tool_name = tool_call.function.name
                        tool_args = json.loads(tool_call.function.arguments)

                        yield f"- Executing {tool_name}({', '.join(f'{k}={v}' for k, v in tool_args.items())})\n"

                        # Execute the tool
                        tool_result = await self.tool_registry.execute_tool(
                            tool_name, **tool_args
                        )

                        # Format tool result
                        if tool_result.success:
                            result_content = json.dumps(tool_result.data, indent=2)
                            yield f"  ✅ Success: {result_content[:200]}{'...' if len(result_content) > 200 else ''}\n"
                        else:
                            yield f"  ❌ Error: {tool_result.error}\n"

                        # Add tool result to conversation
                        current_messages.append(
                            {
                                "role": "tool",
                                "content": json.dumps(
                                    {
                                        "success": tool_result.success,
                                        "data": tool_result.data,
                                        "error": tool_result.error,
                                        "metadata": tool_result.metadata,
                                    }
                                ),
                                "tool_call_id": tool_call.id,
                            }
                        )

                    yield "\n"

                    # Continue the conversation with tool results
                    continue
                else:
                    # No tool calls, we're done
                    break

            if iterations >= self.config.max_research_iterations:
                yield f"\n\n⚠️ Reached maximum research iterations ({self.config.max_research_iterations})"

        except Exception as e:
            logger.error(f"Error in deep research mode: {str(e)}")
            yield f"\n\nError in deep research mode: {str(e)}"


def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application.

    Returns:
        FastAPI: Configured FastAPI application instance.
    """
    config = AppConfig()

    # Validate configuration
    try:
        config.validate_config()
    except ValueError as e:
        logger.error(f"Configuration validation failed: {e}")
        raise

    app = FastAPI(
        title="Deep Research Agent API",
        description="API for streaming chat responses with research capabilities",
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

    # Initialize research agent
    research_agent = ResearchAgent(config)

    @app.post("/chat")
    async def chat_endpoint(request_data: Dict[str, Any]) -> StreamingResponse:
        """
        Stream chat responses with optional deep research mode and tool usage.

        Args:
            request_data: Dictionary containing messages, tools, and research mode.

        Returns:
            StreamingResponse: Streaming response with LLM output and tool results.

        Raises:
            HTTPException: If request validation fails.
        """
        try:
            # Validate required fields
            if not isinstance(request_data, dict):
                raise HTTPException(
                    status_code=400, detail="Request must be a JSON object"
                )

            if "messages" not in request_data:
                raise HTTPException(
                    status_code=400, detail="Missing required field: messages"
                )

            if "tools" not in request_data:
                raise HTTPException(
                    status_code=400, detail="Missing required field: tools"
                )

            if "deep_research_mode" not in request_data:
                raise HTTPException(
                    status_code=400, detail="Missing required field: deep_research_mode"
                )

            # Create ChatRequest object
            request = ChatRequest(
                messages=request_data["messages"],
                tools=request_data["tools"],
                deep_research_mode=request_data["deep_research_mode"],
            )

            logger.info(f"Received chat request with {len(request.messages)} messages")
            logger.info(f"Tools enabled: {request.tools}")
            logger.info(f"Deep research mode: {request.deep_research_mode}")

            # Validate messages format
            for i, message in enumerate(request.messages):
                if (
                    not isinstance(message, dict)
                    or "role" not in message
                    or "content" not in message
                ):
                    raise HTTPException(
                        status_code=400,
                        detail=f"Invalid message format at index {i}. Expected {{role, content}}",
                    )

            # Process chat request
            return StreamingResponse(
                research_agent.process_chat(request), media_type="text/plain"
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
        return {"status": "healthy", "version": "1.0.0"}

    @app.get("/tools")
    async def list_tools() -> Dict[str, List[str]]:
        """
        List available tools.

        Returns:
            Dict[str, List[str]]: Available tools.
        """
        tool_registry = get_tool_registry(config)
        return {
            "available_tools": list(tool_registry.tools.keys()),
            "configured_tools": config.available_tools,
        }

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
        log_level="info",
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
