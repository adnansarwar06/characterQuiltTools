/**
 * API utilities for communicating with the research agent backend
 */

import { config } from '../config/config';
import { SendMessageRequest, ToolsResponse, HealthResponse } from '../types/chat';

/**
 * Base API client for making HTTP requests to the research agent backend
 */
class ApiClient {
  private baseUrl: string;

  constructor(baseUrl: string) {
    this.baseUrl = baseUrl;
    console.log('🔧 API Client initialized with base URL:', baseUrl);
  }

  /**
   * Makes a GET request to the specified endpoint
   * @param endpoint - API endpoint to request
   * @param abortSignal - Optional abort signal for cancellation
   * @returns Promise resolving to the response data
   */
  private async get<T>(endpoint: string, abortSignal?: AbortSignal): Promise<T> {
    const fullUrl = `${this.baseUrl}${endpoint}`;
    console.log('📡 Making GET request to:', fullUrl);
    
    try {
      const response = await fetch(fullUrl, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
        signal: abortSignal,
      });

      console.log('📡 Response status:', response.status, response.statusText);
      
      if (!response.ok) {
        const errorText = await response.text();
        console.error('❌ API request failed:', response.status, response.statusText, errorText);
        throw new Error(`API request failed: ${response.status} ${response.statusText}`);
      }

      const data = await response.json();
      console.log('✅ API response data:', data);
      return data;
    } catch (error) {
      if (error instanceof Error && error.name === 'AbortError') {
        console.log('🛑 Request cancelled by user');
        throw new Error('Request cancelled');
      }
      console.error('❌ API request error:', error);
      throw error;
    }
  }

  /**
   * Makes a POST request to the specified endpoint
   * @param endpoint - API endpoint to request  
   * @param data - Request payload
   * @param abortSignal - Optional abort signal for cancellation
   * @returns Promise resolving to the response data
   */
  private async post<T>(endpoint: string, data: any, abortSignal?: AbortSignal): Promise<T> {
    const fullUrl = `${this.baseUrl}${endpoint}`;
    console.log('📡 Making POST request to:', fullUrl, 'with data:', data);
    
    try {
      const response = await fetch(fullUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(data),
        signal: abortSignal,
      });

      console.log('📡 Response status:', response.status, response.statusText);

      if (!response.ok) {
        const errorText = await response.text();
        console.error('❌ API request failed:', response.status, response.statusText, errorText);
        throw new Error(`API request failed: ${response.status} ${response.statusText}`);
      }

      const responseData = await response.json();
      console.log('✅ API response data:', responseData);
      return responseData;
    } catch (error) {
      if (error instanceof Error && error.name === 'AbortError') {
        console.log('🛑 Request cancelled by user');
        throw new Error('Request cancelled');
      }
      console.error('❌ API request error:', error);
      throw error;
    }
  }

  /**
   * Sends a message to the research agent with streaming response
   * @param request - Message request with tools and settings
   * @param abortSignal - Optional abort signal for cancellation
   * @returns ReadableStream for streaming response
   */
  async sendMessageStream(request: SendMessageRequest, abortSignal?: AbortSignal): Promise<ReadableStream<Uint8Array>> {
    const fullUrl = `${this.baseUrl}/chat`;
    console.log('📡 Making streaming POST request to:', fullUrl, 'with request:', request);
    
    try {
      const response = await fetch(fullUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(request),
        signal: abortSignal,
      });

      console.log('📡 Streaming response status:', response.status, response.statusText);

      if (!response.ok) {
        const errorText = await response.text();
        console.error('❌ Streaming request failed:', response.status, response.statusText, errorText);
        throw new Error(`API request failed: ${response.status} ${response.statusText}`);
      }

      if (!response.body) {
        throw new Error('Response body is null');
      }

      console.log('✅ Streaming response ready');
      return response.body;
    } catch (error) {
      if (error instanceof Error && error.name === 'AbortError') {
        console.log('🛑 Streaming request cancelled by user');
        throw new Error('Request cancelled');
      }
      console.error('❌ Streaming request error:', error);
      throw error;
    }
  }

  /**
   * Gets the list of available tools from the backend
   * @returns Promise resolving to available tools
   */
  async getAvailableTools(): Promise<ToolsResponse> {
    console.log('🔧 Getting available tools...');
    return this.get<ToolsResponse>('/tools');
  }

  /**
   * Checks the health status of the backend
   * @returns Promise resolving to health status
   */
  async getHealthStatus(): Promise<HealthResponse> {
    console.log('💓 Checking health status...');
    return this.get<HealthResponse>('/health');
  }

  /**
   * Get OpenAI API key from the backend
   * @returns OpenAI API key and model configuration
   */
  async getApiKey(): Promise<{ api_key: string; model: string }> {
    const fullUrl = `${this.baseUrl}/api-key`;
    console.log('📡 Getting API key from backend:', fullUrl);
    
    try {
      const response = await fetch(fullUrl, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      console.log('📡 API key response status:', response.status, response.statusText);

      if (!response.ok) {
        const errorText = await response.text();
        console.error('❌ Failed to get API key:', response.status, response.statusText, errorText);
        throw new Error(`Failed to get API key: ${response.status} ${response.statusText}`);
      }

      const data = await response.json();
      console.log('✅ API key retrieved successfully');
      return data;
    } catch (error) {
      console.error('❌ API key request error:', error);
      throw error;
    }
  }

  /**
   * Get backend configuration including API key and model settings
   * @returns Backend configuration
   */
  async getBackendConfig(): Promise<any> {
    const fullUrl = `${this.baseUrl}/config`;
    console.log('📡 Getting backend config:', fullUrl);
    
    try {
      const response = await fetch(fullUrl, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        const errorText = await response.text();
        console.error('❌ Failed to get backend config:', response.status, response.statusText, errorText);
        throw new Error(`Failed to get backend config: ${response.status} ${response.statusText}`);
      }

      const data = await response.json();
      console.log('✅ Backend config retrieved successfully');
      return data;
    } catch (error) {
      console.error('❌ Backend config request error:', error);
      throw error;
    }
  }
}

