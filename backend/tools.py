"""
Tools module for the deep research agent.

This module implements a registry pattern for managing research tools,
including web search, file operations, and weather data retrieval.
"""

import json
import logging
import os
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Union

import aiofiles
import requests

from config import AppConfig

# Configure logging
logger = logging.getLogger(__name__)


@dataclass
class ToolResult:
    """Represents the result of a tool execution."""

    success: bool
    data: Any
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class ToolValidationError(Exception):
    """Exception raised when tool validation fails."""

    pass


class ToolExecutionError(Exception):
    """Exception raised when tool execution fails."""

    pass


class ToolRegistry:
    """
    Registry for managing research tools.

    Provides a centralized way to register, discover, and execute tools.
    """

    def __init__(self, config: AppConfig) -> None:
        """
        Initialize the tool registry.

        Args:
            config: Application configuration instance.
        """
        self.config = config
        self.tools: Dict[str, Callable] = {}
        self.tool_schemas: Dict[str, Dict[str, Any]] = {}

        # Register all tools from the TOOLS registry
        self._register_tools()

    def register_tool(self, name: str, func: Callable, schema: Dict[str, Any]) -> None:
        """
        Register a tool with the registry.

        Args:
            name: Tool name identifier.
            func: Tool function to execute.
            schema: OpenAI function schema for the tool.

        Raises:
            ToolValidationError: If tool registration fails validation.
        """
        if not name or not isinstance(name, str):
            raise ToolValidationError(
                f"Tool name must be a non-empty string, got: {name}"
            )

        if not callable(func):
            raise ToolValidationError(
                f"Tool function must be callable, got: {type(func)}"
            )

        if not isinstance(schema, dict):
            raise ToolValidationError(
                f"Tool schema must be a dictionary, got: {type(schema)}"
            )

        # Validate schema structure
        self._validate_tool_schema(name, schema)

        self.tools[name] = func
        self.tool_schemas[name] = schema
        logger.info(f"Registered tool: {name}")

    def _validate_tool_schema(self, name: str, schema: Dict[str, Any]) -> None:
        """
        Validate tool schema structure.

        Args:
            name: Tool name.
            schema: Tool schema to validate.

        Raises:
            ToolValidationError: If schema validation fails.
        """
        required_keys = ["type", "function"]
        for key in required_keys:
            if key not in schema:
                raise ToolValidationError(
                    f"Tool '{name}' schema missing required key: {key}"
                )

        if schema["type"] != "function":
            raise ToolValidationError(
                f"Tool '{name}' schema type must be 'function', got: {schema['type']}"
            )

        function_schema = schema["function"]
        if not isinstance(function_schema, dict):
            raise ToolValidationError(
                f"Tool '{name}' function schema must be a dictionary"
            )

        function_required_keys = ["name", "description", "parameters"]
        for key in function_required_keys:
            if key not in function_schema:
                raise ToolValidationError(
                    f"Tool '{name}' function schema missing required key: {key}"
                )

        if function_schema["name"] != name:
            raise ToolValidationError(
                f"Tool '{name}' function name must match tool name, got: {function_schema['name']}"
            )

        # Validate parameters schema
        params = function_schema["parameters"]
        if not isinstance(params, dict):
            raise ToolValidationError(f"Tool '{name}' parameters must be a dictionary")

        if params.get("type") != "object":
            raise ToolValidationError(
                f"Tool '{name}' parameters type must be 'object', got: {params.get('type')}"
            )

        if "properties" not in params:
            raise ToolValidationError(
                f"Tool '{name}' parameters missing 'properties' key"
            )

    def get_tool_schemas(self, enabled_tools: List[str]) -> List[Dict[str, Any]]:
        """
        Get OpenAI function schemas for enabled tools.

        Args:
            enabled_tools: List of tool names to include.

        Returns:
            List[Dict[str, Any]]: OpenAI function schemas.

        Raises:
            ToolValidationError: If tool validation fails.
        """
        if not isinstance(enabled_tools, list):
            raise ToolValidationError(
                f"enabled_tools must be a list, got: {type(enabled_tools)}"
            )

        schemas = []
        for tool_name in enabled_tools:
            if not isinstance(tool_name, str):
                logger.warning(f"Skipping non-string tool name: {tool_name}")
                continue

            if tool_name in self.tool_schemas:
                schemas.append(self.tool_schemas[tool_name])
            else:
                logger.warning(f"Tool not found: {tool_name}")

        return schemas

    def _validate_tool_arguments(self, tool_name: str, **kwargs: Any) -> None:
        """
        Validate tool arguments against schema.

        Args:
            tool_name: Name of the tool.
            **kwargs: Tool arguments to validate.

        Raises:
            ToolValidationError: If argument validation fails.
        """
        if tool_name not in self.tool_schemas:
            raise ToolValidationError(f"Tool '{tool_name}' not found in registry")

        schema = self.tool_schemas[tool_name]
        function_schema = schema["function"]
        params_schema = function_schema["parameters"]

        # Check required parameters
        required_params = params_schema.get("required", [])
        for param in required_params:
            if param not in kwargs:
                raise ToolValidationError(
                    f"Tool '{tool_name}' missing required parameter: {param}"
                )

        # Check parameter types
        properties = params_schema.get("properties", {})
        for param_name, param_value in kwargs.items():
            if param_name not in properties:
                logger.warning(
                    f"Tool '{tool_name}' received unexpected parameter: {param_name}"
                )
                continue

            param_schema = properties[param_name]
            expected_type = param_schema.get("type")

            if expected_type == "string" and not isinstance(param_value, str):
                raise ToolValidationError(
                    f"Tool '{tool_name}' parameter '{param_name}' must be string, got: {type(param_value)}"
                )
            elif expected_type == "integer" and not isinstance(param_value, int):
                raise ToolValidationError(
                    f"Tool '{tool_name}' parameter '{param_name}' must be integer, got: {type(param_value)}"
                )
            elif expected_type == "boolean" and not isinstance(param_value, bool):
                raise ToolValidationError(
                    f"Tool '{tool_name}' parameter '{param_name}' must be boolean, got: {type(param_value)}"
                )
            elif expected_type == "number" and not isinstance(
                param_value, (int, float)
            ):
                raise ToolValidationError(
                    f"Tool '{tool_name}' parameter '{param_name}' must be number, got: {type(param_value)}"
                )

    async def execute_tool(self, tool_name: str, **kwargs: Any) -> ToolResult:
        """
        Execute a tool by name.

        Args:
            tool_name: Name of the tool to execute.
            **kwargs: Tool-specific arguments.

        Returns:
            ToolResult: Execution result.
        """
        if not tool_name or not isinstance(tool_name, str):
            return ToolResult(
                success=False,
                data=None,
                error=f"Tool name must be a non-empty string, got: {tool_name}",
            )

        if tool_name not in self.tools:
            return ToolResult(
                success=False,
                data=None,
                error=f"Tool '{tool_name}' not found in registry",
            )

        try:
            # Validate arguments
            self._validate_tool_arguments(tool_name, **kwargs)

            logger.info(f"Executing tool: {tool_name} with args: {kwargs}")

            # Execute the tool
            result = await self.tools[tool_name](**kwargs)

            # Validate result
            if not isinstance(result, ToolResult):
                logger.error(
                    f"Tool '{tool_name}' returned invalid result type: {type(result)}"
                )
                return ToolResult(
                    success=False,
                    data=None,
                    error=f"Tool returned invalid result type: {type(result)}",
                )

            # Log execution result
            if result.success:
                logger.info(f"Tool '{tool_name}' executed successfully")
            else:
                logger.warning(f"Tool '{tool_name}' failed: {result.error}")

            return result

        except ToolValidationError as e:
            logger.error(f"Tool '{tool_name}' validation error: {str(e)}")
            return ToolResult(
                success=False, data=None, error=f"Validation error: {str(e)}"
            )
        except ToolExecutionError as e:
            logger.error(f"Tool '{tool_name}' execution error: {str(e)}")
            return ToolResult(
                success=False, data=None, error=f"Execution error: {str(e)}"
            )
        except Exception as e:
            logger.error(
                f"Tool '{tool_name}' unexpected error: {str(e)}", exc_info=True
            )
            return ToolResult(
                success=False, data=None, error=f"Unexpected error: {str(e)}"
            )

    def _register_tools(self) -> None:
        """Register all tools from the TOOLS registry."""
        for tool_name, tool_config in TOOLS.items():
            try:
                self.register_tool(
                    name=tool_name,
                    func=getattr(self, tool_config["function"]),
                    schema=tool_config["schema"],
                )
            except Exception as e:
                logger.error(f"Failed to register tool '{tool_name}': {str(e)}")

    async def _web_search(self, query: str, num_results: int = 5) -> ToolResult:
        """
        Search the web using DuckDuckGo Instant Answer API (free, no API key needed).

        Args:
            query: Search query string.
            num_results: Number of results to return.

        Returns:
            ToolResult: Search results.
        """
        try:
            # Validate inputs
            if not query or not isinstance(query, str):
                raise ToolValidationError("Query must be a non-empty string")

            if not isinstance(num_results, int) or num_results < 1:
                raise ToolValidationError("num_results must be a positive integer")

            if num_results > 10:
                num_results = 10  # Cap at 10 results

            query = query.strip()
            if len(query) > 500:
                raise ToolValidationError("Query must be 500 characters or less")

            # Use DuckDuckGo Instant Answer API for free web search
            ddg_url = self.config.duckduckgo_api_url

            # First, try to get instant answer
            ddg_params = {
                "q": query,
                "format": "json",
                "pretty": "1",
                "no_html": "1",
                "skip_disambig": "1",
            }

            logger.debug(f"Making DuckDuckGo API request for query: {query}")

            response = requests.get(ddg_url, params=ddg_params, timeout=30)
            response.raise_for_status()

            data = response.json()
            results = []

            # Extract instant answer if available
            if data.get("AbstractText"):
                results.append(
                    {
                        "title": data.get("Heading", "Instant Answer"),
                        "url": data.get("AbstractURL", ""),
                        "snippet": data.get("AbstractText", ""),
                        "source": data.get("AbstractSource", "DuckDuckGo"),
                        "type": "instant_answer",
                    }
                )

            # Extract related topics
            if data.get("RelatedTopics"):
                for topic in data.get("RelatedTopics", [])[: min(num_results - 1, 4)]:
                    if isinstance(topic, dict) and topic.get("Text"):
                        results.append(
                            {
                                "title": topic.get("Text", "").split(" - ")[0],
                                "url": topic.get("FirstURL", ""),
                                "snippet": topic.get("Text", ""),
                                "source": "DuckDuckGo",
                                "type": "related_topic",
                            }
                        )

            # If no results from instant answer, try a simple web search fallback
            if not results:
                search_url = self.config.duckduckgo_search_url
                search_params = {"q": query}

                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                }

                try:
                    logger.debug(f"Attempting fallback web search for query: {query}")
                    search_response = requests.get(
                        search_url, params=search_params, headers=headers, timeout=30
                    )
                    search_response.raise_for_status()

                    # Simple text extraction (basic approach)
                    html_content = search_response.text

                    # Look for title patterns in HTML
                    title_matches = re.findall(
                        r'<a[^>]+class="result__a"[^>]*>([^<]+)</a>', html_content
                    )
                    snippet_matches = re.findall(
                        r'<a[^>]+class="result__snippet"[^>]*>([^<]+)</a>', html_content
                    )

                    for i, title in enumerate(title_matches[:num_results]):
                        snippet = snippet_matches[i] if i < len(snippet_matches) else ""
                        results.append(
                            {
                                "title": title.strip(),
                                "url": f"{self.config.duckduckgo_search_url}?q={query}",
                                "snippet": snippet.strip(),
                                "source": "DuckDuckGo Search",
                                "type": "web_search",
                            }
                        )

                except Exception as fallback_error:
                    logger.warning(f"Fallback search failed: {fallback_error}")

            # If still no results, provide a helpful message
            if not results:
                results = [
                    {
                        "title": f"Search Results for: {query}",
                        "url": f"{self.config.duckduckgo_search_url}?q={query}",
                        "snippet": f"No specific instant answers found for '{query}'. You may want to visit DuckDuckGo directly to search for more detailed information.",
                        "source": "DuckDuckGo",
                        "type": "search_suggestion",
                    }
                ]

            return ToolResult(
                success=True,
                data={"results": results, "total": len(results)},
                metadata={"query": query, "timestamp": datetime.now().isoformat()},
            )

        except ToolValidationError:
            raise
        except requests.exceptions.RequestException as e:
            raise ToolExecutionError(f"Web search API request failed: {str(e)}")
        except Exception as e:
            raise ToolExecutionError(f"Unexpected error during web search: {str(e)}")

    async def _file_write(
        self, filename: str, content: str, append: bool = False
    ) -> ToolResult:
        """
        Write content to a file in the safe output directory.

        Args:
            filename: Name of the file to write.
            content: Content to write.
            append: Whether to append to existing file.

        Returns:
            ToolResult: File write result.
        """
        try:
            # Validate inputs
            if not filename or not isinstance(filename, str):
                raise ToolValidationError("Filename must be a non-empty string")

            if not isinstance(content, str):
                raise ToolValidationError("Content must be a string")

            if not isinstance(append, bool):
                raise ToolValidationError("Append must be a boolean")

            # Ensure safe filename (no path traversal)
            safe_filename = os.path.basename(filename)
            if not safe_filename or safe_filename.startswith("."):
                raise ToolValidationError(
                    "Invalid filename: must not be empty or start with '.'"
                )

            # Check for dangerous file extensions
            dangerous_extensions = [
                ".exe",
                ".bat",
                ".cmd",
                ".sh",
                ".ps1",
                ".scr",
                ".dll",
            ]
            if any(safe_filename.lower().endswith(ext) for ext in dangerous_extensions):
                raise ToolValidationError(
                    f"File extension not allowed for security reasons: {safe_filename}"
                )

            # Check filename length
            if len(safe_filename) > 255:
                raise ToolValidationError("Filename too long (max 255 characters)")

            # Create output directory if it doesn't exist
            output_dir = Path(self.config.file_output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)

            file_path = output_dir / safe_filename

            # Check file size limit
            content_bytes = content.encode("utf-8")
            if len(content_bytes) > self.config.max_file_size:
                raise ToolValidationError(
                    f"Content size ({len(content_bytes)} bytes) exceeds limit ({self.config.max_file_size} bytes)"
                )

            # Write file
            mode = "a" if append else "w"
            async with aiofiles.open(file_path, mode, encoding="utf-8") as f:
                await f.write(content)

            logger.info(f"Successfully wrote {len(content_bytes)} bytes to {file_path}")

            return ToolResult(
                success=True,
                data={
                    "file_path": str(file_path),
                    "size": len(content_bytes),
                    "mode": "appended" if append else "written",
                },
                metadata={
                    "filename": safe_filename,
                    "timestamp": datetime.now().isoformat(),
                },
            )

        except ToolValidationError:
            raise
        except Exception as e:
            raise ToolExecutionError(f"File write operation failed: {str(e)}")

    async def _weather(self, city: str, country: str = "") -> ToolResult:
        """
        Get current weather information using Open-Meteo API (free, no API key needed).

        Args:
            city: City name.
            country: Country code (optional).

        Returns:
            ToolResult: Weather information.
        """
        try:
            # Validate inputs
            if not city or not isinstance(city, str):
                raise ToolValidationError("City must be a non-empty string")

            if not isinstance(country, str):
                raise ToolValidationError("Country must be a string")

            city = city.strip()
            country = country.strip()

            if len(city) > 100:
                raise ToolValidationError("City name too long (max 100 characters)")

            if len(country) > 50:
                raise ToolValidationError("Country name too long (max 50 characters)")

            # First, get coordinates for the city using geocoding
            location_query = f"{city}, {country}" if country else city
            geocoding_url = self.config.openmeteo_geocoding_url

            geocoding_params = {
                "name": location_query,
                "count": 1,
                "language": "en",
                "format": "json",
            }

            logger.debug(f"Making geocoding request for: {location_query}")

            geo_response = requests.get(
                geocoding_url, params=geocoding_params, timeout=30
            )
            geo_response.raise_for_status()

            geo_data = geo_response.json()

            if not geo_data.get("results"):
                raise ToolExecutionError(f"City not found: {location_query}")

            location = geo_data["results"][0]
            latitude = location["latitude"]
            longitude = location["longitude"]

            # Get weather data using correct Open-Meteo API endpoint
            weather_url = self.config.openmeteo_weather_url
            weather_params = {
                "latitude": latitude,
                "longitude": longitude,
                "current": "temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m,wind_direction_10m",
            }

            logger.debug(
                f"Making weather request for coordinates: {latitude}, {longitude}"
            )

            weather_response = requests.get(
                weather_url, params=weather_params, timeout=30
            )
            weather_response.raise_for_status()
            weather_data = weather_response.json()

            current = weather_data["current"]

            # Map weather codes to descriptions
            weather_codes = {
                0: "Clear sky",
                1: "Mainly clear",
                2: "Partly cloudy",
                3: "Overcast",
                45: "Fog",
                48: "Depositing rime fog",
                51: "Light drizzle",
                53: "Moderate drizzle",
                55: "Dense drizzle",
                61: "Slight rain",
                63: "Moderate rain",
                65: "Heavy rain",
                71: "Slight snow",
                73: "Moderate snow",
                75: "Heavy snow",
                80: "Slight rain showers",
                81: "Moderate rain showers",
                82: "Violent rain showers",
                95: "Thunderstorm",
                96: "Thunderstorm with slight hail",
                99: "Thunderstorm with heavy hail",
            }

            weather_description = weather_codes.get(current["weather_code"], "Unknown")

            result_data = {
                "location": {
                    "city": city,
                    "country": location.get("country", ""),
                    "latitude": latitude,
                    "longitude": longitude,
                },
                "current": {
                    "temperature": current["temperature_2m"],
                    "humidity": current["relative_humidity_2m"],
                    "weather_code": current["weather_code"],
                    "weather_description": weather_description,
                    "wind_speed": current["wind_speed_10m"],
                    "wind_direction": current["wind_direction_10m"],
                    "timestamp": current["time"],
                },
                "units": {
                    "temperature": "°C",
                    "humidity": "%",
                    "wind_speed": "km/h",
                    "wind_direction": "°",
                },
            }

            logger.info(f"Successfully retrieved weather data for {city}")

            return ToolResult(
                success=True,
                data=result_data,
                metadata={
                    "query": location_query,
                    "timestamp": datetime.now().isoformat(),
                },
            )

        except ToolValidationError:
            raise
        except requests.exceptions.RequestException as e:
            raise ToolExecutionError(f"Weather API request failed: {str(e)}")
        except Exception as e:
            raise ToolExecutionError(
                f"Unexpected error during weather lookup: {str(e)}"
            )


