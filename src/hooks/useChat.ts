/**
 * Custom React hook for managing chat state and interactions
 * Implements accuracy-first streaming: blocks agent output during tool calls
 * and only displays finalized, correct responses after tool completion
 */

import React, { useState, useCallback, useEffect, useRef } from 'react';
import { ChatMessage, ChatState, ToolCall, AvailableTool, ChatSettings, SendMessageRequest, ErrorNotification, ToolCallEvent, BufferedContent } from '../types/chat';
import { apiClient, processStreamingResponse } from '../utils/api';
import { config } from '../config/config';

/**
 * Custom hook for managing chat functionality
 * Handles message sending, receiving, tool management, streaming responses, and error handling
 * Implements accuracy-first streaming to prevent display of interim or incorrect content
 */
export const useChat = () => {
  const [chatState, setChatState] = useState<ChatState>({
    messages: [],
    isLoading: false,
    isConnected: false,
    currentToolCall: undefined,
    availableTools: [],
    activeToolCalls: [],
    errors: [],
    settings: {
      enabledTools: [],
      deepResearchMode: false,
    },
    streamingMessageId: undefined,
    bufferedContent: {
      chunks: [],
      isBuffering: false,
      hasActiveToolCalls: false,
    },
  });

  const abortControllerRef = useRef<AbortController | null>(null);

  /**
   * Generates a unique ID for messages and errors
   * @returns Unique identifier
   */
  const generateId = useCallback((): string => {
    return `${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }, []);

  /**
   * Adds a new message to the chat
   * @param message - Message data without ID and timestamp
   * @returns The complete message with ID and timestamp
   */
  const addMessage = useCallback((message: Omit<ChatMessage, 'id' | 'timestamp'>) => {
    const newMessage: ChatMessage = {
      ...message,
      id: generateId(),
      timestamp: new Date(),
    };

    setChatState(prev => ({
      ...prev,
      messages: [...prev.messages, newMessage],
    }));

    return newMessage;
  }, [generateId]);

  /**
   * Updates the content of the last agent message (for streaming)
   * Only updates if not currently blocked by tool calls
   * @param content - Additional content to append
   */
  const appendToLastMessage = useCallback((content: string) => {
    setChatState(prev => {
      // Don't append if we're buffering due to active tool calls
      if (prev.bufferedContent.isBuffering && prev.bufferedContent.hasActiveToolCalls) {
        return prev;
      }

      const messages = [...prev.messages];
      const lastMessage = messages[messages.length - 1];
      
      if (lastMessage && lastMessage.sender === 'agent') {
        messages[messages.length - 1] = {
          ...lastMessage,
          content: lastMessage.content + content,
          isBlocked: prev.bufferedContent.hasActiveToolCalls,
        };
      }
      
      return { ...prev, messages };
    });
  }, []);

  /**
   * Flushes buffered content to the current message
   * Called when tool calls complete and it's safe to display content
   */
  const flushBufferedContent = useCallback(() => {
    console.log('🔄 Flushing buffered content...');
    setChatState(prev => {
      console.log('Buffer state:', {
        chunksCount: prev.bufferedContent.chunks.length,
        isBuffering: prev.bufferedContent.isBuffering,
        hasActiveToolCalls: prev.bufferedContent.hasActiveToolCalls,
        activeToolCallsCount: prev.activeToolCalls.length,
        activeToolCalls: prev.activeToolCalls.map(tc => ({ name: tc.toolName, status: tc.status }))
      });

      if (prev.bufferedContent.chunks.length === 0) {
        console.log('No buffered content to flush');
        return {
          ...prev,
          bufferedContent: {
            chunks: [],
            isBuffering: false,
            hasActiveToolCalls: false,
          },
        };
      }

      const messages = [...prev.messages];
      const lastMessage = messages[messages.length - 1];
      
      if (lastMessage && lastMessage.sender === 'agent') {
        const bufferedText = prev.bufferedContent.chunks.join('');
        console.log('Flushing buffered content:', bufferedText.substring(0, 100) + '...');
        
        messages[messages.length - 1] = {
          ...lastMessage,
          content: lastMessage.content + bufferedText,
          isBlocked: false,
        };
      } else {
        console.warn('No agent message found to flush content to');
      }
      
      return {
        ...prev,
        messages,
        bufferedContent: {
          chunks: [],
          isBuffering: false,
          hasActiveToolCalls: false,
        },
      };
    });
  }, []);

  /**
   * Adds content to the buffer instead of directly to the message
   * Used during tool calls to prevent displaying interim content
   * @param content - Content to buffer
   */
  const addToBuffer = useCallback((content: string) => {
    setChatState(prev => ({
      ...prev,
      bufferedContent: {
        ...prev.bufferedContent,
        chunks: [...prev.bufferedContent.chunks, content],
        isBuffering: true,
      },
    }));
  }, []);

  /**
   * Marks the streaming message as complete
   * @param messageId - ID of the message to mark complete
   */
  const markStreamingComplete = useCallback((messageId?: string) => {
    setChatState(prev => {
      const targetMessageId = messageId || prev.streamingMessageId;
      
      // Complete any remaining active tool calls
      const completedToolCalls = prev.activeToolCalls.map(toolCall => {
        if (toolCall.status === 'executing') {
          return {
            ...toolCall,
            status: 'completed' as const,
            endTime: new Date(),
            result: toolCall.result || 'Execution completed',
          };
        }
        return toolCall;
      });

      // Update the message with completed tool calls
      const updatedMessages = prev.messages.map(msg => {
        if (msg.id === targetMessageId) {
          return {
            ...msg,
            isStreaming: false,
            streamingComplete: true,
            toolCalls: completedToolCalls,
            isBlocked: false,
          };
        }
        return msg;
      });

      return {
        ...prev,
        streamingMessageId: undefined,
        messages: updatedMessages,
        activeToolCalls: [], // Clear active tool calls
        currentToolCall: undefined, // Clear current tool call
        bufferedContent: {
          chunks: [],
          isBuffering: false,
          hasActiveToolCalls: false,
        },
      };
    });
  }, []);

  /**
   * Adds or updates a tool call
   * @param toolCall - Tool call data
   */
  const updateToolCall = useCallback((toolCall: ToolCall) => {
    setChatState(prev => {
      const activeToolCalls = [...prev.activeToolCalls];
      const existingIndex = activeToolCalls.findIndex(tc => tc.id === toolCall.id);
      
      if (existingIndex >= 0) {
        activeToolCalls[existingIndex] = toolCall;
      } else {
        activeToolCalls.push(toolCall);
      }

      // Check if we have active tool calls
      const hasActiveToolCalls = activeToolCalls.some(tc => tc.status === 'executing');

      // Update the message with tool calls
      const messages = prev.messages.map(msg => {
        if (msg.id === prev.streamingMessageId) {
          return {
            ...msg,
            toolCalls: activeToolCalls.filter(tc => tc.status !== 'pending'),
            isBlocked: hasActiveToolCalls,
          };
        }
        return msg;
      });

      return {
        ...prev,
        activeToolCalls,
        messages,
        currentToolCall: toolCall.status === 'executing' ? toolCall : undefined,
        bufferedContent: {
          ...prev.bufferedContent,
          hasActiveToolCalls,
        },
      };
    });
  }, []);

  /**
   * Adds an error notification
   * @param error - Error notification data
   */
  const addError = useCallback((error: Omit<ErrorNotification, 'id' | 'timestamp'>) => {
    const newError: ErrorNotification = {
      ...error,
      id: generateId(),
      timestamp: new Date(),
    };

    setChatState(prev => ({
      ...prev,
      errors: [...prev.errors, newError],
    }));

    return newError;
  }, [generateId]);

  /**
   * Dismisses an error notification
   * @param errorId - ID of the error to dismiss
   */
  const dismissError = useCallback((errorId: string) => {
    setChatState(prev => ({
      ...prev,
      errors: prev.errors.filter(error => error.id !== errorId),
    }));
  }, []);

  /**
   * Processes streaming events from the backend with accuracy-first approach
   * Blocks content during tool calls and only displays finalized responses
   * Handles retroactive buffering when tool calls are detected after content starts streaming
   * @param chunk - Raw chunk data from stream
   */
  const processStreamingChunk = useCallback((chunk: string) => {
    try {
      console.log('📨 Processing chunk:', chunk.substring(0, 50).replace(/\n/g, '\\n') + '...');

      // AGGRESSIVE TOOL DETECTION: Look for ANY signs that might indicate tool usage
      const hasToolIndicators = 
        chunk.includes('🔧') || 
        chunk.includes('**Executing') ||
        chunk.includes('Tool:**') ||
        chunk.includes('**Result:**') ||
        chunk.includes('**Error:**') ||
        chunk.includes('✅') ||
        chunk.includes('❌') ||
        chunk.includes('📋') ||
        /\*\*\w+\s*Tool/i.test(chunk) ||
        /Executing\s+\w+/i.test(chunk);

      // If we detect ANY tool indicators, immediately start buffering mode
      if (hasToolIndicators) {
        console.log('🚨 TOOL INDICATORS DETECTED - Starting buffering mode');
        
        setChatState(prev => {
          const messages = [...prev.messages];
          const lastMessage = messages[messages.length - 1];
          
          if (lastMessage && lastMessage.sender === 'agent' && lastMessage.content) {
            console.log('🔄 Moving existing content to buffer:', lastMessage.content.substring(0, 50) + '...');
            // Move existing content to buffer and clear the message
            const existingContent = lastMessage.content;
            messages[messages.length - 1] = {
              ...lastMessage,
              content: '',
              isBlocked: true,
            };
            
            return {
              ...prev,
              messages,
              bufferedContent: {
                chunks: [existingContent, chunk],
                isBuffering: true,
                hasActiveToolCalls: true,
              },
            };
          } else {
            console.log('🔄 Starting buffering mode with current chunk');
            return {
              ...prev,
              bufferedContent: {
                chunks: [...prev.bufferedContent.chunks, chunk],
                isBuffering: true,
                hasActiveToolCalls: true,
              },
            };
          }
        });
        return;
      }

      // Handle tool call start - be more aggressive in detection
      if (chunk.includes('🔧 **Executing Tool:**') || chunk.includes('🔧') && chunk.includes('Executing Tool')) {
        console.log('🔧 Tool call detected:', chunk.trim());
        const toolMatch = chunk.match(/🔧\s*\*\*Executing Tool:\*\*\s*(\w+)\s*\(([^)]*)\)/);
        if (toolMatch) {
          const [, toolName, paramsStr] = toolMatch;
          console.log('Tool call parsed:', { toolName, paramsStr });
          const params = paramsStr ? Object.fromEntries(
            paramsStr.split(',').map(p => {
              const [key, value] = p.split('=');
              return [key?.trim(), value?.trim()];
            })
          ) : {};

          const toolCall: ToolCall = {
            id: generateId(),
            toolName,
            status: 'executing',
            parameters: params,
            startTime: new Date(),
          };

          updateToolCall(toolCall);
        }
        // Already handled by tool indicators check above
        return;
      }

      // Handle tool call result with exact backend format matching
      if (chunk.includes('✅ **Result:**') || chunk.includes('✅') && chunk.includes('Result')) {
        console.log('✅ Tool result detected:', chunk.trim().substring(0, 100) + '...');
        const resultMatch = chunk.match(/✅\s*\*\*Result:\*\*\s*([\s\S]*?)(?=\n|$)/);
        if (resultMatch) {
          const [, resultStr] = resultMatch;
          setChatState(prev => {
            const lastToolCall = prev.activeToolCalls[prev.activeToolCalls.length - 1];
            if (lastToolCall && lastToolCall.status === 'executing') {
              console.log('Completing tool call:', lastToolCall.toolName);
              const updatedToolCall: ToolCall = {
                ...lastToolCall,
                status: 'completed',
                result: resultStr.trim(),
                endTime: new Date(),
              };
              updateToolCall(updatedToolCall);
              
              // Check if this was the last active tool call
              const remainingActiveToolCalls = prev.activeToolCalls.filter(
                tc => tc.id !== lastToolCall.id && tc.status === 'executing'
              );
              
              console.log('Remaining active tool calls:', remainingActiveToolCalls.length);
              
              // If no more active tool calls, flush the buffer
              if (remainingActiveToolCalls.length === 0) {
                console.log('All tool calls complete, flushing buffer');
                setTimeout(() => flushBufferedContent(), 100); // Small delay to ensure state is updated
              }
            }
            return prev;
          });
        }
        // Add to buffer
        setChatState(prev => ({
          ...prev,
          bufferedContent: {
            ...prev.bufferedContent,
            chunks: [...prev.bufferedContent.chunks, chunk],
          },
        }));
        return;
      }

      // Handle tool call error with exact backend format matching
      if (chunk.includes('❌ **Error:**') || chunk.includes('❌') && chunk.includes('Error')) {
        console.log('❌ Tool error detected:', chunk.trim());
        const errorMatch = chunk.match(/❌\s*\*\*Error:\*\*\s*(.*?)(?=\n|$)/);
        if (errorMatch) {
          const [, errorStr] = errorMatch;
          setChatState(prev => {
            const lastToolCall = prev.activeToolCalls[prev.activeToolCalls.length - 1];
            if (lastToolCall && lastToolCall.status === 'executing') {
              console.log('Failing tool call:', lastToolCall.toolName, errorStr.trim());
              const updatedToolCall: ToolCall = {
                ...lastToolCall,
                status: 'failed',
                error: errorStr.trim(),
                endTime: new Date(),
              };
              updateToolCall(updatedToolCall);
              
              // Check if this was the last active tool call
              const remainingActiveToolCalls = prev.activeToolCalls.filter(
                tc => tc.id !== lastToolCall.id && tc.status === 'executing'
              );
              
              console.log('Remaining active tool calls after error:', remainingActiveToolCalls.length);
              
              // If no more active tool calls, flush the buffer
              if (remainingActiveToolCalls.length === 0) {
                console.log('All tool calls complete (with error), flushing buffer');
                setTimeout(() => flushBufferedContent(), 100); // Small delay to ensure state is updated
              }
            }
            return prev;
          });

          // Add error notification
          addError({
            type: 'tool_error',
            title: 'Tool Execution Failed',
            message: errorStr.trim(),
            dismissible: true,
            autoHide: true,
            duration: 5000,
          });
        }
        // Add to buffer
        setChatState(prev => ({
          ...prev,
          bufferedContent: {
            ...prev.bufferedContent,
            chunks: [...prev.bufferedContent.chunks, chunk],
          },
        }));
        return;
      }

      // Handle research iteration markers - don't display these
      if (chunk.includes('📋 **Research Iteration') || 
          chunk.includes('✨ **Research complete**') || 
          chunk.includes('🔄 **Continuing research**')) {
        
        console.log('Research marker detected:', chunk.trim());
        
        if (chunk.includes('✨ **Research complete**')) {
          console.log('Research complete - flushing buffer');
          // Research complete - flush any buffered content
          setTimeout(() => flushBufferedContent(), 100);
        }
        
        // Add to buffer
        setChatState(prev => ({
          ...prev,
          bufferedContent: {
            ...prev.bufferedContent,
            chunks: [...prev.bufferedContent.chunks, chunk],
          },
        }));
        return;
      }

      // Handle regular message content with improved buffering logic
      setChatState(prev => {
        const hasActiveToolCalls = prev.activeToolCalls.some(tc => tc.status === 'executing');
        
        if (hasActiveToolCalls || prev.bufferedContent.isBuffering) {
          // Buffer content during tool calls or if already buffering
          console.log('📦 Buffering chunk:', chunk.substring(0, 20) + '...', { hasActiveToolCalls, isBuffering: prev.bufferedContent.isBuffering });
          return {
            ...prev,
            bufferedContent: {
              ...prev.bufferedContent,
              chunks: [...prev.bufferedContent.chunks, chunk],
              isBuffering: true,
              hasActiveToolCalls: hasActiveToolCalls,
            },
          };
        } else {
          // No active tool calls - safe to display content
          // First flush any buffered content, then add new content
          if (prev.bufferedContent.chunks.length > 0) {
            console.log('📤 Flushing buffer and displaying new chunk:', chunk.substring(0, 20) + '...');
            const bufferedText = prev.bufferedContent.chunks.join('');
            appendToLastMessage(bufferedText + chunk);
            return {
              ...prev,
              bufferedContent: {
                chunks: [],
                isBuffering: false,
                hasActiveToolCalls: false,
              },
            };
          } else {
            console.log('📺 Directly displaying chunk:', chunk.substring(0, 20) + '...');
            appendToLastMessage(chunk);
            return prev;
          }
        }
      });

    } catch (error) {
      console.error('Error processing streaming chunk:', error);
      // Fallback: add to buffer if we have active tool calls, otherwise append directly
      setChatState(prev => {
        if (prev.bufferedContent.hasActiveToolCalls || prev.bufferedContent.isBuffering) {
          console.log('📦 Error fallback - buffering chunk');
          return {
            ...prev,
            bufferedContent: {
              ...prev.bufferedContent,
              chunks: [...prev.bufferedContent.chunks, chunk],
            },
          };
        } else {
          console.log('📺 Error fallback - displaying chunk');
          appendToLastMessage(chunk);
          return prev;
        }
      });
    }
  }, [appendToLastMessage, updateToolCall, addError, generateId, flushBufferedContent]);

  /**
   * Loads available tools from the backend
   */
  const loadAvailableTools = useCallback(async () => {
    console.log('🔧 Loading available tools...');
    try {
      const toolsResponse = await apiClient.getAvailableTools();
      console.log('🔧 Tools response received:', toolsResponse);
      
      const availableTools: AvailableTool[] = toolsResponse.available_tools.map(toolName => ({
        name: toolName,
        description: getToolDescription(toolName),
        enabled: false,
      }));

      console.log('🔧 Processed available tools:', availableTools);

      setChatState(prev => ({
        ...prev,
        availableTools,
        settings: {
          ...prev.settings,
          enabledTools: [], // No tools enabled by default
        },
      }));
    } catch (error) {
      console.error('❌ Failed to load available tools:', error);
      addError({
        type: 'api_error',
        title: 'Failed to Load Tools',
        message: 'Could not retrieve available tools from the backend.',
        dismissible: true,
        autoHide: true,
        duration: 5000,
      });
    }
  }, [addError]);

  /**
   * Gets a user-friendly description for a tool
   * @param toolName - Name of the tool
   * @returns Human-readable description
   */
  const getToolDescription = (toolName: string): string => {
    const descriptions: Record<string, string> = {
      web_search: 'Search the web for current information and research',
      file_write: 'Create and save files with analysis results',
      weather: 'Get current weather information for any location',
      codebase_search: 'Search through codebase for relevant code and documentation',
      grep_search: 'Search for specific text patterns in files',
      read_file: 'Read and analyze file contents',
      list_dir: 'List directory contents and file structure',
      run_terminal_cmd: 'Execute terminal commands and scripts',
    };
    
    return descriptions[toolName] || `${toolName.replace(/_/g, ' ')} tool`;
  };

  /**
   * Checks backend connectivity
   */
  const checkConnectivity = useCallback(async () => {
    console.log('🔍 Checking backend connectivity...');
    try {
      const healthResponse = await apiClient.getHealthStatus();
      console.log('💓 Health response received:', healthResponse);
      
      const isConnected = healthResponse.status === 'healthy';
      console.log('🔌 Connection status:', isConnected ? 'CONNECTED' : 'DISCONNECTED');
      
      setChatState(prev => ({
        ...prev,
        isConnected,
      }));

      if (!isConnected && healthResponse.error) {
        addError({
          type: 'connection_error',
          title: 'Backend Connection Issue',
          message: healthResponse.error,
          dismissible: true,
          autoHide: false,
        });
      }
    } catch (error) {
      console.error('❌ Connectivity check failed:', error);
      setChatState(prev => ({
        ...prev,
        isConnected: false,
      }));

      addError({
        type: 'connection_error',
        title: 'Connection Failed',
        message: 'Could not connect to the backend server.',
        dismissible: true,
        autoHide: false,
      });
    }
  }, [addError]);

  /**
   * Handles sending a user message and receiving agent response via streaming
   * Implements accuracy-first streaming with proper tool call handling
   * @param content - The user's message content
   */
  const handleUserMessage = useCallback(async (content: string) => {
    if (!content.trim() || chatState.isLoading) return;

    // Cancel any ongoing request
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }

    // Create new abort controller for this request
    const abortController = new AbortController();
    abortControllerRef.current = abortController;

    setChatState(prev => ({ 
      ...prev, 
      isLoading: true, 
      activeToolCalls: [],
      bufferedContent: {
        chunks: [],
        isBuffering: false,
        hasActiveToolCalls: false,
      },
    }));

    // Add user message
    addMessage({
      content,
      sender: 'user',
    });

    // Create agent message placeholder for streaming
    const agentMessage = addMessage({
      content: '',
      sender: 'agent',
      isStreaming: true,
      streamingComplete: false,
      isBlocked: false,
    });

    setChatState(prev => ({ ...prev, streamingMessageId: agentMessage.id }));

    console.log('🚀 Sending message with settings:', {
      enabledTools: chatState.settings.enabledTools,
      deepResearchMode: chatState.settings.deepResearchMode,
      message: content
    });

    try {
      // Prepare request payload
      const messages = [
        ...chatState.messages.map(msg => ({
          role: msg.sender === 'user' ? 'user' as const : 'assistant' as const,
          content: msg.content,
        })),
        {
          role: 'user' as const,
          content,
        },
      ];

      const request: SendMessageRequest = {
        messages,
        tools: chatState.settings.enabledTools,
        deep_research_mode: chatState.settings.deepResearchMode,
      };

      // Send message and process streaming response with abort signal
      const stream = await apiClient.sendMessageStream(request, abortController.signal);
      
      await processStreamingResponse(
        stream,
        (chunk) => {
          // Check if cancelled before processing chunk
          if (abortController.signal.aborted) {
            return;
          }
          // Process the streaming chunk with accuracy-first logic
          processStreamingChunk(chunk);
        },
        (error) => {
          console.error('Streaming error:', error);
          if (!abortController.signal.aborted) {
            addError({
              type: 'api_error',
              title: 'Streaming Error',
              message: error,
              dismissible: true,
              autoHide: true,
              duration: 5000,
            });
          }
        },
        abortController.signal
      );

      // Flush any remaining buffered content and mark streaming as complete
      flushBufferedContent();
      markStreamingComplete(agentMessage.id);

    } catch (error) {
      console.error('Error sending message:', error);
      
      // Don't show error if it was cancelled by user
      if (error instanceof Error && error.message === 'Request cancelled') {
        appendToLastMessage('\n\n🛑 Request cancelled by user');
      } else if (!abortController.signal.aborted) {
        const errorMessage = error instanceof Error ? error.message : 'An unexpected error occurred';
        
        addError({
          type: 'api_error',
          title: 'Message Send Failed',
          message: errorMessage,
          dismissible: true,
          autoHide: true,
          duration: 5000,
        });

        appendToLastMessage(`\n\n❌ Error: ${errorMessage}`);
      }
      
      // Flush any buffered content and mark streaming as complete
      flushBufferedContent();
      markStreamingComplete(agentMessage.id);
    } finally {
      setChatState(prev => ({ ...prev, isLoading: false }));
      // Clear the abort controller reference
      if (abortControllerRef.current === abortController) {
        abortControllerRef.current = null;
      }
    }
  }, [chatState.messages, chatState.settings, chatState.isLoading, addMessage, appendToLastMessage, processStreamingChunk, addError, markStreamingComplete, flushBufferedContent]);

  /**
   * Updates chat settings (enabled tools and deep research mode)
   * @param newSettings - Updated settings object
   */
  const updateSettings = useCallback((newSettings: ChatSettings) => {
    setChatState(prev => ({
      ...prev,
      settings: newSettings,
    }));
  }, []);

  /**
   * Clears all messages from the chat
   */
  const clearMessages = useCallback(() => {
    // Cancel any ongoing request
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }

    setChatState(prev => ({
      ...prev,
      messages: [],
      currentToolCall: undefined,
      activeToolCalls: [],
      isLoading: false,
      streamingMessageId: undefined,
      bufferedContent: {
        chunks: [],
        isBuffering: false,
        hasActiveToolCalls: false,
      },
    }));
  }, []);

  /**
   * Cancels the current message request
   */
  const cancelCurrentRequest = useCallback(() => {
    console.log('🛑 User requested to cancel current request');
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      setChatState(prev => ({ ...prev, isLoading: false }));
    }
  }, []);

  // Load available tools and check connectivity on mount
  useEffect(() => {
    loadAvailableTools();
    checkConnectivity();
  }, [loadAvailableTools, checkConnectivity]);

  // Periodic connectivity check
  useEffect(() => {
    const interval = setInterval(checkConnectivity, 30000); // Check every 30 seconds
    return () => clearInterval(interval);
  }, [checkConnectivity]);

  // Cleanup abort controller on unmount
  useEffect(() => {
    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, []);

  return {
    messages: chatState.messages,
    isLoading: chatState.isLoading,
    isConnected: chatState.isConnected,
    currentToolCall: chatState.currentToolCall,
    availableTools: chatState.availableTools,
    activeToolCalls: chatState.activeToolCalls,
    errors: chatState.errors,
    settings: chatState.settings,
    streamingMessageId: chatState.streamingMessageId,
    bufferedContent: chatState.bufferedContent,
    handleUserMessage,
    updateSettings,
    clearMessages,
    cancelCurrentRequest,
    loadAvailableTools,
    checkConnectivity,
    dismissError,
    updateToolCall,
    addError,
  };
}; 