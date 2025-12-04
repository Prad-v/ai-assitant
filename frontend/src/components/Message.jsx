import React, { useState } from 'react';
import '../styles/Message.css';

const Message = ({ message, index }) => {
  const [showActions, setShowActions] = useState(false);
  const [copied, setCopied] = useState(false);
  const [shareUrl, setShareUrl] = useState(null);

  const formatTime = (timestamp) => {
    if (!timestamp) return '';
    const date = new Date(timestamp);
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(message.content);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy:', err);
    }
  };

  const handleShare = async () => {
    try {
      const shareData = {
        title: 'SRE Agent Conversation',
        text: `${message.role === 'user' ? 'You' : 'SRE Agent'}: ${message.content}`,
      };

      if (navigator.share && navigator.canShare(shareData)) {
        await navigator.share(shareData);
      } else {
        // Fallback: copy to clipboard with share format
        const shareText = `SRE Agent Conversation\n\n${message.role === 'user' ? 'You' : 'SRE Agent'} (${formatTime(message.timestamp)}):\n${message.content}`;
        await navigator.clipboard.writeText(shareText);
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
      }
    } catch (err) {
      if (err.name !== 'AbortError') {
        console.error('Failed to share:', err);
      }
    }
  };

  const formatContent = (content) => {
    // Simple markdown-like formatting
    let formatted = content;
    
    // Code blocks
    formatted = formatted.replace(/```([\s\S]*?)```/g, '<pre><code>$1</code></pre>');
    
    // Inline code
    formatted = formatted.replace(/`([^`]+)`/g, '<code>$1</code>');
    
    // Bold
    formatted = formatted.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
    
    // Italic
    formatted = formatted.replace(/\*(.+?)\*/g, '<em>$1</em>');
    
    // Links
    formatted = formatted.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>');
    
    // Line breaks
    formatted = formatted.split('\n').map((line, i) => {
      if (line.trim() === '') return '<br />';
      return line;
    }).join('\n');
    
    return formatted;
  };

  const isUser = message.role === 'user';
  const formattedContent = formatContent(message.content);

  return (
    <div 
      className={`message-wrapper ${isUser ? 'user' : 'assistant'}`}
      onMouseEnter={() => setShowActions(true)}
      onMouseLeave={() => setShowActions(false)}
    >
      <div className="message-container">
        {!isUser && (
          <div className="message-avatar">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
              <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 3c1.66 0 3 1.34 3 3s-1.34 3-3 3-3-1.34-3-3 1.34-3 3-3zm0 14.2c-2.5 0-4.71-1.28-6-3.22.03-1.99 4-3.08 6-3.08 1.99 0 5.97 1.09 6 3.08-1.29 1.94-3.5 3.22-6 3.22z" fill="currentColor"/>
            </svg>
          </div>
        )}
        <div className="message-content-wrapper">
          <div className="message-header">
            <span className="message-author">{isUser ? 'You' : 'SRE Agent'}</span>
            {message.timestamp && (
              <span className="message-time">{formatTime(message.timestamp)}</span>
            )}
          </div>
          <div 
            className={`message-bubble ${isUser ? 'user-bubble' : 'assistant-bubble'}`}
            dangerouslySetInnerHTML={{ __html: formattedContent }}
          />
          {showActions && (
            <div className="message-actions">
              <button
                className="action-button copy-button"
                onClick={handleCopy}
                title="Copy message"
              >
                {copied ? (
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41L9 16.17z" fill="currentColor"/>
                  </svg>
                ) : (
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <path d="M16 1H4c-1.1 0-2 .9-2 2v14h2V3h12V1zm3 4H8c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h11c1.1 0 2-.9 2-2V7c0-1.1-.9-2-2-2zm0 16H8V7h11v14z" fill="currentColor"/>
                  </svg>
                )}
                <span>{copied ? 'Copied!' : 'Copy'}</span>
              </button>
              <button
                className="action-button share-button"
                onClick={handleShare}
                title="Share message"
              >
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                  <path d="M18 16.08c-.76 0-1.44.3-1.96.77L8.91 12.7c.05-.23.09-.46.09-.7s-.04-.47-.09-.7l7.05-4.11c.54.5 1.25.81 2.04.81 1.66 0 3-1.34 3-3s-1.34-3-3-3-3 1.34-3 3c0 .24.04.47.09.7L8.04 9.81C7.5 9.31 6.79 9 6 9c-1.66 0-3 1.34-3 3s1.34 3 3 3c.79 0 1.5-.31 2.04-.81l7.12 4.16c-.05.21-.08.43-.08.65 0 1.61 1.31 2.92 2.92 2.92 1.61 0 2.92-1.31 2.92-2.92s-1.31-2.92-2.92-2.92z" fill="currentColor"/>
                </svg>
                <span>Share</span>
              </button>
            </div>
          )}
        </div>
        {isUser && (
          <div className="message-avatar user-avatar">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
              <path d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z" fill="currentColor"/>
            </svg>
          </div>
        )}
      </div>
    </div>
  );
};

export default Message;

