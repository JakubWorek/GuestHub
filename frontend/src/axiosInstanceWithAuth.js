import axios from 'axios';

const axiosInstanceWithAuth = axios.create({
  baseURL: "http://127.0.0.1:5000/api",
});

axiosInstanceWithAuth.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

export default axiosInstanceWithAuth;