"""
Deep Research Agent LLM Module.

This module implements the core agent loop for the deep research agent system.
It handles LLM interactions, function calling, streaming responses, and tool orchestration.
"""

import json
import asyncio
import logging
from typing import List, Dict, Any, AsyncGenerator, Optional, Union
from dataclasses import dataclass
from enum import Enum

from openai import AsyncOpenAI
from openai.types.chat import ChatCompletion, ChatCompletionChunk

from config import AppConfig
from tools import ToolRegistry, ToolResult

# Configure logging
logger = logging.getLogger(__name__)


class AgentEventType(Enum):
    """Event types for agent streaming."""

    MESSAGE_CHUNK = "message_chunk"
    TOOL_CALL_START = "tool_call_start"
    TOOL_CALL_RESULT = "tool_call_result"
    ITERATION_START = "iteration_start"
    ITERATION_END = "iteration_end"
    AGENT_COMPLETE = "agent_complete"
    ERROR = "error"


@dataclass
class AgentEvent:
    """Represents an event in the agent processing pipeline."""

    event_type: AgentEventType
    data: Any
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class AgentMessage:
    """Represents a message in the agent conversation."""

    role: str
    content: Optional[str] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None
    tool_call_id: Optional[str] = None
    name: Optional[str] = None


@dataclass
class AgentConfig:
    """Configuration for the deep research agent."""

    max_iterations: int = 10
    timeout: int = 300
    temperature: float = 0.7
    max_tokens: int = 4096
    stream_delay: float = 0.01
    model: str = "gpt-4-1106-preview"


class LLMClient:
    """
    LLM client wrapper providing a unified interface for different LLM providers.

    Currently supports OpenAI, but can be extended for other providers like Ollama,
    Anthropic, or local models through LangChain.
    """

    def __init__(self, config: AppConfig):
        """
        Initialize the LLM client.

        Args:
            config: Application configuration instance.
        """
        self.config = config
        self.client = AsyncOpenAI(
            api_key=config.openai_api_key, base_url=config.openai_base_url
        )

    async def create_chat_completion(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        stream: bool = False,
        **kwargs,
    ) -> Union[ChatCompletion, AsyncGenerator[ChatCompletionChunk, None]]:
        """
        Create a chat completion with the LLM.

        Args:
            messages: List of message dictionaries.
            tools: Optional list of tool schemas.
            stream: Whether to stream the response.
            **kwargs: Additional parameters for the completion.

        Returns:
            ChatCompletion or AsyncGenerator of ChatCompletionChunk.
        """
        try:
            completion_params = {
                "model": self.config.llm_model,
                "messages": messages,
                "temperature": self.config.llm_temperature,
                "max_tokens": self.config.llm_max_tokens,
                "stream": stream,
                **kwargs,
            }

            if tools:
                completion_params["tools"] = tools
                completion_params["tool_choice"] = "auto"

            response = await self.client.chat.completions.create(**completion_params)

            if stream:
                return response  # Already an AsyncGenerator when stream=True
            else:
                return response

        except Exception as e:
            logger.error(f"LLM client error: {str(e)}")
            raise

    async def _stream_response(
        self, response: AsyncGenerator[ChatCompletionChunk, None]
    ) -> AsyncGenerator[ChatCompletionChunk, None]:
        """
        Stream response chunks with optional delay.

        Args:
            response: Response stream from the LLM.

        Yields:
            ChatCompletionChunk: Response chunks.
        """
        async for chunk in response:
            yield chunk
            if self.config.streaming_delay > 0:
                await asyncio.sleep(self.config.streaming_delay)


