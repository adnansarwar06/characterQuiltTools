/**
 * Tool selector component for configuring research agent capabilities
 */

import React from 'react';
import { AvailableTool, ChatSettings } from '../types/chat';

interface ToolSelectorProps {
  /** List of available tools from the backend */
  availableTools: AvailableTool[];
  /** Current chat settings including enabled tools and deep research mode */
  settings: ChatSettings;
  /** Callback fired when settings are updated */
  onSettingsChange: (settings: ChatSettings) => void;
  /** Whether the tool selector should be disabled */
  disabled?: boolean;
  /** Additional CSS class name for styling */
  className?: string;
}

/**
 * Gets a user-friendly description for a tool
 * @param toolName - Name of the tool
 * @returns Human-readable description
 */
const getToolDescription = (toolName: string): string => {
  const descriptions: Record<string, string> = {
    'web_search': 'Search the internet for current information',
    'file_write': 'Create and save files with analysis results',
    'weather': 'Get current weather conditions for any location',
    'codebase_search': 'Search through code repositories and documentation',
    'grep_search': 'Find specific text patterns in files',
    'read_file': 'Read and analyze file contents',
    'list_dir': 'Browse directory contents and file structure',
    'run_terminal_cmd': 'Execute system commands and scripts',
  };
  
  return descriptions[toolName] || 'Research tool';
};

/**
 * Formats tool names for display (converts snake_case to Title Case)
 * @param toolName - Raw tool name from the backend
 * @returns Formatted tool name
 */
const formatToolName = (toolName: string): string => {
  const toolNameMappings: Record<string, string> = {
    'web_search': 'Web Search',
    'file_write': 'File Writer',
    'weather': 'Weather Info',
    'codebase_search': 'Code Search',
    'grep_search': 'Text Search',
    'read_file': 'File Reader',
    'list_dir': 'Directory List',
    'run_terminal_cmd': 'Terminal Command',
  };
  
  return toolNameMappings[toolName] || 
         toolName.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
};

/**
 * Component for selecting enabled tools and configuring research mode
 * Provides checkboxes for individual tools and a toggle for deep research mode
 */
export const ToolSelector: React.FC<ToolSelectorProps> = ({
  availableTools,
  settings,
  onSettingsChange,
  disabled = false,
  className = '',
}) => {
  /**
   * Handles toggling a tool's enabled state
   * @param toolName - Name of the tool to toggle
   */
  const handleToolToggle = (toolName: string) => {
    const isCurrentlyEnabled = settings.enabledTools.includes(toolName);
    const updatedTools = isCurrentlyEnabled
      ? settings.enabledTools.filter(tool => tool !== toolName)
      : [...settings.enabledTools, toolName];

    onSettingsChange({
      ...settings,
      enabledTools: updatedTools,
    });
  };

  /**
   * Handles toggling deep research mode
   */
  const handleDeepResearchToggle = () => {
    onSettingsChange({
      ...settings,
      deepResearchMode: !settings.deepResearchMode,
    });
  };

  /**
   * Handles selecting all tools
   */
  const handleSelectAllTools = () => {
    const allToolNames = availableTools.map(tool => tool.name);
    onSettingsChange({
      ...settings,
      enabledTools: allToolNames,
    });
  };

  /**
   * Handles deselecting all tools
   */
  const handleDeselectAllTools = () => {
    onSettingsChange({
      ...settings,
      enabledTools: [],
    });
  };

  const allToolsSelected = availableTools.length > 0 && 
    settings.enabledTools.length === availableTools.length;
  const someToolsSelected = settings.enabledTools.length > 0;

  return (
    <div className={`tool-selector ${className}`}>
      <div className="tool-selector__header">
        <h3 className="tool-selector__title">Research Tools & Settings</h3>
        <div className="tool-selector__actions">
          <button
            type="button"
            className="tool-selector__action-button"
            onClick={allToolsSelected ? handleDeselectAllTools : handleSelectAllTools}
            disabled={disabled || availableTools.length === 0}
            aria-label={allToolsSelected ? 'Disable all research tools' : 'Enable all research tools'}
            title={allToolsSelected ? 'Disable all tools' : 'Enable all available tools'}
          >
            {allToolsSelected ? 'Disable All Tools' : 'Enable All Tools'}
          </button>
        </div>
      </div>

      <div className="tool-selector__deep-research">
        <label className="tool-selector__toggle-label">
          <input
            type="checkbox"
            className="tool-selector__toggle-input"
            checked={settings.deepResearchMode}
            onChange={handleDeepResearchToggle}
            disabled={disabled}
            aria-describedby="deep-research-help"
          />
          <span className="tool-selector__toggle-slider"></span>
          <span className="tool-selector__toggle-text">
            Deep Research Mode
          </span>
        </label>
        <p id="deep-research-help" className="tool-selector__help-text">
          Enable multi-step analysis and investigation. When disabled, each response uses tools only once.
        </p>
      </div>

      <div className="tool-selector__tools">
        <h4 className="tool-selector__section-title">
          Available Tools ({settings.enabledTools.length} of {availableTools.length} enabled)
        </h4>
        
        {availableTools.length === 0 ? (
          <div className="tool-selector__empty-state">
            <p className="tool-selector__empty-text">
              No research tools available. Please check your connection and try reconnecting.
            </p>
          </div>
        ) : (
          <div className="tool-selector__tool-list" role="group" aria-label="Available research tools">
            {availableTools.map((tool) => {
              const isEnabled = settings.enabledTools.includes(tool.name);
              const formattedName = formatToolName(tool.name);
              const description = tool.description || getToolDescription(tool.name);
              
              return (
                <label
                  key={tool.name}
                  className={`tool-selector__tool-item ${
                    isEnabled ? 'tool-selector__tool-item--enabled' : ''
                  }`}
                >
                  <input
                    type="checkbox"
                    className="tool-selector__tool-checkbox"
                    checked={isEnabled}
                    onChange={() => handleToolToggle(tool.name)}
                    disabled={disabled}
                    aria-describedby={`tool-${tool.name}-description`}
                  />
                  <div className="tool-selector__tool-content">
                    <span className="tool-selector__tool-name">
                      {formattedName}
                    </span>
                    <span 
                      id={`tool-${tool.name}-description`}
                      className="tool-selector__tool-description"
                    >
                      {description}
                    </span>
                  </div>
                  <span className="tool-selector__tool-indicator" aria-hidden="true">
                    {isEnabled ? '✓' : '○'}
                  </span>
                </label>
              );
            })}
          </div>
        )}
      </div>

      {someToolsSelected && (
        <div className="tool-selector__summary">
          <p className="tool-selector__summary-text">
            {settings.enabledTools.length} tool{settings.enabledTools.length !== 1 ? 's' : ''} ready
            {settings.deepResearchMode ? ' • Deep research enabled' : ' • Quick responses'}
          </p>
        </div>
      )}
    </div>
  );
}; 