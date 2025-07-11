/**
 * Custom React hook for managing chat state and interactions
 */

import React, { useState, useCallback, useEffect } from 'react';
import { ChatMessage, ChatState, ToolCall } from '../types/chat';
import { simulateSendMessage } from '../utils/api';
import { config } from '../config/config';

/**
 * Custom hook for managing chat functionality
 * Handles message sending, receiving, and tool call management
 */
export const useChat = () => {
  const [chatState, setChatState] = useState<ChatState>({
    messages: [],
    isLoading: false,
    isConnected: true, // Simulated connection for prototype
    currentToolCall: undefined,
  });

  /**
   * Generates a unique ID for messages
   */
  const generateMessageId = useCallback((): string => {
    return `msg_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }, []);

  /**
   * Adds a new message to the chat
   */
  const addMessage = useCallback((message: Omit<ChatMessage, 'id' | 'timestamp'>) => {
    const newMessage: ChatMessage = {
      ...message,
      id: generateMessageId(),
      timestamp: new Date(),
    };

    setChatState(prev => ({
      ...prev,
      messages: [...prev.messages, newMessage],
    }));

    return newMessage;
  }, [generateMessageId]);

  /**
   * Updates a tool call status
   */
  const updateToolCall = useCallback((messageId: string, toolCallId: string, updates: Partial<ToolCall>) => {
    setChatState(prev => ({
      ...prev,
      messages: prev.messages.map(msg =>
        msg.id === messageId
          ? {
              ...msg,
              toolCalls: msg.toolCalls?.map(tool =>
                tool.id === toolCallId ? { ...tool, ...updates } : tool
              ),
            }
          : msg
      ),
    }));
  }, []);

  /**
   * Handles sending a user message and receiving agent response
   */
  const handleUserMessage = useCallback(async (content: string) => {
    if (!content.trim()) return;

    setChatState(prev => ({ ...prev, isLoading: true }));

    // Add user message
    const userMessage = addMessage({
      content,
      sender: 'user',
    });

    try {
      // Simulate API call
      const response = await simulateSendMessage(content);

      // Add agent response
      const agentMessage = addMessage({
        content: response.content,
        sender: 'agent',
        toolCalls: response.toolCalls,
      });

      // Simulate tool call execution
      if (response.toolCalls && response.toolCalls.length > 0) {
        const toolCall = response.toolCalls[0];
        setChatState(prev => ({ ...prev, currentToolCall: toolCall }));

        // Simulate tool execution completion
        setTimeout(() => {
          updateToolCall(agentMessage.id, toolCall.id, {
            status: 'completed',
            result: 'Tool execution completed successfully',
          });
          setChatState(prev => ({ ...prev, currentToolCall: undefined }));
        }, 2000);
      }
    } catch (error) {
      console.error('Error sending message:', error);
      addMessage({
        content: 'Sorry, I encountered an error while processing your message. Please try again.',
        sender: 'agent',
      });
    } finally {
      setChatState(prev => ({ ...prev, isLoading: false }));
    }
  }, [addMessage, updateToolCall]);

  /**
   * Clears all messages from the chat
   */
  const clearMessages = useCallback(() => {
    setChatState(prev => ({
      ...prev,
      messages: [],
      currentToolCall: undefined,
    }));
  }, []);

  /**
   * Simulates connection status updates
   */
  useEffect(() => {
    const interval = setInterval(() => {
      setChatState(prev => ({
        ...prev,
        isConnected: Math.random() > 0.1, // 90% uptime simulation
      }));
    }, 5000);

    return () => clearInterval(interval);
  }, []);

  return {
    messages: chatState.messages,
    isLoading: chatState.isLoading,
    isConnected: chatState.isConnected,
    currentToolCall: chatState.currentToolCall,
    handleUserMessage,
    clearMessages,
  };
}; 