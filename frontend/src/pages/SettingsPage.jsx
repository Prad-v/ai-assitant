import React, { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { getModelSettings, updateModelSettings, validateApiKey, listAvailableModels, reloadAgent, testSavedConfiguration } from '../services/settingsApi';
import UserManagementPage from './UserManagementPage';
import TokenManagementPage from './TokenManagementPage';
import '../styles/SettingsPage.css';

const PROVIDERS = [
  { value: 'openai', label: 'OpenAI' },
  { value: 'gemini', label: 'Google Gemini' },
  { value: 'anthropic', label: 'Anthropic Claude' },
];

function SettingsPage() {
  const { isAdmin } = useAuth();
  const [activeTab, setActiveTab] = useState('model');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [validating, setValidating] = useState(false);
  const [fetchingModels, setFetchingModels] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);
  const [validationResult, setValidationResult] = useState(null);
  const [availableModels, setAvailableModels] = useState([]);
  const [apiKeyValidated, setApiKeyValidated] = useState(false);

  const [formData, setFormData] = useState({
    provider: 'openai',
    model_name: '',
    api_key: '',
    max_tokens: '',
    temperature: '',
  });

  useEffect(() => {
    if (activeTab === 'model') {
      loadSettings();
    }
  }, [activeTab]);

  const loadSettings = async () => {
    try {
      setLoading(true);
      setError(null);
      const settings = await getModelSettings();
      const provider = settings.provider || 'openai';
      const modelName = settings.model_name || getDefaultModel(provider);
      setFormData({
        provider: provider,
        model_name: modelName,
        api_key: '', // Don't show existing API key
        max_tokens: settings.max_tokens?.toString() || '',
        temperature: settings.temperature?.toString() || '',
      });
    } catch (err) {
      setError(err.message || 'Failed to load settings');
    } finally {
      setLoading(false);
    }
  };

  const getDefaultModel = (provider) => {
    const defaults = {
      openai: 'gpt-4',
      gemini: 'gemini-2.0-flash',
      anthropic: 'claude-3-sonnet-20240229',
    };
    return defaults[provider] || '';
  };

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => {
      const updated = {
        ...prev,
        [name]: value,
      };
      // When provider changes, set default model
      if (name === 'provider') {
        updated.model_name = getDefaultModel(value);
      }
      return updated;
    });
    // Clear validation result and models when fields change
    if (name === 'provider' || name === 'api_key') {
      setValidationResult(null);
      setApiKeyValidated(false);
      setAvailableModels([]);
    }
  };

  const handleValidate = async () => {
    if (!formData.api_key.trim()) {
      setError('Please enter an API key to validate');
      return;
    }

    // Ensure we have a model name (use default if not set)
    const modelToValidate = formData.model_name || getDefaultModel(formData.provider);
    if (!modelToValidate) {
      setError('Please select a model provider');
      return;
    }

    try {
      setValidating(true);
      setError(null);
      setValidationResult(null);
      setApiKeyValidated(false);
      setAvailableModels([]);
      
      // Use the selected model (or default) for validation
      const result = await validateApiKey(
        formData.provider,
        modelToValidate,
        formData.api_key
      );
      
      setValidationResult(result);
      
      if (result.valid) {
        setApiKeyValidated(true);
        // Fetch available models after successful validation
        await fetchAvailableModels();
      } else {
        setError(result.message);
      }
    } catch (err) {
      setError(err.message || 'Failed to validate API key');
      setValidationResult({ valid: false, message: err.message });
      setApiKeyValidated(false);
    } finally {
      setValidating(false);
    }
  };

  const fetchAvailableModels = async () => {
    if (!formData.api_key.trim()) {
      return;
    }

    try {
      setFetchingModels(true);
      setError(null);
      const result = await listAvailableModels(formData.provider, formData.api_key);
      
      if (result.success && result.models && result.models.length > 0) {
        setAvailableModels(result.models);
        // Auto-select first model if none selected
        if (!formData.model_name) {
          setFormData(prev => ({ ...prev, model_name: result.models[0] }));
        }
      } else {
        setError(result.message || 'No models available');
        setAvailableModels([]);
      }
    } catch (err) {
      setError(err.message || 'Failed to fetch available models');
      setAvailableModels([]);
    } finally {
      setFetchingModels(false);
    }
  };

  const handleTest = async () => {
    if (!formData.model_name.trim()) {
      setError('Please select a model');
      return;
    }

    try {
      setTesting(true);
      setError(null);
      setSuccess(null);
      
      let result;
      
      // If API key is provided, test with that key
      // Otherwise, test with saved configuration
      if (formData.api_key.trim()) {
        // Test with new API key
        result = await validateApiKey(
          formData.provider,
          formData.model_name,
          formData.api_key
        );
        
        if (result.valid) {
          setSuccess(`Model test successful! ${formData.provider}/${formData.model_name} is ready to use.`);
        } else {
          setError(`Model test failed: ${result.message}`);
        }
      } else {
        // Test with saved configuration
        result = await testSavedConfiguration();
        
        if (result.valid) {
          setSuccess(result.message || 'Saved configuration test successful!');
        } else {
          setError(result.message || 'Failed to test saved configuration. Please enter and validate a new API key.');
        }
      }
    } catch (err) {
      setError(err.message || 'Failed to test model');
    } finally {
      setTesting(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!formData.model_name.trim()) {
      setError('Model name is required');
      return;
    }

    if (!formData.api_key.trim()) {
      setError('API key is required');
      return;
    }

    try {
      setSaving(true);
      setError(null);
      setSuccess(null);

      // Validate API key first
      const validation = await validateApiKey(
        formData.provider,
        formData.model_name,
        formData.api_key
      );

      if (!validation.valid) {
        setError(`API key validation failed: ${validation.message}`);
        setValidationResult(validation);
        return;
      }

      // Update settings
      const settings = {
        provider: formData.provider,
        model_name: formData.model_name,
        api_key: formData.api_key,
        max_tokens: formData.max_tokens ? parseInt(formData.max_tokens) : null,
        temperature: formData.temperature ? parseFloat(formData.temperature) : null,
      };

      await updateModelSettings(settings);
      setSuccess('Settings saved successfully!');

      // Reload agent with new settings
      try {
        await reloadAgent();
        setSuccess('Settings saved and agent reloaded successfully!');
      } catch (reloadErr) {
        setSuccess('Settings saved, but agent reload failed. Please reload manually.');
        console.error('Agent reload error:', reloadErr);
      }

      // Clear API key from form after successful save
      setFormData(prev => ({ ...prev, api_key: '' }));
      setValidationResult(null);
    } catch (err) {
      setError(err.message || 'Failed to save settings');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="settings-page">
      <div className="settings-container">
        <div className="settings-tabs">
          <button
            className={`tab ${activeTab === 'model' ? 'active' : ''}`}
            onClick={() => setActiveTab('model')}
          >
            Model Configuration
          </button>
          <button
            className={`tab ${activeTab === 'tokens' ? 'active' : ''}`}
            onClick={() => setActiveTab('tokens')}
          >
            Token Management
          </button>
          {isAdmin && (
            <button
              className={`tab ${activeTab === 'users' ? 'active' : ''}`}
              onClick={() => setActiveTab('users')}
            >
              User Management
            </button>
          )}
        </div>

        <div className="settings-content">
          {activeTab === 'model' && (
            <>
              <h1>Model Configuration</h1>
              <p className="settings-description">
                Configure the LLM model and API key for the SRE Agent. Changes will be applied immediately.
              </p>

              {error && (
                <div className="alert alert-error">
                  {error}
                </div>
              )}

              {success && (
                <div className="alert alert-success">
                  {success}
                </div>
              )}

              {validationResult && (
                <div className={`alert ${validationResult.valid ? 'alert-success' : 'alert-error'}`}>
                  {validationResult.message}
                </div>
              )}

              {loading ? (
                <p>Loading settings...</p>
              ) : (
                <form onSubmit={handleSubmit} className="settings-form">
                  <div className="form-group">
                    <label htmlFor="provider">Model Provider *</label>
                    <select
                      id="provider"
                      name="provider"
                      value={formData.provider}
                      onChange={handleChange}
                      required
                      disabled={saving}
                    >
                      {PROVIDERS.map(provider => (
                        <option key={provider.value} value={provider.value}>
                          {provider.label}
                        </option>
                      ))}
                    </select>
                  </div>

                  <div className="form-group">
                    <label htmlFor="api_key">API Key *</label>
                    <div className="api-key-group">
                      <input
                        type="password"
                        id="api_key"
                        name="api_key"
                        value={formData.api_key}
                        onChange={handleChange}
                        placeholder="Enter API key"
                        required
                        disabled={saving || validating}
                      />
                      <button
                        type="button"
                        onClick={handleValidate}
                        disabled={validating || fetchingModels || !formData.api_key.trim() || saving}
                        className="btn-validate"
                      >
                        {validating ? 'Validating...' : 'Validate'}
                      </button>
                    </div>
                    <small className="form-hint">
                      API key will be encrypted before storage. Leave empty to test with saved configuration.
                    </small>
                  </div>

                  <div className="form-group">
                    <label htmlFor="model_name">Model Name *</label>
                    {apiKeyValidated && fetchingModels ? (
                      <div className="loading-models">Fetching available models...</div>
                    ) : apiKeyValidated && availableModels.length > 0 ? (
                      <>
                        <select
                          id="model_name"
                          name="model_name"
                          value={formData.model_name}
                          onChange={handleChange}
                          required
                          disabled={saving}
                        >
                          <option value="">-- Select a model --</option>
                          {availableModels.map(model => (
                            <option key={model} value={model}>
                              {model}
                            </option>
                          ))}
                        </select>
                        <small className="form-hint">
                          {availableModels.length} model(s) available. Select a model from the list.
                        </small>
                      </>
                    ) : (
                      <>
                        <input
                          type="text"
                          id="model_name"
                          name="model_name"
                          value={formData.model_name}
                          onChange={handleChange}
                          placeholder={getDefaultModel(formData.provider) || 'e.g., gpt-4'}
                          required
                          disabled={saving || validating}
                        />
                        <small className="form-hint">
                          Default model: {getDefaultModel(formData.provider) || 'N/A'}. Validate API key to see all available models.
                        </small>
                      </>
                    )}
                  </div>

                  <div className="form-group">
                    <label htmlFor="max_tokens">Max Tokens (Optional)</label>
                    <input
                      type="number"
                      id="max_tokens"
                      name="max_tokens"
                      value={formData.max_tokens}
                      onChange={handleChange}
                      placeholder="e.g., 2000"
                      min="1"
                    />
                    <small className="form-hint">
                      Limit the maximum number of tokens in the response
                    </small>
                  </div>

                  <div className="form-group">
                    <label htmlFor="temperature">Temperature (Optional)</label>
                    <input
                      type="number"
                      id="temperature"
                      name="temperature"
                      value={formData.temperature}
                      onChange={handleChange}
                      placeholder="e.g., 0.7"
                      min="0"
                      max="2"
                      step="0.1"
                    />
                    <small className="form-hint">
                      Control randomness (0.0 = focused, 2.0 = creative). Range: 0.0-2.0
                    </small>
                  </div>

                  <div className="form-actions">
                    <button
                      type="submit"
                      disabled={saving || !apiKeyValidated || !formData.model_name.trim()}
                      className="btn-primary"
                    >
                      {saving ? 'Saving...' : 'Save Settings'}
                    </button>
                    <button
                      type="button"
                      onClick={handleTest}
                      disabled={testing || !formData.model_name.trim() || saving}
                      className="btn-secondary"
                      title={formData.api_key.trim() ? "Test with entered API key" : "Test with saved configuration"}
                    >
                      {testing ? 'Testing...' : formData.api_key.trim() ? 'Test Model (New Key)' : 'Test Model (Saved Config)'}
                    </button>
                    <button
                      type="button"
                      onClick={loadSettings}
                      disabled={loading || saving}
                      className="btn-secondary"
                    >
                      Reset
                    </button>
                  </div>
                </form>
              )}
            </>
          )}

          {activeTab === 'tokens' && <TokenManagementPage />}

          {activeTab === 'users' && isAdmin && <UserManagementPage />}
        </div>
      </div>
    </div>
  );
}

export default SettingsPage;
