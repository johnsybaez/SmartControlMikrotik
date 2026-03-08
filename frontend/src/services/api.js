import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || '';

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000,
  withCredentials: true,
});

// Add auth and CSRF headers to every request.
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('authToken');
    const csrfToken = localStorage.getItem('csrfToken');

    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }

    if (csrfToken && ['post', 'put', 'patch', 'delete'].includes((config.method || '').toLowerCase())) {
      config.headers['X-CSRF-Token'] = csrfToken;
    }

    return config;
  },
  (error) => Promise.reject(error)
);

// Handle auth errors.
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('authToken');
      localStorage.removeItem('csrfToken');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

export default api;
