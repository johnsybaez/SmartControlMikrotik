import { create } from 'zustand';
import api from '../services/api';

const useAuthStore = create((set) => ({
  user: null,
  token: localStorage.getItem('authToken'),
  isAuthenticated: false,
  isLoading: false,
  error: null,

  // Initialize auth state.
  init: async () => {
    const token = localStorage.getItem('authToken');
    if (token) {
      try {
        set({ isLoading: true, error: null });
        const response = await api.get('/api/auth/me');
        set({
          user: response.data,
          token,
          isAuthenticated: true,
          isLoading: false,
        });
      } catch (error) {
        localStorage.removeItem('authToken');
        localStorage.removeItem('csrfToken');
        set({
          user: null,
          token: null,
          isAuthenticated: false,
          isLoading: false,
          error: 'Sesion expirada',
        });
      }
    } else {
      set({ isLoading: false, isAuthenticated: false });
    }
  },

  // Login.
  login: async (username, password, otpCode = null) => {
    try {
      set({ isLoading: true, error: null });

      const response = await api.post('/api/auth/login', {
        username,
        password,
        otp_code: otpCode || undefined,
      });

      const { access_token, csrf_token } = response.data;
      localStorage.setItem('authToken', access_token);
      localStorage.setItem('csrfToken', csrf_token);

      const userResponse = await api.get('/api/auth/me');

      set({
        user: userResponse.data,
        token: access_token,
        isAuthenticated: true,
        isLoading: false,
        error: null,
      });

      return true;
    } catch (error) {
      const errorMessage = error.response?.data?.detail || 'Error de autenticacion';
      localStorage.removeItem('authToken');
      localStorage.removeItem('csrfToken');
      set({
        user: null,
        token: null,
        isAuthenticated: false,
        isLoading: false,
        error: errorMessage,
      });
      return false;
    }
  },

  // Logout.
  logout: () => {
    localStorage.removeItem('authToken');
    localStorage.removeItem('csrfToken');
    set({
      user: null,
      token: null,
      isAuthenticated: false,
      error: null,
    });
  },

  // Clear error.
  clearError: () => set({ error: null }),
}));

export default useAuthStore;