class DeepResearchAgent:
    """
    Deep Research Agent for handling multi-step research tasks.

    This agent orchestrates the interaction between the LLM and various tools,
    maintaining conversation state and handling streaming responses.
    """

    def __init__(self, config: AppConfig, tool_registry: ToolRegistry):
        """
        Initialize the deep research agent.

        Args:
            config: Application configuration.
            tool_registry: Tool registry for executing tools.
        """
        self.config = config
        self.tool_registry = tool_registry
        self.llm_client = LLMClient(config)
        self.agent_config = AgentConfig(
            max_iterations=config.max_research_iterations,
            timeout=config.research_timeout,
            temperature=config.llm_temperature,
            max_tokens=config.llm_max_tokens,
            stream_delay=config.streaming_delay,
            model=config.llm_model,
        )

    async def process_research_request(
        self,
        messages: List[Dict[str, Any]],
        enabled_tools: List[str],
        deep_research_mode: bool = True,
    ) -> AsyncGenerator[AgentEvent, None]:
        """
        Process a research request with the agent loop.

        Args:
            messages: List of conversation messages.
            enabled_tools: List of enabled tool names.
            deep_research_mode: Whether to use deep research mode.

        Yields:
            AgentEvent: Stream of agent events.
        """
        try:
            if not deep_research_mode:
                async for event in self._simple_chat_mode(messages):
                    yield event
                return

            # Get tool schemas for enabled tools
            tool_schemas = self.tool_registry.get_tool_schemas(enabled_tools)

            if not tool_schemas:
                logger.warning("No valid tools available, falling back to simple chat")
                async for event in self._simple_chat_mode(messages):
                    yield event
                return

            # Start the agent loop
            async for event in self._agent_loop(messages, tool_schemas):
                yield event

        except Exception as e:
            logger.error(f"Research agent error: {str(e)}")
            yield AgentEvent(
                event_type=AgentEventType.ERROR,
                data={"error": str(e)},
                metadata={"timestamp": asyncio.get_event_loop().time()},
            )

    async def _simple_chat_mode(
        self, messages: List[Dict[str, Any]]
    ) -> AsyncGenerator[AgentEvent, None]:
        """
        Handle simple chat without tools.

        Args:
            messages: List of conversation messages.

        Yields:
            AgentEvent: Stream of message chunks.
        """
        try:
            response_stream = await self.llm_client.create_chat_completion(
                messages=messages, stream=True
            )

            async for chunk in response_stream:
                if (
                    hasattr(chunk, "choices")
                    and chunk.choices
                    and chunk.choices[0].delta.content is not None
                ):
                    yield AgentEvent(
                        event_type=AgentEventType.MESSAGE_CHUNK,
                        data={"content": chunk.choices[0].delta.content},
                        metadata={
                            "model": getattr(chunk, "model", "unknown"),
                            "chunk_id": getattr(chunk, "id", "unknown"),
                        },
                    )

            yield AgentEvent(
                event_type=AgentEventType.AGENT_COMPLETE,
                data={"mode": "simple_chat"},
                metadata={"timestamp": asyncio.get_event_loop().time()},
            )

        except Exception as e:
            logger.error(f"Simple chat error: {str(e)}")
            yield AgentEvent(
                event_type=AgentEventType.ERROR,
                data={"error": str(e)},
                metadata={"mode": "simple_chat"},
            )

    async def _agent_loop(
        self, messages: List[Dict[str, Any]], tool_schemas: List[Dict[str, Any]]
    ) -> AsyncGenerator[AgentEvent, None]:
        """
        Main agent loop handling LLM <-> tool interactions.

        Args:
            messages: List of conversation messages.
            tool_schemas: List of available tool schemas.

        Yields:
            AgentEvent: Stream of agent events.
        """
        current_messages = messages.copy()
        iterations = 0

        while iterations < self.agent_config.max_iterations:
            iterations += 1

            yield AgentEvent(
                event_type=AgentEventType.ITERATION_START,
                data={"iteration": iterations},
                metadata={"max_iterations": self.agent_config.max_iterations},
            )

            try:
                # Get LLM response
                response = await self.llm_client.create_chat_completion(
                    messages=current_messages, tools=tool_schemas, stream=False
                )

                choice = response.choices[0]
                message = choice.message

                # Add assistant message to conversation
                assistant_message = {
                    "role": "assistant",
                    "content": message.content or "",
                }

                if message.tool_calls:
                    assistant_message["tool_calls"] = [
                        {
                            "id": tc.id,
                            "type": tc.type,
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments,
                            },
                        }
                        for tc in message.tool_calls
                    ]

                current_messages.append(assistant_message)

                # Stream the assistant's response content
                if message.content:
                    for char in message.content:
                        yield AgentEvent(
                            event_type=AgentEventType.MESSAGE_CHUNK,
                            data={"content": char},
                            metadata={"iteration": iterations},
                        )
                        await asyncio.sleep(self.agent_config.stream_delay)

                # Handle tool calls if present
                if message.tool_calls:
                    tool_results = []

                    for tool_call in message.tool_calls:
                        # Signal tool call start
                        yield AgentEvent(
                            event_type=AgentEventType.TOOL_CALL_START,
                            data={
                                "tool_name": tool_call.function.name,
                                "tool_args": json.loads(tool_call.function.arguments),
                                "tool_call_id": tool_call.id,
                            },
                            metadata={"iteration": iterations},
                        )

                        # Execute the tool
                        tool_result = await self.tool_registry.execute_tool(
                            tool_call.function.name,
                            **json.loads(tool_call.function.arguments),
                        )

                        tool_results.append((tool_call.id, tool_result))

                        # Signal tool call result
                        yield AgentEvent(
                            event_type=AgentEventType.TOOL_CALL_RESULT,
                            data={
                                "tool_call_id": tool_call.id,
                                "tool_name": tool_call.function.name,
                                "success": tool_result.success,
                                "result": tool_result.data,
                                "error": tool_result.error,
                            },
                            metadata={"iteration": iterations},
                        )

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

                    # Continue the loop for next iteration
                    yield AgentEvent(
                        event_type=AgentEventType.ITERATION_END,
                        data={"iteration": iterations, "has_tool_calls": True},
                        metadata={"tool_calls_count": len(message.tool_calls)},
                    )
                    continue

                else:
                    # No tool calls, agent is complete
                    yield AgentEvent(
                        event_type=AgentEventType.ITERATION_END,
                        data={"iteration": iterations, "has_tool_calls": False},
                        metadata={"final_iteration": True},
                    )
                    break

            except Exception as e:
                logger.error(f"Agent loop error at iteration {iterations}: {str(e)}")
                yield AgentEvent(
                    event_type=AgentEventType.ERROR,
                    data={"error": str(e), "iteration": iterations},
                    metadata={"recoverable": False},
                )
                break

        yield AgentEvent(
            event_type=AgentEventType.AGENT_COMPLETE,
            data={"total_iterations": iterations, "mode": "deep_research"},
            metadata={"timestamp": asyncio.get_event_loop().time()},
        )


