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

    max_iterations: int
    timeout: int
    temperature: float
    max_tokens: int
    stream_delay: float
    model: str


# Deep Research System Prompt with ReAct Pattern
DEEP_RESEARCH_SYSTEM_PROMPT = """You are an expert research assistant with access to various tools. When conducting deep research, you must follow this structured approach:

1. **Think**: Analyze the question and plan your approach step by step
2. **Act**: Use available tools to gather information when needed
3. **Observe**: Review the results and determine next steps
4. **Repeat**: Continue this cycle until you have sufficient information

Format your responses as follows:
- Use "Thought: " to show your reasoning and planning
- Use "Action: " only when you need to call a tool (the system will handle the actual tool execution)
- Use "Observation: " to reflect on tool results (this will be added automatically)
- Use "Final Answer: " when you're ready to provide the complete response

Rules:
- Always start with "Thought: " to explain your reasoning
- Break complex questions into smaller investigative steps
- Use multiple tools and iterations as needed
- Don't provide a final answer until you've thoroughly researched the topic
- Be explicit about your reasoning process at each step

Available tools: {tools}

Remember: Think step by step, act systematically, observe carefully, and only provide your final answer when you're confident you have comprehensive information."""

# Regular Mode System Prompt (unchanged)
REGULAR_MODE_SYSTEM_PROMPT = """You are a helpful research assistant with access to various tools. Provide accurate, helpful responses to user questions. You may use tools when needed to enhance your response, but aim to be concise and direct.

Available tools: {tools}"""

