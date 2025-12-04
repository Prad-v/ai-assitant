import React from 'react';
import { BrowserRouter as Router, Routes, Route, Link, useLocation, useNavigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import ProtectedRoute from './components/ProtectedRoute';
import Chat from './components/Chat';
import InventoryPage from './pages/InventoryPage';
import SettingsPage from './pages/SettingsPage';
import LoginPage from './pages/LoginPage';
import './styles/App.css';

function Navigation() {
  const location = useLocation();
  const { user, logout, isAuthenticated } = useAuth();
  const navigate = useNavigate();
  
  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };
  
  // Only show navigation links when authenticated
  if (!isAuthenticated) {
    return null;
  }
  
  return (
    <nav className="app-nav">
      <Link 
        to="/" 
        className={location.pathname === '/' ? 'nav-link active' : 'nav-link'}
      >
        Chat
      </Link>
      <Link 
        to="/inventory" 
        className={location.pathname === '/inventory' ? 'nav-link active' : 'nav-link'}
      >
        Cluster Inventory
      </Link>
      <Link 
        to="/settings" 
        className={location.pathname === '/settings' ? 'nav-link active' : 'nav-link'}
        title="Settings"
      >
        <svg 
          width="16" 
          height="16" 
          viewBox="0 0 24 24" 
          fill="none" 
          stroke="currentColor" 
          strokeWidth="2" 
          strokeLinecap="round" 
          strokeLinejoin="round"
          style={{ display: 'inline-block', verticalAlign: 'middle', marginRight: '0.5rem' }}
        >
          <circle cx="12" cy="12" r="3"></circle>
          <path d="M12 1v6m0 6v6M5.64 5.64l4.24 4.24m4.24 4.24l4.24 4.24M1 12h6m6 0h6M5.64 18.36l4.24-4.24m4.24-4.24l4.24-4.24"></path>
        </svg>
        Settings
      </Link>
      {user && (
        <div className="user-menu">
          <span className="username">{user.username}</span>
          <button className="btn-logout" onClick={handleLogout}>
            Logout
          </button>
        </div>
      )}
    </nav>
  );
}

function AppContent() {
  const location = useLocation();
  const { isAuthenticated } = useAuth();
  const isLoginPage = location.pathname === '/login';
  
  return (
    <div className="app">
      {/* Only show header when not on login page */}
      {!isLoginPage && (
        <header className="app-header">
          <div>
            <h1>SRE Agent</h1>
            <span className="subtitle">Kubernetes Troubleshooting & Security Assistant</span>
          </div>
          <div className="header-right">
            <Navigation />
            {isAuthenticated && (
              <div className="status-indicator">
                <div className="status-dot"></div>
                <span>Connected</span>
              </div>
            )}
          </div>
        </header>
      )}
      <main className={isLoginPage ? "app-main login-main" : "app-main"}>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route 
            path="/" 
            element={
              <ProtectedRoute>
                <Chat />
              </ProtectedRoute>
            } 
          />
          <Route 
            path="/inventory" 
            element={
              <ProtectedRoute>
                <InventoryPage />
              </ProtectedRoute>
            } 
          />
          <Route 
            path="/settings" 
            element={
              <ProtectedRoute>
                <SettingsPage />
              </ProtectedRoute>
            } 
          />
        </Routes>
      </main>
    </div>
  );
}

function App() {
  return (
    <AuthProvider>
      <Router>
        <AppContent />
      </Router>
    </AuthProvider>
  );
}

export default App;