async def deep_research_agent(
    messages: List[Dict[str, Any]],
    enabled_tools: List[str],
    deep_research_mode: bool,
    config: AppConfig,
    tool_registry: ToolRegistry,
) -> AsyncGenerator[str, None]:
    """
    Main entry point for the deep research agent.

    This function creates an agent instance and processes the research request,
    yielding formatted string responses for the API.

    Args:
        messages: List of conversation messages.
        enabled_tools: List of enabled tool names.
        deep_research_mode: Whether to use deep research mode.
        config: Application configuration.
        tool_registry: Tool registry for executing tools.

    Yields:
        str: Formatted response strings for streaming.
    """
    agent = DeepResearchAgent(config, tool_registry)

    try:
        async for event in agent.process_research_request(
            messages, enabled_tools, deep_research_mode
        ):
            formatted_response = _format_agent_event(event)
            if formatted_response:
                yield formatted_response

    except Exception as e:
        logger.error(f"Deep research agent error: {str(e)}")
        yield f"Error: {str(e)}"


def _format_agent_event(event: AgentEvent) -> Optional[str]:
    """
    Format an agent event for streaming response.

    Args:
        event: Agent event to format.

    Returns:
        Optional[str]: Formatted string or None if no output needed.
    """
    if event.event_type == AgentEventType.MESSAGE_CHUNK:
        return event.data.get("content", "")

    elif event.event_type == AgentEventType.TOOL_CALL_START:
        tool_name = event.data.get("tool_name")
        tool_args = event.data.get("tool_args", {})
        args_str = ", ".join(f"{k}={v}" for k, v in tool_args.items())
        return f"\n\n🔧 **Executing Tool:** {tool_name}({args_str})\n"

    elif event.event_type == AgentEventType.TOOL_CALL_RESULT:
        success = event.data.get("success")
        result = event.data.get("result")
        error = event.data.get("error")

        if success:
            result_str = json.dumps(result, indent=2) if result else "Success"
            if len(result_str) > 200:
                result_str = result_str[:200] + "..."
            return f"✅ **Result:** {result_str}\n"
        else:
            return f"❌ **Error:** {error}\n"

    elif event.event_type == AgentEventType.ITERATION_START:
        iteration = event.data.get("iteration")
        return f"\n📋 **Research Iteration {iteration}**\n"

    elif event.event_type == AgentEventType.ERROR:
        error = event.data.get("error")
        return f"\n❌ **Agent Error:** {error}\n"

    # No output needed for other event types
    return None


# Configuration for alternative LLM providers (commented out for reference)
"""
Alternative LLM Provider Integration Examples:

1. Ollama (Local LLM):
   - Install: pip install ollama
   - Usage: Replace OpenAI client with Ollama client
   
2. Anthropic Claude:
   - Install: pip install anthropic
   - Usage: Replace OpenAI client with Anthropic client
   
3. LangChain Integration:
   - Install: pip install langchain
   - Usage: Use LangChain's unified interface for multiple providers
   
4. Hugging Face Transformers:
   - Install: pip install transformers torch
   - Usage: Load local models through transformers library

To integrate these, modify the LLMClient class to support multiple backends
and add provider-specific configuration to AppConfig.
"""