# No Tools System Prompt (unchanged)
NO_TOOLS_SYSTEM_PROMPT = """You are a helpful research assistant. Provide accurate, helpful responses based on your knowledge. You do not have access to external tools, so rely on your training data and reasoning abilities."""


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
        **kwargs: Any,
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

        Raises:
            ValueError: If input validation fails.
            RuntimeError: If API call fails.
            TimeoutError: If request times out.
        """
        try:
            # Validate inputs
            if not messages:
                raise ValueError("Messages list cannot be empty")

            if not all(isinstance(msg, dict) for msg in messages):
                raise ValueError("All messages must be dictionaries")

            if not all("role" in msg and "content" in msg for msg in messages):
                raise ValueError("All messages must have 'role' and 'content' fields")

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

            logger.debug(f"Making LLM request with model: {self.config.llm_model}")
            response = await self.client.chat.completions.create(**completion_params)

            if stream:
                return response  # Already an AsyncGenerator when stream=True
            else:
                return response

        except ValueError as e:
            logger.error(f"LLM input validation error: {str(e)}")
            raise
        except asyncio.TimeoutError as e:
            logger.error(f"LLM request timeout: {str(e)}")
            raise TimeoutError(
                f"LLM request timed out after {self.config.api_timeout} seconds"
            )
        except Exception as e:
            error_type = type(e).__name__
            logger.error(f"LLM client error [{error_type}]: {str(e)}", exc_info=True)
            raise RuntimeError(f"LLM API error: {str(e)}")

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

    def _prepare_messages_with_system_prompt(
        self, messages: List[Dict[str, Any]], system_prompt: str
    ) -> List[Dict[str, Any]]:
        """
        Prepare messages with appropriate system prompt.

        Args:
            messages: Original conversation messages.
            system_prompt: System prompt to add.

        Returns:
            List[Dict[str, Any]]: Messages with system prompt.
        """
        # Check if there's already a system message
        has_system = any(msg.get("role") == "system" for msg in messages)

        if has_system:
            # Replace existing system message
            prepared_messages = []
            for msg in messages:
                if msg.get("role") == "system":
                    prepared_messages.append(
                        {"role": "system", "content": system_prompt}
                    )
                else:
                    prepared_messages.append(msg)
        else:
            # Add system message at the beginning
            prepared_messages = [
                {"role": "system", "content": system_prompt}
            ] + messages

        return prepared_messages

    async def process_research_request(
        self,
        messages: List[Dict[str, Any]],
        enabled_tools: List[str],
        deep_research_mode: bool = True,
        request: Optional[Any] = None,
    ) -> AsyncGenerator[AgentEvent, None]:
        """
        Process a research request with the agent loop.

        Args:
            messages: List of conversation messages.
            enabled_tools: List of enabled tool names.
            deep_research_mode: Whether to use deep research mode.
            request: Optional FastAPI request object for cancellation checking.

        Yields:
            AgentEvent: Stream of agent events.
        """
        try:
            # Get tool schemas for enabled tools
            tool_schemas = self.tool_registry.get_tool_schemas(enabled_tools)

            if deep_research_mode:
                # Deep Research Mode: Multi-step reasoning with tools
                if tool_schemas:
                    # Use deep research mode with tools
                    async for event in self._deep_research_mode(
                        messages, tool_schemas, request
                    ):
                        yield event
                else:
                    # No tools available, use chain-of-thought reasoning without tools
                    async for event in self._deep_research_no_tools_mode(
                        messages, request
                    ):
                        yield event
            else:
                # Regular Mode: Direct answers with at most one tool call
                if tool_schemas:
                    # Use regular mode with tools (at most one tool call)
                    async for event in self._regular_mode_with_tools(
                        messages, tool_schemas, request
                    ):
                        yield event
                else:
                    # No tools available, use direct answer mode
                    async for event in self._regular_mode_no_tools(messages, request):
                        yield event

        except Exception as e:
            logger.error(f"Research agent error: {str(e)}")
            yield AgentEvent(
                event_type=AgentEventType.ERROR,
                data={"error": str(e)},
                metadata={"timestamp": asyncio.get_event_loop().time()},
            )

    async def _deep_research_mode(
        self,
        messages: List[Dict[str, Any]],
        tool_schemas: List[Dict[str, Any]],
        request: Optional[Any] = None,
    ) -> AsyncGenerator[AgentEvent, None]:
        """
        Deep research mode implementing the ReAct pattern (Reason-Act-Observe).
        
        This mode implements an iterative loop where the agent:
        1. Thinks and plans its approach
        2. Acts by using tools when needed
        3. Observes the results
        4. Repeats until reaching a final answer
        
        Args:
            messages: List of conversation messages.
            tool_schemas: List of available tool schemas.
            request: Optional FastAPI request object for cancellation checking.

        Yields:
            AgentEvent: Stream of agent events.
        """
        # Extract tool names for prompt
        tool_names = [tool.get("function", {}).get("name", "unknown") for tool in tool_schemas]
        tools_text = ", ".join(tool_names) if tool_names else "none"
        
        # Prepare messages with deep research system prompt
        system_prompt = DEEP_RESEARCH_SYSTEM_PROMPT.format(tools=tools_text)
        prepared_messages = self._prepare_messages_with_system_prompt(messages, system_prompt)
        
        # Initialize working memory with conversation history
        working_memory = prepared_messages.copy()
        iterations = 0
        
        yield AgentEvent(
            event_type=AgentEventType.ITERATION_START,
            data={"iteration": 0, "mode": "deep_research_start"},
            metadata={"max_iterations": self.agent_config.max_iterations},
        )

        while iterations < self.agent_config.max_iterations:
            iterations += 1
            
            # Check for client disconnection
            if (
                request
                and hasattr(request, "is_disconnected")
                and await request.is_disconnected()
            ):
                logger.info(f"Client disconnected during iteration {iterations}")
                yield AgentEvent(
                    event_type=AgentEventType.AGENT_COMPLETE,
                    data={"total_iterations": iterations - 1, "cancelled": True},
                    metadata={"mode": "deep_research"},
                )
                return

            yield AgentEvent(
                event_type=AgentEventType.ITERATION_START,
                data={"iteration": iterations},
                metadata={"max_iterations": self.agent_config.max_iterations},
            )

            try:
                # Get LLM response with current working memory
                response = await self.llm_client.create_chat_completion(
                    messages=working_memory,
                    tools=tool_schemas,
                    stream=False,
                    temperature=self.agent_config.temperature,
                    max_tokens=self.agent_config.max_tokens,
                )

                if not hasattr(response, "choices") or not response.choices:
                    raise RuntimeError("Invalid LLM response format")

                choice = response.choices[0]
                message = choice.message

                # Handle tool calls
                if message.tool_calls:
                    # Add assistant message with tool calls to working memory
                    assistant_message = {
                        "role": "assistant",
                        "content": message.content or "",
                        "tool_calls": [
                            {
                                "id": tc.id,
                                "type": tc.type,
                                "function": {
                                    "name": tc.function.name,
                                    "arguments": tc.function.arguments,
                                },
                            }
                            for tc in message.tool_calls
                        ],
                    }
                    working_memory.append(assistant_message)
                    
                    # Stream the agent's reasoning if any
                    if message.content and message.content.strip():
                        async for chunk in self._stream_content_chunks(message.content, request):
                            yield AgentEvent(
                                event_type=AgentEventType.MESSAGE_CHUNK,
                                data={"content": chunk},
                                metadata={"iteration": iterations, "type": "reasoning"},
                            )

                    # Execute each tool call
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
                        tool_result = await self._execute_tool_safely(tool_call)

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

                        # Add tool result to working memory
                        tool_message = {
                            "role": "tool",
                            "content": json.dumps({
                                "success": tool_result.success,
                                "data": tool_result.data,
                                "error": tool_result.error,
                            }),
                            "tool_call_id": tool_call.id,
                        }
                        working_memory.append(tool_message)

                    # Continue to next iteration after tool execution
                    yield AgentEvent(
                        event_type=AgentEventType.ITERATION_END,
                        data={"iteration": iterations, "has_tool_calls": True},
                        metadata={"tool_calls_count": len(message.tool_calls)},
                    )
                    continue

                else:
                    # No tool calls - this is reasoning or final answer
                    if message.content:
                        content = message.content.strip()
                        
                        # Check if this is a final answer
                        is_final_answer = (
                            content.lower().startswith("final answer:") or
                            "final answer:" in content.lower() or
                            content.lower().startswith("conclusion:") or
                            iterations >= self.agent_config.max_iterations
                        )
                        
                        if is_final_answer:
                            # This is the final answer - stream it and complete
                            async for chunk in self._stream_content_chunks(content, request):
                                yield AgentEvent(
                                    event_type=AgentEventType.MESSAGE_CHUNK,
                                    data={"content": chunk},
                                    metadata={"iteration": iterations, "final": True},
                                )
                            
                            # Add final message to working memory
                            working_memory.append({
                                "role": "assistant",
                                "content": content,
                            })
                            
                            yield AgentEvent(
                                event_type=AgentEventType.ITERATION_END,
                                data={"iteration": iterations, "final_answer": True},
                                metadata={"final_iteration": True},
                            )
                            break
                        else:
                            # This is intermediate reasoning - add to memory and continue
                            async for chunk in self._stream_content_chunks(content, request):
                                yield AgentEvent(
                                    event_type=AgentEventType.MESSAGE_CHUNK,
                                    data={"content": chunk},
                                    metadata={"iteration": iterations, "type": "reasoning"},
                                )
                            
                            # Add reasoning to working memory
                            working_memory.append({
                                "role": "assistant",
                                "content": content,
                            })
                            
                            yield AgentEvent(
                                event_type=AgentEventType.ITERATION_END,
                                data={"iteration": iterations, "has_reasoning": True},
                                metadata={"reasoning_length": len(content)},
                            )
                            continue
                    else:
                        # Empty response - something went wrong
                        logger.warning(f"Empty response from LLM at iteration {iterations}")
                        break

            except Exception as e:
                logger.error(f"Deep research iteration {iterations} error: {str(e)}")
                yield AgentEvent(
                    event_type=AgentEventType.ERROR,
                    data={"error": str(e), "iteration": iterations},
                    metadata={"mode": "deep_research", "recoverable": True},
                )
                break

        # Complete the agent process
        yield AgentEvent(
            event_type=AgentEventType.AGENT_COMPLETE,
            data={"total_iterations": iterations, "mode": "deep_research"},
            metadata={"timestamp": asyncio.get_event_loop().time()},
        )

    async def _deep_research_no_tools_mode(
        self, messages: List[Dict[str, Any]], request: Optional[Any] = None
    ) -> AsyncGenerator[AgentEvent, None]:
        """
        Deep research mode without tools - chain-of-thought reasoning only.

        Args:
            messages: List of conversation messages.
            request: Optional FastAPI request object for cancellation checking.

        Yields:
            AgentEvent: Stream of agent events.
        """
        # Prepare messages with deep research system prompt
        prepared_messages = self._prepare_messages_with_system_prompt(
            messages, DEEP_RESEARCH_SYSTEM_PROMPT
        )

        try:
            # Check for client disconnection before starting streaming
            if (
                request
                and hasattr(request, "is_disconnected")
                and await request.is_disconnected()
            ):
                logger.info("Client disconnected, stopping deep research no tools mode")
                yield AgentEvent(
                    event_type=AgentEventType.AGENT_COMPLETE,
                    data={"mode": "deep_research_no_tools", "cancelled": True},
                    metadata={"timestamp": asyncio.get_event_loop().time()},
                )
                return

            # Get LLM response with streaming
            response_stream = await self.llm_client.create_chat_completion(
                messages=prepared_messages, stream=True
            )

            async for chunk in response_stream:
                # Check for client disconnection before processing each chunk
                if (
                    request
                    and hasattr(request, "is_disconnected")
                    and await request.is_disconnected()
                ):
                    logger.info(
                        "Client disconnected during streaming, stopping deep research no tools mode"
                    )
                    break

                if (
                    hasattr(chunk, "choices")
                    and chunk.choices
                    and chunk.choices[0].delta.content is not None
                ):
                    content = chunk.choices[0].delta.content
                    
                    if content:
                        # Filter out problematic characters
                        filtered_content = "".join(
                            char
                            for char in content
                            if char.isprintable() or char in "\n\t\r"
                        )

                        if filtered_content:
                            yield AgentEvent(
                                event_type=AgentEventType.MESSAGE_CHUNK,
                                data={"content": filtered_content},
                                metadata={"mode": "deep_research_no_tools"},
                            )

            yield AgentEvent(
                event_type=AgentEventType.AGENT_COMPLETE,
                data={"mode": "deep_research_no_tools"},
                metadata={"timestamp": asyncio.get_event_loop().time()},
            )

        except Exception as e:
            logger.error(f"Deep research no tools error: {str(e)}")
            yield AgentEvent(
                event_type=AgentEventType.ERROR,
                data={"error": str(e)},
                metadata={"mode": "deep_research_no_tools"},
            )

    async def _regular_mode_with_tools(
        self,
        messages: List[Dict[str, Any]],
        tool_schemas: List[Dict[str, Any]],
        request: Optional[Any] = None,
    ) -> AsyncGenerator[AgentEvent, None]:
        """
        Regular mode with tools - direct answer with at most one tool call.
        
        This mode provides efficient, single-step responses with optional tool use.
        Unlike deep research mode, it doesn't iterate but provides a direct answer
        after at most one tool execution.

        Args:
            messages: List of conversation messages.
            tool_schemas: List of available tool schemas.
            request: Optional FastAPI request object for cancellation checking.

        Yields:
            AgentEvent: Stream of agent events.
        """
        # Extract tool names for prompt
        tool_names = [tool.get("function", {}).get("name", "unknown") for tool in tool_schemas]
        tools_text = ", ".join(tool_names) if tool_names else "none"
        
        # Prepare messages with regular mode system prompt
        system_prompt = REGULAR_MODE_SYSTEM_PROMPT.format(tools=tools_text)
        prepared_messages = self._prepare_messages_with_system_prompt(messages, system_prompt)

        try:
            # Check for client disconnection before starting
            if (
                request
                and hasattr(request, "is_disconnected")
                and await request.is_disconnected()
            ):
                logger.info("Client disconnected, stopping regular mode with tools")
                yield AgentEvent(
                    event_type=AgentEventType.AGENT_COMPLETE,
                    data={"mode": "regular_with_tools", "cancelled": True},
                    metadata={"timestamp": asyncio.get_event_loop().time()},
                )
                return

            # Get LLM response with tools
            response = await self.llm_client.create_chat_completion(
                messages=prepared_messages,
                tools=tool_schemas,
                stream=False,
                temperature=self.agent_config.temperature,
                max_tokens=self.agent_config.max_tokens,
            )

            if not hasattr(response, "choices") or not response.choices:
                raise RuntimeError("Invalid LLM response format")

            choice = response.choices[0]
            message = choice.message

            # Handle tool calls if present
            if message.tool_calls:
                # In regular mode, we only handle the first tool call
                tool_call = message.tool_calls[0]

                # Signal tool call start
                yield AgentEvent(
                    event_type=AgentEventType.TOOL_CALL_START,
                    data={
                        "tool_name": tool_call.function.name,
                        "tool_args": json.loads(tool_call.function.arguments),
                        "tool_call_id": tool_call.id,
                    },
                    metadata={"mode": "regular_with_tools"},
                )

                # Execute the tool
                tool_result = await self._execute_tool_safely(tool_call)

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
                    metadata={"mode": "regular_with_tools"},
                )

                # Now get the final response from the LLM using the tool result
                messages_with_tool = prepared_messages.copy()
                messages_with_tool.append(
                    {
                        "role": "assistant",
                        "content": message.content or "",
                        "tool_calls": [
                            {
                                "id": tool_call.id,
                                "type": tool_call.type,
                                "function": {
                                    "name": tool_call.function.name,
                                    "arguments": tool_call.function.arguments,
                                },
                            }
                        ],
                    }
                )
                messages_with_tool.append(
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

                # Get final response (no more tools allowed)
                final_response = await self.llm_client.create_chat_completion(
                    messages=messages_with_tool, stream=False
                )

                # Stream the final response
                if hasattr(final_response, "choices") and final_response.choices:
                    final_message = final_response.choices[0].message
                    if final_message.content:
                        async for chunk in self._stream_content_chunks(
                            final_message.content, request
                        ):
                            yield AgentEvent(
                                event_type=AgentEventType.MESSAGE_CHUNK,
                                data={"content": chunk},
                                metadata={"mode": "regular_with_tools", "final": True},
                            )

            else:
                # No tool calls, stream the direct response
                if message.content:
                    async for chunk in self._stream_content_chunks(
                        message.content, request
                    ):
                        yield AgentEvent(
                            event_type=AgentEventType.MESSAGE_CHUNK,
                            data={"content": chunk},
                            metadata={"mode": "regular_with_tools", "final": True},
                        )

            yield AgentEvent(
                event_type=AgentEventType.AGENT_COMPLETE,
                data={"mode": "regular_with_tools"},
                metadata={"timestamp": asyncio.get_event_loop().time()},
            )

        except Exception as e:
            logger.error(f"Regular mode with tools error: {str(e)}")
            yield AgentEvent(
                event_type=AgentEventType.ERROR,
                data={"error": str(e)},
                metadata={"mode": "regular_with_tools"},
            )

    async def _regular_mode_no_tools(
        self, messages: List[Dict[str, Any]], request: Optional[Any] = None
    ) -> AsyncGenerator[AgentEvent, None]:
        """
        Regular mode without tools - direct answer using internal knowledge.

        Args:
            messages: List of conversation messages.
            request: Optional FastAPI request object for cancellation checking.

        Yields:
            AgentEvent: Stream of agent events.
        """
        # Prepare messages with no tools system prompt
        prepared_messages = self._prepare_messages_with_system_prompt(
            messages, NO_TOOLS_SYSTEM_PROMPT
        )

        try:
            # Check for client disconnection before starting streaming
            if (
                request
                and hasattr(request, "is_disconnected")
                and await request.is_disconnected()
            ):
                logger.info("Client disconnected, stopping regular mode no tools")
                yield AgentEvent(
                    event_type=AgentEventType.AGENT_COMPLETE,
                    data={"mode": "regular_no_tools", "cancelled": True},
                    metadata={"timestamp": asyncio.get_event_loop().time()},
                )
                return

            # Get LLM response with streaming
            response_stream = await self.llm_client.create_chat_completion(
                messages=prepared_messages, stream=True
            )

            async for chunk in response_stream:
                # Check for client disconnection before processing each chunk
                if (
                    request
                    and hasattr(request, "is_disconnected")
                    and await request.is_disconnected()
                ):
                    logger.info(
                        "Client disconnected during streaming, stopping regular mode no tools"
                    )
                    break

                if (
                    hasattr(chunk, "choices")
                    and chunk.choices
                    and chunk.choices[0].delta.content is not None
                ):
                    content = chunk.choices[0].delta.content

                    if content:
                        # Filter out problematic characters
                        filtered_content = "".join(
                            char
                            for char in content
                            if char.isprintable() or char in "\n\t\r"
                        )

                        if filtered_content:
                            yield AgentEvent(
                                event_type=AgentEventType.MESSAGE_CHUNK,
                                data={"content": filtered_content},
                                metadata={"mode": "regular_no_tools"},
                            )

            yield AgentEvent(
                event_type=AgentEventType.AGENT_COMPLETE,
                data={"mode": "regular_no_tools"},
                metadata={"timestamp": asyncio.get_event_loop().time()},
            )

        except Exception as e:
            logger.error(f"Regular mode no tools error: {str(e)}")
            yield AgentEvent(
                event_type=AgentEventType.ERROR,
                data={"error": str(e)},
                metadata={"mode": "regular_no_tools"},
            )

    async def _execute_tool_safely(self, tool_call) -> ToolResult:
        """
        Execute a tool call with proper error handling.

        Args:
            tool_call: Tool call object from LLM.

        Returns:
            ToolResult: Result of tool execution.
        """
        try:
            tool_args = json.loads(tool_call.function.arguments)
            logger.debug(
                f"Executing tool {tool_call.function.name} with args: {tool_args}"
            )

            tool_result = await self.tool_registry.execute_tool(
                tool_call.function.name, **tool_args
            )

            if not tool_result.success:
                logger.warning(
                    f"Tool {tool_call.function.name} failed: {tool_result.error}"
                )

            return tool_result

        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in tool call arguments: {str(e)}")
            return ToolResult(
                success=False,
                data=None,
                error=f"Invalid JSON in tool arguments: {str(e)}",
            )
        except Exception as e:
            logger.error(f"Tool execution error: {str(e)}", exc_info=True)
            return ToolResult(
                success=False,
                data=None,
                error=f"Tool execution failed: {str(e)}",
            )

    async def _stream_content_chunks(
        self, content: str, request: Optional[Any] = None
    ) -> AsyncGenerator[str, None]:
        """
        Stream content in word-based chunks for natural display.

        Args:
            content: Content to stream.
            request: Optional FastAPI request object for cancellation checking.

        Yields:
            str: Content chunks.
        """
        if not content:
            return

        # Split content into words for smoother streaming
        words = content.split()
        for i, word in enumerate(words):
            # Check for client disconnection before streaming each word
            if (
                request
                and hasattr(request, "is_disconnected")
                and await request.is_disconnected()
            ):
                logger.info("Client disconnected during content streaming")
                break

            # Add space before word (except first word)
            chunk = (" " + word) if i > 0 else word

            # Filter out problematic characters
            filtered_chunk = "".join(
                char for char in chunk if char.isprintable() or char in "\n\t\r"
            )

            if filtered_chunk:
                yield filtered_chunk

            # Small delay between words for natural streaming
            await asyncio.sleep(self.agent_config.stream_delay)

    async def _stream_content(self, content: str, iteration: int) -> None:
        """
        Log content streaming for debugging.

        Args:
            content: Content being streamed.
            iteration: Current iteration number.
        """
        logger.debug(
            f"Streaming content for iteration {iteration}: {len(content)} characters"
        )


async def deep_research_agent(
    messages: List[Dict[str, Any]],
    enabled_tools: List[str],
    deep_research_mode: bool,
    config: AppConfig,
    tool_registry: ToolRegistry,
    request: Optional[Any] = None,
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
        request: Optional FastAPI request object for cancellation checking.

    Yields:
        str: Formatted response strings for streaming.

    Raises:
        ValueError: If input validation fails.
        RuntimeError: If agent initialization fails.
    """
    try:
        # Validate inputs
        if not messages:
            raise ValueError("Messages list cannot be empty")

        if not isinstance(enabled_tools, list):
            raise ValueError("enabled_tools must be a list")

        if not isinstance(deep_research_mode, bool):
            raise ValueError("deep_research_mode must be a boolean")

        logger.info(
            f"Starting deep research agent with {len(enabled_tools)} tools, deep_research_mode={deep_research_mode}"
        )

        agent = DeepResearchAgent(config, tool_registry)

        async for event in agent.process_research_request(
            messages, enabled_tools, deep_research_mode, request
        ):
            # Check for client disconnection before processing event
            if (
                request
                and hasattr(request, "is_disconnected")
                and await request.is_disconnected()
            ):
                logger.info("Client disconnected, stopping agent processing")
                break

            formatted_response = _format_agent_event(event)
            if formatted_response:
                yield formatted_response

    except ValueError as e:
        logger.error(f"Deep research agent validation error: {str(e)}")
        yield f"❌ **Validation Error:** {str(e)}"
    except RuntimeError as e:
        logger.error(f"Deep research agent runtime error: {str(e)}")
        yield f"❌ **Runtime Error:** {str(e)}"
    except Exception as e:
        error_type = type(e).__name__
        logger.error(
            f"Deep research agent unexpected error [{error_type}]: {str(e)}",
            exc_info=True,
        )
        yield f"❌ **Unexpected Error:** {str(e)}"


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
        tool_call_id = event.data.get("tool_call_id")
        
        # Create a more structured format for frontend parsing
        args_str = (
            ", ".join(f"{k}={v}" for k, v in tool_args.items()) if tool_args else ""
        )
        
        return f"\n\n🔧 **Executing Tool:** {tool_name}({args_str})\n"

    elif event.event_type == AgentEventType.TOOL_CALL_RESULT:
        success = event.data.get("success")
        result = event.data.get("result")
        error = event.data.get("error")
        tool_name = event.data.get("tool_name", "")

        if success:
            # Format result based on type
            if isinstance(result, dict):
                # For structured results like weather data, format nicely
                if tool_name == "weather" and "current" in result:
                    weather_info = result["current"]
                    location_info = result.get("location", {})
                    city = location_info.get("city", "Unknown")
                    temp = weather_info.get("temperature", "N/A")
                    desc = weather_info.get("weather_description", "Unknown")
                    humidity = weather_info.get("humidity", "N/A")
                    wind = weather_info.get("wind_speed", "N/A")
                    
                    result_str = f"Weather in {city}: {temp}°C, {desc}, Humidity: {humidity}%, Wind: {wind} km/h"
                elif tool_name == "file_write" and "file_path" in result:
                    file_info = result.get("file_path", "file")
                    size_info = result.get("size", "")
                    result_str = f"File saved: {file_info}" + (
                        f" ({size_info} bytes)" if size_info else ""
                    )
                else:
                    # Generic structured result
                    result_str = json.dumps(result, indent=2)
                    if len(result_str) > 300:
                        result_str = result_str[:300] + "..."
            else:
                result_str = str(result) if result else "Success"
                if len(result_str) > 300:
                    result_str = result_str[:300] + "..."
            
            return f"✅ **Result:** {result_str}\n"
        else:
            return f"❌ **Error:** {error}\n"

    elif event.event_type == AgentEventType.ITERATION_START:
        iteration = event.data.get("iteration")
        return f"\n📋 **Research Iteration {iteration}**\n"

    elif event.event_type == AgentEventType.ITERATION_END:
        iteration = event.data.get("iteration")
        has_tool_calls = event.data.get("has_tool_calls", False)
        if has_tool_calls:
            return f"\n🔄 **Continuing research...**\n"
        else:
            return f"\n✨ **Research complete**\n"

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
