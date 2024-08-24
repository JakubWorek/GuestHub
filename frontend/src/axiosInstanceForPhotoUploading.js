import axios from 'axios';

const axiosInstanceForPhotoUploading = axios.create({
  baseURL: "http://localhost:4000/api",
});

export default axiosInstanceForPhotoUploading;