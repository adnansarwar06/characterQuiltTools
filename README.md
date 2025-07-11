# Research Agent Chat UI

A professional React-based chat interface prototype for deep research agent interactions. This UI provides a modern, accessible chat experience with support for tool call visualization and real-time communication.

## Features

- **Professional Chat Interface**: Clean, modern design with distinct user and agent message bubbles
- **Tool Call Indicators**: Visual indicators showing when the agent is using tools (Web Search, Code Analysis, etc.)
- **Real-time Communication**: WebSocket support for live chat interactions
- **Accessibility First**: Full ARIA support, keyboard navigation, and screen reader compatibility
- **Responsive Design**: Works seamlessly across desktop, tablet, and mobile devices
- **Configuration-Driven**: All settings loaded from environment variables or config files
- **TypeScript Support**: Full type safety throughout the application
- **Professional Code Quality**: JSDoc comments, proper error handling, and modular architecture

## Prerequisites

- Node.js (v16 or higher)
- npm or yarn package manager

## Installation

1. Clone the repository or extract the project files
2. Install dependencies:

```bash
npm install
```

## Configuration

### Environment Variables

Create a `.env` file in the project root with the following variables:

```env
REACT_APP_API_BASE_URL=http://localhost:8000/api
REACT_APP_WEBSOCKET_URL=ws://localhost:8000/ws
REACT_APP_AGENT_NAME=Research Agent
REACT_APP_TOOLS_WEB_SEARCH=Web Search
REACT_APP_TOOLS_CODE_ANALYSIS=Code Analysis
REACT_APP_TOOLS_FILE_READER=File Reader
REACT_APP_TOOLS_DOCUMENT_SEARCH=Document Search
```

### Configuration File

Alternatively, you can modify the configuration in `src/config/config.ts`:

```typescript
export const config: AppConfig = {
  apiBaseUrl: 'http://localhost:8000/api',
  websocketUrl: 'ws://localhost:8000/ws',
  agentName: 'Research Agent',
  tools: {
    webSearch: 'Web Search',
    codeAnalysis: 'Code Analysis',
    fileReader: 'File Reader',
    documentSearch: 'Document Search',
  },
};
```

## Usage

### Development

Start the development server:

```bash
npm start
```

The application will be available at `http://localhost:3000`.

### Production Build

Create a production build:

```bash
npm run build
```

The built files will be in the `build` directory.

### Code Formatting

Format code using Prettier:

```bash
npm run format
```

## Project Structure

```
src/
├── components/
│   ├── Chat.tsx              # Main chat component
│   └── ToolIndicator.tsx     # Tool call indicator component
├── hooks/
│   └── useChat.ts            # Chat state management hook
├── utils/
│   └── api.ts                # API utility functions
├── config/
│   └── config.ts             # Configuration management
├── types/
│   └── chat.ts               # TypeScript type definitions
├── styles/
│   └── global.css            # Global styles
└── index.tsx                 # Application entry point
```

## Component Overview

### Chat Component (`src/components/Chat.tsx`)

The main chat interface component that handles:
- Message display with user/agent distinction
- User input and message sending
- Tool call visualization
- Real-time updates
- Accessibility features

### ToolIndicator Component (`src/components/ToolIndicator.tsx`)

Displays tool call status with:
- Visual icons for different states (pending, executing, completed, failed)
- Loading animations
- Error handling
- Accessibility labels

### useChat Hook (`src/hooks/useChat.ts`)

Custom React hook managing:
- Chat state (messages, loading, connection)
- Message sending and receiving
- Tool call updates
- Connection status simulation

## API Integration

The application is designed to work with a backend API. For the prototype, it uses simulated responses. To integrate with a real backend:

1. Update the API client in `src/utils/api.ts`
2. Replace `simulateSendMessage` with actual API calls
3. Implement WebSocket connections for real-time updates

## Accessibility Features

- **Keyboard Navigation**: Full keyboard support for all interactive elements
- **Screen Reader Support**: ARIA labels, roles, and live regions
- **High Contrast Mode**: Automatic support for high contrast display preferences
- **Reduced Motion**: Respects user preferences for reduced motion
- **Focus Management**: Proper focus handling and visible focus indicators

## Browser Support

- Chrome (latest)
- Firefox (latest)
- Safari (latest)
- Edge (latest)

## Development Guidelines

### Code Style

- Use TypeScript for all new code
- Follow the existing naming conventions
- Add JSDoc comments for all functions and components
- Use semantic HTML elements
- Implement proper error handling

### Testing

Run tests with:

```bash
npm test
```

### Linting

The project uses ESLint and TypeScript compiler for code quality:

```bash
npm run lint
```

## Customization

### Styling

Modify `src/styles/global.css` to customize the appearance:
- Colors and themes
- Typography
- Layout and spacing
- Animations and transitions

### Tool Integration

Add new tools by:
1. Updating the configuration in `src/config/config.ts`
2. Adding new tool types to `src/types/chat.ts`
3. Implementing tool-specific logic in `src/hooks/useChat.ts`

## Performance Considerations

- Uses React.memo for component optimization
- Implements proper cleanup in useEffect hooks
- Uses CSS animations for smooth interactions
- Lazy loading for large message histories

## Security

- Input sanitization for user messages
- XSS prevention through proper React rendering
- CSRF protection for API calls
- Environment variable validation

## Contributing

1. Follow the existing code style and patterns
2. Add proper TypeScript types for new features
3. Include JSDoc comments for all public functions
4. Test accessibility features
5. Update documentation for new features

## License

This project is licensed under the MIT License. 