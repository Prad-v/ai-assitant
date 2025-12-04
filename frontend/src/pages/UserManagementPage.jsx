import React, { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { listUsers, createUser, updateUser, deleteUser, resetPassword } from '../services/userApi';
import { changePassword } from '../services/authApi';
import '../styles/UserManagementPage.css';

const UserManagementPage = () => {
  const { user: currentUser, isAdmin } = useAuth();
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [showAddModal, setShowAddModal] = useState(false);
  const [showEditModal, setShowEditModal] = useState(null);
  const [showResetPasswordModal, setShowResetPasswordModal] = useState(null);
  const [showChangePasswordModal, setShowChangePasswordModal] = useState(false);
  
  // Form states
  const [newUser, setNewUser] = useState({ username: '', password: '', role: 'user' });
  const [editUser, setEditUser] = useState({});
  const [resetPasswordData, setResetPasswordData] = useState({ newPassword: '' });
  const [changePasswordData, setChangePasswordData] = useState({ oldPassword: '', newPassword: '' });

  useEffect(() => {
    if (isAdmin) {
      loadUsers();
    }
  }, [isAdmin]);

  const loadUsers = async () => {
    try {
      setLoading(true);
      const data = await listUsers();
      setUsers(data);
    } catch (err) {
      setError(err.detail || 'Failed to load users');
    } finally {
      setLoading(false);
    }
  };

  const handleCreateUser = async (e) => {
    e.preventDefault();
    try {
      setError('');
      await createUser(newUser);
      setSuccess('User created successfully');
      setShowAddModal(false);
      setNewUser({ username: '', password: '', role: 'user' });
      loadUsers();
    } catch (err) {
      setError(err.detail || 'Failed to create user');
    }
  };

  const handleUpdateUser = async (e) => {
    e.preventDefault();
    try {
      setError('');
      await updateUser(showEditModal, editUser);
      setSuccess('User updated successfully');
      setShowEditModal(null);
      setEditUser({});
      loadUsers();
    } catch (err) {
      setError(err.detail || 'Failed to update user');
    }
  };

  const handleDeleteUser = async (userId) => {
    if (!window.confirm('Are you sure you want to delete this user?')) {
      return;
    }
    try {
      setError('');
      await deleteUser(userId);
      setSuccess('User deleted successfully');
      loadUsers();
    } catch (err) {
      setError(err.detail || 'Failed to delete user');
    }
  };

  const handleResetPassword = async (e) => {
    e.preventDefault();
    try {
      setError('');
      await resetPassword(showResetPasswordModal, resetPasswordData.newPassword);
      setSuccess('Password reset successfully');
      setShowResetPasswordModal(null);
      setResetPasswordData({ newPassword: '' });
    } catch (err) {
      setError(err.detail || 'Failed to reset password');
    }
  };

  const handleChangePassword = async (e) => {
    e.preventDefault();
    try {
      setError('');
      await changePassword(changePasswordData.oldPassword, changePasswordData.newPassword);
      setSuccess('Password changed successfully');
      setShowChangePasswordModal(false);
      setChangePasswordData({ oldPassword: '', newPassword: '' });
    } catch (err) {
      setError(err.detail || 'Failed to change password');
    }
  };

  if (!isAdmin) {
    return (
      <div className="user-management-page">
        <div className="alert alert-error">
          Access denied. Admin privileges required.
        </div>
      </div>
    );
  }

  return (
    <div className="user-management-page">
      <div className="page-header">
        <h1>User Management</h1>
        <button className="btn-primary" onClick={() => setShowAddModal(true)}>
          Add User
        </button>
      </div>

      {error && <div className="alert alert-error">{error}</div>}
      {success && <div className="alert alert-success">{success}</div>}

      {/* Change Own Password Section */}
      <div className="section">
        <h2>Change My Password</h2>
        <button className="btn-secondary" onClick={() => setShowChangePasswordModal(true)}>
          Change Password
        </button>
      </div>

      {/* Users Table */}
      <div className="section">
        <h2>All Users</h2>
        {loading ? (
          <div>Loading...</div>
        ) : (
          <table className="users-table">
            <thead>
              <tr>
                <th>ID</th>
                <th>Username</th>
                <th>Role</th>
                <th>Status</th>
                <th>Created</th>
                <th>Last Login</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {users.map((u) => (
                <tr key={u.id}>
                  <td>{u.id}</td>
                  <td>{u.username}</td>
                  <td>{u.role}</td>
                  <td>{u.is_active ? 'Active' : 'Inactive'}</td>
                  <td>{u.created_at ? new Date(u.created_at).toLocaleDateString() : '-'}</td>
                  <td>{u.last_login ? new Date(u.last_login).toLocaleDateString() : '-'}</td>
                  <td>
                    <button className="btn-small" onClick={() => {
                      setEditUser(u);
                      setShowEditModal(u.id);
                    }}>
                      Edit
                    </button>
                    <button className="btn-small" onClick={() => setShowResetPasswordModal(u.id)}>
                      Reset Password
                    </button>
                    {u.id !== currentUser?.id && (
                      <button className="btn-small btn-danger" onClick={() => handleDeleteUser(u.id)}>
                        Delete
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Add User Modal */}
      {showAddModal && (
        <div className="modal-overlay" onClick={() => setShowAddModal(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h2>Add User</h2>
            <form onSubmit={handleCreateUser}>
              <div className="form-group">
                <label>Username</label>
                <input
                  type="text"
                  value={newUser.username}
                  onChange={(e) => setNewUser({ ...newUser, username: e.target.value })}
                  required
                />
              </div>
              <div className="form-group">
                <label>Password</label>
                <input
                  type="password"
                  value={newUser.password}
                  onChange={(e) => setNewUser({ ...newUser, password: e.target.value })}
                  required
                />
              </div>
              <div className="form-group">
                <label>Role</label>
                <select
                  value={newUser.role}
                  onChange={(e) => setNewUser({ ...newUser, role: e.target.value })}
                >
                  <option value="user">User</option>
                  <option value="admin">Admin</option>
                </select>
              </div>
              <div className="modal-actions">
                <button type="submit" className="btn-primary">Create</button>
                <button type="button" className="btn-secondary" onClick={() => setShowAddModal(false)}>
                  Cancel
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Edit User Modal */}
      {showEditModal && (
        <div className="modal-overlay" onClick={() => {
          setShowEditModal(null);
          setEditUser({});
        }}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h2>Edit User</h2>
            <form onSubmit={handleUpdateUser}>
              <div className="form-group">
                <label>Username</label>
                <input
                  type="text"
                  value={editUser.username || ''}
                  onChange={(e) => setEditUser({ ...editUser, username: e.target.value })}
                  required
                />
              </div>
              <div className="form-group">
                <label>Role</label>
                <select
                  value={editUser.role || 'user'}
                  onChange={(e) => setEditUser({ ...editUser, role: e.target.value })}
                >
                  <option value="user">User</option>
                  <option value="admin">Admin</option>
                </select>
              </div>
              <div className="form-group">
                <label>
                  <input
                    type="checkbox"
                    checked={editUser.is_active !== false}
                    onChange={(e) => setEditUser({ ...editUser, is_active: e.target.checked })}
                  />
                  Active
                </label>
              </div>
              <div className="modal-actions">
                <button type="submit" className="btn-primary">Update</button>
                <button type="button" className="btn-secondary" onClick={() => {
                  setShowEditModal(null);
                  setEditUser({});
                }}>
                  Cancel
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Reset Password Modal */}
      {showResetPasswordModal && (
        <div className="modal-overlay" onClick={() => {
          setShowResetPasswordModal(null);
          setResetPasswordData({ newPassword: '' });
        }}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h2>Reset Password</h2>
            <form onSubmit={handleResetPassword}>
              <div className="form-group">
                <label>New Password</label>
                <input
                  type="password"
                  value={resetPasswordData.newPassword}
                  onChange={(e) => setResetPasswordData({ newPassword: e.target.value })}
                  required
                />
              </div>
              <div className="modal-actions">
                <button type="submit" className="btn-primary">Reset</button>
                <button type="button" className="btn-secondary" onClick={() => {
                  setShowResetPasswordModal(null);
                  setResetPasswordData({ newPassword: '' });
                }}>
                  Cancel
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Change Password Modal */}
      {showChangePasswordModal && (
        <div className="modal-overlay" onClick={() => {
          setShowChangePasswordModal(false);
          setChangePasswordData({ oldPassword: '', newPassword: '' });
        }}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h2>Change My Password</h2>
            <form onSubmit={handleChangePassword}>
              <div className="form-group">
                <label>Old Password</label>
                <input
                  type="password"
                  value={changePasswordData.oldPassword}
                  onChange={(e) => setChangePasswordData({ ...changePasswordData, oldPassword: e.target.value })}
                  required
                />
              </div>
              <div className="form-group">
                <label>New Password</label>
                <input
                  type="password"
                  value={changePasswordData.newPassword}
                  onChange={(e) => setChangePasswordData({ ...changePasswordData, newPassword: e.target.value })}
                  required
                />
              </div>
              <div className="modal-actions">
                <button type="submit" className="btn-primary">Change</button>
                <button type="button" className="btn-secondary" onClick={() => {
                  setShowChangePasswordModal(false);
                  setChangePasswordData({ oldPassword: '', newPassword: '' });
                }}>
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

export default UserManagementPage;

