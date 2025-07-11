# Deep Research Agent Backend

A FastAPI backend for the deep research agent project that provides streaming chat responses.

## Features

- **Streaming Chat API**: `/chat` endpoint that streams responses character by character
- **Configuration Management**: Environment-based configuration using `.env` files
- **CORS Support**: Configurable CORS for frontend integration
- **Health Check**: `/health` endpoint for monitoring
- **Professional Code**: Type annotations, docstrings, and black formatting

## Quick Start

### 1. Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 2. Configure Environment

Create a `.env` file in the backend directory:

```bash
# Server Configuration
APP_HOST=localhost
APP_PORT=8000
DEBUG_MODE=true

# CORS Configuration
ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000

# API Configuration
API_TIMEOUT=30
MAX_REQUEST_SIZE=1048576

# Streaming Configuration
STREAMING_DELAY=0.05

# Logging Configuration
LOG_LEVEL=INFO

# Research Agent Configuration
MAX_RESEARCH_ITERATIONS=10
RESEARCH_TIMEOUT=300

# Tool Configuration
AVAILABLE_TOOLS=web_search,code_analysis,document_search

# LLM Configuration
LLM_MODEL=gpt-4
LLM_TEMPERATURE=0.7
LLM_MAX_TOKENS=4096

# Security Configuration
SECRET_KEY=your-secret-key-here
# API_KEY=your-api-key-here

# Rate Limiting Configuration
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_WINDOW=3600
```

### 3. Run the Server

```bash
# Option 1: Using uvicorn directly
uvicorn app:app --host localhost --port 8000 --reload

# Option 2: Using Python
python app.py
```

### 4. Test the API

```bash
# Health check
curl http://localhost:8000/health

# Chat endpoint
curl -X POST "http://localhost:8000/chat" \
     -H "Content-Type: application/json" \
     -d '{
       "messages": [
         {"role": "user", "content": "Hello, how are you?"},
         {"role": "assistant", "content": "I am doing well, thank you!"},
         {"role": "user", "content": "Can you help me with research?"}
       ],
       "tools": ["web_search", "code_analysis"],
       "deep_research_mode": true
     }'
```

## API Endpoints

### POST `/chat`

Streams a dummy response for chat messages.

**Request Body:**
```json
{
  "messages": [
    {"role": "user", "content": "Your message here"}
  ],
  "tools": ["web_search", "code_analysis"],
  "deep_research_mode": true
}
```

**Response:**
- Content-Type: `text/plain`
- Streaming response with character-by-character output

### GET `/health`

Returns health status of the API.

**Response:**
```json
{
  "status": "healthy"
}
```

## Configuration

All configuration is managed through environment variables or `.env` files. See `config.py` for available options.

Key configuration options:
- `APP_HOST`: Server host (default: localhost)
- `APP_PORT`: Server port (default: 8000)
- `DEBUG_MODE`: Enable debug mode (default: false)
- `ALLOWED_ORIGINS`: CORS allowed origins
- `STREAMING_DELAY`: Delay between characters in streaming (default: 0.05)

## Project Structure

```
backend/
├── app.py              # Main FastAPI application
├── config.py           # Configuration management
├── requirements.txt    # Python dependencies
├── __init__.py         # Package initialization
└── README.md          # This file
```

## Development

### Code Formatting

The code is formatted using `black`:

```bash
black app.py config.py
```

### Type Checking

The code includes type annotations for better development experience:

```bash
mypy app.py config.py
```

## Future Enhancements

The backend is designed to be easily extensible:

- **LLM Integration**: Add actual language model calls
- **Tool System**: Implement research tools (web search, code analysis, etc.)
- **Database**: Add persistence for chat history
- **Authentication**: Add user authentication and authorization
- **Rate Limiting**: Implement request rate limiting
- **Monitoring**: Add metrics and logging

## Notes

- This is a prototype implementation with dummy responses
- The streaming response simulates real-time communication
- Configuration is centralized in `config.py` to avoid hardcoded values
- All functions include proper docstrings and type annotations 