/**
 * Default API client instance configured with the base URL from config
 */
export const apiClient = new ApiClient(config.apiBaseUrl);

/**
 * SSE-based streaming for better reliability and built-in reconnection
 */
export class SSEClient {
  private eventSource: EventSource | null = null;
  private baseUrl: string;

  constructor(baseUrl: string = config.apiBaseUrl) {
    this.baseUrl = baseUrl;
  }

  /**
   * Start SSE streaming chat
   */
  startStream(
    request: SendMessageRequest,
    onMessage: (data: string) => void,
    onError: (error: string) => void,
    onComplete: () => void
  ): () => void {
    const url = new URL(`${this.baseUrl}/chat/stream`);
    
    // Add request data as query params or use POST endpoint
    const params = new URLSearchParams({
      data: JSON.stringify(request)
    });
    
    this.eventSource = new EventSource(`${url}?${params}`);
    
    this.eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === 'chunk') {
          onMessage(data.content);
        } else if (data.type === 'complete') {
          onComplete();
        }
      } catch (error) {
        console.error('Error parsing SSE data:', error);
        onError('Failed to parse streaming data');
      }
    };

    this.eventSource.onerror = (error) => {
      console.error('SSE error:', error);
      onError('Streaming connection error');
    };

    // Return cleanup function
    return () => this.stopStream();
  }

  stopStream(): void {
    if (this.eventSource) {
      this.eventSource.close();
      this.eventSource = null;
    }
  }
}

/**
 * Processes a streaming chat response and calls the callback for each chunk
 * @param stream - ReadableStream from the chat endpoint
 * @param onChunk - Callback function for each content chunk
 * @param onError - Callback function for errors
 * @param abortSignal - Optional abort signal for cancellation
 */
