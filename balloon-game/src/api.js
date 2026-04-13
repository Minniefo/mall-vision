import axios from "axios";

/**
 * Enterprise Base API Configuration for MallVision
 * 
 * We use Vite's `import.meta.env` to inject the correct backend URL depending on whether 
 * we ran `npm run dev` (.env) or `npm run build` (.env.production).
 * Fallback to localhost is included seamlessly just in case the env var isn't loaded.
 */

const API_BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    "Content-Type": "application/json",
  },
  // timeout: 5000, // Optional: timeout for API requests
});

// Example of interceptors for future expansion (e.g. adding auth tokens here)
api.interceptors.request.use(
  (config) => {
    // config.headers.Authorization = `Bearer some_token`;
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

export default api;

/* 
===============================================
HOW TO USE THIS API FILE
===============================================

Instead of hardcoding axios imports like this:
  import axios from 'axios';
  axios.post("http://localhost:8000/start_game")

Update your component to import this api instance:
  import api from '../api';  // path depends on where your component is

And make the call cleanly:
  const res = await api.post("/start_game");
  const res = await api.post("/upload_frame", { image: base64Data });

This guarantees it works on AWS and localhost automatically!
*/
