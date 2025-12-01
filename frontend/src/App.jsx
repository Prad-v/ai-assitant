import React from 'react';
import Chat from './components/Chat';
import './styles/App.css';

function App() {
  return (
    <div className="app">
      <header className="app-header">
        <div>
          <h1>SRE Agent</h1>
          <span className="subtitle">Kubernetes Troubleshooting & Security Assistant</span>
        </div>
        <div className="status-indicator">
          <div className="status-dot"></div>
          <span>Connected</span>
        </div>
      </header>
      <main className="app-main">
        <Chat />
      </main>
    </div>
  );
}

export default App;

