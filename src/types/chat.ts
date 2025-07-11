/**
 * Type definitions for the research agent chat system
 */

export interface ChatMessage {
  id: string;
  content: string;
  sender: 'user' | 'agent';
  timestamp: Date;
  toolCalls?: ToolCall[];
}

export interface ToolCall {
  id: string;
  toolName: string;
  status: 'pending' | 'executing' | 'completed' | 'failed';
  parameters?: Record<string, any>;
  result?: any;
  error?: string;
}

export interface ChatState {
  messages: ChatMessage[];
  isLoading: boolean;
  isConnected: boolean;
  currentToolCall?: ToolCall;
}

export interface SendMessageRequest {
  content: string;
  conversationId?: string;
}

export interface SendMessageResponse {
  messageId: string;
  content: string;
  toolCalls?: ToolCall[];
} 