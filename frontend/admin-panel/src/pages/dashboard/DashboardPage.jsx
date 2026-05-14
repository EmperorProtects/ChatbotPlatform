import React, { useState, useEffect } from 'react'
import {
  Grid,
  Paper,
  Typography,
  Box,
  Card,
  CardContent,
  CircularProgress,
  Alert,
} from '@mui/material'
import {
  Chat,
  TrendingUp,
  CheckCircle,
  Speed,
  Storage,
  Psychology,
} from '@mui/icons-material'
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  BarChart,
  Bar,
} from 'recharts'
import { adminApi, analyticsApi, knowledgeApi } from '../../services/api'

const StatCard = ({ title, value, icon, color, loading = false }) => (
  <Card>
    <CardContent>
      <Box display="flex" justifyContent="space-between" alignItems="center">
        <Box>
          <Typography color="textSecondary" gutterBottom variant="body2">
            {title}
          </Typography>
          <Typography variant="h4">
            {loading ? <CircularProgress size={24} /> : value}
          </Typography>
        </Box>
        <Box
          sx={{
            backgroundColor: color,
            borderRadius: '50%',
            width: 60,
            height: 60,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}
        >
          {icon}
        </Box>
      </Box>
    </CardContent>
  </Card>
)

export default function DashboardPage() {
  const [dashboardData, setDashboardData] = useState({
    overview: null,
    channelMetrics: null,
    knowledgeStats: null,
    servicesStatus: null
  })
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    fetchDashboardData()
  }, [])

  const fetchDashboardData = async () => {
    try {
      setLoading(true)
      setError(null)
      
      // Fetch data from multiple endpoints in parallel
      const promises = {
        overview: analyticsApi.getOverview(7).catch(() => null),
        channelMetrics: analyticsApi.getChannelMetrics().catch(() => null),
        knowledgeStats: knowledgeApi.getBusinessStats().catch(() => null),
        servicesStatus: adminApi.getServicesStatus().catch(() => null)
      }
      
      const results = await Promise.allSettled([
        promises.overview,
        promises.channelMetrics,
        promises.knowledgeStats,
        promises.servicesStatus
      ])
      
      const [overviewRes, channelRes, knowledgeRes, servicesRes] = results
      
      setDashboardData({
        overview: overviewRes.status === 'fulfilled' ? overviewRes.value?.data : null,
        channelMetrics: channelRes.status === 'fulfilled' ? channelRes.value?.data : null,
        knowledgeStats: knowledgeRes.status === 'fulfilled' ? knowledgeRes.value?.data : null,
        servicesStatus: servicesRes.status === 'fulfilled' ? servicesRes.value?.data : null
      })
      
      // If all services failed, show warning but continue with mock data
      const allFailed = results.every(r => r.status === 'rejected')
      if (allFailed) {
        setError('Не удалось получить данные с сервисов. Показаны тестовые данные.')
      }
    } catch (err) {
      console.error('Dashboard data fetch error:', err)
      setError('Ошибка загрузки данных дашборда')
    } finally {
      setLoading(false)
    }
  }
  
  // Parse analytics data for charts
  const getActivityData = () => {
    if (!dashboardData.overview?.daily_breakdown) {
      return [
        { name: 'Пн', messages: 65, responses: 62 },
        { name: 'Вт', messages: 78, responses: 75 },
        { name: 'Ср', messages: 90, responses: 86 },
        { name: 'Чт', messages: 81, responses: 78 },
        { name: 'Пт', messages: 56, responses: 54 },
        { name: 'Сб', messages: 34, responses: 32 },
        { name: 'Вс', messages: 29, responses: 28 },
      ]
    }
    
    return dashboardData.overview.daily_breakdown.map(day => {
      const date = new Date(day.date)
      const dayName = date.toLocaleDateString('ru', { weekday: 'short' })
      return {
        name: dayName,
        messages: day.messages || 0,
        responses: Math.floor((day.messages || 0) * 0.95), // Approximate response rate
        users: day.unique_users || 0
      }
    }).reverse() // Show chronologically
  }
  
  const getChannelData = () => {
    if (!dashboardData.channelMetrics) {
      return [
        { name: 'Web', value: 45, color: '#0088FE' },
        { name: 'WhatsApp', value: 30, color: '#00C49F' },
        { name: 'Instagram', value: 25, color: '#FFBB28' },
      ]
    }
    
    const channels = Object.entries(dashboardData.channelMetrics)
    const colors = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884D8']
    
    return channels.map(([name, data], index) => ({
      name: name.charAt(0).toUpperCase() + name.slice(1),
      value: data.messages_received || 0,
      color: colors[index % colors.length]
    }))
  }
  
  // Calculate stats from real data
  const getStats = () => {
    const overview = dashboardData.overview
    const knowledge = dashboardData.knowledgeStats
    
    return {
      totalMessages: overview?.total_messages || 0,
      uniqueUsers: overview?.unique_users || 0,
      knowledgeItems: knowledge?.total_documents || 0,
      avgResponseTime: '1.2s', // This would need to be calculated from conversation data
      conversionRate: overview ? 
        Math.round((overview.unique_users / overview.total_messages) * 100) + '%' : '0%'
    }
  }
  
  const stats = getStats()
  const activityData = getActivityData()
  const channelData = getChannelData()

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="60vh">
        <CircularProgress />
      </Box>
    )
  }

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Дашборд
      </Typography>

      {error && (
        <Alert severity="warning" sx={{ mb: 3 }}>
          {error}
        </Alert>
      )}

      <Grid container spacing={3}>
        {/* Stats Cards */}
        <Grid item xs={12} sm={6} md={3}>
          <StatCard
            title="Сообщения (всего)"
            value={stats.totalMessages}
            icon={<Chat style={{ color: 'white' }} />}
            color="#1976d2"
            loading={loading}
          />
        </Grid>
        
        <Grid item xs={12} sm={6} md={3}>
          <StatCard
            title="Уникальные пользователи"
            value={stats.uniqueUsers}
            icon={<TrendingUp style={{ color: 'white' }} />}
            color="#2e7d32"
            loading={loading}
          />
        </Grid>
        
        <Grid item xs={12} sm={6} md={3}>
          <StatCard
            title="База знаний"
            value={stats.knowledgeItems}
            icon={<Storage style={{ color: 'white' }} />}
            color="#ed6c02"
            loading={loading}
          />
        </Grid>
        
        <Grid item xs={12} sm={6} md={3}>
          <StatCard
            title="Конверсия"
            value={stats.conversionRate}
            icon={<Psychology style={{ color: 'white' }} />}
            color="#9c27b0"
            loading={loading}
          />
        </Grid>

        {/* Activity Chart */}
        <Grid item xs={12} md={8}>
          <Paper sx={{ p: 2 }}>
            <Typography variant="h6" gutterBottom>
              Активность по дням
            </Typography>
            <Box sx={{ height: 300 }}>
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={activityData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="name" />
                  <YAxis />
                  <Tooltip />
                  <Line 
                    type="monotone" 
                    dataKey="messages" 
                    stroke="#1976d2" 
                    strokeWidth={2}
                    name="Сообщения"
                  />
                  <Line 
                    type="monotone" 
                    dataKey="users" 
                    stroke="#2e7d32" 
                    strokeWidth={2}
                    name="Пользователи"
                  />
                </LineChart>
              </ResponsiveContainer>
            </Box>
          </Paper>
        </Grid>

        {/* Channel Distribution */}
        <Grid item xs={12} md={4}>
          <Paper sx={{ p: 2 }}>
            <Typography variant="h6" gutterBottom>
              Каналы связи
            </Typography>
            <Box sx={{ height: 300 }}>
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={channelData}
                    cx="50%"
                    cy="50%"
                    innerRadius={60}
                    outerRadius={100}
                    paddingAngle={5}
                    dataKey="value"
                    label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                  >
                    {channelData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip />
                </PieChart>
              </ResponsiveContainer>
            </Box>
          </Paper>
        </Grid>

        {/* Services Status */}
        <Grid item xs={12}>
          <Paper sx={{ p: 2 }}>
            <Typography variant="h6" gutterBottom>
              Статус сервисов
            </Typography>
            {dashboardData.servicesStatus ? (
              <Grid container spacing={2}>
                {Object.entries(dashboardData.servicesStatus).map(([serviceName, serviceData]) => (
                  <Grid item xs={12} sm={6} md={3} key={serviceName}>
                    <Card variant="outlined">
                      <CardContent>
                        <Typography variant="subtitle2" color="textSecondary">
                          {serviceName.replace('_', ' ').toUpperCase()}
                        </Typography>
                        <Box display="flex" alignItems="center" mt={1}>
                          <CheckCircle 
                            color={serviceData.status === 'healthy' ? 'success' : 'error'}
                            sx={{ mr: 1 }}
                          />
                          <Typography variant="body2">
                            {serviceData.status === 'healthy' ? 'Здоров' : 'Недоступен'}
                          </Typography>
                        </Box>
                      </CardContent>
                    </Card>
                  </Grid>
                ))}
              </Grid>
            ) : (
              <Typography color="textSecondary">
                Данные о сервисах недоступны
              </Typography>
            )}
          </Paper>
        </Grid>
      </Grid>
    </Box>
  )
}
