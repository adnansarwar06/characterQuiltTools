import { ChatMessage, ToolCall, SendMessageRequest } from '../types/chat';
import { config } from '../config/config';

export interface RobustStreamingState {
  content: string;
  isStreaming: boolean;
  toolCalls: ToolCall[];
  hasActiveToolCalls: boolean;
  error?: string;
  buffer: string;
  lastUpdateTime: number;
}

export class RobustStreamingClient {
  private controller?: AbortController;
  private state: RobustStreamingState;
  private callbacks: {
    onContent: (content: string) => void;
    onToolCall: (toolCall: ToolCall) => void;
    onError: (error: string) => void;
    onComplete: () => void;
  };
  
  // Debounced processing timers
  private contentProcessingTimer?: number;

  constructor() {
    this.state = {
      content: '',
      isStreaming: false,
      toolCalls: [],
      hasActiveToolCalls: false,
      buffer: '',
      lastUpdateTime: 0
    };
    
    this.callbacks = {
      onContent: () => {},
      onToolCall: () => {},
      onError: () => {},
      onComplete: () => {}
    };
  }

  /**
   * Start robust streaming with proper UTF-8 handling
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
    this.resetState();

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

      await this.processRobustStream(response.body);
    } catch (error) {
      if (error instanceof Error && error.name === 'AbortError') {
        console.log('Stream aborted');
        return;
      }
      this.callbacks.onError(error instanceof Error ? error.message : 'Unknown error');
    }
  }

  /**
   * Process stream with maximum UTF-8 accuracy
   */
  private async processRobustStream(stream: ReadableStream<Uint8Array>): Promise<void> {
    const reader = stream.getReader();
    let accumulatedBytes = new Uint8Array(0);
    let textBuffer = '';
    let currentToolCall: ToolCall | null = null;

    try {
      while (true) {
        const { done, value } = await reader.read();
        
        if (done) {
          // Process any remaining accumulated bytes
          if (accumulatedBytes.length > 0) {
            try {
              const decoder = new TextDecoder('utf-8', { fatal: false });
              const finalText = decoder.decode(accumulatedBytes, { stream: false });
              textBuffer += finalText;
            } catch (e) {
              console.warn('Failed to decode final bytes:', e);
            }
          }
          
          // Process final buffer content
          if (textBuffer.trim()) {
            const processedResult = this.processTextWithAccuracy(textBuffer, currentToolCall);
            currentToolCall = processedResult.toolCall;
          }
          
          // Complete streaming
          this.callbacks.onComplete();
          break;
        }

        // Accumulate bytes to handle UTF-8 character boundaries properly
        const newAccumulated = new Uint8Array(accumulatedBytes.length + value.length);
        newAccumulated.set(accumulatedBytes);
        newAccumulated.set(value, accumulatedBytes.length);
        accumulatedBytes = newAccumulated;

        // Try to decode with fallback handling
        let decodedText = '';
        let remainingBytes = new Uint8Array(0);
        
        try {
          const decoder = new TextDecoder('utf-8', { fatal: false });
          decodedText = decoder.decode(accumulatedBytes, { stream: true });
          accumulatedBytes = new Uint8Array(0); // Clear if successful
        } catch (error) {
          // If decoding fails, try to find the last complete UTF-8 character
          let validLength = accumulatedBytes.length;
          for (let i = Math.max(0, accumulatedBytes.length - 4); i < accumulatedBytes.length; i++) {
            try {
              const decoder = new TextDecoder('utf-8', { fatal: true });
              decodedText = decoder.decode(accumulatedBytes.slice(0, i), { stream: true });
              remainingBytes = accumulatedBytes.slice(i);
              validLength = i;
              break;
            } catch (innerError) {
              // Continue trying
            }
          }
          accumulatedBytes = remainingBytes;
          
          // If we still can't decode, use non-fatal decoder
          if (!decodedText && validLength > 0) {
            const decoder = new TextDecoder('utf-8', { fatal: false });
            decodedText = decoder.decode(accumulatedBytes.slice(0, validLength), { stream: true });
            accumulatedBytes = accumulatedBytes.slice(validLength);
          }
        }

        // Add decoded text to buffer
        if (decodedText) {
          textBuffer += decodedText;
          
          // Process complete lines only for accuracy
          const lines = textBuffer.split('\n');
          
          // Keep the last potentially incomplete line in buffer
          if (lines.length > 1) {
            textBuffer = lines.pop() || '';
            
            // Process complete lines with accuracy
            for (const line of lines) {
              if (line.trim()) {
                const processedResult = this.processTextWithAccuracy(line, currentToolCall);
                currentToolCall = processedResult.toolCall;
              }
            }
          }
        }
        
        // Small delay to prevent overwhelming the UI
        await new Promise(resolve => setTimeout(resolve, 10));
      }
    } finally {
      reader.releaseLock();
    }
  }

  /**
   * Process text with maximum accuracy
   */
  private processTextWithAccuracy(text: string, currentToolCall: ToolCall | null): {
    toolCall: ToolCall | null;
    content: string;
  } {
    const trimmed = text.trim();
    
    // Skip empty lines
    if (!trimmed) {
      return { toolCall: currentToolCall, content: '' };
    }

    // Handle tool call start
    if (this.isToolCallStart(trimmed)) {
      const toolCall = this.extractToolCall(trimmed);
      if (toolCall) {
        this.callbacks.onToolCall(toolCall);
        return { toolCall, content: '' };
      }
    }

    // Handle tool completion
    if (currentToolCall && this.isToolCallEnd(trimmed)) {
      const completedToolCall = this.completeToolCall(currentToolCall, trimmed);
      this.callbacks.onToolCall(completedToolCall);
      return { toolCall: null, content: '' };
    }

    // Handle error messages
    if (this.isErrorMessage(trimmed)) {
      const error = this.extractError(trimmed);
      if (error) {
        this.callbacks.onError(error);
      }
      return { toolCall: currentToolCall, content: '' };
    }

    // Handle regular content (only if not tool-related)
    if (!this.isToolRelated(trimmed)) {
      const cleanContent = this.cleanContentAccurately(trimmed);
      if (cleanContent) {
        // Use debounced processing for content accuracy
        this.scheduleContentProcessing(cleanContent);
      }
    }

    return { toolCall: currentToolCall, content: trimmed };
  }

