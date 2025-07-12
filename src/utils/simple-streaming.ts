import { ChatMessage, ToolCall, SendMessageRequest } from '../types/chat';
import { config } from '../config/config';

export interface StreamingEvent {
  type: 'content' | 'toolStart' | 'toolEnd' | 'error' | 'complete';
  data: string;
  toolCall?: ToolCall;
  error?: string;
}

export class SimpleStreamingClient {
  private controller?: AbortController;
  private callbacks: {
    onContent: (content: string) => void;
    onToolCall: (toolCall: ToolCall) => void;
    onError: (error: string) => void;
    onComplete: () => void;
  } = {
    onContent: () => {},
    onToolCall: () => {},
    onError: () => {},
    onComplete: () => {}
  };

  constructor() {
    this.controller = new AbortController();
  }

  /**
   * Simple streaming with proper UTF-8 handling and line buffering
   */
  async startStream(
    request: SendMessageRequest,
    callbacks: {
      onContent: (content: string) => void;
      onToolCall: (toolCall: ToolCall) => void;
      onError: (error: string) => void;
      onComplete: () => void;
    }
  ): Promise<void> {
    this.callbacks = callbacks;
    this.controller = new AbortController();

    try {
      const response = await fetch(`${config.apiBaseUrl}/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(request),
        signal: this.controller.signal,
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      if (!response.body) {
        throw new Error('Response body is null');
      }

      await this.processStream(response.body);
    } catch (error) {
      if (error instanceof Error && error.name === 'AbortError') {
        console.log('Stream aborted');
        return;
      }
      this.callbacks.onError(error instanceof Error ? error.message : 'Unknown error');
    }
  }

  /**
   * Process stream with simplified logic
   */
  private async processStream(stream: ReadableStream<Uint8Array>): Promise<void> {
    const reader = stream.getReader();
    const decoder = new TextDecoder('utf-8');
    let buffer = '';
    let currentToolCall: ToolCall | null = null;

    try {
      while (true) {
        const { done, value } = await reader.read();
        
        if (done) {
          // Process any remaining buffer
          if (buffer.trim()) {
            this.processLine(buffer.trim(), currentToolCall);
          }
          this.callbacks.onComplete();
          break;
        }

        // Decode chunk with proper UTF-8 handling
        const chunk = decoder.decode(value, { stream: true });
        buffer += chunk;

        // Process complete lines
        const lines = buffer.split('\n');
        buffer = lines.pop() || ''; // Keep incomplete line in buffer

        for (const line of lines) {
          if (line.trim()) {
            const toolCallUpdate = this.processLine(line, currentToolCall);
            if (toolCallUpdate) {
              currentToolCall = toolCallUpdate;
            }
          }
        }
      }
    } finally {
      reader.releaseLock();
    }
  }

  /**
   * Simplified line processing with better pattern matching
   */
  private processLine(line: string, currentToolCall: ToolCall | null): ToolCall | null {
    const trimmed = line.trim();
    
    // Handle tool call start
    if (trimmed.includes('🔧') && trimmed.includes('Tool:')) {
      const toolMatch = trimmed.match(/🔧.*Tool:\s*(\w+)/);
      if (toolMatch) {
        const toolCall: ToolCall = {
          id: `tool_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
          toolName: toolMatch[1],
          status: 'executing',
          startTime: new Date()
        };
        this.callbacks.onToolCall(toolCall);
        return toolCall;
      }
    }

    // Handle tool completion
    if (currentToolCall && (trimmed.includes('✅') || trimmed.includes('❌'))) {
      const completedToolCall: ToolCall = {
        ...currentToolCall,
        status: trimmed.includes('✅') ? 'completed' : 'failed',
        endTime: new Date(),
        result: trimmed.includes('✅') ? 'Success' : 'Failed'
      };
      this.callbacks.onToolCall(completedToolCall);
      return null; // Clear current tool call
    }

    // Handle error messages
    if (trimmed.includes('❌') && trimmed.includes('Error:')) {
      const errorMatch = trimmed.match(/❌.*Error:\s*(.*)/);
      if (errorMatch) {
        this.callbacks.onError(errorMatch[1]);
        return currentToolCall;
      }
    }

    // Handle regular content (only if not a tool-related line)
    if (!trimmed.includes('🔧') && !trimmed.includes('✅') && !trimmed.includes('❌')) {
      // Clean content from any control characters
      const cleanContent = trimmed.replace(/[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]/g, '');
      if (cleanContent) {
        this.callbacks.onContent(cleanContent + '\n');
      }
    }

    return currentToolCall;
  }

  /**
   * Cancel current streaming
   */
  abort(): void {
    if (this.controller) {
      this.controller.abort();
    }
  }

  /**
   * Check if currently streaming
   */
  isActive(): boolean {
    return !!(this.controller && !this.controller.signal.aborted);
  }
}

/**
 * Hook for using the simplified streaming client
 */
export const useSimpleStreaming = () => {
  const client = new SimpleStreamingClient();
  
  return {
    startStream: client.startStream.bind(client),
    abort: client.abort.bind(client),
    isActive: client.isActive.bind(client),
  };
}; 