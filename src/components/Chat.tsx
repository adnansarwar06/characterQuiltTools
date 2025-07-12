/**
 * Main Chat component for the research agent interface
 * Implements accuracy-first streaming with proper tool call handling
 */

import React, { useState, useRef, useEffect, useCallback } from 'react';
import { ChatMessage } from '../types/chat';
import { ToolIndicator } from './ToolIndicator';
import { ToolCallBubble } from './ToolCallBubble';
import { StreamingMessage, ToolExecutionIndicator } from './StreamingMessage';
import { ErrorNotificationContainer } from './ErrorNotification';
import { ToolSelector } from './ToolSelector';
import { useChat } from '../hooks/useChat';
import { useOpenAIChat } from '../hooks/useOpenAIChat';
import { config } from '../config/config';
import { useRobustStreaming } from '../utils/robust-streaming';

interface ChatProps {
  className?: string;
}

/**
 * Formats tool names for display (converts snake_case to Title Case)
 * @param toolName - Raw tool name from the backend
 * @returns Formatted tool name
 */
const formatToolName = (toolName: string): string => {
  const toolNameMappings: Record<string, string> = {
    'web_search': 'Web Search',
    'file_write': 'File Writer',
    'weather': 'Weather Info',
    'codebase_search': 'Code Search',
    'grep_search': 'Text Search',
    'read_file': 'File Reader',
    'list_dir': 'Directory List',
    'run_terminal_cmd': 'Terminal Command',
  };
  
  return toolNameMappings[toolName] || 
         toolName.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
};

/**
 * Main chat interface component
 * Handles message display, user input, tool selection, streaming, and error notifications
 * Implements accuracy-first streaming to ensure only correct content is displayed
 */
