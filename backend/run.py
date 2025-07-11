#!/usr/bin/env python3
"""
Simple runner script for the Deep Research Agent backend.

This script provides an easy way to start the FastAPI server with proper configuration.
"""

import sys
import os

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import uvicorn
from config import AppConfig


def main():
    """
    Main entry point for running the FastAPI server.
    """
    try:
        # Load configuration
        config = AppConfig()
        
        # Validate configuration
        config.validate_config()
        
        print(f"Starting Deep Research Agent Backend...")
        print(f"Configuration: {config}")
        print(f"Server will be available at: http://{config.host}:{config.port}")
        print(f"API docs available at: http://{config.host}:{config.port}/docs")
        print(f"Health check at: http://{config.host}:{config.port}/health")
        
        # Start the server
        uvicorn.run(
            "app:app",
            host=config.host,
            port=config.port,
            reload=config.debug_mode,
            log_level=config.log_level.lower(),
            access_log=config.debug_mode,
        )
        
    except KeyboardInterrupt:
        print("\nShutting down server...")
    except Exception as e:
        print(f"Error starting server: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 