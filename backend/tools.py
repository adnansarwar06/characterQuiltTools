"""
Tools module for the deep research agent.

This module implements a registry pattern for managing research tools,
including web search, file operations, and weather data retrieval.
"""

import os
import json
import logging
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass
from pathlib import Path
import requests
import aiofiles
from datetime import datetime

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


class ToolRegistry:
    """
    Registry for managing research tools.
    
    Provides a centralized way to register, discover, and execute tools.
    """
    
    def __init__(self, config: AppConfig):
        """
        Initialize the tool registry.
        
        Args:
            config: Application configuration instance.
        """
        self.config = config
        self.tools: Dict[str, Callable] = {}
        self.tool_schemas: Dict[str, Dict[str, Any]] = {}
        
        # Register built-in tools
        self._register_builtin_tools()
    
    def register_tool(self, name: str, func: Callable, schema: Dict[str, Any]) -> None:
        """
        Register a tool with the registry.
        
        Args:
            name: Tool name identifier.
            func: Tool function to execute.
            schema: OpenAI function schema for the tool.
        """
        self.tools[name] = func
        self.tool_schemas[name] = schema
        logger.info(f"Registered tool: {name}")
    
    def get_tool_schemas(self, enabled_tools: List[str]) -> List[Dict[str, Any]]:
        """
        Get OpenAI function schemas for enabled tools.
        
        Args:
            enabled_tools: List of tool names to include.
            
        Returns:
            List[Dict[str, Any]]: OpenAI function schemas.
        """
        schemas = []
        for tool_name in enabled_tools:
            if tool_name in self.tool_schemas:
                schemas.append(self.tool_schemas[tool_name])
            else:
                logger.warning(f"Tool not found: {tool_name}")
        return schemas
    
    async def execute_tool(self, tool_name: str, **kwargs) -> ToolResult:
        """
        Execute a tool by name.
        
        Args:
            tool_name: Name of the tool to execute.
            **kwargs: Tool-specific arguments.
            
        Returns:
            ToolResult: Execution result.
        """
        if tool_name not in self.tools:
            return ToolResult(
                success=False,
                data=None,
                error=f"Tool '{tool_name}' not found"
            )
        
        try:
            logger.info(f"Executing tool: {tool_name} with args: {kwargs}")
            result = await self.tools[tool_name](**kwargs)
            return result
        except Exception as e:
            logger.error(f"Tool execution error for {tool_name}: {str(e)}")
            return ToolResult(
                success=False,
                data=None,
                error=str(e)
            )
    
    def _register_builtin_tools(self) -> None:
        """Register all built-in tools."""
        # Web search tool
        self.register_tool(
            "web_search",
            self._web_search,
            {
                "type": "function",
                "function": {
                    "name": "web_search",
                    "description": "Search the web for information using DuckDuckGo (free, no API key needed)",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Search query to find information"
                            },
                            "num_results": {
                                "type": "integer",
                                "description": "Number of results to return (max 10)",
                                "default": 5
                            }
                        },
                        "required": ["query"]
                    }
                }
            }
        )
        
        # File write tool
        self.register_tool(
            "file_write",
            self._file_write,
            {
                "type": "function",
                "function": {
                    "name": "file_write",
                    "description": "Write content to a file in the safe output directory",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "filename": {
                                "type": "string",
                                "description": "Name of the file to write (without path)"
                            },
                            "content": {
                                "type": "string",
                                "description": "Content to write to the file"
                            },
                            "append": {
                                "type": "boolean",
                                "description": "Whether to append to existing file",
                                "default": False
                            }
                        },
                        "required": ["filename", "content"]
                    }
                }
            }
        )
        
        # Weather tool
        self.register_tool(
            "weather",
            self._weather,
            {
                "type": "function",
                "function": {
                    "name": "weather",
                    "description": "Get current weather information for a city using Open-Meteo API (free, no API key needed)",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "city": {
                                "type": "string",
                                "description": "City name to get weather for"
                            },
                            "country": {
                                "type": "string",
                                "description": "Country code (optional, e.g., 'US', 'GB')",
                                "default": ""
                            }
                        },
                        "required": ["city"]
                    }
                }
            }
        )
    
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
            # Use DuckDuckGo Instant Answer API for free web search
            ddg_url = "https://api.duckduckgo.com/"
            
            # First, try to get instant answer
            ddg_params = {
                "q": query,
                "format": "json",
                "pretty": "1",
                "no_html": "1",
                "skip_disambig": "1"
            }
            
            response = requests.get(ddg_url, params=ddg_params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            results = []
            
            # Extract instant answer if available
            if data.get("AbstractText"):
                results.append({
                    "title": data.get("Heading", "Instant Answer"),
                    "url": data.get("AbstractURL", ""),
                    "snippet": data.get("AbstractText", ""),
                    "source": data.get("AbstractSource", "DuckDuckGo"),
                    "type": "instant_answer"
                })
            
            # Extract related topics
            if data.get("RelatedTopics"):
                for topic in data.get("RelatedTopics", [])[:min(num_results-1, 4)]:
                    if isinstance(topic, dict) and topic.get("Text"):
                        results.append({
                            "title": topic.get("Text", "").split(" - ")[0],
                            "url": topic.get("FirstURL", ""),
                            "snippet": topic.get("Text", ""),
                            "source": "DuckDuckGo",
                            "type": "related_topic"
                        })
            
            # If no results from instant answer, try a simple web search fallback
            if not results:
                # Use a simple HTML search approach as fallback
                search_url = "https://html.duckduckgo.com/html/"
                search_params = {"q": query}
                
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                }
                
                try:
                    search_response = requests.get(
                        search_url, params=search_params, headers=headers, timeout=30
                    )
                    search_response.raise_for_status()
                    
                    # Simple text extraction (basic approach)
                    html_content = search_response.text
                    
                    # Extract some basic information (this is a simplified approach)
                    import re
                    
                    # Look for title patterns in HTML
                    title_matches = re.findall(r'<a[^>]+class="result__a"[^>]*>([^<]+)</a>', html_content)
                    snippet_matches = re.findall(r'<a[^>]+class="result__snippet"[^>]*>([^<]+)</a>', html_content)
                    
                    for i, title in enumerate(title_matches[:num_results]):
                        snippet = snippet_matches[i] if i < len(snippet_matches) else ""
                        results.append({
                            "title": title.strip(),
                            "url": f"https://duckduckgo.com/?q={query}",
                            "snippet": snippet.strip(),
                            "source": "DuckDuckGo Search",
                            "type": "web_search"
                        })
                        
                except Exception as fallback_error:
                    logger.warning(f"Fallback search failed: {fallback_error}")
            
            # If still no results, provide a helpful message
            if not results:
                results = [{
                    "title": f"Search Results for: {query}",
                    "url": f"https://duckduckgo.com/?q={query}",
                    "snippet": f"No specific instant answers found for '{query}'. You may want to visit DuckDuckGo directly to search for more detailed information.",
                    "source": "DuckDuckGo",
                    "type": "search_suggestion"
                }]
            
            return ToolResult(
                success=True,
                data={"results": results, "total": len(results)},
                metadata={"query": query, "timestamp": datetime.now().isoformat()}
            )
            
        except requests.exceptions.RequestException as e:
            return ToolResult(
                success=False,
                data=None,
                error=f"Web search failed: {str(e)}"
            )
        except Exception as e:
            return ToolResult(
                success=False,
                data=None,
                error=f"Unexpected error during web search: {str(e)}"
            )
    
    async def _file_write(self, filename: str, content: str, append: bool = False) -> ToolResult:
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
            # Ensure safe filename (no path traversal)
            safe_filename = os.path.basename(filename)
            if not safe_filename or safe_filename.startswith('.'):
                return ToolResult(
                    success=False,
                    data=None,
                    error="Invalid filename"
                )
            
            # Create output directory if it doesn't exist
            output_dir = Path(self.config.file_output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)
            
            file_path = output_dir / safe_filename
            
            # Check file size limit
            if len(content.encode('utf-8')) > self.config.max_file_size:
                return ToolResult(
                    success=False,
                    data=None,
                    error=f"Content size exceeds limit ({self.config.max_file_size} bytes)"
                )
            
            # Write file
            mode = "a" if append else "w"
            async with aiofiles.open(file_path, mode, encoding="utf-8") as f:
                await f.write(content)
            
            return ToolResult(
                success=True,
                data={
                    "file_path": str(file_path),
                    "size": len(content.encode('utf-8')),
                    "mode": "appended" if append else "written"
                },
                metadata={"filename": safe_filename, "timestamp": datetime.now().isoformat()}
            )
            
        except Exception as e:
            return ToolResult(
                success=False,
                data=None,
                error=f"File write failed: {str(e)}"
            )
    
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
            # First, get coordinates for the city using geocoding
            location_query = f"{city}, {country}" if country else city
            geocoding_url = "https://geocoding-api.open-meteo.com/v1/search"
            
            geocoding_params = {
                "name": location_query,
                "count": 1,
                "language": "en",
                "format": "json"
            }
            
            geo_response = requests.get(geocoding_url, params=geocoding_params, timeout=30)
            geo_response.raise_for_status()
            geo_data = geo_response.json()
            
            if not geo_data.get("results"):
                return ToolResult(
                    success=False,
                    data=None,
                    error=f"City not found: {location_query}"
                )
            
            location = geo_data["results"][0]
            latitude = location["latitude"]
            longitude = location["longitude"]
            
            # Get weather data
            weather_url = "https://api.open-meteo.com/v1/current"
            weather_params = {
                "latitude": latitude,
                "longitude": longitude,
                "current": "temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m,wind_direction_10m"
            }
            
            weather_response = requests.get(weather_url, params=weather_params, timeout=30)
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
                99: "Thunderstorm with heavy hail"
            }
            
            weather_description = weather_codes.get(current["weather_code"], "Unknown")
            
            result_data = {
                "location": {
                    "city": city,
                    "country": location.get("country", ""),
                    "latitude": latitude,
                    "longitude": longitude
                },
                "current": {
                    "temperature": current["temperature_2m"],
                    "humidity": current["relative_humidity_2m"],
                    "weather_code": current["weather_code"],
                    "weather_description": weather_description,
                    "wind_speed": current["wind_speed_10m"],
                    "wind_direction": current["wind_direction_10m"],
                    "timestamp": current["time"]
                },
                "units": {
                    "temperature": "°C",
                    "humidity": "%",
                    "wind_speed": "km/h",
                    "wind_direction": "°"
                }
            }
            
            return ToolResult(
                success=True,
                data=result_data,
                metadata={"query": location_query, "timestamp": datetime.now().isoformat()}
            )
            
        except requests.exceptions.RequestException as e:
            return ToolResult(
                success=False,
                data=None,
                error=f"Weather API request failed: {str(e)}"
            )
        except Exception as e:
            return ToolResult(
                success=False,
                data=None,
                error=f"Unexpected error during weather lookup: {str(e)}"
            )


# Global tool registry instance
tool_registry = None


def get_tool_registry(config: AppConfig) -> ToolRegistry:
    """
    Get the global tool registry instance.
    
    Args:
        config: Application configuration.
        
    Returns:
        ToolRegistry: Global tool registry instance.
    """
    global tool_registry
    if tool_registry is None:
        tool_registry = ToolRegistry(config)
    return tool_registry