export const processStreamingResponse = async (
  stream: ReadableStream<Uint8Array>,
  onChunk: (content: string) => void,
  onError?: (error: string) => void,
  abortSignal?: AbortSignal
): Promise<void> => {
  const reader = stream.getReader();
  const decoder = new TextDecoder('utf-8', { fatal: false, ignoreBOM: true });
  let buffer = '';

  try {
    while (true) {
      // Check if cancelled before reading
      if (abortSignal?.aborted) {
        console.log('🛑 Stream processing cancelled');
        throw new Error('Stream processing cancelled');
      }

      const { done, value } = await reader.read();
      
      if (done) {
        // Process any remaining buffer content
        if (buffer.trim()) {
          const cleanText = sanitizeStreamingText(buffer);
          if (cleanText) {
            console.log('📨 Final buffer flush:', cleanText.substring(0, 50) + '...');
            onChunk(cleanText);
          }
        }
        break;
      }

      // Decode the chunk with proper UTF-8 handling
      const chunk = decoder.decode(value, { stream: true });
      
      // Add to buffer
      buffer += chunk;
      
      // Process buffer with tool-call awareness
      let processedText = '';
      let remainingBuffer = buffer;
      
      // Split buffer by potential tool call markers and process safely
      while (remainingBuffer.length > 0) {
        // Check for complete tool call markers
        const toolCallMarkers = ['🔧 **Executing Tool:**', '✅ **Result:**', '❌ **Error:**'];
        let foundMarkerIndex = -1;
        let foundMarker = '';
        
        for (const marker of toolCallMarkers) {
          const index = remainingBuffer.indexOf(marker);
          if (index !== -1 && (foundMarkerIndex === -1 || index < foundMarkerIndex)) {
            foundMarkerIndex = index;
            foundMarker = marker;
          }
        }
        
        if (foundMarkerIndex === -1) {
          // No tool call markers found
          // Check if we might have a partial tool call marker at the end
          let hasPartialMarker = false;
          for (const marker of toolCallMarkers) {
            // Check if the end of the buffer starts any of the markers
            for (let i = 1; i < marker.length && i <= remainingBuffer.length; i++) {
              if (remainingBuffer.endsWith(marker.substring(0, i))) {
                hasPartialMarker = true;
                break;
              }
            }
            if (hasPartialMarker) break;
          }
          
          if (hasPartialMarker && !done) {
            // Hold back the potentially partial marker text
            const holdBackLength = Math.min(50, remainingBuffer.length);
            const safeText = remainingBuffer.slice(0, -holdBackLength);
            const heldText = remainingBuffer.slice(-holdBackLength);
            
            if (safeText.trim()) {
              processedText += safeText;
            }
            remainingBuffer = heldText;
            break; // Wait for more data
          } else {
            // No partial markers, safe to process all remaining text
            processedText += remainingBuffer;
            remainingBuffer = '';
          }
        } else {
          // Found a complete tool call marker
          // Process text before the marker
          const textBeforeMarker = remainingBuffer.slice(0, foundMarkerIndex);
          if (textBeforeMarker.trim()) {
            processedText += textBeforeMarker;
          }
          
          // Find the end of this tool call marker line
          const afterMarker = remainingBuffer.slice(foundMarkerIndex);
          const lineEndIndex = afterMarker.indexOf('\n');
          
                     if (lineEndIndex === -1 && !done) {
             // Tool call marker line is incomplete, wait for more data
             remainingBuffer = remainingBuffer.slice(foundMarkerIndex);
             break;
          } else {
            // Complete tool call marker line
            const endIndex = lineEndIndex === -1 ? afterMarker.length : lineEndIndex + 1;
            const markerLine = afterMarker.slice(0, endIndex);
            processedText += markerLine;
            
            // Continue with remaining buffer after the marker line
            remainingBuffer = afterMarker.slice(endIndex);
          }
        }
      }
      
      // Update buffer with what we couldn't process
      buffer = remainingBuffer;
      
      // Send processed text if we have any
      if (processedText.trim()) {
        const cleanText = sanitizeStreamingText(processedText);
        if (cleanText) {
          console.log('📨 Sending processed chunk:', cleanText.substring(0, 50) + '...');
          onChunk(cleanText);
        }
      }
    }
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : 'Unknown streaming error';
    console.error('Streaming error:', errorMessage);
    onError?.(errorMessage);
  } finally {
    reader.releaseLock();
  }
};

/**
 * Sanitizes streaming text to remove problematic characters
 * @param text - Raw text to sanitize
 * @returns Cleaned text safe for display
 */
const sanitizeStreamingText = (text: string): string => {
  if (!text) return '';
  
  // Remove null characters, undefined text, and control characters
  let cleanText = text
    .replace(/undefined/g, '') // Remove literal "undefined" text
    .replace(/[\x00-\x08\x0B\x0C\x0E-\x1F]/g, '') // Remove control characters
    .replace(/\uFFFD/g, '') // Remove replacement characters (from invalid UTF-8)
    .replace(/^\s*$/, ''); // Remove whitespace-only strings
  
  // Remove any remaining non-printable characters except newlines and tabs
  cleanText = cleanText.replace(/[^\x20-\x7E\x09\x0A\x0D\u00A0-\uFFFF]/g, '');
  
  return cleanText;
};

/**
 * Simulates sending a message to the research agent for prototype purposes
 * Returns a mock response with tool calls
 * @deprecated Use real API calls instead
 */
export const simulateSendMessage = async (message: string): Promise<any> => {
  // Simulate network delay
  await new Promise(resolve => setTimeout(resolve, 1000));

  return {
    messageId: `msg_${Date.now()}`,
    content: `Thank you for your message: "${message}". I'm analyzing your request and will provide a comprehensive response.`,
    toolCalls: [
      {
        id: `tool_${Date.now()}`,
        toolName: 'web_search',
        status: 'executing',
        parameters: { query: message },
      },
    ],
  };
}; 