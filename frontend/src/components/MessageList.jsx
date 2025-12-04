import React from 'react';
import Message from './Message';
import './../styles/Chat.css';
import './../styles/Message.css';

const MessageList = ({ messages, isLoading }) => {
  if (messages.length === 0 && !isLoading) {
    return (
      <div className="messages-container">
        <div className="empty-state">
          <div className="empty-state-icon">
            <svg width="48" height="48" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
              <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 3c1.66 0 3 1.34 3 3s-1.34 3-3 3-3-1.34-3-3 1.34-3 3-3zm0 14.2c-2.5 0-4.71-1.28-6-3.22.03-1.99 4-3.08 6-3.08 1.99 0 5.97 1.09 6 3.08-1.29 1.94-3.5 3.22-6 3.22z" fill="#8e8ea0"/>
            </svg>
          </div>
          <h3>Welcome to SRE Agent</h3>
          <p>
            Start a conversation by asking about Kubernetes troubleshooting, 
            security reviews, or cluster analysis.
          </p>
          <div className="empty-state-suggestions">
            <p>Try:</p>
            <ul>
              <li>"List all pods in default namespace"</li>
              <li>"Review security of test-app deployment"</li>
              <li>"What resources are consuming the most CPU?"</li>
            </ul>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="messages-container">
      {messages.map((message, index) => (
        <Message key={index} message={message} index={index} />
      ))}
      {isLoading && (
        <div className="message-wrapper assistant">
          <div className="message-container">
            <div className="message-avatar">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 3c1.66 0 3 1.34 3 3s-1.34 3-3 3-3-1.34-3-3 1.34-3 3-3zm0 14.2c-2.5 0-4.71-1.28-6-3.22.03-1.99 4-3.08 6-3.08 1.99 0 5.97 1.09 6 3.08-1.29 1.94-3.5 3.22-6 3.22z" fill="currentColor"/>
              </svg>
            </div>
            <div className="message-content-wrapper">
              <div className="message-header">
                <span className="message-author">SRE Agent</span>
              </div>
              <div className="loading-indicator">
                <span>Thinking</span>
                <div className="loading-dots">
                  <div className="loading-dot"></div>
                  <div className="loading-dot"></div>
                  <div className="loading-dot"></div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default MessageList;

