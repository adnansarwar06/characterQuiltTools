/**
 * Enhanced tool call bubble component with animations and detailed status
 * Provides visual feedback for tool execution in accuracy-first streaming mode
 */

import React, { useState } from 'react';
import { ToolCall } from '../types/chat';

interface ToolCallBubbleProps {
  toolCall: ToolCall;
  className?: string;
  onExpand?: (expanded: boolean) => void;
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
 * Displays tool calls as animated bubbles with expandable details
 * Provides visual feedback for tool execution status and results
 * Supports accessibility with proper ARIA attributes and keyboard navigation
 */
export const ToolCallBubble: React.FC<ToolCallBubbleProps> = ({ 
  toolCall, 
  className = '',
  onExpand 
}) => {
  const [isExpanded, setIsExpanded] = useState(false);

  /**
   * Toggles the expanded state of the tool call details
   */
  const handleToggleExpand = () => {
    const newExpanded = !isExpanded;
    setIsExpanded(newExpanded);
    onExpand?.(newExpanded);
  };

  /**
   * Returns the appropriate status icon for the tool call state
   * @param status - Current tool call status
   * @returns Status icon emoji
   */
  const getStatusIcon = (status: ToolCall['status']): string => {
    switch (status) {
      case 'pending':
        return '⏳';
      case 'executing':
        return '⚡';
      case 'completed':
        return '✅';
      case 'failed':
        return '❌';
      default:
        return '⏳';
    }
  };

  /**
   * Returns the appropriate status color for the tool call state
   * @param status - Current tool call status
   * @returns CSS color value
   */
  const getStatusColor = (status: ToolCall['status']): string => {
    switch (status) {
      case 'pending':
        return '#f59e0b';
      case 'executing':
        return '#3b82f6';
      case 'completed':
        return '#10b981';
      case 'failed':
        return '#ef4444';
      default:
        return '#6b7280';
    }
  };

  /**
   * Returns user-friendly status text
   * @param status - Current tool call status
   * @returns Formatted status text
   */
  const getStatusText = (status: ToolCall['status']): string => {
    switch (status) {
      case 'pending':
        return 'Queued';
      case 'executing':
        return 'Running';
      case 'completed':
        return 'Complete';
      case 'failed':
        return 'Error';
      default:
        return 'Unknown';
    }
  };

  /**
   * Formats the execution duration if available
   * @returns Formatted duration string or null if not available
   */
  const formatDuration = (): string | null => {
    if (!toolCall.startTime || !toolCall.endTime) return null;
    const duration = toolCall.endTime.getTime() - toolCall.startTime.getTime();
    return `${(duration / 1000).toFixed(2)}s`;
  };

  /**
   * Formats tool parameters for display
   * @param params - Tool parameters object
   * @returns Formatted parameters string
   */
  const formatParameters = (params?: Record<string, any>): string => {
    if (!params || Object.keys(params).length === 0) return '';
    return Object.entries(params)
      .map(([key, value]) => `${key}: ${JSON.stringify(value)}`)
      .join(', ');
  };

  /**
   * Formats tool result for display
   * @param result - Tool execution result
   * @returns Formatted result string
   */
  const formatResult = (result: any): string => {
    if (!result) return '';
    if (typeof result === 'string') return result;
    if (typeof result === 'object') {
      return JSON.stringify(result, null, 2);
    }
    return String(result);
  };

  const formattedToolName = formatToolName(toolCall.toolName);
  const statusText = getStatusText(toolCall.status);
  const duration = formatDuration();

  return (
    <div
      className={`tool-call-bubble tool-call-bubble--${toolCall.status} ${className}`}
      role="region"
      aria-label={`Tool execution: ${formattedToolName}`}
      style={{ '--status-color': getStatusColor(toolCall.status) } as React.CSSProperties}
    >
      <div 
        className="tool-call-bubble__header" 
        onClick={handleToggleExpand}
        role="button"
        tabIndex={0}
        aria-expanded={isExpanded}
        aria-controls={`tool-details-${toolCall.id}`}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            handleToggleExpand();
          }
        }}
      >
        <div className="tool-call-bubble__status-indicator">
          <span className="tool-call-bubble__icon" aria-hidden="true">
            {getStatusIcon(toolCall.status)}
          </span>
          {toolCall.status === 'executing' && (
            <div className="tool-call-bubble__pulse" aria-hidden="true" />
          )}
        </div>
        
        <div className="tool-call-bubble__info">
          <div className="tool-call-bubble__title">
            <span className="tool-call-bubble__tool-name">
              {formattedToolName}
            </span>
            <span className="tool-call-bubble__status-text">
              {statusText}
            </span>
          </div>
          
          {toolCall.parameters && (
            <div className="tool-call-bubble__parameters">
              {formatParameters(toolCall.parameters)}
            </div>
          )}
          
          {duration && (
            <div className="tool-call-bubble__duration">
              Completed in {duration}
            </div>
          )}
        </div>
        
        <div className="tool-call-bubble__expand-indicator">
          <span 
            className={`tool-call-bubble__chevron ${isExpanded ? 'tool-call-bubble__chevron--expanded' : ''}`}
            aria-hidden="true"
          >
            ⌄
          </span>
        </div>
      </div>
      
      {isExpanded && (
        <div 
          id={`tool-details-${toolCall.id}`}
          className="tool-call-bubble__details"
          role="region"
          aria-label="Tool execution details"
        >
          {toolCall.parameters && Object.keys(toolCall.parameters).length > 0 && (
            <div className="tool-call-bubble__section">
              <h4 className="tool-call-bubble__section-title">Input Parameters</h4>
              <pre className="tool-call-bubble__code">
                {JSON.stringify(toolCall.parameters, null, 2)}
              </pre>
            </div>
          )}
          
          {toolCall.result && (
            <div className="tool-call-bubble__section">
              <h4 className="tool-call-bubble__section-title">Output</h4>
              <pre className="tool-call-bubble__code tool-call-bubble__code--result">
                {formatResult(toolCall.result)}
              </pre>
            </div>
          )}
          
          {toolCall.error && (
            <div className="tool-call-bubble__section">
              <h4 className="tool-call-bubble__section-title">Error Details</h4>
              <div className="tool-call-bubble__error-message">
                {toolCall.error}
              </div>
            </div>
          )}
          
          <div className="tool-call-bubble__section">
            <h4 className="tool-call-bubble__section-title">Execution Details</h4>
            <div className="tool-call-bubble__metadata">
              <div>ID: <code>{toolCall.id}</code></div>
              {toolCall.startTime && (
                <div>Started: {toolCall.startTime.toLocaleTimeString()}</div>
              )}
              {toolCall.endTime && (
                <div>Completed: {toolCall.endTime.toLocaleTimeString()}</div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}; 