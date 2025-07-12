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
    }
  }
}

export interface AppConfig {
  apiBaseUrl: string;
  websocketUrl: string;
  agentName: string;
}

/**
 * Application configuration loaded from environment variables
 * Tools are now loaded dynamically from the backend API
 */
export const config: AppConfig = {
  apiBaseUrl: process.env.REACT_APP_API_BASE_URL || 'http://localhost:8000',
  websocketUrl: process.env.REACT_APP_WEBSOCKET_URL || 'ws://localhost:8000/ws',
  agentName: process.env.REACT_APP_AGENT_NAME || 'Research Agent',
};

/**
 * Validates that all required configuration values are present
 * @throws Error if any required configuration is missing
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

  // Validate URL formats
  try {
    new URL(config.apiBaseUrl);
  } catch {
    throw new Error(`Invalid API base URL: ${config.apiBaseUrl}`);
  }

  try {
    new URL(config.websocketUrl);
  } catch {
    throw new Error(`Invalid WebSocket URL: ${config.websocketUrl}`);
  }
}; 