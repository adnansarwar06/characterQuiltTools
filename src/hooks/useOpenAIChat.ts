import { useState, useCallback, useEffect, useRef } from 'react';
import { ChatMessage, ToolCall, SendMessageRequest } from '../types/chat';
import { apiClient } from '../utils/api';

// Simple state interface
interface ChatState {
  messages: ChatMessage[];
  isLoading: boolean;
  isConnected: boolean;
  currentToolCall?: ToolCall;
  availableTools: any[];
  activeToolCalls: ToolCall[];
  errors: any[];
  settings: {
    enabledTools: string[];
    deepResearchMode: boolean;
  };
  streamingMessageId?: string;
  bufferedContent: {
    chunks: any[];
    isBuffering: boolean;
    hasActiveToolCalls: boolean;
  };
}

/**
 * Simplified OpenAI chat hook that falls back to backend streaming
 * Focus on getting basic functionality working first
 */
export const useOpenAIChat = () => {
  const abortControllerRef = useRef<AbortController | null>(null);
  
  const [state, setState] = useState<ChatState>({
    messages: [],
    isLoading: false,
    isConnected: false,
    availableTools: [
      { name: 'web_search', description: 'Search the web', enabled: false },
      { name: 'file_write', description: 'Write files', enabled: false },
      { name: 'weather', description: 'Get weather info', enabled: false },
    ],
    activeToolCalls: [],
    errors: [],
    settings: {
      enabledTools: [],
      deepResearchMode: false,
    },
    bufferedContent: {
      chunks: [],
      isBuffering: false,
      hasActiveToolCalls: false,
    },
  });

  /**
   * Generate unique message ID
   */
  const generateId = useCallback(() => {
    return `msg_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
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

    setState(prev => ({
      ...prev,
      messages: [...prev.messages, newMessage],
    }));

    return newMessage;
  }, [generateId]);

  /**
   * Update message content
   */
  const updateMessageContent = useCallback((messageId: string, content: string) => {
    setState(prev => ({
      ...prev,
      messages: prev.messages.map(msg => 
        msg.id === messageId 
          ? { ...msg, content: msg.content + content }
          : msg
      ),
    }));
  }, []);

  /**
   * Complete message streaming
   */
  const completeMessage = useCallback((messageId: string) => {
    setState(prev => ({
      ...prev,
      messages: prev.messages.map(msg => 
        msg.id === messageId 
          ? { ...msg, isStreaming: false, streamingComplete: true }
          : msg
      ),
      isLoading: false,
    }));
  }, []);

  /**
   * Check backend connectivity and get API key
   */
  const checkConnectivity = useCallback(async () => {
    try {
      console.log('🔧 Checking backend connectivity...');
      const response = await apiClient.getApiKey();
      console.log('✅ Backend connected, API key available');
      setState(prev => ({ ...prev, isConnected: true }));
      return true;
    } catch (error) {
      console.error('❌ Backend connection failed:', error);
      setState(prev => ({ 
        ...prev, 
        isConnected: false,
        errors: [...prev.errors, {
          id: `error_${Date.now()}`,
          type: 'connection_error',
          title: 'Backend Connection Failed',
          message: 'Could not connect to backend. Please ensure the Python backend is running.',
          timestamp: new Date(),
          dismissible: true,
        }]
      }));
      return false;
    }
  }, []);

  /**
   * Send message using backend streaming (for now, until OpenAI hooks are stable)
   */
  const handleUserMessage = useCallback(async (content: string) => {
    if (!content.trim() || state.isLoading) return;

    console.log('📨 Sending message:', content.trim());

    // Cancel any ongoing request
    if (abortControllerRef.current) {
      console.log('🛑 Cancelling previous request');
      abortControllerRef.current.abort();
    }

    // Create new abort controller for this request
    const abortController = new AbortController();
    abortControllerRef.current = abortController;

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

    setState(prev => ({ ...prev, isLoading: true }));

    try {
      // Use backend streaming for now (more reliable)
      console.log('🔧 Using backend streaming...');
      
      const request: SendMessageRequest = {
        messages: [
          ...state.messages.map(msg => ({
            role: msg.sender === 'user' ? 'user' as const : 'assistant' as const,
            content: msg.content,
          })),
          { role: 'user', content: content.trim() }
        ],
        tools: state.settings.enabledTools,
        deep_research_mode: state.settings.deepResearchMode,
      };

      const stream = await apiClient.sendMessageStream(request, abortController.signal);
      
      // Process stream
      const reader = stream.getReader();
      const decoder = new TextDecoder();
      
      try {
        while (true) {
          // Check if cancelled before reading
          if (abortController.signal.aborted) {
            console.log('🛑 Stream cancelled, stopping reader');
            break;
          }
          
          const { done, value } = await reader.read();
          
          if (done) {
            completeMessage(agentMessage.id);
            break;
          }
          
          const chunk = decoder.decode(value, { stream: true });
          if (chunk) {
            // Check if cancelled before processing chunk
            if (!abortController.signal.aborted) {
              updateMessageContent(agentMessage.id, chunk);
            }
          }
        }
      } finally {
        reader.releaseLock();
      }

    } catch (error) {
      console.error('❌ Failed to send message:', error);
      
      // Don't show error if it was cancelled by user
      if (error instanceof Error && error.message === 'Request cancelled') {
        console.log('🛑 Request cancelled by user');
        updateMessageContent(agentMessage.id, '\n\n🛑 Request cancelled by user');
      } else if (!abortController.signal.aborted) {
        const errorMessage = error instanceof Error ? error.message : 'Unknown error';
        updateMessageContent(agentMessage.id, `\n\n❌ Error: ${errorMessage}`);
        
        setState(prev => ({
          ...prev,
          errors: [...prev.errors, {
            id: `error_${Date.now()}`,
            type: 'message_error',
            title: 'Failed to send message',
            message: errorMessage,
            timestamp: new Date(),
            dismissible: true,
          }]
        }));
      }
      
      completeMessage(agentMessage.id);
    } finally {
      setState(prev => ({ ...prev, isLoading: false }));
      // Clear the abort controller reference
      if (abortControllerRef.current === abortController) {
        abortControllerRef.current = null;
      }
    }
  }, [state.isLoading, state.messages, state.settings, addMessage, updateMessageContent, completeMessage]);

  /**
   * Update settings
   */
  const updateSettings = useCallback((settings: { enabledTools?: string[], deepResearchMode?: boolean }) => {
    setState(prev => ({
      ...prev,
      settings: {
        enabledTools: settings.enabledTools ?? prev.settings.enabledTools,
        deepResearchMode: settings.deepResearchMode ?? prev.settings.deepResearchMode,
      },
      availableTools: prev.availableTools.map(tool => ({
        ...tool,
        enabled: settings.enabledTools?.includes(tool.name) ?? tool.enabled,
      })),
    }));
  }, []);

  /**
   * Clear all messages
   */
  const clearMessages = useCallback(() => {
    setState(prev => ({
      ...prev,
      messages: [],
      activeToolCalls: [],
      errors: [],
    }));
  }, []);

  /**
   * Cancel current request
   */
  const cancelCurrentRequest = useCallback(() => {
    console.log('🛑 Cancelling current request');
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    setState(prev => ({ ...prev, isLoading: false }));
  }, []);

  /**
   * Dismiss error
   */
  const dismissError = useCallback((errorId: string) => {
    setState(prev => ({
      ...prev,
      errors: prev.errors.filter(error => error.id !== errorId),
    }));
  }, []);

  /**
   * Load available tools
   */
  const loadAvailableTools = useCallback(async () => {
    try {
      const config = await apiClient.getBackendConfig();
      const tools = config.config.available_tools || ['web_search', 'file_write', 'weather'];
      setState(prev => ({
        ...prev,
        availableTools: tools.map((tool: string) => ({
          name: tool,
          description: `${tool} tool`,
          enabled: prev.settings.enabledTools.includes(tool),
        })),
      }));
    } catch (error) {
      console.error('Failed to load available tools:', error);
    }
  }, []);

  // Initialize on mount
  useEffect(() => {
    console.log('🚀 Initializing OpenAI chat hook...');
    checkConnectivity();
    loadAvailableTools();
  }, [checkConnectivity, loadAvailableTools]);

  return {
    messages: state.messages,
    isLoading: state.isLoading,
    isConnected: state.isConnected,
    currentToolCall: state.currentToolCall,
    availableTools: state.availableTools,
    activeToolCalls: state.activeToolCalls,
    errors: state.errors,
    settings: state.settings,
    streamingMessageId: state.streamingMessageId,
    bufferedContent: state.bufferedContent,
    handleUserMessage,
    updateSettings,
    clearMessages,
    cancelCurrentRequest,
    loadAvailableTools,
    checkConnectivity,
    dismissError,
  };
}; 