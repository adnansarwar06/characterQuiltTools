#!/usr/bin/env python3
"""
Quick test script for individual components.
"""

import asyncio
import sys
from config import AppConfig
from tools import get_tool_registry
from llm import deep_research_agent


async def test_config():
    """Test configuration loading."""
    try:
        config = AppConfig()
        config.validate_config()
        print("✅ Configuration loaded successfully")
        print(f"   Model: {config.llm_model}")
        print(f"   Tools: {config.available_tools}")
        return True
    except Exception as e:
        print(f"❌ Configuration failed: {e}")
        return False


async def test_tools():
    """Test tool registry."""
    try:
        config = AppConfig()
        tool_registry = get_tool_registry(config)
        tools = list(tool_registry.tool_schemas.keys())
        print(f"✅ Tools loaded: {tools}")
        return True
    except Exception as e:
        print(f"❌ Tools loading failed: {e}")
        return False


async def test_simple_chat():
    """Test simple chat functionality."""
    try:
        config = AppConfig()
        tool_registry = get_tool_registry(config)
        
        messages = [{"role": "user", "content": "Hello! Just say 'Hi' back."}]
        
        print("🤖 Agent Response:")
        response = ""
        async for chunk in deep_research_agent(
            messages=messages,
            enabled_tools=[],
            deep_research_mode=False,
            config=config,
            tool_registry=tool_registry
        ):
            print(chunk, end="", flush=True)
            response += chunk
        
        print("\n✅ Simple chat test completed")
        return len(response) > 0
        
    except Exception as e:
        print(f"❌ Simple chat failed: {e}")
        return False


async def test_web_search():
    """Test web search tool."""
    try:
        config = AppConfig()
        tool_registry = get_tool_registry(config)
        
        # Test web search directly
        result = await tool_registry.execute_tool("web_search", query="Python programming", num_results=3)
        
        if result.success:
            print("✅ Web search tool working")
            print(f"   Found {len(result.data)} results")
            return True
        else:
            print(f"❌ Web search failed: {result.error}")
            return False
            
    except Exception as e:
        print(f"❌ Web search test failed: {e}")
        return False


async def test_file_write():
    """Test file write tool."""
    try:
        config = AppConfig()
        tool_registry = get_tool_registry(config)
        
        # Test file write directly
        result = await tool_registry.execute_tool(
            "file_write", 
            filename="test.txt", 
            content="Hello, this is a test file!"
        )
        
        if result.success:
            print("✅ File write tool working")
            print(f"   File: {result.data['file_path']}")
            return True
        else:
            print(f"❌ File write failed: {result.error}")
            return False
            
    except Exception as e:
        print(f"❌ File write test failed: {e}")
        return False


async def test_weather():
    """Test weather tool."""
    try:
        config = AppConfig()
        tool_registry = get_tool_registry(config)
        
        # Test weather directly
        result = await tool_registry.execute_tool("weather", city="London")
        
        if result.success:
            print("✅ Weather tool working")
            print(f"   Location: {result.data['location']['city']}")
            print(f"   Temperature: {result.data['current']['temperature']}°C")
            return True
        else:
            print(f"❌ Weather failed: {result.error}")
            return False
            
    except Exception as e:
        print(f"❌ Weather test failed: {e}")
        return False


async def main():
    """Run all component tests."""
    print("🧪 Running Component Tests")
    print("=" * 40)
    
    tests = [
        ("Configuration", test_config),
        ("Tool Registry", test_tools),
        ("Simple Chat", test_simple_chat),
        ("Web Search", test_web_search),
        ("File Write", test_file_write),
        ("Weather", test_weather)
    ]
    
    results = []
    for name, test_func in tests:
        print(f"\n📋 Testing {name}...")
        try:
            success = await test_func()
            results.append((name, success))
        except Exception as e:
            print(f"❌ {name} test crashed: {e}")
            results.append((name, False))
    
    # Summary
    print("\n" + "=" * 40)
    print("📊 TEST SUMMARY")
    print("=" * 40)
    
    passed = 0
    for name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{name}: {status}")
        if success:
            passed += 1
    
    print(f"\nPassed: {passed}/{len(results)}")
    
    if passed == len(results):
        print("🎉 All tests passed!")
    else:
        print("⚠️  Some tests failed. Check the output above.")


if __name__ == "__main__":
    asyncio.run(main()) 