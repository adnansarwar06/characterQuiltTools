/**
 * Configuration settings for the research agent chat UI
 * Loads from environment variables with fallback defaults
 */

// Type declaration for React environment variables
declare global {
  namespace NodeJS {
    interface ProcessEnv {
      REACT_APP_API_BASE_URL?: string;
      REACT_APP_WEBSOCKET_URL?: string;
      REACT_APP_AGENT_NAME?: string;
      REACT_APP_TOOLS_WEB_SEARCH?: string;
      REACT_APP_TOOLS_CODE_ANALYSIS?: string;
      REACT_APP_TOOLS_FILE_READER?: string;
      REACT_APP_TOOLS_DOCUMENT_SEARCH?: string;
    }
  }
}

export interface AppConfig {
  apiBaseUrl: string;
  websocketUrl: string;
  agentName: string;
  tools: {
    webSearch: string;
    codeAnalysis: string;
    fileReader: string;
    documentSearch: string;
  };
}

/**
 * Application configuration loaded from environment variables
 */
export const config: AppConfig = {
  apiBaseUrl: process.env.REACT_APP_API_BASE_URL || 'http://localhost:8000/api',
  websocketUrl: process.env.REACT_APP_WEBSOCKET_URL || 'ws://localhost:8000/ws',
  agentName: process.env.REACT_APP_AGENT_NAME || 'Research Agent',
  tools: {
    webSearch: process.env.REACT_APP_TOOLS_WEB_SEARCH || 'Web Search',
    codeAnalysis: process.env.REACT_APP_TOOLS_CODE_ANALYSIS || 'Code Analysis',
    fileReader: process.env.REACT_APP_TOOLS_FILE_READER || 'File Reader',
    documentSearch: process.env.REACT_APP_TOOLS_DOCUMENT_SEARCH || 'Document Search',
  },
};

/**
 * Validates that all required configuration values are present
 */
export const validateConfig = (): void => {
  const requiredFields = [
    'apiBaseUrl',
    'websocketUrl',
    'agentName',
  ];

  for (const field of requiredFields) {
    if (!config[field as keyof AppConfig]) {
      throw new Error(`Missing required configuration: ${field}`);
    }
  }
}; 