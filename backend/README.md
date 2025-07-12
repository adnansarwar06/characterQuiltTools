# AI Research Agent Backend

A production-ready backend system for AI research with deep research capabilities, multi-tool integration, and streaming responses.

## 🏗️ Architecture

```
Backend System
├── llm.py          # Core agent logic and LLM integration
├── tools.py        # Tool registry and execution engine
├── config.py       # Configuration management
├── app.py          # FastAPI application and endpoints
└── run.py          # Application entry point
```

## 🚀 Features

- **Deep Research Mode**: Multi-step research with iterative analysis
- **Tool Integration**: Web search, file operations, weather data
- **Streaming API**: Real-time response generation
- **Flexible Configuration**: Environment-based settings
- **Production Ready**: Comprehensive error handling and logging

## 📦 Installation

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure Environment**:
   ```bash
   cp environment.env.example environment.env
   # Edit environment.env and add your OpenAI API key
   ```

3. **Start the Server**:
   ```bash
   python run.py
   ```

## 🔧 Configuration

### Required Settings (`environment.env`)
```env
# OpenAI API Configuration
API_KEY=your_openai_api_key_here

# Optional Settings
LLM_MODEL=gpt-4-1106-preview
LLM_TEMPERATURE=0.7
MAX_RESEARCH_ITERATIONS=10
AVAILABLE_TOOLS=web_search,file_write,weather
APP_HOST=localhost
APP_PORT=8000
```

### Configuration Options
- **API_KEY**: OpenAI API key (required)
- **LLM_MODEL**: OpenAI model to use
- **LLM_TEMPERATURE**: Response creativity (0.0-2.0)
- **MAX_RESEARCH_ITERATIONS**: Maximum research steps
- **AVAILABLE_TOOLS**: Comma-separated list of enabled tools

## 🛠️ Available Tools

### Web Search
- **Function**: Real-time web research
- **Provider**: DuckDuckGo (no API key required)
- **Usage**: Automatic for research queries

### File Operations
- **Function**: Create, read, write files
- **Security**: Restricted to safe directories
- **Formats**: Text, JSON, CSV, Markdown

### Weather Data
- **Function**: Current weather information
- **Coverage**: Global weather data
- **Details**: Temperature, conditions, humidity

## 🔌 API Endpoints

### Chat Endpoints
```
POST /chat
- Main chat endpoint with streaming support
- Request body: ChatRequest
- Response: Streaming text/plain

POST /chat/stream
- Server-sent events streaming
- Request body: ChatRequest
- Response: text/event-stream
```

### System Endpoints
```
GET /health
- System health check
- Response: {"status": "healthy", "timestamp": "..."}

GET /tools
- List available tools
- Response: {"tools": [...]}

GET /config
- System configuration (non-sensitive)
- Response: {"config": {...}}
```

### Request Format
```json
{
  "messages": [
    {"role": "user", "content": "Your research question"}
  ],
  "tools": ["web_search", "file_write"],
  "deep_research_mode": true
}
```

## 🎯 Usage Examples

### Deep Research Mode
```python
import requests

response = requests.post("http://localhost:8000/chat", json={
    "messages": [
        {"role": "user", "content": "Research AI trends in 2024"}
    ],
    "tools": ["web_search", "file_write"],
    "deep_research_mode": True
})
```

### Quick Chat Mode
```python
response = requests.post("http://localhost:8000/chat", json={
    "messages": [
        {"role": "user", "content": "What's the weather in Paris?"}
    ],
    "tools": ["weather"],
    "deep_research_mode": False
})
```

### Streaming Chat
```python
import requests

response = requests.post(
    "http://localhost:8000/chat/stream",
    json={
        "messages": [{"role": "user", "content": "Research question"}],
        "tools": ["web_search"],
        "deep_research_mode": True
    },
    stream=True
)

for chunk in response.iter_content(chunk_size=None):
    if chunk:
        print(chunk.decode(), end="", flush=True)
```

## 🔧 Tool Extension

### Adding Custom Tools

