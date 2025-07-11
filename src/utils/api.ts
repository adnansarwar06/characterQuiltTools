/**
 * API utilities for communicating with the research agent backend
 */

import { config } from '../config/config';
import { SendMessageRequest, SendMessageResponse } from '../types/chat';

/**
 * Base API client for making HTTP requests to the research agent backend
 */
class ApiClient {
  private baseUrl: string;

  constructor(baseUrl: string) {
    this.baseUrl = baseUrl;
  }

  /**
   * Makes a POST request to the specified endpoint
   */
  private async post<T>(endpoint: string, data: any): Promise<T> {
    const response = await fetch(`${this.baseUrl}${endpoint}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(data),
    });

    if (!response.ok) {
      throw new Error(`API request failed: ${response.status} ${response.statusText}`);
    }

    return response.json();
  }

  /**
   * Sends a message to the research agent and returns the response
   */
  async sendMessage(request: SendMessageRequest): Promise<SendMessageResponse> {
    return this.post<SendMessageResponse>('/chat/message', request);
  }
}

/**
 * Default API client instance configured with the base URL from config
 */
export const apiClient = new ApiClient(config.apiBaseUrl);

/**
 * Simulates sending a message to the research agent for prototype purposes
 * Returns a mock response with tool calls
 */
export const simulateSendMessage = async (message: string): Promise<SendMessageResponse> => {
  // Simulate network delay
  await new Promise(resolve => setTimeout(resolve, 1000));

  return {
    messageId: `msg_${Date.now()}`,
    content: `Thank you for your message: "${message}". I'm analyzing your request and will provide a comprehensive response.`,
    toolCalls: [
      {
        id: `tool_${Date.now()}`,
        toolName: config.tools.webSearch,
        status: 'executing',
        parameters: { query: message },
      },
    ],
  };
}; 