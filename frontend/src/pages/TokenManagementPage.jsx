import React, { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { listTokens, createToken, revokeToken } from '../services/tokenApi';
import '../styles/TokenManagementPage.css';

const TokenManagementPage = () => {
  const { isAuthenticated } = useAuth();
  const [tokens, setTokens] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [newToken, setNewToken] = useState({ name: '', expires_at: '' });
  const [createdToken, setCreatedToken] = useState(null);

  useEffect(() => {
    if (isAuthenticated) {
      loadTokens();
    }
  }, [isAuthenticated]);

  const loadTokens = async () => {
    try {
      setLoading(true);
      const data = await listTokens();
      setTokens(data);
    } catch (err) {
      setError(err.detail || 'Failed to load tokens');
    } finally {
      setLoading(false);
    }
  };

  const handleCreateToken = async (e) => {
    e.preventDefault();
    try {
      setError('');
      const data = await createToken(newToken);
      setCreatedToken(data);
      setSuccess('Token created successfully. Copy it now - it will not be shown again!');
      setShowCreateModal(false);
      setNewToken({ name: '', expires_at: '' });
      loadTokens();
    } catch (err) {
      setError(err.detail || 'Failed to create token');
    }
  };

  const handleRevokeToken = async (tokenId) => {
    if (!window.confirm('Are you sure you want to revoke this token?')) {
      return;
    }
    try {
      setError('');
      await revokeToken(tokenId);
      setSuccess('Token revoked successfully');
      loadTokens();
    } catch (err) {
      setError(err.detail || 'Failed to revoke token');
    }
  };

  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text).then(() => {
      setSuccess('Token copied to clipboard!');
    }).catch(() => {
      setError('Failed to copy token');
    });
  };

  return (
    <div className="token-management-page">
      <div className="page-header">
        <h1>API Token Management</h1>
        <button className="btn-primary" onClick={() => setShowCreateModal(true)}>
          Create Token
        </button>
      </div>

      {error && <div className="alert alert-error">{error}</div>}
      {success && <div className="alert alert-success">{success}</div>}

      {/* Created Token Display (one-time) */}
      {createdToken && (
        <div className="alert alert-warning">
          <h3>Token Created - Copy Now!</h3>
          <p>This token will only be shown once. Make sure to copy it now.</p>
          <div className="token-display">
            <code>{createdToken.token}</code>
            <button className="btn-secondary" onClick={() => copyToClipboard(createdToken.token)}>
              Copy
            </button>
          </div>
          <button className="btn-secondary" onClick={() => setCreatedToken(null)}>
            I've copied it
          </button>
        </div>
      )}

      {/* Tokens Table */}
      <div className="section">
        <h2>My API Tokens</h2>
        {loading ? (
          <div>Loading...</div>
        ) : tokens.length === 0 ? (
          <p>No API tokens created yet.</p>
        ) : (
          <table className="tokens-table">
            <thead>
              <tr>
                <th>Name</th>
                <th>Created</th>
                <th>Last Used</th>
                <th>Expires</th>
                <th>Status</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {tokens.map((token) => (
                <tr key={token.id}>
                  <td>{token.name}</td>
                  <td>{token.created_at ? new Date(token.created_at).toLocaleString() : '-'}</td>
                  <td>{token.last_used_at ? new Date(token.last_used_at).toLocaleString() : 'Never'}</td>
                  <td>{token.expires_at ? new Date(token.expires_at).toLocaleString() : 'Never'}</td>
                  <td>
                    {token.is_expired ? (
                      <span className="badge badge-error">Expired</span>
                    ) : (
                      <span className="badge badge-success">Active</span>
                    )}
                  </td>
                  <td>
                    <button
                      className="btn-small btn-danger"
                      onClick={() => handleRevokeToken(token.id)}
                    >
                      Revoke
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Create Token Modal */}
      {showCreateModal && (
        <div className="modal-overlay" onClick={() => setShowCreateModal(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h2>Create API Token</h2>
            <form onSubmit={handleCreateToken}>
              <div className="form-group">
                <label>Token Name</label>
                <input
                  type="text"
                  value={newToken.name}
                  onChange={(e) => setNewToken({ ...newToken, name: e.target.value })}
                  placeholder="e.g., Production API"
                  required
                />
              </div>
              <div className="form-group">
                <label>Expires At (Optional)</label>
                <input
                  type="datetime-local"
                  value={newToken.expires_at}
                  onChange={(e) => setNewToken({ ...newToken, expires_at: e.target.value })}
                />
                <small>Leave empty for no expiration</small>
              </div>
              <div className="modal-actions">
                <button type="submit" className="btn-primary">Create</button>
                <button
                  type="button"
                  className="btn-secondary"
                  onClick={() => setShowCreateModal(false)}
                >
                  Cancel
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default TokenManagementPage;

