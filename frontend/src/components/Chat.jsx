import React, { useState, useEffect, useRef } from 'react';
import MessageList from './MessageList';
import MessageInput from './MessageInput';
import { sendMessage, checkHealth } from '../services/api';
import { listClusters } from '../services/clusterApi';
import '../styles/Chat.css';

const Chat = () => {
  const [messages, setMessages] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [sessionId, setSessionId] = useState(null);
  const [healthStatus, setHealthStatus] = useState({ status: 'unknown', agent_ready: false, mcp_connected: false });
  const [clusters, setClusters] = useState([]);
  const [selectedClusterId, setSelectedClusterId] = useState(null);
  const messagesEndRef = useRef(null);

  // User ID is now managed by authentication - removed hardcoded userId

  // Scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  // Check health on mount
  useEffect(() => {
    const checkBackendHealth = async () => {
      try {
        const health = await checkHealth();
        setHealthStatus(health);
      } catch (err) {
        setHealthStatus({ status: 'error', agent_ready: false, mcp_connected: false });
      }
    };
    // Check health on mount and every 30 seconds
    checkBackendHealth();
    const interval = setInterval(checkBackendHealth, 30000);
    return () => clearInterval(interval);
  }, []);

  // Load clusters on mount
  useEffect(() => {
    const loadClusters = async () => {
      try {
        const clusterList = await listClusters();
        // Ensure clusterList is an array
        const clustersArray = Array.isArray(clusterList) ? clusterList : [];
        setClusters(clustersArray);
        // Auto-select first connected cluster if available
        if (clustersArray.length > 0) {
          const connectedCluster = clustersArray.find(c => c && c.status === 'connected');
          if (connectedCluster) {
            setSelectedClusterId(connectedCluster.id);
          } else {
            setSelectedClusterId(clustersArray[0].id);
          }
        }
      } catch (err) {
        console.error('Failed to load clusters:', err);
        // Set empty array on error to prevent .find() errors
        setClusters([]);
      }
    };
    loadClusters();
  }, []);

  const handleSendMessage = async (messageText) => {
    // Add user message to UI immediately
    const userMessage = {
      role: 'user',
      content: messageText,
      timestamp: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, userMessage]);
    setIsLoading(true);
    setError(null);

    try {
      const response = await sendMessage(messageText, sessionId, selectedClusterId);
      
      // Update session ID if provided
      if (response.session_id) {
        setSessionId(response.session_id);
      }

      // Add assistant response
      const assistantMessage = {
        role: 'assistant',
        content: response.response,
        timestamp: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, assistantMessage]);
    } catch (err) {
      setError(err.message || 'Failed to send message');
      // Remove user message on error (optional - you might want to keep it)
      setMessages((prev) => prev.slice(0, -1));
    } finally {
      setIsLoading(false);
    }
  };

  // Ensure clusters is always an array
  const clustersArray = Array.isArray(clusters) ? clusters : [];
  const selectedCluster = clustersArray.find(c => c && c.id === selectedClusterId) || null;

  return (
    <div className="chat-container">
      {clustersArray.length > 0 && (
        <div className="cluster-selector">
          <label htmlFor="cluster-select">Cluster:</label>
          <select
            id="cluster-select"
            value={selectedClusterId || ''}
            onChange={(e) => setSelectedClusterId(e.target.value || null)}
            className="cluster-select"
          >
            <option value="">Default (No cluster selected)</option>
            {clustersArray.map((cluster) => (
              <option key={cluster.id} value={cluster.id}>
                {cluster.name} ({cluster.status || 'unknown'})
              </option>
            ))}
          </select>
          {selectedCluster && (
            <span className={`cluster-status-badge status-${selectedCluster.status || 'unknown'}`}>
              {selectedCluster.status || 'unknown'}
            </span>
          )}
        </div>
      )}
      {error && (
        <div className="error-message">
          Error: {error}
        </div>
      )}
      <MessageList messages={messages} isLoading={isLoading} />
      <div ref={messagesEndRef} />
      <MessageInput onSendMessage={handleSendMessage} disabled={isLoading} />
    </div>
  );
};

export default Chat;