export const Chat: React.FC<ChatProps> = ({ className = '' }) => {
  const [inputValue, setInputValue] = useState('');
  const [showToolSelector, setShowToolSelector] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const messagesContainerRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  
  // Option 2: Use the OpenAI streaming hooks (RECOMMENDED - fixes random words and spelling errors)
  const {
    messages,
    isLoading,
    isConnected,
    currentToolCall,
    availableTools,
    activeToolCalls,
    errors,
    settings,
    streamingMessageId,
    bufferedContent,
    handleUserMessage,
    updateSettings,
    clearMessages,
    cancelCurrentRequest,
    loadAvailableTools,
    checkConnectivity,
    dismissError,
  } = useOpenAIChat();

  /**
   * Checks if user is near the bottom of the chat
   * @returns True if user is close to the bottom of the chat
   */
  const isNearBottom = (): boolean => {
    const messagesContainer = messagesContainerRef.current;
    if (!messagesContainer) return true;
    
    const threshold = 100; // pixels from bottom
    const { scrollTop, scrollHeight, clientHeight } = messagesContainer;
    return scrollTop + clientHeight >= scrollHeight - threshold;
  };

  /**
   * Scrolls to the bottom of the messages container only if user is near bottom
   * @param force - Whether to force scroll regardless of current position
   */
  const scrollToBottom = (force: boolean = false) => {
    if (force || isNearBottom()) {
      messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
  };

  /**
   * Handles form submission for sending messages
   * @param e - Form submission event
   */
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputValue.trim() || isLoading || !isConnected) return;

    const messageContent = inputValue.trim();
    setInputValue('');
    
    await handleUserMessage(messageContent);
  };

  /**
   * Handles keyboard shortcuts in the input field
   * @param e - Keyboard event
   */
  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    } else if (e.key === 'Escape' && isLoading) {
      e.preventDefault();
      cancelCurrentRequest();
    }
  };

  /**
   * Formats timestamp for display
   * @param timestamp - Date object to format
   * @returns Formatted time string
   */
  const formatTimestamp = (timestamp: Date): string => {
    return new Intl.DateTimeFormat('en-US', {
      hour: '2-digit',
      minute: '2-digit',
      hour12: true,
    }).format(timestamp);
  };

  /**
   * Toggles the tool selector visibility
   */
  const handleToggleToolSelector = () => {
    setShowToolSelector(prev => !prev);
  };

  /**
   * Handles refreshing available tools
   */
  const handleRefreshTools = async () => {
    await loadAvailableTools();
    await checkConnectivity();
  };

  /**
   * Renders a single chat message with enhanced streaming and tool support
   * Handles accuracy-first streaming and blocked message states
   * @param message - Chat message to render
   * @returns JSX element for the message
   */
  const renderMessage = (message: ChatMessage) => {
    const isUser = message.sender === 'user';
    const isStreaming = message.isStreaming && message.id === streamingMessageId;
    const isBlocked = message.isBlocked && activeToolCalls.length > 0;
    
    return (
      <div
        key={message.id}
        className={`message message--${message.sender} ${isStreaming ? 'message--streaming' : ''} ${isBlocked ? 'message--blocked' : ''}`}
        role="article"
        aria-label={`${isUser ? 'Your' : config.agentName} message`}
      >
        <div className="message__avatar">
          {isUser ? '👤' : '🤖'}
        </div>
        <div className="message__content">
          <div className="message__header">
            <span className="message__sender">
              {isUser ? 'You' : config.agentName}
            </span>
            <span className="message__timestamp">
              {formatTimestamp(message.timestamp)}
            </span>
            {isStreaming && (
              <span className="message__streaming-indicator" aria-label="Message is being generated">
                {isBlocked ? '🔧 Using tools' : '✨ Responding'}
              </span>
            )}
          </div>
          
          {/* Enhanced message content with accuracy-first streaming support */}
          <div className="message__text">
            {isUser ? (
              message.content
            ) : (
              <StreamingMessage
                message={message}
                isStreaming={isStreaming}
                onStreamingComplete={() => {
                  // Optional: Handle streaming completion
                }}
              />
            )}
          </div>
          
          {/* Show tool execution indicator for blocked messages */}
          {isBlocked && currentToolCall && (
            <div className="message__tool-execution" role="region" aria-label="Tool execution in progress">
              <ToolExecutionIndicator
                toolName={currentToolCall.toolName}
                className="message__tool-execution-indicator"
              />
            </div>
          )}
          
          {/* Enhanced tool call display */}
          {message.toolCalls && message.toolCalls.length > 0 && (
            <div className="message__tools" role="region" aria-label="Tool executions">
              {message.toolCalls.map(toolCall => (
                <ToolCallBubble
                  key={toolCall.id}
                  toolCall={toolCall}
                  className="message__tool-bubble"
                />
              ))}
            </div>
          )}
          
          {/* Show active tool calls for streaming messages */}
          {isStreaming && activeToolCalls.length > 0 && !isBlocked && (
            <div className="message__active-tools" role="region" aria-label="Active tool executions">
              {activeToolCalls.map(toolCall => (
                <ToolCallBubble
                  key={toolCall.id}
                  toolCall={toolCall}
                  className="message__tool-bubble message__tool-bubble--active"
                />
              ))}
            </div>
          )}
        </div>
      </div>
    );
  };

  // Auto-scroll to bottom when new messages arrive (but not during streaming updates)
  useEffect(() => {
    // Only auto-scroll if user is near the bottom or if this is a new message
    if (messages.length > 0) {
      const lastMessage = messages[messages.length - 1];
      const isNewMessage = !lastMessage.isStreaming || lastMessage.content === '';
      
      if (isNewMessage) {
        // Force scroll for new messages
        scrollToBottom(true);
      } else {
        // For streaming updates, only scroll if user is near bottom
        // Use a small timeout to avoid excessive scroll calls during rapid updates
        const timeoutId = setTimeout(() => {
          scrollToBottom(false);
        }, 100);
        
        return () => clearTimeout(timeoutId);
      }
    }
  }, [messages]);

  // Auto-scroll for tool calls only if user is near bottom
  useEffect(() => {
    scrollToBottom(false);
  }, [activeToolCalls]);

  // Focus input on mount and when loading stops
  useEffect(() => {
    if (!isLoading) {
      inputRef.current?.focus();
    }
  }, [isLoading]);

  const hasEnabledTools = settings.enabledTools.length > 0;
  const connectionStatusText = isConnected ? 'Backend Connected' : 'Backend Disconnected';
  const connectionStatusIcon = isConnected ? '🟢' : '🔴';

  return (
    <div className={`chat ${className}`} role="main" aria-label="Research agent chat">
      {/* Enhanced header with better accessibility */}
      <header className="chat__header">
        <div className="chat__title-section">
          <h1 className="chat__title">{config.agentName}</h1>
          <div className="chat__connection-status">
            <span className="chat__connection-icon" aria-hidden="true">
              {connectionStatusIcon}
            </span>
            <span className="chat__connection-text">
              {connectionStatusText}
            </span>
          </div>
        </div>
        
        <div className="chat__controls">
          <button
            type="button"
            className="chat__control-button"
            onClick={handleToggleToolSelector}
            aria-label="Configure research tools and settings"
            aria-expanded={showToolSelector}
            title="Configure tools and research mode"
          >
            🔧 Configure Tools ({settings.enabledTools.length} enabled)
          </button>
          
          <button
            type="button"
            className="chat__control-button"
            onClick={handleRefreshTools}
            aria-label="Reconnect to backend and refresh tools"
            disabled={!isConnected}
            title="Reconnect to backend server"
          >
            🔄 Reconnect
          </button>
          
          <button
            type="button"
            className="chat__control-button"
            onClick={clearMessages}
            aria-label="Clear conversation history"
            title="Clear all messages from this conversation"
          >
            🗑️ Clear Chat
          </button>
          
          {isLoading && (
            <button
              type="button"
              className="chat__control-button chat__control-button--cancel"
              onClick={cancelCurrentRequest}
              aria-label="Stop current response generation"
              title="Cancel the current response (press Escape)"
            >
              ⏹️ Stop Generation
            </button>
          )}
        </div>
      </header>

      {/* Tool selector panel */}
      {showToolSelector && (
        <div className="chat__tool-selector" role="region" aria-label="Research tools configuration">
          <ToolSelector
            availableTools={availableTools}
            settings={settings}
            onSettingsChange={updateSettings}
            disabled={isLoading || !isConnected}
            className="chat__tool-selector-panel"
          />
        </div>
      )}

      {/* Error notifications */}
      <ErrorNotificationContainer
        errors={errors}
        onDismiss={dismissError}
      />

      {/* Messages container */}
      <div
        ref={messagesContainerRef}
        className="chat__messages"
        role="log"
        aria-live="polite"
        aria-label="Chat messages"
      >
        {messages.length === 0 && (
          <div className="chat__empty-state">
            <div className="chat__empty-icon">💬</div>
            <h2 className="chat__empty-title">
              Welcome to {config.agentName}
            </h2>
            <p className="chat__empty-description">
              Ask me anything and I'll help you research, analyze, and solve problems.
              {hasEnabledTools && (
                <span> I have {settings.enabledTools.length} research tools available to help you.</span>
              )}
            </p>
            <p className="chat__empty-hint">
              <strong>Quick tips:</strong> Press Enter to send • Press Escape to stop • Shift+Enter for new line
            </p>
          </div>
        )}
        
        {messages.map(renderMessage)}
        
        {/* Show buffered content indicator if content is being buffered */}
        {bufferedContent.isBuffering && bufferedContent.chunks.length > 0 && (
          <div className="chat__buffered-indicator" role="status" aria-label="Processing response">
            <span className="chat__buffered-icon">⏳</span>
            <span className="chat__buffered-text">
              Processing response...
            </span>
          </div>
        )}
        
        <div ref={messagesEndRef} />
      </div>

      {/* Input form */}
      <form className="chat__input-form" onSubmit={handleSubmit}>
        <div className="chat__input-container">
          <input
            ref={inputRef}
            type="text"
            className="chat__input"
            placeholder={isConnected ? "Ask me anything..." : "Connecting to backend..."}
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={isLoading || !isConnected}
            aria-label="Message input"
            aria-describedby="input-help"
          />
          <button
            type="submit"
            className="chat__send-button"
            disabled={!inputValue.trim() || isLoading || !isConnected}
            aria-label="Send message"
            title={isLoading ? "Please wait..." : "Send your message"}
          >
            {isLoading ? '⏳' : '➤'}
          </button>
        </div>
        
        <div id="input-help" className="chat__input-help" aria-live="polite">
          {isLoading ? "Generating response..." : "Type your question and press Enter to send"}
        </div>
        
        {/* Status indicators */}
        <div className="chat__status-bar">
          <div className="chat__status-left">
            {currentToolCall && (
              <div className="chat__current-tool" role="status">
                <span className="chat__current-tool-icon">🔧</span>
                <span className="chat__current-tool-text">
                  Using: {formatToolName(currentToolCall.toolName)}
                </span>
              </div>
            )}
            
            {settings.deepResearchMode && (
              <div className="chat__deep-research-indicator" role="status">
                <span className="chat__deep-research-icon">🔍</span>
                <span className="chat__deep-research-text">
                  Deep Research Active
                </span>
              </div>
            )}
          </div>
          
          <div className="chat__status-right">
            <div className="chat__message-count">
              {messages.length} messages
            </div>
          </div>
        </div>
      </form>
    </div>
  );
}; 