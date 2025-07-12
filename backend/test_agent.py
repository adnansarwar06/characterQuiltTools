"""
Test script for the Deep Research Agent.

This script demonstrates how to use the deep research agent locally
for development and testing purposes.
"""

import asyncio
import json
import logging
from typing import List, Dict, Any

from config import AppConfig
from tools import get_tool_registry
from llm import deep_research_agent

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def test_simple_chat():
    """Test simple chat mode without tools."""
    print("🧪 Testing Simple Chat Mode...")
    print("=" * 50)

    config = AppConfig()
    tool_registry = get_tool_registry(config)

    messages = [{"role": "user", "content": "Hello! Tell me about Python programming."}]

    try:
        async for chunk in deep_research_agent(
            messages=messages,
            enabled_tools=[],
            deep_research_mode=False,
            config=config,
            tool_registry=tool_registry,
        ):
            print(chunk, end="", flush=True)

        print("\n" + "=" * 50)
        print("✅ Simple chat test completed successfully!")

    except Exception as e:
        print(f"\n❌ Simple chat test failed: {str(e)}")


async def test_web_search():
    """Test deep research mode with web search."""
    print("\n🧪 Testing Deep Research Mode with Web Search...")
    print("=" * 50)

    config = AppConfig()
    tool_registry = get_tool_registry(config)

    messages = [
        {
            "role": "user",
            "content": "What are the latest developments in AI and machine learning in 2024?",
        }
    ]

    try:
        async for chunk in deep_research_agent(
            messages=messages,
            enabled_tools=["web_search"],
            deep_research_mode=True,
            config=config,
            tool_registry=tool_registry,
        ):
            print(chunk, end="", flush=True)

        print("\n" + "=" * 50)
        print("✅ Web search test completed successfully!")

    except Exception as e:
        print(f"\n❌ Web search test failed: {str(e)}")


async def test_file_operations():
    """Test deep research mode with file operations."""
    print("\n🧪 Testing Deep Research Mode with File Operations...")
    print("=" * 50)

    config = AppConfig()
    tool_registry = get_tool_registry(config)

    messages = [
        {
            "role": "user",
            "content": "Create a Python script that demonstrates how to use async/await and save it to a file called 'async_example.py'.",
        }
    ]

    try:
        async for chunk in deep_research_agent(
            messages=messages,
            enabled_tools=["file_write"],
            deep_research_mode=True,
            config=config,
            tool_registry=tool_registry,
        ):
            print(chunk, end="", flush=True)

        print("\n" + "=" * 50)
        print("✅ File operations test completed successfully!")

    except Exception as e:
        print(f"\n❌ File operations test failed: {str(e)}")


async def test_multi_tool_research():
    """Test deep research mode with multiple tools."""
    print("\n🧪 Testing Deep Research Mode with Multiple Tools...")
    print("=" * 50)

    config = AppConfig()
    tool_registry = get_tool_registry(config)

    messages = [
        {
            "role": "user",
            "content": "Research the current weather in New York, find some recent news about climate change, and create a summary report saved to a file.",
        }
    ]

    try:
        async for chunk in deep_research_agent(
            messages=messages,
            enabled_tools=["web_search", "weather", "file_write"],
            deep_research_mode=True,
            config=config,
            tool_registry=tool_registry,
        ):
            print(chunk, end="", flush=True)

        print("\n" + "=" * 50)
        print("✅ Multi-tool research test completed successfully!")

    except Exception as e:
        print(f"\n❌ Multi-tool research test failed: {str(e)}")


async def test_conversation_continuity():
    """Test conversation continuity with multiple rounds."""
    print("\n🧪 Testing Conversation Continuity...")
    print("=" * 50)

    config = AppConfig()
    tool_registry = get_tool_registry(config)

    # Simulate a multi-turn conversation
    messages = [
        {"role": "user", "content": "What's the weather like in Paris?"},
        {"role": "assistant", "content": "I'll check the weather in Paris for you."},
        {
            "role": "user",
            "content": "Based on that weather, what activities would you recommend?",
        },
    ]

    try:
        async for chunk in deep_research_agent(
            messages=messages,
            enabled_tools=["weather", "web_search"],
            deep_research_mode=True,
            config=config,
            tool_registry=tool_registry,
        ):
            print(chunk, end="", flush=True)

        print("\n" + "=" * 50)
        print("✅ Conversation continuity test completed successfully!")

    except Exception as e:
        print(f"\n❌ Conversation continuity test failed: {str(e)}")


