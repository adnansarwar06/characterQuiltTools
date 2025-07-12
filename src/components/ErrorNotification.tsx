/**
 * Error notification component for displaying API and tool errors
 */

import React, { useEffect, useState } from 'react';
import { ErrorNotification as ErrorNotificationType } from '../types/chat';

interface ErrorNotificationProps {
  error: ErrorNotificationType;
  onDismiss: (errorId: string) => void;
  className?: string;
}

/**
 * Displays error notifications as dismissible toasts
 * Supports auto-hide functionality and different error types
 */
export const ErrorNotification: React.FC<ErrorNotificationProps> = ({
  error,
  onDismiss,
  className = ''
}) => {
  const [isVisible, setIsVisible] = useState(true);
  const [isExiting, setIsExiting] = useState(false);

  useEffect(() => {
    if (error.autoHide && error.duration) {
      const timer = setTimeout(() => {
        handleDismiss();
      }, error.duration);

      return () => clearTimeout(timer);
    }
  }, [error.autoHide, error.duration]);

  const handleDismiss = () => {
    if (!isExiting) {
      setIsExiting(true);
      setTimeout(() => {
        setIsVisible(false);
        onDismiss(error.id);
      }, 300); // Animation duration
    }
  };

  const getErrorIcon = (type: ErrorNotificationType['type']): string => {
    switch (type) {
      case 'api_error':
        return '🌐';
      case 'tool_error':
        return '🔧';
      case 'connection_error':
        return '📡';
      case 'validation_error':
        return '⚠️';
      default:
        return '❌';
    }
  };

  const getErrorColor = (type: ErrorNotificationType['type']): string => {
    switch (type) {
      case 'api_error':
        return '#dc2626';
      case 'tool_error':
        return '#ea580c';
      case 'connection_error':
        return '#7c2d12';
      case 'validation_error':
        return '#facc15';
      default:
        return '#dc2626';
    }
  };

  const getErrorTypeDescription = (type: ErrorNotificationType['type']): string => {
    switch (type) {
      case 'api_error':
        return 'API Error';
      case 'tool_error':
        return 'Tool Error';
      case 'connection_error':
        return 'Connection Error';
      case 'validation_error':
        return 'Validation Error';
      default:
        return 'Error';
    }
  };

  if (!isVisible) return null;

  const typeDescription = getErrorTypeDescription(error.type);

  return (
    <div
      className={`error-notification error-notification--${error.type} ${
        isExiting ? 'error-notification--exiting' : ''
      } ${className}`}
      role="alert"
      aria-live="assertive"
      style={{ '--error-color': getErrorColor(error.type) } as React.CSSProperties}
    >
      <div className="error-notification__content">
        <div className="error-notification__icon" aria-hidden="true">
          {getErrorIcon(error.type)}
        </div>
        
        <div className="error-notification__text">
          <div className="error-notification__title">
            {error.title || typeDescription}
          </div>
          <div className="error-notification__message">
            {error.message}
          </div>
          <div className="error-notification__timestamp">
            {error.timestamp.toLocaleTimeString()}
          </div>
        </div>
        
        {error.dismissible && (
          <button
            className="error-notification__dismiss"
            onClick={handleDismiss}
            aria-label={`Dismiss ${typeDescription.toLowerCase()}`}
            title="Click to dismiss this error"
            type="button"
          >
            <span aria-hidden="true">×</span>
          </button>
        )}
      </div>
      
      {error.autoHide && error.duration && (
        <div 
          className="error-notification__progress"
          style={{
            animationDuration: `${error.duration}ms`,
            animationPlayState: isExiting ? 'paused' : 'running'
          }}
          aria-hidden="true"
        />
      )}
    </div>
  );
};

interface ErrorNotificationContainerProps {
  errors: ErrorNotificationType[];
  onDismiss: (errorId: string) => void;
  maxVisible?: number;
  className?: string;
}

/**
 * Container for managing multiple error notifications
 * Handles stacking and maximum visible count
 */
export const ErrorNotificationContainer: React.FC<ErrorNotificationContainerProps> = ({
  errors,
  onDismiss,
  maxVisible = 5,
  className = ''
}) => {
  const visibleErrors = errors.slice(-maxVisible);

  if (visibleErrors.length === 0) return null;

  return (
    <div
      className={`error-notification-container ${className}`}
      role="region"
      aria-label="Error notifications"
      aria-live="polite"
    >
      {visibleErrors.map((error) => (
        <ErrorNotification
          key={error.id}
          error={error}
          onDismiss={onDismiss}
        />
      ))}
    </div>
  );
}; 