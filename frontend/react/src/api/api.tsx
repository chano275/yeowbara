import axios from 'axios';
import type { InternalAxiosRequestConfig } from 'axios';

// const baseURL = process.env.REACT_APP_API_URL || 'http://localhost:8080';
// const baseURL = import.meta.env.VITE_API_BASE || "https://k12b107.p.ssafy.io";
const baseURL = import.meta.env.VITE_API_BASE || "https://k12b107.p.ssafy.io/api";
console.log('API Base URL:', baseURL);
const api = axios.create({
  baseURL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor
api.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const token = localStorage.getItem('access_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor
api.interceptors.response.use(
  (response) => {
    console.log('API 응답 성공:', response.config.url, response.status);
    return response;
  },
  async (error) => {
    console.error('API 응답 오류:', 
      error.config?.url, 
      error.response?.status, 
      error.response?.data || error.message
    );
    
    if (error.response?.status === 401) {
      // Handle token expiration or unauthorized access
      localStorage.removeItem('access_token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

export default api; 