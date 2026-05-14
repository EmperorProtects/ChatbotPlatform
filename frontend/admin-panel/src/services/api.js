import axios from 'axios'
import { useAuthStore } from '../stores/authStore'

// const API_URL = import.meta.env.VITE_API_URL || '/api' 
const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Request interceptor - add token
api.interceptors.request.use(
  (config) => {
    // Check if Authorization header is already set (e.g., from direct token parameter)
    if (!config.headers.Authorization) {
      const token = useAuthStore.getState().token
      if (token) {
        config.headers.Authorization = `Bearer ${token}`
      }
    }
    return config
  },
  (error) => Promise.reject(error)
)

// Response interceptor - handle errors
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      useAuthStore.getState().logout()
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

// Auth API
export const authApi = {
  login: (username, password) =>
    api.post('/auth/token', new URLSearchParams({ username, password }), {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    }),
  
  getMe: (token = null) => {
    const headers = { 'Content-Type': 'application/json' }
    if (token) {
      headers.Authorization = `Bearer ${token}`
    }
    return api.get('/auth/users/me', { headers })
  },
}

// Admin API (from admin_service)
export const adminApi = {
  getStats: () => api.get('/admin/stats'),
  getServicesStatus: () => api.get('/admin/services/status'),
  addKnowledge: (data) => api.post('/admin/knowledge', data),
  listKnowledge: (params) => api.get('/admin/knowledge', { params }),
}

// Analytics API (from analytics_service)
export const analyticsApi = {
  trackEvent: (event) => api.post('/analytics/events', event),
  getOverview: (days = 7) => api.get(`/analytics/metrics/overview?days=${days}`),
  getChannelMetrics: () => api.get('/analytics/metrics/channels'),
}

// Knowledge API (from knowledge_service)
export const knowledgeApi = {
  search: (query, params) => api.post('/knowledge/search', { query, ...params }),
  addBusiness: (data) => api.post('/knowledge/add/business', data),
  addUser: (data) => api.post('/knowledge/add/user', data),
  bulkAddBusiness: (items) => {
    console.log('Adding bulk business items:', items)
    api.post('/knowledge/add/business/bulk',  items ) },
  getBusinessStats: () =>{
    console.log(API_URL)
    return api.get('/knowledge/stats/business')
  }, 
  getUserStats: () => api.get('/knowledge/stats/user'),
  listItems: (params) => api.get('/knowledge/list', { params }),

  addExcelProducts: (formData) =>api.post('/knowledge/add/excel/business/products', formData, {headers: { 'Content-Type': 'multipart/form-data' }}),
  updateItem: (id, data, collection = 'business') => 
    api.put(`/knowledge/update/${id}?which=${collection}`, data),
  deleteItem: (id, collection = 'business') => 
    api.delete(`/knowledge/delete/${id}?which=${collection}`),
  getItem: (id, collection = 'business') => 
    api.get(`/knowledge/get/${id}?which=${collection}`),
  getCategories: (collection = 'business') => 
    api.get(`/knowledge/categories?which=${collection}`),
  getBriefs: (collection = 'business') => 
    api.get(`/knowledge/briefs?which=${collection}`),
  adminSeed: (force = false) => 
    api.post('/knowledge/admin/seed', null, { params: { force } }),
  adminReset: (confirm = false) => 
    api.post('/knowledge/admin/reset', null, { params: { confirm } }),
  deleteBrief: (id) =>
    api.delete(`/knowledge/briefs/${id}`),
  
}

// Bot API (from bot_service)
export const botApi = {
  sendMessage: (message) => api.post('/bot/incoming', message),
  getConversationHistory: (userId, limit = 50) => 
    api.get(`/bot/conversation/${userId}`, { params: { limit } }),
  getAllConversations: (limit = 100) => api.get('/bot/conversation'),
  disableDialog: (userId) => api.post(`/bot/conversation/disable/${userId}`),
  enableDialog: (userId) => api.post(`/bot/conversation/enable/${userId}`),
}

// AI API (from ai_service)
export const aiApi = {
  generate: (request) => api.post('/ai/generate', request),
  getModels: () => api.get('/ai/models'),
  generateEmbeddings: (text, model = 'nomic-embed-text') => 
    api.post('/ai/embeddings', null, { params: { text, model } }),
}

// Legacy APIs for backward compatibility
export const briefsApi = {
  getAll: () => knowledgeApi.getBriefs(),
  getById: (id) => knowledgeApi.getItem(id),
  create: (data) => knowledgeApi.addBusiness(data),
  update: (id, data) => knowledgeApi.updateItem(id, data),
  delete: (id) => knowledgeApi.deleteItem(id),
}

export const dialogsApi = {
  getAll: (params) => botApi.getConversationHistory(params?.user_id, params?.limit),
  getById: (id) => api.get(`/bot/conversation/${id}`),
}

export default api
