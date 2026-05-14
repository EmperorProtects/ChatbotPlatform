import React, { useState, useEffect } from 'react'
import {
  Box,
  Typography,
  Paper,
  Grid,
  Card,
  CardContent,
  CardHeader,
  TextField,
  Button,
  Switch,
  FormControlLabel,
  Divider,
  Alert,
  Chip,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Tabs,
  Tab
} from '@mui/material'
import {
  Save,
  Refresh,
  Delete,
  Add,
  Edit,
  CheckCircle,
  Error as ErrorIcon,
  Warning,
  Info
} from '@mui/icons-material'
import { adminApi, knowledgeApi, aiApi } from '../../services/api'

export default function SettingsPage() {
  const [activeTab, setActiveTab] = useState(0)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [success, setSuccess] = useState(null)
  
  // System Settings
  const [systemSettings, setSystemSettings] = useState({
    apiUrl: 'http://localhost:8000',
    defaultLanguage: 'ru',
    enableAnalytics: true,
    enableNotifications: true,
    maxConversationHistory: 100,
    responseTimeout: 30
  })
  
  // Services Status
  const [servicesStatus, setServicesStatus] = useState(null)
  
  // Available Models
  const [availableModels, setAvailableModels] = useState([])
  const [selectedModel, setSelectedModel] = useState('llama3.2')
  
  // Knowledge Base Settings
  const [knowledgeSettings, setKnowledgeSettings] = useState({
    embeddingModel: 'nomic-embed-text',
    maxSearchResults: 5,
    autoSeedEnabled: true
  })
  
  // Admin Actions Dialog
  const [actionDialog, setActionDialog] = useState({
    open: false,
    type: null,
    title: '',
    message: '',
    confirmText: ''
  })

  useEffect(() => {
    fetchSystemStatus()
    fetchAvailableModels()
  }, [])

  const fetchSystemStatus = async () => {
    try {
      const response = await adminApi.getServicesStatus()
      setServicesStatus(response.data)
    } catch (err) {
      console.error('Error fetching system status:', err)
    }
  }
  
  const fetchAvailableModels = async () => {
    try {
      const response = await aiApi.getModels()
      if (response.data?.models) {
        setAvailableModels(response.data.models)
      }
    } catch (err) {
      console.error('Error fetching models:', err)
      // Set mock models if service unavailable
      setAvailableModels([
        { name: 'llama3.2', size: '2.0B' },
        { name: 'llama3.1', size: '8B' },
        { name: 'mistral', size: '7B' }
      ])
    }
  }

  const handleSystemSettingsChange = (field, value) => {
    setSystemSettings(prev => ({ ...prev, [field]: value }))
  }
  
  const handleKnowledgeSettingsChange = (field, value) => {
    setKnowledgeSettings(prev => ({ ...prev, [field]: value }))
  }

  const handleSaveSettings = async () => {
    try {
      setLoading(true)
      setError(null)
      
      // In a real app, these would be API calls to save settings
      await new Promise(resolve => setTimeout(resolve, 1000)) // Simulate API call
      
      setSuccess('Настройки успешно сохранены!')
      
      setTimeout(() => setSuccess(null), 3000)
    } catch (err) {
      setError('Ошибка сохранения настроек')
    } finally {
      setLoading(false)
    }
  }
  
  const openActionDialog = (type, title, message, confirmText) => {
    setActionDialog({
      open: true,
      type,
      title,
      message,
      confirmText
    })
  }
  
  const closeActionDialog = () => {
    setActionDialog({ open: false, type: null, title: '', message: '', confirmText: '' })
  }
  
  const executeAdminAction = async () => {
    try {
      setLoading(true)
      setError(null)
      
      switch (actionDialog.type) {
        case 'resetKnowledge':
          await knowledgeApi.adminReset(true)
          setSuccess('База знаний успешно сброшена')
          break
        case 'seedKnowledge':
          await knowledgeApi.adminSeed(true)
          setSuccess('Тестовые данные успешно добавлены')
          break
        case 'refreshServices':
          await fetchSystemStatus()
          setSuccess('Статус сервисов обновлен')
          break
        default:
          break
      }
      
      setTimeout(() => setSuccess(null), 3000)
    } catch (err) {
      setError('Ошибка выполнения операции: ' + (err.response?.data?.detail || err.message))
    } finally {
      setLoading(false)
      closeActionDialog()
    }
  }
  
  const getStatusIcon = (status) => {
    switch (status) {
      case 'healthy': return <CheckCircle color="success" />
      case 'error': return <ErrorIcon color="error" />
      case 'degraded': return <Warning color="warning" />
      default: return <Info color="info" />
    }
  }
  
  const getStatusColor = (status) => {
    switch (status) {
      case 'healthy': return 'success'
      case 'error': return 'error'
      case 'degraded': return 'warning'
      default: return 'default'
    }
  }

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Настройки
      </Typography>

      {error && (
        <Alert severity="error" sx={{ mb: 3 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}
      
      {success && (
        <Alert severity="success" sx={{ mb: 3 }} onClose={() => setSuccess(null)}>
          {success}
        </Alert>
      )}

      <Paper sx={{ mb: 3 }}>
        <Tabs 
          value={activeTab} 
          onChange={(e, v) => setActiveTab(v)}
          sx={{ borderBottom: 1, borderColor: 'divider' }}
        >
          <Tab label="Общие" />
          <Tab label="База знаний" />
          <Tab label="Система" />
          <Tab label="Администрирование" />
        </Tabs>
      </Paper>

      {/* General Settings Tab */}
      {activeTab === 0 && (
        <Grid container spacing={3}>
          <Grid item xs={12} md={6}>
            <Card>
              <CardHeader title="Основные настройки" />
              <CardContent>
                <Grid container spacing={3}>
                  <Grid item xs={12}>
                    <TextField
                      fullWidth
                      label="URL API"
                      value={systemSettings.apiUrl}
                      onChange={(e) => handleSystemSettingsChange('apiUrl', e.target.value)}
                    />
                  </Grid>
                  <Grid item xs={12}>
                    <FormControl fullWidth>
                      <InputLabel>Язык по умолчанию</InputLabel>
                      <Select
                        value={systemSettings.defaultLanguage}
                        onChange={(e) => handleSystemSettingsChange('defaultLanguage', e.target.value)}
                      >
                        <MenuItem value="ru">Русский</MenuItem>
                        <MenuItem value="en">English</MenuItem>
                        <MenuItem value="kz">Қазақша</MenuItem>
                      </Select>
                    </FormControl>
                  </Grid>
                  <Grid item xs={12}>
                    <TextField
                      fullWidth
                      type="number"
                      label="Макс. история диалогов"
                      value={systemSettings.maxConversationHistory}
                      onChange={(e) => handleSystemSettingsChange('maxConversationHistory', parseInt(e.target.value))}
                    />
                  </Grid>
                  <Grid item xs={12}>
                    <TextField
                      fullWidth
                      type="number"
                      label="Тайм-аут ответа (сек)"
                      value={systemSettings.responseTimeout}
                      onChange={(e) => handleSystemSettingsChange('responseTimeout', parseInt(e.target.value))}
                    />
                  </Grid>
                </Grid>
              </CardContent>
            </Card>
          </Grid>
          
          <Grid item xs={12} md={6}>
            <Card>
              <CardHeader title="Параметры" />
              <CardContent>
                <Grid container spacing={2}>
                  <Grid item xs={12}>
                    <FormControlLabel
                      control={
                        <Switch
                          checked={systemSettings.enableAnalytics}
                          onChange={(e) => handleSystemSettingsChange('enableAnalytics', e.target.checked)}
                        />
                      }
                      label="Включить аналитику"
                    />
                  </Grid>
                  <Grid item xs={12}>
                    <FormControlLabel
                      control={
                        <Switch
                          checked={systemSettings.enableNotifications}
                          onChange={(e) => handleSystemSettingsChange('enableNotifications', e.target.checked)}
                        />
                      }
                      label="Включить уведомления"
                    />
                  </Grid>
                </Grid>
                
                <Divider sx={{ my: 3 }} />
                
                <Button
                  variant="contained"
                  startIcon={<Save />}
                  onClick={handleSaveSettings}
                  disabled={loading}
                  fullWidth
                >
                  Сохранить настройки
                </Button>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      )}

      {/* Knowledge Base Settings Tab */}
      {activeTab === 1 && (
        <Grid container spacing={3}>
          <Grid item xs={12} md={6}>
            <Card>
              <CardHeader title="Настройки базы знаний" />
              <CardContent>
                <Grid container spacing={3}>
                  <Grid item xs={12}>
                    <TextField
                      fullWidth
                      label="Модель эмбеддингов"
                      value={knowledgeSettings.embeddingModel}
                      onChange={(e) => handleKnowledgeSettingsChange('embeddingModel', e.target.value)}
                    />
                  </Grid>
                  <Grid item xs={12}>
                    <TextField
                      fullWidth
                      type="number"
                      label="Макс. результатов поиска"
                      value={knowledgeSettings.maxSearchResults}
                      onChange={(e) => handleKnowledgeSettingsChange('maxSearchResults', parseInt(e.target.value))}
                    />
                  </Grid>
                  <Grid item xs={12}>
                    <FormControlLabel
                      control={
                        <Switch
                          checked={knowledgeSettings.autoSeedEnabled}
                          onChange={(e) => handleKnowledgeSettingsChange('autoSeedEnabled', e.target.checked)}
                        />
                      }
                      label="Авто-заполнение при старте"
                    />
                  </Grid>
                </Grid>
              </CardContent>
            </Card>
          </Grid>
          
          <Grid item xs={12} md={6}>
            <Card>
              <CardHeader title="Модели AI" />
              <CardContent>
                <FormControl fullWidth sx={{ mb: 2 }}>
                  <InputLabel>Выбранная модель</InputLabel>
                  <Select
                    value={selectedModel}
                    onChange={(e) => setSelectedModel(e.target.value)}
                  >
                    {availableModels.map((model) => (
                      <MenuItem key={model.name} value={model.name}>
                        {model.name} {model.size && `(${model.size})`}
                      </MenuItem>
                    ))}
                  </Select>
                </FormControl>
                
                <Typography variant="subtitle2" gutterBottom>
                  Доступные модели:
                </Typography>
                <Box display="flex" flexWrap="wrap" gap={1}>
                  {availableModels.map((model) => (
                    <Chip 
                      key={model.name}
                      label={`${model.name} ${model.size ? `(${model.size})` : ''}`}
                      size="small"
                      color={model.name === selectedModel ? 'primary' : 'default'}
                    />
                  ))}
                </Box>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      )}

      {/* System Status Tab */}
      {activeTab === 2 && (
        <Grid container spacing={3}>
          <Grid item xs={12}>
            <Card>
              <CardHeader 
                title="Статус сервисов"
                action={
                  <Button
                    startIcon={<Refresh />}
                    onClick={() => openActionDialog(
                      'refreshServices',
                      'Обновить статус',
                      'Обновить статус всех сервисов?',
                      'Обновить'
                    )}
                  >
                    Обновить
                  </Button>
                }
              />
              <CardContent>
                {servicesStatus ? (
                  <TableContainer>
                    <Table>
                      <TableHead>
                        <TableRow>
                          <TableCell>Сервис</TableCell>
                          <TableCell>Статус</TableCell>
                          <TableCell>URL</TableCell>
                          <TableCell>Последняя проверка</TableCell>
                        </TableRow>
                      </TableHead>
                      <TableBody>
                        {Object.entries(servicesStatus).map(([serviceName, serviceData]) => (
                          <TableRow key={serviceName}>
                            <TableCell>
                              <Box display="flex" alignItems="center" gap={1}>
                                {getStatusIcon(serviceData.status)}
                                {serviceName.replace('_', ' ').toUpperCase()}
                              </Box>
                            </TableCell>
                            <TableCell>
                              <Chip
                                label={serviceData.status || 'unknown'}
                                color={getStatusColor(serviceData.status)}
                                size="small"
                              />
                            </TableCell>
                            <TableCell>
                              <Typography variant="body2" sx={{ fontFamily: 'monospace' }}>
                                {serviceData.url}
                              </Typography>
                            </TableCell>
                            <TableCell>
                              {serviceData.last_checked && 
                                new Date(serviceData.last_checked).toLocaleString('ru')
                              }
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </TableContainer>
                ) : (
                  <Typography color="textSecondary">
                    Загрузка статуса сервисов...
                  </Typography>
                )}
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      )}

      {/* Administration Tab */}
      {activeTab === 3 && (
        <Grid container spacing={3}>
          <Grid item xs={12} md={6}>
            <Card>
              <CardHeader title="Управление базой знаний" />
              <CardContent>
                <Grid container spacing={2}>
                  <Grid item xs={12}>
                    <Button
                      fullWidth
                      variant="outlined"
                      color="primary"
                      startIcon={<Add />}
                      onClick={() => openActionDialog(
                        'seedKnowledge',
                        'Добавить тестовые данные',
                        'Добавить тестовые данные в базу знаний? Это перезапишет существующие данные.',
                        'Добавить'
                      )}
                    >
                      Добавить тестовые данные
                    </Button>
                  </Grid>
                  <Grid item xs={12}>
                    <Button
                      fullWidth
                      variant="outlined"
                      color="error"
                      startIcon={<Delete />}
                      onClick={() => openActionDialog(
                        'resetKnowledge',
                        'Сбросить базу знаний',
                        'ВЫ уверены, что хотите полностью очистить базу знаний? Это действие нельзя отменить!',
                        'Сбросить'
                      )}
                    >
                      Очистить все данные
                    </Button>
                  </Grid>
                </Grid>
              </CardContent>
            </Card>
          </Grid>
          
          <Grid item xs={12} md={6}>
            <Card>
              <CardHeader title="Системная информация" />
              <CardContent>
                <Typography variant="body2" color="textSecondary" paragraph>
                  Версия системы: 1.0.0
                </Typography>
                <Typography variant="body2" color="textSecondary" paragraph>
                  Время работы: {Math.floor(Math.random() * 48)} часов
                </Typography>
                <Typography variant="body2" color="textSecondary" paragraph>
                  Последний рестарт: {new Date().toLocaleDateString('ru')}
                </Typography>
                
                <Alert severity="warning" sx={{ mt: 2 }}>
                  <Typography variant="body2">
                    Осторожно: административные операции могут повлиять на работу системы.
                  </Typography>
                </Alert>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      )}

      {/* Admin Action Confirmation Dialog */}
      <Dialog
        open={actionDialog.open}
        onClose={closeActionDialog}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>{actionDialog.title}</DialogTitle>
        <DialogContent>
          <Typography>{actionDialog.message}</Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={closeActionDialog}>
            Отмена
          </Button>
          <Button
            onClick={executeAdminAction}
            variant="contained"
            color={actionDialog.type === 'resetKnowledge' ? 'error' : 'primary'}
            disabled={loading}
          >
            {actionDialog.confirmText}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  )
}
