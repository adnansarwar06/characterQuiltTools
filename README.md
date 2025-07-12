# AI Research Agent

A powerful AI research assistant with deep research capabilities, multi-tool integration, and a professional chat interface. This system combines advanced language models with real-time tool execution for comprehensive research tasks.

## 🚀 Features

### Core Capabilities
- **Deep Research Mode**: Multi-step research with iterative analysis and tool usage
- **Multi-Tool Integration**: Web search, file operations, weather data, and more
- **Real-time Streaming**: Live response generation with cancellation support
- **Professional UI**: Modern, accessible React interface with tool visualization
- **Flexible Architecture**: Modular backend with extensible tool system

### Research Modes
- **Deep Research**: Complex multi-step investigations with tool chaining
- **Quick Chat**: Direct answers with optional single-tool usage
- **Tool-Free Mode**: LLM-only responses using internal knowledge

### Built-in Tools
- **Web Search**: Real-time web research using DuckDuckGo
- **File Operations**: Create, read, and write files for research output
- **Weather Data**: Current weather information for any location
- **Extensible**: Easy to add custom tools for specific research needs

## 🏗️ Architecture

```
Frontend (React + TypeScript)
├── Professional chat interface
├── Tool call visualization
├── Real-time streaming
└── Configuration management

Backend (Python + FastAPI)
├── Deep research agent
├── Tool execution engine
├── Streaming API
└── Configuration system
```

## 📦 Installation

### Prerequisites
- **Node.js** (v16 or higher)
- **Python** (3.8 or higher)
- **OpenAI API Key** (required for LLM functionality)

### Quick Start

1. **Clone and Setup**:
   ```bash
   git clone <repository-url>
   cd ai-research-agent
   npm install
   ```

2. **Configure Backend**:
   ```bash
   cd backend
   pip install -r requirements.txt
   cp environment.env.example environment.env
   # Edit environment.env and add your OpenAI API key
   ```

3. **Start the System**:
   ```bash
   # Terminal 1: Start backend
   cd backend
   python run.py

   # Terminal 2: Start frontend
   npm start
   ```

4. **Access the Interface**:
   - Frontend: `http://localhost:3000`
   - API Documentation: `http://localhost:8000/docs`

## 🔧 Configuration

### Backend Configuration (`backend/environment.env`)
```env
# Required
API_KEY=your_openai_api_key_here

# Optional
LLM_MODEL=gpt-4-1106-preview
LLM_TEMPERATURE=0.7
MAX_RESEARCH_ITERATIONS=10
AVAILABLE_TOOLS=web_search,file_write,weather
APP_HOST=localhost
APP_PORT=8000
```

### Frontend Configuration (`.env`)
```env
REACT_APP_API_BASE_URL=http://localhost:8000
REACT_APP_WEBSOCKET_URL=ws://localhost:8000/ws
```

## 🎯 Usage

### Deep Research Mode
Perfect for complex investigations requiring multiple tools and analysis steps:

```
"Research the latest developments in AI coding assistants and their 
integration with IDEs in 2024. Create a comprehensive analysis document 
that includes current market trends, technical implementations, and code 
examples. Save your findings to a detailed report file."
```

### Quick Chat Mode
For direct questions with optional tool usage:

```
"What's the current weather in Paris?"
"Search for recent news about renewable energy"
```

### Tool Configuration
- **Enable/Disable Tools**: Use the tool selector in the UI
- **Deep Research Toggle**: Switch between modes as needed
- **Real-time Control**: Change settings during conversation

## 🛠️ Available Tools

### Web Search
- **Purpose**: Real-time web research and information gathering
- **Provider**: DuckDuckGo (no API key required)
- **Usage**: Automatic activation for research queries

### File Operations
- **Purpose**: Save research findings, create reports, manage documents
- **Features**: Create, read, write files with safety checks
- **Security**: Restricted to safe directories and file types

### Weather Data
- **Purpose**: Current weather information for any location
- **Features**: Temperature, conditions, humidity, wind speed
- **Coverage**: Global weather data

## 🔌 API Endpoints

### Chat API
- **POST** `/chat` - Main chat endpoint with streaming support
- **POST** `/chat/stream` - Server-sent events streaming

