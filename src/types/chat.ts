/**
 * Type definitions for the research agent chat system
 */

export interface ChatMessage {
  id: string;
  content: string;
  sender: 'user' | 'agent';
  timestamp: Date;
  toolCalls?: ToolCall[];
  isStreaming?: boolean;
  streamingComplete?: boolean;
  isBlocked?: boolean; // New: indicates if message is blocked due to tool calls
}

export interface ToolCall {
  id: string;
  toolName: string;
  status: 'pending' | 'executing' | 'completed' | 'failed';
  parameters?: Record<string, any>;
  result?: any;
  error?: string;
  startTime?: Date;
  endTime?: Date;
  duration?: number;
}

/**
 * Streaming event types from backend
 */
export interface StreamingEvent {
  type: 'message_chunk' | 'tool_call_start' | 'tool_call_result' | 'iteration_start' | 'iteration_end' | 'agent_complete' | 'error';
  data: any;
  metadata?: Record<string, any>;
}

/**
 * Tool call event for real-time updates
 */
export interface ToolCallEvent {
  id: string;
  type: 'start' | 'progress' | 'result' | 'error';
  toolName: string;
  parameters?: Record<string, any>;
  result?: any;
  error?: string;
  timestamp: Date;
}

/**
 * Buffered content state for accuracy-first streaming
 */
export interface BufferedContent {
  chunks: string[];
  isBuffering: boolean;
  hasActiveToolCalls: boolean;
}

/**
 * Error notification types
 */
export interface ErrorNotification {
  id: string;
  type: 'api_error' | 'tool_error' | 'connection_error' | 'validation_error';
  title: string;
  message: string;
  timestamp: Date;
  dismissible: boolean;
  autoHide?: boolean;
  duration?: number;
}

/**
 * Available tool definition from backend
 */
export interface AvailableTool {
  name: string;
  description: string;
  enabled: boolean;
}

/**
 * Chat configuration settings
 */
export interface ChatSettings {
  enabledTools: string[];
  deepResearchMode: boolean;
}

/**
 * Enhanced chat state with streaming and error support
 */
export interface ChatState {
  messages: ChatMessage[];
  isLoading: boolean;
  isConnected: boolean;
  currentToolCall?: ToolCall;
  availableTools: AvailableTool[];
  settings: ChatSettings;
  activeToolCalls: ToolCall[];
  errors: ErrorNotification[];
  streamingMessageId?: string;
  bufferedContent: BufferedContent; // New: for accuracy-first streaming
}

/**
 * Request payload for sending messages to the backend
 */
export interface SendMessageRequest {
  messages: Array<{
    role: 'user' | 'assistant' | 'system';
    content: string;
  }>;
  tools: string[];
  deep_research_mode: boolean;
}

/**
 * Response from the backend tools endpoint
 */
export interface ToolsResponse {
  available_tools: string[];
  total_count: number;
  timestamp: string;
}

/**
 * Backend health check response
 */
export interface HealthResponse {
  status: 'healthy' | 'unhealthy';
  service: string;
  version: string;
  tools_available?: number;
  model?: string;
  timestamp: string;
  error?: string;
}

export interface SendMessageResponse {
  messageId: string;
  content: string;
  toolCalls?: ToolCall[];
} 