1. **Define Tool Function** (`tools.py`):
   ```python
   def my_custom_tool(self, param1: str, param2: int) -> ToolResult:
       """Custom tool description"""
       try:
           # Your tool implementation
           result = perform_operation(param1, param2)
           return ToolResult(success=True, data=result)
       except Exception as e:
           return ToolResult(success=False, error=str(e))
   ```

2. **Register Tool**:
   ```python
   def _register_builtin_tools(self):
       # ... existing tools ...
       
       self.register_tool(
           "my_custom_tool",
           self.my_custom_tool,
           {
               "type": "function",
               "function": {
                   "name": "my_custom_tool",
                   "description": "Description of your tool",
                   "parameters": {
                       "type": "object",
                       "properties": {
                           "param1": {"type": "string"},
                           "param2": {"type": "integer"}
                       },
                       "required": ["param1", "param2"]
                   }
               }
           }
       )
   ```

3. **Enable Tool**:
   ```env
   AVAILABLE_TOOLS=web_search,file_write,weather,my_custom_tool
   ```

## 🚀 Production Deployment

### Using Uvicorn
```bash
uvicorn app:app --host 0.0.0.0 --port 8000 --workers 4
```

### Using Gunicorn
```bash
gunicorn -w 4 -k uvicorn.workers.UvicornWorker app:app --bind 0.0.0.0:8000
```

### Docker Deployment
```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Environment Variables for Production
```env
# Production settings
API_KEY=your_production_api_key
APP_HOST=0.0.0.0
APP_PORT=8000
LOG_LEVEL=INFO

# Performance settings
MAX_RESEARCH_ITERATIONS=15
LLM_MAX_TOKENS=4096
REQUEST_TIMEOUT=300
```

## 🔐 Security

### API Security
- **Environment Variables**: All sensitive data externalized
- **Input Validation**: Comprehensive request validation
- **Error Handling**: Secure error messages
- **Rate Limiting**: Configurable request limits

### Tool Security
- **File Operations**: Restricted to safe directories
- **Input Sanitization**: All parameters validated
- **Dangerous Extensions**: Blocked file types (.exe, .bat, etc.)

## 📊 Performance

### Optimization Features
- **Async Operations**: Non-blocking tool execution
- **Streaming**: Real-time response generation
- **Connection Pooling**: Efficient HTTP client usage
- **Memory Management**: Proper resource cleanup

### Performance Monitoring
- **Request Timing**: Built-in performance logging
- **Error Tracking**: Comprehensive error logging
- **Health Checks**: System status monitoring

## 🔍 Monitoring & Debugging

### Logging
```python
import logging

# Configure logging level
logging.basicConfig(level=logging.INFO)

# View logs
tail -f app.log
```

### Health Monitoring
```bash
# Check system health
curl http://localhost:8000/health

# Check available tools
curl http://localhost:8000/tools

# Check configuration
curl http://localhost:8000/config
```

## 🔧 Troubleshooting

### Common Issues

1. **API Key Error**:
   ```
   ValueError: OpenAI API key is required
   ```
   **Solution**: Set `API_KEY` in `environment.env`

2. **Port Already in Use**:
   ```
   Error: Port 8000 is already in use
   ```
   **Solution**: Change `APP_PORT` in `environment.env`

3. **Tool Import Error**:
   ```
   ImportError: Tool 'web_search' not found
   ```
   **Solution**: Check `AVAILABLE_TOOLS` configuration

4. **Memory Issues**:
   ```
   Out of memory during research
   ```
   **Solution**: Reduce `MAX_RESEARCH_ITERATIONS`

## 📚 API Documentation

Once the server is running, access:
- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

## 🤝 Integration

### Frontend Integration
The backend is designed to work with the React frontend:
- **CORS**: Configured for frontend domain
- **WebSocket**: Real-time communication support
- **Streaming**: Compatible with frontend streaming hooks

### Third-party Integration
- **Webhook Support**: Add webhooks for external integrations
- **API Keys**: Support for multiple API key management
- **Custom Headers**: Configurable request headers

## 📄 License

MIT License - see LICENSE file for details. 