### System API
- **GET** `/health` - System health check
- **GET** `/tools` - List available tools
- **GET** `/config` - System configuration (non-sensitive)

### Example Request
```json
{
  "messages": [
    {"role": "user", "content": "Research AI trends in 2024"}
  ],
  "tools": ["web_search", "file_write"],
  "deep_research_mode": true
}
```

## 🎨 User Interface

### Chat Interface
- **Professional Design**: Clean, modern chat bubbles
- **Tool Visualization**: Real-time tool execution indicators
- **Streaming Support**: Live response generation
- **Cancellation**: Stop button for long-running operations

### Tool Controls
- **Tool Selector**: Enable/disable specific tools
- **Deep Research Toggle**: Switch between research modes
- **Settings Panel**: Configure system behavior
- **Status Indicators**: Real-time system status

### Accessibility
- **Keyboard Navigation**: Full keyboard support
- **Screen Reader Support**: Comprehensive ARIA labels
- **High Contrast**: Automatic support for accessibility preferences
- **Focus Management**: Proper focus handling throughout

## 🔧 Extending the System

### Adding New Tools

1. **Register Tool** (`backend/tools.py`):
   ```python
   def my_custom_tool(self, param1: str, param2: int) -> ToolResult:
       # Your tool implementation
       return ToolResult(success=True, data=result)
   ```

2. **Add Configuration**:
   ```env
   AVAILABLE_TOOLS=web_search,file_write,weather,my_custom_tool
   ```

3. **Update Frontend** (optional):
   Add tool-specific UI components if needed

### Custom LLM Providers
The system supports multiple LLM providers:
- **OpenAI** (default)
- **Anthropic** (with modifications)
- **Local models** (Ollama, etc.)

## 🚀 Production Deployment

### Backend Deployment
```bash
# Using Uvicorn
uvicorn app:app --host 0.0.0.0 --port 8000

# Using Gunicorn
gunicorn -w 4 -k uvicorn.workers.UvicornWorker app:app
```

### Frontend Deployment
```bash
npm run build
# Deploy build/ directory to your web server
```

### Docker Deployment
```dockerfile
# Backend
FROM python:3.11-slim
WORKDIR /app
COPY backend/requirements.txt .
RUN pip install -r requirements.txt
COPY backend/ .
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]

# Frontend
FROM node:18-alpine
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
RUN npm run build
CMD ["npx", "serve", "-s", "build"]
```

## 🔐 Security

### API Security
- **Environment Variables**: All sensitive data in environment files
- **Input Validation**: Comprehensive request validation
- **Rate Limiting**: Configurable request limits
- **CORS**: Proper cross-origin resource sharing

### Tool Security
- **File Operations**: Restricted to safe directories
- **Input Sanitization**: All tool inputs are validated
- **Error Handling**: Secure error messages without data leaks

## 📊 Performance

### Backend Performance
- **Streaming**: Real-time response generation
- **Async Operations**: Non-blocking tool execution
- **Connection Pooling**: Efficient resource management
- **Caching**: Configurable response caching

### Frontend Performance
- **React Optimization**: Proper memoization and state management
- **Bundle Size**: Optimized build with code splitting
- **Lazy Loading**: Dynamic component loading
- **Responsive Design**: Efficient rendering across devices

## 🔍 Monitoring & Debugging

### Logging
- **Comprehensive Logs**: Detailed system logging
- **Log Levels**: Configurable logging verbosity
- **Error Tracking**: Structured error logging
- **Performance Metrics**: Request timing and usage stats

### Health Checks
- **System Health**: `/health` endpoint monitoring
- **Tool Status**: Individual tool health checks
- **Configuration**: System configuration validation

## 📱 Browser Support

- **Chrome** (latest)
- **Firefox** (latest)
- **Safari** (latest)
- **Edge** (latest)
- **Mobile browsers** (iOS Safari, Chrome Mobile)

## 🤝 Support

For issues, questions, or contributions:
1. Check the API documentation at `/docs`
2. Review the configuration files
3. Check logs for error messages
4. Ensure all environment variables are set

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

---

**Built with**: React, TypeScript, Python, FastAPI, OpenAI API 