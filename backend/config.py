"""
Configuration module for the deep research agent backend.

This module handles loading configuration from environment variables
and .env files, providing a centralized configuration management system.
"""

import os
from typing import List, Optional
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass
class AppConfig:
    """
    Application configuration class.
    
    Loads configuration from environment variables and .env files.
    All configuration values are centralized here to avoid hardcoding.
    """
    
    def __init__(self):
        """Initialize configuration by loading from environment and .env files."""
        # Load environment variables from .env file if it exists
        load_dotenv()
        
        # Server configuration
        self.host: str = os.getenv("APP_HOST", "localhost")
        self.port: int = int(os.getenv("APP_PORT", "8000"))
        self.debug_mode: bool = os.getenv("DEBUG_MODE", "False").lower() == "true"
        
        # CORS configuration
        self.allowed_origins: List[str] = self._parse_cors_origins(
            os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000")
        )
        
        # API configuration
        self.api_timeout: int = int(os.getenv("API_TIMEOUT", "30"))
        self.max_request_size: int = int(os.getenv("MAX_REQUEST_SIZE", "1048576"))  # 1MB
        
        # Streaming configuration
        self.streaming_delay: float = float(os.getenv("STREAMING_DELAY", "0.05"))
        
        # Logging configuration
        self.log_level: str = os.getenv("LOG_LEVEL", "INFO")
        
        # Research agent configuration (for future use)
        self.max_research_iterations: int = int(os.getenv("MAX_RESEARCH_ITERATIONS", "10"))
        self.research_timeout: int = int(os.getenv("RESEARCH_TIMEOUT", "300"))
        
        # Tool configuration (for future use)
        self.available_tools: List[str] = self._parse_tools(
            os.getenv("AVAILABLE_TOOLS", "web_search,code_analysis,document_search")
        )
        
        # LLM configuration (for future use)
        self.llm_model: str = os.getenv("LLM_MODEL", "gpt-4")
        self.llm_temperature: float = float(os.getenv("LLM_TEMPERATURE", "0.7"))
        self.llm_max_tokens: int = int(os.getenv("LLM_MAX_TOKENS", "4096"))
        
        # Database configuration (for future use)
        self.database_url: Optional[str] = os.getenv("DATABASE_URL")
        
        # Security configuration (for future use)
        self.secret_key: str = os.getenv("SECRET_KEY", "your-secret-key-here")
        self.api_key: Optional[str] = os.getenv("API_KEY")
        
        # Rate limiting configuration (for future use)
        self.rate_limit_requests: int = int(os.getenv("RATE_LIMIT_REQUESTS", "100"))
        self.rate_limit_window: int = int(os.getenv("RATE_LIMIT_WINDOW", "3600"))
    
    def _parse_cors_origins(self, origins_str: str) -> List[str]:
        """
        Parse CORS origins from comma-separated string.
        
        Args:
            origins_str: Comma-separated string of allowed origins.
            
        Returns:
            List[str]: List of allowed origins.
        """
        if not origins_str:
            return ["*"]
        
        origins = [origin.strip() for origin in origins_str.split(",")]
        return [origin for origin in origins if origin]
    
    def _parse_tools(self, tools_str: str) -> List[str]:
        """
        Parse available tools from comma-separated string.
        
        Args:
            tools_str: Comma-separated string of available tools.
            
        Returns:
            List[str]: List of available tools.
        """
        if not tools_str:
            return []
        
        tools = [tool.strip() for tool in tools_str.split(",")]
        return [tool for tool in tools if tool]
    
    def get_database_config(self) -> dict:
        """
        Get database configuration dictionary.
        
        Returns:
            dict: Database configuration parameters.
        """
        return {
            "url": self.database_url,
            "pool_size": int(os.getenv("DB_POOL_SIZE", "5")),
            "max_overflow": int(os.getenv("DB_MAX_OVERFLOW", "10")),
            "pool_timeout": int(os.getenv("DB_POOL_TIMEOUT", "30")),
        }
    
    def get_llm_config(self) -> dict:
        """
        Get LLM configuration dictionary.
        
        Returns:
            dict: LLM configuration parameters.
        """
        return {
            "model": self.llm_model,
            "temperature": self.llm_temperature,
            "max_tokens": self.llm_max_tokens,
            "api_key": self.api_key,
        }
    
    def get_rate_limit_config(self) -> dict:
        """
        Get rate limiting configuration dictionary.
        
        Returns:
            dict: Rate limiting configuration parameters.
        """
        return {
            "requests": self.rate_limit_requests,
            "window": self.rate_limit_window,
        }
    
    def is_development(self) -> bool:
        """
        Check if running in development mode.
        
        Returns:
            bool: True if in development mode, False otherwise.
        """
        return self.debug_mode
    
    def is_production(self) -> bool:
        """
        Check if running in production mode.
        
        Returns:
            bool: True if in production mode, False otherwise.
        """
        return not self.debug_mode
    
    def validate_config(self) -> None:
        """
        Validate the configuration values.
        
        Raises:
            ValueError: If any configuration value is invalid.
        """
        if self.port < 1 or self.port > 65535:
            raise ValueError(f"Invalid port number: {self.port}")
        
        if self.api_timeout < 1:
            raise ValueError(f"Invalid API timeout: {self.api_timeout}")
        
        if self.max_request_size < 1:
            raise ValueError(f"Invalid max request size: {self.max_request_size}")
        
        if self.streaming_delay < 0:
            raise ValueError(f"Invalid streaming delay: {self.streaming_delay}")
        
        if self.llm_temperature < 0 or self.llm_temperature > 2:
            raise ValueError(f"Invalid LLM temperature: {self.llm_temperature}")
        
        if self.llm_max_tokens < 1:
            raise ValueError(f"Invalid LLM max tokens: {self.llm_max_tokens}")
    
    def __str__(self) -> str:
        """
        String representation of the configuration.
        
        Returns:
            str: Configuration summary (excludes sensitive values).
        """
        return (
            f"AppConfig(host={self.host}, port={self.port}, "
            f"debug_mode={self.debug_mode}, log_level={self.log_level})"
        ) 