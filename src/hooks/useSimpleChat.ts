import { useState, useCallback, useRef } from 'react';
import { ChatMessage, ChatState, ToolCall, SendMessageRequest } from '../types/chat';
import { RobustStreamingClient } from '../utils/robust-streaming';
import { config } from '../config/config';

/**
 * Simplified chat hook that replaces the complex buffering logic
 */
export const useSimpleChat = () => {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [activeToolCalls, setActiveToolCalls] = useState<ToolCall[]>([]);
  const [currentStreamingId, setCurrentStreamingId] = useState<string | null>(null);
  const streamingClient = useRef<RobustStreamingClient | null>(null);

  /**
   * Generate unique message ID
   */
  const generateId = useCallback(() => {
    return `${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }, []);

  /**
   * Add a new message
   */
  const addMessage = useCallback((message: Omit<ChatMessage, 'id' | 'timestamp'>) => {
    const newMessage: ChatMessage = {
      ...message,
      id: generateId(),
      timestamp: new Date(),
    };

    setMessages(prev => [...prev, newMessage]);
    return newMessage;
  }, [generateId]);

  /**
   * Update message content (for streaming)
   */
  const updateMessageContent = useCallback((messageId: string, content: string) => {
    setMessages(prev => prev.map(msg => 
      msg.id === messageId 
        ? { ...msg, content: msg.content + content }
        : msg
    ));
  }, []);

  /**
   * Update message tool calls
   */
  const updateMessageToolCalls = useCallback((messageId: string, toolCalls: ToolCall[]) => {
    setMessages(prev => prev.map(msg => 
      msg.id === messageId 
        ? { ...msg, toolCalls }
        : msg
    ));
  }, []);

  /**
   * Send message with simplified streaming
   */
  const sendMessage = useCallback(async (
    content: string, 
    enabledTools: string[] = [], 
    deepResearchMode: boolean = false
  ) => {
    if (!content.trim() || isLoading) return;

    // Add user message
    const userMessage = addMessage({
      content: content.trim(),
      sender: 'user',
    });

    // Add initial agent message
    const agentMessage = addMessage({
      content: '',
      sender: 'agent',
      isStreaming: true,
    });

    setIsLoading(true);
    setCurrentStreamingId(agentMessage.id);

    // Prepare request
    const request: SendMessageRequest = {
      messages: [
        ...messages.map(msg => ({
          role: msg.sender === 'user' ? 'user' as const : 'assistant' as const,
          content: msg.content,
        })),
        {
          role: 'user',
          content: content.trim(),
        }
      ],
      tools: enabledTools,
      deep_research_mode: deepResearchMode,
    };

    // Start streaming
    streamingClient.current = new RobustStreamingClient();
    
    try {
      await streamingClient.current.startStream(request, {
        onContent: (chunk) => {
          updateMessageContent(agentMessage.id, chunk);
        },
        
        onToolCall: (toolCall) => {
          // Update active tool calls
          setActiveToolCalls(prev => {
            const existing = prev.find(tc => tc.id === toolCall.id);
            if (existing) {
              return prev.map(tc => tc.id === toolCall.id ? toolCall : tc);
            } else {
              return [...prev, toolCall];
            }
          });
          
          // Update message tool calls
          updateMessageToolCalls(agentMessage.id, 
            activeToolCalls.map(tc => tc.id === toolCall.id ? toolCall : tc)
          );
        },
        
        onError: (error) => {
          console.error('Streaming error:', error);
          updateMessageContent(agentMessage.id, `\n\n❌ Error: ${error}`);
        },
        
        onComplete: () => {
          setMessages(prev => prev.map(msg => 
            msg.id === agentMessage.id 
              ? { ...msg, isStreaming: false, streamingComplete: true }
              : msg
          ));
          setIsLoading(false);
          setCurrentStreamingId(null);
          setActiveToolCalls([]);
        }
      });
    } catch (error) {
      console.error('Failed to send message:', error);
      updateMessageContent(agentMessage.id, `\n\n❌ Failed to send message: ${error}`);
      setIsLoading(false);
      setCurrentStreamingId(null);
    }
  }, [messages, isLoading, addMessage, updateMessageContent, updateMessageToolCalls, activeToolCalls]);

  /**
   * Cancel current streaming
   */
  const cancelStreaming = useCallback(() => {
    if (streamingClient.current) {
      streamingClient.current.abort();
      setIsLoading(false);
      setCurrentStreamingId(null);
    }
  }, []);

  /**
   * Clear all messages
   */
  const clearMessages = useCallback(() => {
    setMessages([]);
    setActiveToolCalls([]);
    cancelStreaming();
  }, [cancelStreaming]);

  return {
    messages,
    isLoading,
    activeToolCalls,
    currentStreamingId,
    sendMessage,
    cancelStreaming,
    clearMessages,
  };
}; 