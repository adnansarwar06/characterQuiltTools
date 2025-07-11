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
        return 'Pending';
      case 'executing':
        return 'Executing';
      case 'completed':
        return 'Completed';
      case 'failed':
        return 'Failed';
      default:
        return 'Unknown';
    }
  };

  return (
    <div
      className={`tool-indicator tool-indicator--${toolCall.status} ${className}`}
      role="status"
      aria-label={`Tool call: ${toolCall.toolName} - ${getStatusText(toolCall.status)}`}
    >
      <div className="tool-indicator__icon">
        {getStatusIcon(toolCall.status)}
      </div>
      <div className="tool-indicator__content">
        <div className="tool-indicator__title">
          Calling Tool: {toolCall.toolName}
        </div>
        <div className="tool-indicator__status">
          {getStatusText(toolCall.status)}
        </div>
        {toolCall.error && (
          <div className="tool-indicator__error">
            Error: {toolCall.error}
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