async def test_error_handling():
    """Test error handling with invalid tool requests."""
    print("\n🧪 Testing Error Handling...")
    print("=" * 50)

    config = AppConfig()
    tool_registry = get_tool_registry(config)

    messages = [
        {
            "role": "user",
            "content": "Use the nonexistent_tool to do something impossible.",
        }
    ]

    try:
        async for chunk in deep_research_agent(
            messages=messages,
            enabled_tools=["nonexistent_tool"],
            deep_research_mode=True,
            config=config,
            tool_registry=tool_registry,
        ):
            print(chunk, end="", flush=True)

        print("\n" + "=" * 50)
        print("✅ Error handling test completed successfully!")

    except Exception as e:
        print(f"\n❌ Error handling test failed: {str(e)}")


async def run_all_tests():
    """Run all test cases."""
    print("🚀 Starting Deep Research Agent Tests")
    print("=" * 60)

    # Check configuration
    try:
        config = AppConfig()
        config.validate_config()
        print("✅ Configuration validated successfully!")
    except Exception as e:
        print(f"❌ Configuration validation failed: {str(e)}")
        print("Please check your environment.env file and ensure API_KEY is set.")
        return

    # Run test cases
    test_cases = [
        ("Simple Chat", test_simple_chat),
        ("Web Search", test_web_search),
        ("File Operations", test_file_operations),
        ("Multi-Tool Research", test_multi_tool_research),
        ("Conversation Continuity", test_conversation_continuity),
        ("Error Handling", test_error_handling),
    ]

    results = []
    for name, test_func in test_cases:
        try:
            print(f"\n🧪 Running {name} test...")
            await test_func()
            results.append((name, "✅ PASSED"))
        except Exception as e:
            results.append((name, f"❌ FAILED: {str(e)}"))
            logger.error(f"Test {name} failed: {str(e)}")

    # Print summary
    print("\n" + "=" * 60)
    print("📊 TEST SUMMARY")
    print("=" * 60)

    for name, result in results:
        print(f"{name}: {result}")

    passed = sum(1 for _, result in results if result.startswith("✅"))
    total = len(results)
    print(f"\nTests passed: {passed}/{total}")

    if passed == total:
        print("🎉 All tests passed!")
    else:
        print(f"⚠️  {total - passed} tests failed. Check the logs for details.")


async def interactive_test():
    """Interactive test mode for manual testing."""
    print("\n🎮 Interactive Test Mode")
    print("=" * 50)
    print("Type your questions and see the agent respond in real-time.")
    print("Available tools: web_search, file_write, weather")
    print(
        "Type 'exit' to quit, 'tools' to toggle tools, 'mode' to toggle research mode"
    )
    print("=" * 50)

    config = AppConfig()
    tool_registry = get_tool_registry(config)

    # Interactive settings
    enabled_tools = ["web_search", "file_write", "weather"]
    deep_research_mode = True
    conversation_history = []

    while True:
        try:
            user_input = input("\n👤 You: ").strip()

            if user_input.lower() == "exit":
                print("👋 Goodbye!")
                break
            elif user_input.lower() == "tools":
                print(f"Current tools: {enabled_tools}")
                new_tools = input(
                    "Enter tools (comma-separated) or press Enter to keep current: "
                ).strip()
                if new_tools:
                    enabled_tools = [t.strip() for t in new_tools.split(",")]
                print(f"Tools updated to: {enabled_tools}")
                continue
            elif user_input.lower() == "mode":
                deep_research_mode = not deep_research_mode
                print(f"Deep research mode: {'ON' if deep_research_mode else 'OFF'}")
                continue
            elif not user_input:
                continue

            # Add user message to history
            conversation_history.append({"role": "user", "content": user_input})

            print("\n🤖 Agent: ", end="", flush=True)

            # Get agent response
            response_content = ""
            async for chunk in deep_research_agent(
                messages=conversation_history,
                enabled_tools=enabled_tools,
                deep_research_mode=deep_research_mode,
                config=config,
                tool_registry=tool_registry,
            ):
                print(chunk, end="", flush=True)
                response_content += chunk

            # Add assistant response to history
            conversation_history.append(
                {"role": "assistant", "content": response_content}
            )

            # Keep conversation history reasonable
            if len(conversation_history) > 10:
                conversation_history = conversation_history[-8:]

        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"\n❌ Error: {str(e)}")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "interactive":
        # Run interactive mode
        asyncio.run(interactive_test())
    else:
        # Run all tests
        asyncio.run(run_all_tests())

        # Optionally run interactive mode after tests
        if (
            input("\nWould you like to try interactive mode? (y/n): ")
            .lower()
            .startswith("y")
        ):
            asyncio.run(interactive_test())
