import React from 'react';
import './../styles/Chat.css';

const MessageList = ({ messages, isLoading }) => {
  const formatTime = (timestamp) => {
    if (!timestamp) return '';
    const date = new Date(timestamp);
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  if (messages.length === 0 && !isLoading) {
    return (
      <div className="messages-container">
        <div className="empty-state">
          <h3>Welcome to SRE Agent</h3>
          <p>
            Start a conversation by asking about Kubernetes troubleshooting, 
            security reviews, or cluster analysis.
          </p>
          <p style={{ marginTop: '1rem', fontSize: '0.875rem' }}>
            Try: "List all pods in default namespace" or 
            "Review security of test-app deployment"
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="messages-container">
      {messages.map((message, index) => (
        <div key={index} className={`message ${message.role}`}>
          <div className="message-label">
            {message.role === 'user' ? 'You' : 'SRE Agent'}
          </div>
          <div className="message-bubble">
            {message.content.split('\n').map((line, i) => (
              <React.Fragment key={i}>
                {line}
                {i < message.content.split('\n').length - 1 && <br />}
              </React.Fragment>
            ))}
          </div>
          {message.timestamp && (
            <div className="message-time">{formatTime(message.timestamp)}</div>
          )}
        </div>
      ))}
      {isLoading && (
        <div className="message assistant">
          <div className="message-label">SRE Agent</div>
          <div className="loading-indicator">
            <span>Thinking</span>
            <div className="loading-dots">
              <div className="loading-dot"></div>
              <div className="loading-dot"></div>
              <div className="loading-dot"></div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default MessageList;

