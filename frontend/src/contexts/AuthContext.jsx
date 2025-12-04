import React, { createContext, useContext, useState, useEffect } from 'react';
import { login as loginApi, logout as logoutApi, refreshToken as refreshTokenApi, getCurrentUser } from '../services/authApi';

const AuthContext = createContext(null);

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return context;
};

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [token, setToken] = useState(null);
  const [sessionToken, setSessionToken] = useState(null);

  // Load user from localStorage on mount
  useEffect(() => {
    let mounted = true;
    
    const initAuth = async () => {
      try {
        const storedUser = localStorage.getItem('user');
        const storedToken = localStorage.getItem('accessToken');
        const storedSessionToken = localStorage.getItem('sessionToken');
        
        if (storedUser && storedToken) {
          setUser(JSON.parse(storedUser));
          setToken(storedToken);
          if (storedSessionToken) {
            setSessionToken(storedSessionToken);
          }
          
          // Verify token is still valid by getting current user
          try {
            const currentUser = await getCurrentUser();
            if (mounted) {
              setUser(currentUser);
              localStorage.setItem('user', JSON.stringify(currentUser));
            }
          } catch (error) {
            // Token invalid, clear auth
            if (mounted) {
              clearAuth();
            }
          }
        }
      } catch (error) {
        console.error('Auth initialization error:', error);
        if (mounted) {
          clearAuth();
        }
      } finally {
        if (mounted) {
          setLoading(false);
        }
      }
    };
    
    initAuth();
    
    return () => {
      mounted = false;
    };
  }, []); // Empty dependency array - only run on mount
  
  // Set up token refresh interval (separate effect, doesn't depend on user)
  useEffect(() => {
    const refreshInterval = setInterval(async () => {
      const refreshTokenValue = localStorage.getItem('refreshToken');
      const currentUser = user; // Get current user value
      if (refreshTokenValue && currentUser) {
        try {
          await refreshTokenApi();
          const newToken = localStorage.getItem('accessToken');
          setToken(newToken);
        } catch (error) {
          console.error('Auto token refresh failed:', error);
          // If refresh fails, user will be logged out on next API call
        }
      }
    }, 14 * 60 * 1000); // Refresh every 14 minutes (access token expires in 15 minutes)
    
    return () => clearInterval(refreshInterval);
  }, [user]); // This can depend on user since it's just for the refresh interval

  const clearAuth = () => {
    setUser(null);
    setToken(null);
    setSessionToken(null);
    localStorage.removeItem('user');
    localStorage.removeItem('accessToken');
    localStorage.removeItem('refreshToken');
    localStorage.removeItem('sessionToken');
  };

  const login = async (username, password) => {
    try {
      const response = await loginApi(username, password);
      
      // Store tokens
      localStorage.setItem('accessToken', response.access_token);
      localStorage.setItem('refreshToken', response.refresh_token);
      localStorage.setItem('sessionToken', response.session_token);
      localStorage.setItem('user', JSON.stringify(response.user));
      
      setUser(response.user);
      setToken(response.access_token);
      setSessionToken(response.session_token);
      
      return response;
    } catch (error) {
      console.error('Login error:', error);
      throw error;
    }
  };

  const logout = async () => {
    try {
      await logoutApi();
    } catch (error) {
      console.error('Logout error:', error);
    } finally {
      clearAuth();
    }
  };

  const refreshToken = async () => {
    try {
      const response = await refreshTokenApi();
      const newToken = localStorage.getItem('accessToken');
      setToken(newToken);
      return response;
    } catch (error) {
      console.error('Token refresh error:', error);
      clearAuth();
      throw error;
    }
  };

  const value = {
    user,
    token,
    sessionToken,
    loading,
    login,
    logout,
    refreshToken,
    isAuthenticated: !!user,
    isAdmin: user?.role === 'admin',
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};

