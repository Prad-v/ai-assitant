import React, { useState, useRef } from 'react';
import '../../styles/Modal.css';

const UploadClusterModal = ({ isOpen, onClose, onSubmit, isSubmitting }) => {
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [tags, setTags] = useState('');
  const [kubeconfig, setKubeconfig] = useState('');
  const [kubeconfigFile, setKubeconfigFile] = useState(null);
  const [errors, setErrors] = useState({});
  const fileInputRef = useRef(null);

  const handleFileSelect = (event) => {
    const file = event.target.files[0];
    if (file) {
      setKubeconfigFile(file);
      const reader = new FileReader();
      reader.onload = (e) => {
        setKubeconfig(e.target.result);
      };
      reader.onerror = () => {
        setErrors({ ...errors, kubeconfig: 'Failed to read file' });
      };
      reader.readAsText(file);
    }
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    
    // Validation
    const newErrors = {};
    if (!name.trim()) {
      newErrors.name = 'Cluster name is required';
    }
    if (!kubeconfig.trim()) {
      newErrors.kubeconfig = 'Kubeconfig is required';
    }
    
    if (Object.keys(newErrors).length > 0) {
      setErrors(newErrors);
      return;
    }
    
    // Parse tags
    const tagsArray = tags.split(',').map(t => t.trim()).filter(t => t.length > 0);
    
    onSubmit({
      name: name.trim(),
      description: description.trim(),
      tags: tagsArray,
      kubeconfig: kubeconfig.trim(),
    });
  };

  const handleClose = () => {
    if (!isSubmitting) {
      setName('');
      setDescription('');
      setTags('');
      setKubeconfig('');
      setKubeconfigFile(null);
      setErrors({});
      onClose();
    }
  };

  if (!isOpen) return null;

  return (
    <div className="modal-overlay" onClick={handleClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>Add Kubernetes Cluster</h2>
          <button className="modal-close" onClick={handleClose} disabled={isSubmitting}>
            ×
          </button>
        </div>
        
        <form onSubmit={handleSubmit} className="modal-body">
          <div className="form-group">
            <label htmlFor="cluster-name">
              Cluster Name <span className="required">*</span>
            </label>
            <input
              id="cluster-name"
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g., Production Cluster"
              disabled={isSubmitting}
              className={errors.name ? 'error' : ''}
            />
            {errors.name && <span className="error-message">{errors.name}</span>}
          </div>
          
          <div className="form-group">
            <label htmlFor="cluster-description">Description</label>
            <textarea
              id="cluster-description"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Optional description of the cluster"
              rows={3}
              disabled={isSubmitting}
            />
          </div>
          
          <div className="form-group">
            <label htmlFor="cluster-tags">Tags (comma-separated)</label>
            <input
              id="cluster-tags"
              type="text"
              value={tags}
              onChange={(e) => setTags(e.target.value)}
              placeholder="e.g., production, us-east, critical"
              disabled={isSubmitting}
            />
          </div>
          
          <div className="form-group">
            <label htmlFor="kubeconfig">
              Kubeconfig <span className="required">*</span>
            </label>
            <div className="file-upload-section">
              <input
                ref={fileInputRef}
                type="file"
                accept=".yaml,.yml,.config"
                onChange={handleFileSelect}
                disabled={isSubmitting}
                style={{ display: 'none' }}
              />
              <button
                type="button"
                onClick={() => fileInputRef.current?.click()}
                disabled={isSubmitting}
                className="file-upload-button"
              >
                {kubeconfigFile ? kubeconfigFile.name : 'Choose File'}
              </button>
              {kubeconfigFile && (
                <button
                  type="button"
                  onClick={() => {
                    setKubeconfigFile(null);
                    setKubeconfig('');
                    if (fileInputRef.current) {
                      fileInputRef.current.value = '';
                    }
                  }}
                  disabled={isSubmitting}
                  className="file-remove-button"
                >
                  Remove
                </button>
              )}
            </div>
            <textarea
              id="kubeconfig"
              value={kubeconfig}
              onChange={(e) => setKubeconfig(e.target.value)}
              placeholder="Paste kubeconfig content here, or upload a file"
              rows={8}
              disabled={isSubmitting}
              className={errors.kubeconfig ? 'error' : ''}
            />
            {errors.kubeconfig && <span className="error-message">{errors.kubeconfig}</span>}
          </div>
          
          <div className="modal-footer">
            <button
              type="button"
              onClick={handleClose}
              disabled={isSubmitting}
              className="button-secondary"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="button-primary"
            >
              {isSubmitting ? 'Adding...' : 'Add Cluster'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default UploadClusterModal;

