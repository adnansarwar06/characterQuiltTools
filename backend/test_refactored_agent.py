#!/usr/bin/env python3
"""
Test script for the refactored deep research agent.

This script tests both agent modes (deep research and regular)
with and without tools to ensure the refactoring works correctly.
"""

import asyncio
import logging
import sys
from typing import List, Dict, Any

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import our modules
from config import AppConfig
from tools import get_tool_registry
from llm import deep_research_agent


async def test_agent_mode(
    messages: List[Dict[str, Any]],
    enabled_tools: List[str],
    deep_research_mode: bool,
    test_name: str,
) -> None:
    """Test a specific agent mode configuration."""
    print(f"\n{'='*50}")
    print(f"TEST: {test_name}")
    print(f"Deep Research Mode: {deep_research_mode}")
    print(f"Enabled Tools: {enabled_tools}")
    print(f"{'='*50}")

    try:
        # Load configuration
        config = AppConfig()
        config.validate_config()

        # Get tool registry
        tool_registry = get_tool_registry(config)

        # Run the agent
        response_chunks = []
        async for chunk in deep_research_agent(
            messages=messages,
            enabled_tools=enabled_tools,
            deep_research_mode=deep_research_mode,
            config=config,
            tool_registry=tool_registry,
        ):
            response_chunks.append(chunk)
            print(chunk, end="", flush=True)

        print(f"\n\n✅ {test_name} completed successfully!")
        print(f"Total response chunks: {len(response_chunks)}")

    except Exception as e:
        print(f"\n❌ {test_name} failed with error: {str(e)}")
        logger.error(f"Test failed: {str(e)}", exc_info=True)


async def main():
    """Run all agent tests."""
    print("Testing Refactored Deep Research Agent")
    print("=" * 50)

    # Test messages
    test_messages = [{"role": "user", "content": "What is the capital of France?"}]

    weather_messages = [
        {"role": "user", "content": "What's the weather like in Paris?"}
    ]

    # Test cases
    test_cases = [
        {
            "messages": test_messages,
            "enabled_tools": [],
            "deep_research_mode": False,
            "test_name": "Regular Mode - No Tools",
        },
        {
            "messages": test_messages,
            "enabled_tools": [],
            "deep_research_mode": True,
            "test_name": "Deep Research Mode - No Tools",
        },
        {
            "messages": weather_messages,
            "enabled_tools": ["weather"],
            "deep_research_mode": False,
            "test_name": "Regular Mode - With Weather Tool",
        },
        {
            "messages": weather_messages,
            "enabled_tools": ["weather"],
            "deep_research_mode": True,
            "test_name": "Deep Research Mode - With Weather Tool",
        },
    ]

    # Run tests
    for test_case in test_cases:
        await test_agent_mode(**test_case)
        await asyncio.sleep(1)  # Small delay between tests

    print(f"\n{'='*50}")
    print("All tests completed!")
    print(f"{'='*50}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nTest suite failed: {str(e)}")
        logger.error(f"Test suite error: {str(e)}", exc_info=True)
        sys.exit(1)
