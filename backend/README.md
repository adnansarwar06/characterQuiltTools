# Deep Research Agent - Production-Ready Backend

A modular, production-ready deep research agent system built with FastAPI, featuring dynamic tool execution, streaming responses, and clean architecture.

## 🏗️ Architecture

The system is built with clean separation of concerns:

- **`llm.py`** - Core agent loop, LLM client, and streaming logic
- **`tools.py`** - Tool registry and execution system
- **`config.py`** - Configuration management
- **`app.py`** - FastAPI application and API endpoints
- **`test_agent.py`** - Test suite and development utilities

## 🚀 Features

- **Production-Ready**: Type annotations, logging, error handling, and documentation
- **Modular Design**: Clean separation between LLM, tools, and API layers
- **Streaming Support**: Real-time response streaming with tool execution updates
- **Dynamic Tool Loading**: Tools are loaded dynamically from the registry
- **Configuration Management**: Environment-based configuration with validation
- **Multi-Provider Support**: Extensible LLM client (OpenAI, with examples for others)
- **Comprehensive Testing**: Full test suite with interactive mode

## 📦 Installation

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure Environment**:
   ```bash
   cp environment.env.example environment.env
   # Edit environment.env and add your API_KEY
   ```

3. **Run the Application**:
   ```bash
   python run.py
   ```

## 🔧 Configuration

Edit `environment.env` to configure the system:

```env
# Required
API_KEY=your_openai_api_key_here

# Optional
LLM_MODEL=gpt-4-1106-preview
LLM_TEMPERATURE=0.7
MAX_RESEARCH_ITERATIONS=10
AVAILABLE_TOOLS=web_search,file_write,weather
```

## 🧪 Testing

### Run All Tests:
```bash
python test_agent.py
```

### Interactive Testing:
```bash
python test_agent.py interactive
```

### Test Individual Components:
```python
from config import AppConfig
from tools import get_tool_registry
from llm import deep_research_agent

# Your test code here
```

## 🛠️ Usage

### API Endpoints

- **POST `/chat`** - Main chat endpoint with streaming
- **GET `/health`** - Health check
- **GET `/tools`** - List available tools
- **GET `/config`** - Get configuration (non-sensitive)

### Chat Request Format:
```json
{
  "messages": [
    {"role": "user", "content": "What's the weather like in Paris?"}
  ],
  "tools": ["weather", "web_search"],
  "deep_research_mode": true
}
```

### Programmatic Usage:
```python
from llm import deep_research_agent
from config import AppConfig
from tools import get_tool_registry

config = AppConfig()
tool_registry = get_tool_registry(config)

messages = [{"role": "user", "content": "Research AI trends"}]

async for chunk in deep_research_agent(
    messages=messages,
    enabled_tools=["web_search"],
    deep_research_mode=True,
    config=config,
    tool_registry=tool_registry
):
    print(chunk, end="", flush=True)
```

## 🔌 Available Tools

- **`web_search`** - Search the web using DuckDuckGo
- **`file_write`** - Write content to files
- **`weather`** - Get weather information

## 🧩 Extending the System

### Adding New Tools:

1. **Register the Tool** in `tools.py`:
   ```python
   def my_custom_tool(self, param1: str, param2: int) -> ToolResult:
       # Implementation
       return ToolResult(success=True, data=result)
   
   # In _register_builtin_tools():
   self.register_tool("my_tool", self.my_custom_tool, schema)
   ```

2. **Add to Configuration**:
   ```env
   AVAILABLE_TOOLS=web_search,file_write,weather,my_tool
   ```

### Adding New LLM Providers:

The system is designed to support multiple LLM providers. Examples:

```python
# Ollama Integration
from ollama import AsyncClient

class OllamaLLMClient(LLMClient):
    def __init__(self, config):
        self.client = AsyncClient(host=config.ollama_host)
    
    async def create_chat_completion(self, **kwargs):
        # Implementation for Ollama
        pass

# Anthropic Integration
from anthropic import AsyncAnthropic

class AnthropicLLMClient(LLMClient):
    def __init__(self, config):
        self.client = AsyncAnthropic(api_key=config.anthropic_api_key)
```

## 🏃‍♂️ Development

### Code Quality:
- All code is formatted with `black`
- Type hints throughout
- Comprehensive docstrings
- Error handling and logging

### Running Development Server:
```bash
python run.py
```

### Running Tests:
```bash
python test_agent.py
```

## 🚀 Production Deployment

### Using Uvicorn:
```bash
uvicorn app:app --host 0.0.0.0 --port 8000
```

### Using Gunicorn:
```bash
gunicorn -w 4 -k uvicorn.workers.UvicornWorker app:app
```

### Docker:
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
```

## 🔐 Security

- API keys loaded from environment variables
- Input validation on all endpoints
- Rate limiting ready (configured in environment)
- File operations restricted to safe directories

## 📚 API Documentation

Start the server and visit:
- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

## 🐛 Troubleshooting

### Common Issues:

1. **Missing API Key**:
   ```
   ValueError: OpenAI API key is required
   ```
   Solution: Set `API_KEY` in `environment.env`

2. **Import Errors**:
   ```
   ModuleNotFoundError: No module named 'openai'
   ```
   Solution: `pip install -r requirements.txt`

3. **Port Already in Use**:
   ```
   Error: Port 8000 is already in use
   ```
   Solution: Change `APP_PORT` in `environment.env`

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests: `python test_agent.py`
5. Format code: `python -m black .`
6. Submit a pull request

## 📄 License

This project is licensed under the MIT License. 