import axios from 'axios'

const API_BASE_URL = 'http://localhost:8000'

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json'
  }
})

api.interceptors.request.use((config) => {
  if (typeof window !== 'undefined') {
    const token = localStorage.getItem('token')
    if (token) {
      config.headers['Authorization'] = `Bearer ${token}`
    }
  }
  return config
})

export const login = async (username, password) => {
  const res = await api.post('/auth/login', { username, password })
  return res.data
}

export const getMe = async () => {
  const res = await api.get('/auth/me')
  return res.data
}

// Upload document
export const uploadDocument = async (file, useCloudOCR = true, classification='PUBLIC') => {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('use_cloud_ocr', useCloudOCR.toString())
  formData.append('classification', classification)

  const response = await api.post('/upload', formData, {
    headers: {
      'Content-Type': 'multipart/form-data'
    }
  })
  return response.data
}

// Get all documents
export const getDocuments = async () => {
  const response = await api.get('/documents')
  return response.data
}

// Ask question
export const askQuestion = async (question, documentFilename = null, topK = 15) => {
  const response = await api.post('/ask', {
    question,
    document_filename: documentFilename,
    top_k: topK
  })
  return response.data
}

// Get specific page content
export const getPageContent = async (filename, pageNumber) => {
  const response = await api.post('/page', {
    filename,
    page_number: pageNumber
  })
  return response.data
}

// Check if PDF exists
export const checkPDFExists = async (docId) => {
  const response = await api.get(`/document/${docId}/check-pdf`)
  return response.data
}

// Health check
export const healthCheck = async () => {
  const response = await api.get('/health')
  return response.data
}

export default api