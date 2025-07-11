/**
 * Main entry point for the Research Agent Chat UI
 */

import React from 'react';
import { createRoot } from 'react-dom/client';
import { Chat } from './components/Chat';
import { validateConfig } from './config/config';
import './styles/global.css';

/**
 * Initialize the application
 */
const initializeApp = () => {
  try {
    // Validate configuration before starting
    validateConfig();
    
    // Get the root element
    const container = document.getElementById('root');
    if (!container) {
      throw new Error('Root element not found');
    }

    // Create React root and render the app
    const root = createRoot(container);
    root.render(
      <React.StrictMode>
        <div className="app">
          <Chat />
        </div>
      </React.StrictMode>
    );

    console.log('Research Agent Chat UI initialized successfully');
  } catch (error) {
    console.error('Failed to initialize application:', error);
    
    // Show error message to user
    const container = document.getElementById('root');
    if (container) {
      container.innerHTML = `
        <div class="error-container">
          <h1>Application Error</h1>
          <p>Failed to initialize the chat application:</p>
          <pre>${error instanceof Error ? error.message : String(error)}</pre>
          <p>Please check the console for more details.</p>
        </div>
      `;
    }
  }
};

// Initialize the app when DOM is ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initializeApp);
} else {
  initializeApp();
} 