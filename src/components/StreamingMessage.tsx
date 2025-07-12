/**
 * Streaming message component for real-time token rendering
 * Implements accuracy-first streaming: blocks display during tool calls
 * and only shows finalized, correct agent responses
 */

import React, { useState, useEffect, useRef } from 'react';
import { ChatMessage } from '../types/chat';

interface StreamingMessageProps {
  message: ChatMessage;
  isStreaming?: boolean;
  className?: string;
  onStreamingComplete?: () => void;
}

/**
 * Displays messages with real-time streaming animation
 * Shows appropriate placeholders during tool calls to ensure accuracy
 * Only displays finalized content after tool completion
 */
export const StreamingMessage: React.FC<StreamingMessageProps> = ({
  message,
  isStreaming = false,
  className = '',
  onStreamingComplete
}) => {
  const [displayedContent, setDisplayedContent] = useState('');
  const [showCursor, setShowCursor] = useState(isStreaming);
  const contentRef = useRef<HTMLDivElement>(null);
  const lastContentRef = useRef('');

  // Handle streaming content updates with accuracy-first logic
  useEffect(() => {
    if (message.content !== lastContentRef.current) {
      // Sanitize content to remove any problematic characters
      const sanitizedContent = sanitizeContent(message.content);
      
      // If message is blocked due to tool calls, don't update display
      if (message.isBlocked) {
        lastContentRef.current = message.content;
        return;
      }
      
      if (isStreaming && !message.isBlocked) {
        // In streaming mode, animate the new content
        const lastSanitizedContent = sanitizeContent(lastContentRef.current);
        const newContent = sanitizedContent.slice(lastSanitizedContent.length);
        if (newContent) {
          animateNewContent(newContent);
        }
      } else {
        // Not streaming or blocked, show content immediately
        setDisplayedContent(sanitizedContent);
      }
      lastContentRef.current = message.content;
    }
  }, [message.content, message.isBlocked, isStreaming]);

  // Handle streaming state changes
  useEffect(() => {
    // Only show cursor if streaming and not blocked
    setShowCursor(isStreaming && !message.isBlocked);
    
    if (!isStreaming && message.streamingComplete) {
      // Streaming completed - use sanitized content
      setDisplayedContent(sanitizeContent(message.content));
      onStreamingComplete?.();
    }
  }, [isStreaming, message.streamingComplete, message.isBlocked, onStreamingComplete]);

  /**
   * Animates new content character by character for natural typing effect
   * @param newContent - New content to animate
   */
  const animateNewContent = (newContent: string) => {
    let charIndex = 0;
    
    const animateChar = () => {
      if (charIndex < newContent.length && !message.isBlocked) {
        setDisplayedContent(prev => prev + newContent[charIndex]);
        charIndex++;
        // Randomize typing speed for more natural feel
        const delay = Math.random() * 30 + 10; // 10-40ms per character
        setTimeout(animateChar, delay);
      }
    };

    animateChar();
  };

  // Auto-scroll to bottom when content changes
  useEffect(() => {
    if (contentRef.current) {
      contentRef.current.scrollTop = contentRef.current.scrollHeight;
    }
  }, [displayedContent]);

  /**
   * Sanitizes content to remove problematic characters
   * @param content - Content to sanitize
   * @returns Cleaned content safe for display
   */
  const sanitizeContent = (content: string): string => {
    if (!content) return '';
    
    // Remove null characters and other problematic control characters
    // but keep newlines, tabs, and carriage returns
    return content.replace(/[\x00-\x08\x0B\x0C\x0E-\x1F\x7F-\x9F]/g, '');
  };

  /**
   * Renders the appropriate content based on message state
   * @returns JSX element for the message content
   */
  const renderMessageContent = () => {
    // If message is blocked due to tool calls, show placeholder
    if (message.isBlocked && isStreaming) {
      return (
        <div className="streaming-message__blocked">
          <div className="streaming-message__tool-placeholder">
            <span className="streaming-message__tool-icon" aria-hidden="true">
              🔧
            </span>
            <span className="streaming-message__tool-text">
              Using research tools...
            </span>
            <div className="streaming-message__tool-spinner" aria-hidden="true">
              <span></span>
              <span></span>
              <span></span>
            </div>
          </div>
        </div>
      );
    }

    // Normal content display
    return (
      <div 
        className="streaming-message__text"
        style={{ 
          whiteSpace: 'pre-wrap', 
          wordBreak: 'break-word',
          fontFamily: 'ui-monospace, SFMono-Regular, "SF Mono", Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace'
        }}
      >
        {displayedContent}
        {isStreaming && !message.isBlocked && (
          <span 
            className={`streaming-message__cursor ${showCursor ? 'streaming-message__cursor--visible' : ''}`}
            aria-hidden="true"
          >
            |
          </span>
        )}
      </div>
    );
  };

  return (
    <div 
      className={`streaming-message ${className}`}
      role="article"
      aria-live={isStreaming ? 'polite' : 'off'}
      aria-atomic="false"
    >
      <div 
        ref={contentRef}
        className="streaming-message__content"
      >
        {renderMessageContent()}
      </div>
      
      {isStreaming && !message.isBlocked && (
        <div 
          className="streaming-message__status"
          role="status"
          aria-label="Message is being generated"
        >
          <span className="streaming-message__typing-indicator">
            <span></span>
            <span></span>
            <span></span>
          </span>
          <span className="streaming-message__status-text">
            Generating response...
          </span>
        </div>
      )}
    </div>
  );
};

interface TypingIndicatorProps {
  className?: string;
  message?: string;
}

/**
 * Standalone typing indicator component
 * Shows animated dots to indicate AI is processing
 */
export const TypingIndicator: React.FC<TypingIndicatorProps> = ({
  className = '',
  message = 'Processing your request...'
}) => {
  return (
    <div 
      className={`typing-indicator ${className}`}
      role="status"
      aria-label={message}
    >
      <div className="typing-indicator__content">
        <div className="typing-indicator__dots">
          <span></span>
          <span></span>
          <span></span>
        </div>
        <span className="typing-indicator__text">
          {message}
        </span>
      </div>
    </div>
  );
};

interface ToolExecutionIndicatorProps {
  toolName?: string;
  className?: string;
}

/**
 * Tool execution indicator component
 * Shows when tools are being executed with accuracy-first approach
 */
export const ToolExecutionIndicator: React.FC<ToolExecutionIndicatorProps> = ({
  toolName,
  className = ''
}) => {
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

  const displayName = toolName ? formatToolName(toolName) : 'Tool';
  
  return (
    <div 
      className={`tool-execution-indicator ${className}`}
      role="status"
      aria-label={`Using ${displayName}`}
    >
      <div className="tool-execution-indicator__content">
        <span className="tool-execution-indicator__icon" aria-hidden="true">
          🔧
        </span>
        <span className="tool-execution-indicator__text">
          Using {displayName}...
        </span>
        <div className="tool-execution-indicator__spinner" aria-hidden="true">
          <span></span>
          <span></span>
          <span></span>
        </div>
      </div>
    </div>
  );
};