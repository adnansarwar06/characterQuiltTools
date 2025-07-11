/**
 * Main Chat component for the research agent interface
 */

import React, { useState, useRef, useEffect } from 'react';
import { ChatMessage } from '../types/chat';
import { ToolIndicator } from './ToolIndicator';
import { useChat } from '../hooks/useChat';
import { config } from '../config/config';

interface ChatProps {
  className?: string;
}

/**
 * Main chat interface component
 * Handles message display, user input, and tool call indicators
 */
export const Chat: React.FC<ChatProps> = ({ className = '' }) => {
  const [inputValue, setInputValue] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  
  const {
    messages,
    isLoading,
    isConnected,
    currentToolCall,
    handleUserMessage,
    clearMessages,
  } = useChat();

  /**
   * Scrolls to the bottom of the messages container
   */
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  /**
   * Handles form submission for sending messages
   */
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputValue.trim() || isLoading) return;

    const messageContent = inputValue.trim();
    setInputValue('');
    
    await handleUserMessage(messageContent);
  };

  /**
   * Handles keyboard shortcuts in the input field
   */
  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  /**
   * Formats timestamp for display
   */
  const formatTimestamp = (timestamp: Date): string => {
    return new Intl.DateTimeFormat('en-US', {
      hour: '2-digit',
      minute: '2-digit',
      hour12: true,
    }).format(timestamp);
  };

  /**
   * Renders a single chat message
   */
  const renderMessage = (message: ChatMessage) => {
    const isUser = message.sender === 'user';
    
    return (
      <div
        key={message.id}
        className={`message message--${message.sender}`}
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
          </div>
          <div className="message__text">
            {message.content}
          </div>
          {message.toolCalls && message.toolCalls.length > 0 && (
            <div className="message__tools">
              {message.toolCalls.map(toolCall => (
                <ToolIndicator
                  key={toolCall.id}
                  toolCall={toolCall}
                  className="message__tool-indicator"
                />
              ))}
            </div>
          )}
        </div>
      </div>
    );
  };

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Focus input on mount
  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  return (
    <div className={`chat ${className}`}>
      <div className="chat__header">
        <h1 className="chat__title">
          {config.agentName} Chat
        </h1>
        <div className="chat__status">
          <span
            className={`chat__connection-status ${
              isConnected ? 'chat__connection-status--connected' : 'chat__connection-status--disconnected'
            }`}
            aria-label={`Connection status: ${isConnected ? 'Connected' : 'Disconnected'}`}
          >
            {isConnected ? '🟢' : '🔴'}
          </span>
          <button
            type="button"
            className="chat__clear-button"
            onClick={clearMessages}
            aria-label="Clear all messages"
            title="Clear all messages"
          >
            🗑️
          </button>
        </div>
      </div>

      <div className="chat__messages" role="log" aria-live="polite">
        {messages.length === 0 ? (
          <div className="chat__empty-state">
            <div className="chat__empty-icon">💬</div>
            <p className="chat__empty-text">
              Start a conversation with {config.agentName}
            </p>
          </div>
        ) : (
          messages.map(renderMessage)
        )}
        
        {currentToolCall && (
          <div className="chat__current-tool-call">
            <ToolIndicator toolCall={currentToolCall} />
          </div>
        )}
        
        <div ref={messagesEndRef} />
      </div>

      <form className="chat__input-form" onSubmit={handleSubmit}>
        <div className="chat__input-container">
          <input
            ref={inputRef}
            type="text"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={`Message ${config.agentName}...`}
            className="chat__input"
            disabled={isLoading || !isConnected}
            aria-label="Message input"
            aria-describedby="chat-input-help"
          />
          <button
            type="submit"
            className="chat__send-button"
            disabled={isLoading || !isConnected || !inputValue.trim()}
            aria-label="Send message"
            title="Send message (Enter)"
          >
            {isLoading ? '⏳' : '📤'}
          </button>
        </div>
        <div id="chat-input-help" className="chat__input-help">
          Press Enter to send, Shift+Enter for new line
        </div>
      </form>
    </div>
  );
}; 