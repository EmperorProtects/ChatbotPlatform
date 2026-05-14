import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Container,
  Box,
  Paper,
  TextField,
  Button,
  Typography,
  Alert,
} from '@mui/material'
import { authApi } from '../../services/api'
import { useAuthStore } from '../../stores/authStore'

export default function LoginPage() {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  
  const navigate = useNavigate()
  const login = useAuthStore((state) => state.login)

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)

    try {
      // First, authenticate and get the token
      console.log('Attempting login...')
      const { data } = await authApi.login(username, password)
      console.log('Login successful, token received')
      
      // Then get user info using the token directly
      console.log('Fetching user info...')
      const { data: user } = await authApi.getMe(data.access_token)
      console.log('User info received:', user)
      
      // Finally, store both token and user info
      login(user, data.access_token)
      navigate('/dashboard')
    } catch (err) {
      console.error('Login error:', err)
      setError(err.response?.data?.detail || 'Ошибка авторизации')
    } finally {
      setLoading(false)
    }
  }

  return (
    <Container maxWidth="sm">
      <Box
        sx={{
          marginTop: 8,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
        }}
      >
        <Paper elevation={3} sx={{ p: 4, width: '100%' }}>
          <Typography component="h1" variant="h5" align="center" gutterBottom>
            Chatbot Admin Panel
          </Typography>
          
          {error && (
            <Alert severity="error" sx={{ mb: 2 }}>
              {error}
            </Alert>
          )}

          <Box component="form" onSubmit={handleSubmit} sx={{ mt: 1 }}>
            <TextField
              margin="normal"
              required
              fullWidth
              label="Имя пользователя"
              autoFocus
              value={username}
              onChange={(e) => setUsername(e.target.value)}
            />
            <TextField
              margin="normal"
              required
              fullWidth
              label="Пароль"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
            <Button
              type="submit"
              fullWidth
              variant="contained"
              sx={{ mt: 3, mb: 2 }}
              disabled={loading}
            >
              {loading ? 'Вход...' : 'Войти'}
            </Button>
            
            <Typography variant="caption" color="text.secondary" align="center" display="block">
              По умолчанию: admin / admin123
            </Typography>
          </Box>
        </Paper>
      </Box>
    </Container>
  )
}