  /**
   * Enhanced tool call detection
   */
  private isToolCallStart(text: string): boolean {
    const patterns = [
      /🔧.*(?:Tool|Calling|Executing):\s*\w+/i,
      /🔧.*(?:Using|Running)\s+tool:\s*\w+/i,
      /🔧.*\w+\s+tool/i,
      /Tool\s+call:\s*\w+/i
    ];
    
    return patterns.some(pattern => pattern.test(text));
  }

  /**
   * Enhanced tool call completion detection
   */
  private isToolCallEnd(text: string): boolean {
    const patterns = [
      /(?:✅|❌).*(?:completed|finished|done|failed|error)/i,
      /(?:✅|❌).*(?:success|complete)/i,
      /Tool\s+(?:completed|finished|done|failed)/i
    ];
    
    return patterns.some(pattern => pattern.test(text));
  }

  /**
   * Check if text is tool-related
   */
  private isToolRelated(text: string): boolean {
    const patterns = [
      /(?:🔧|✅|❌)/,
      /(?:Tool|Calling|Executing|Using|Running):\s*\w+/i,
      /(?:completed|finished|done|failed|error).*tool/i
    ];
    
    return patterns.some(pattern => pattern.test(text));
  }

  /**
   * Check if text is an error message
   */
  private isErrorMessage(text: string): boolean {
    return /❌.*(?:Error|Failed|Exception):/i.test(text);
  }

  /**
   * Extract tool call information
   */
  private extractToolCall(text: string): ToolCall | null {
    const patterns = [
      /🔧.*(?:Tool|Calling|Executing):\s*(\w+)/i,
      /🔧.*(?:Using|Running)\s+tool:\s*(\w+)/i,
      /🔧.*(\w+)\s+tool/i,
      /Tool\s+call:\s*(\w+)/i
    ];
    
    for (const pattern of patterns) {
      const match = text.match(pattern);
      if (match && match[1]) {
        return {
          id: `tool_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
          toolName: match[1],
          status: 'executing',
          startTime: new Date()
        };
      }
    }
    
    return null;
  }

  /**
   * Complete tool call
   */
  private completeToolCall(toolCall: ToolCall, text: string): ToolCall {
    const isSuccess = text.includes('✅') || 
                     /(?:completed|finished|done|success)/i.test(text) ||
                     !/(?:failed|error)/i.test(text);
    
    return {
      ...toolCall,
      status: isSuccess ? 'completed' : 'failed',
      endTime: new Date(),
      result: isSuccess ? 'Success' : 'Failed'
    };
  }

  /**
   * Extract error message
   */
  private extractError(text: string): string | null {
    const patterns = [
      /❌.*(?:Error|Failed|Exception):\s*([^\n]+)/i,
      /❌\s*([^\n]+)/i
    ];
    
    for (const pattern of patterns) {
      const match = text.match(pattern);
      if (match && match[1]) {
        return match[1].trim();
      }
    }
    
    return null;
  }

  /**
   * Clean content with enhanced accuracy
   */
  private cleanContentAccurately(text: string): string {
    // Remove control characters but preserve formatting
    let cleaned = text.replace(/[\x00-\x08\x0B\x0C\x0E-\x1F\x7F-\x9F]/g, '');
    
    // Remove common streaming artifacts
    cleaned = cleaned.replace(/\ufffd/g, ''); // replacement character
    cleaned = cleaned.replace(/\u0000/g, ''); // null character
    cleaned = cleaned.replace(/\uFEFF/g, ''); // BOM
    
    // Remove duplicate spaces but preserve intentional formatting
    cleaned = cleaned.replace(/[ \t]+/g, ' ');
    
    // Remove leading/trailing whitespace
    cleaned = cleaned.trim();
    
    return cleaned;
  }

  /**
   * Schedule content processing with debouncing for accuracy
   */
  private scheduleContentProcessing(content: string): void {
    if (this.contentProcessingTimer) {
      clearTimeout(this.contentProcessingTimer);
    }
    
    this.contentProcessingTimer = setTimeout(() => {
      if (content && !this.state.hasActiveToolCalls) {
        this.callbacks.onContent(content + '\n');
      }
    }, 50) as unknown as number; // Reduced delay for better responsiveness
  }

  /**
   * Reset internal state
   */
  private resetState(): void {
    this.state = {
      content: '',
      isStreaming: true,
      toolCalls: [],
      hasActiveToolCalls: false,
      buffer: '',
      lastUpdateTime: Date.now()
    };
    
    // Clear any existing timers
    if (this.contentProcessingTimer) {
      clearTimeout(this.contentProcessingTimer);
    }
  }

  /**
   * Cancel current streaming
   */
  abort(): void {
    if (this.controller) {
      this.controller.abort();
    }
    
    // Clear timers
    if (this.contentProcessingTimer) {
      clearTimeout(this.contentProcessingTimer);
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
 * Hook for using the robust streaming client
 */
export const useRobustStreaming = () => {
  const client = new RobustStreamingClient();
  
  return {
    startStream: client.startStream.bind(client),
    abort: client.abort.bind(client),
    isActive: client.isActive.bind(client),
  };
}; 