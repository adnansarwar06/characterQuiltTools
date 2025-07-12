/**
 * Component for displaying tool call indicators in the chat
 */

import React from 'react';
import { ToolCall } from '../types/chat';

interface ToolIndicatorProps {
  toolCall: ToolCall;
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
 * Displays a visual indicator for active tool calls
 * Shows tool name, status, and loading animation
 */
export const ToolIndicator: React.FC<ToolIndicatorProps> = ({ toolCall, className = '' }) => {
  const getStatusIcon = (status: ToolCall['status']): string => {
    switch (status) {
      case 'pending':
        return '⏳';
      case 'executing':
        return '🔄';
      case 'completed':
        return '✅';
      case 'failed':
        return '❌';
      default:
        return '⏳';
    }
  };

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

  const formattedToolName = formatToolName(toolCall.toolName);
  const statusText = getStatusText(toolCall.status);

  return (
    <div
      className={`tool-indicator tool-indicator--${toolCall.status} ${className}`}
      role="status"
      aria-label={`Tool call: ${formattedToolName} - ${statusText}`}
    >
      <div className="tool-indicator__icon">
        {getStatusIcon(toolCall.status)}
      </div>
      <div className="tool-indicator__content">
        <div className="tool-indicator__title">
          Using Tool: {formattedToolName}
        </div>
        <div className="tool-indicator__status">
          {statusText}
        </div>
        {toolCall.error && (
          <div className="tool-indicator__error">
            Failed: {toolCall.error}
          </div>
        )}
      </div>
      {toolCall.status === 'executing' && (
        <div className="tool-indicator__spinner" aria-hidden="true">
          <div className="spinner"></div>
        </div>
      )}
    </div>
  );
}; 