# TOOLS registry - centralized tool definitions
TOOLS: Dict[str, Dict[str, Any]] = {
    "web_search": {
        "function": "_web_search",
        "schema": {
            "type": "function",
            "function": {
                "name": "web_search",
                "description": "Search the web for information using DuckDuckGo (free, no API key needed)",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query to find information",
                        },
                        "num_results": {
                            "type": "integer",
                            "description": "Number of results to return (max 10)",
                            "default": 5,
                        },
                    },
                    "required": ["query"],
                },
            },
        },
    },
    "file_write": {
        "function": "_file_write",
        "schema": {
            "type": "function",
            "function": {
                "name": "file_write",
                "description": "Write content to a file in the safe output directory",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "filename": {
                            "type": "string",
                            "description": "Name of the file to write (without path)",
                        },
                        "content": {
                            "type": "string",
                            "description": "Content to write to the file",
                        },
                        "append": {
                            "type": "boolean",
                            "description": "Whether to append to existing file",
                            "default": False,
                        },
                    },
                    "required": ["filename", "content"],
                },
            },
        },
    },
    "weather": {
        "function": "_weather",
        "schema": {
            "type": "function",
            "function": {
                "name": "weather",
                "description": "Get current weather information for a city using Open-Meteo API (free, no API key needed)",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "city": {
                            "type": "string",
                            "description": "City name to get weather for",
                        },
                        "country": {
                            "type": "string",
                            "description": "Country code (optional, e.g., 'US', 'GB')",
                            "default": "",
                        },
                    },
                    "required": ["city"],
                },
            },
        },
    },
}


# Global tool registry instance
_tool_registry: Optional[ToolRegistry] = None


def get_tool_registry(config: AppConfig) -> ToolRegistry:
    """
    Get the global tool registry instance.

    Args:
        config: Application configuration.

    Returns:
        ToolRegistry: Global tool registry instance.
    """
    global _tool_registry
    if _tool_registry is None:
        _tool_registry = ToolRegistry(config)
    return _tool_registry
