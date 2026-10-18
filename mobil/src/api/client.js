import axios from 'axios';

// Expo SDK 49+ natively supports EXPO_PUBLIC_* environment variables from .env
// Fallback to http://localhost:8000 if not specified
const BASE_URL = process.env.EXPO_PUBLIC_API_URL || 'http://localhost:8000';

const client = axios.create({
  baseURL: BASE_URL,
  timeout: 60000,
  headers: {
    'Content-Type': 'application/json',
    'Accept': 'application/json',
  },
});

// Response interceptor for clear error handling
client.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error('[API Error]:', error.message || error);
    return Promise.reject(error);
  }
);

export default client;
