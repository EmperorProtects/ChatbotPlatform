import React, { useState, useEffect } from 'react'
import {
  Box,
  Typography,
  Paper,
  Grid,
  Card,
  CardContent,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Alert,
  CircularProgress,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Chip
} from '@mui/material'
import { DatePicker } from '@mui/x-date-pickers/DatePicker'
import {
  BarChart,
  Bar,
  LineChart,
  Line,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  AreaChart,
  Area
} from 'recharts'
import { analyticsApi, botApi } from '../../services/api'

export default function AnalyticsPage() {
  const [timeRange, setTimeRange] = useState(7) // Days
  const [overviewData, setOverviewData] = useState(null)
  const [channelData, setChannelData] = useState(null)
  const [conversationSamples, setConversationSamples] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  useEffect(() => {
    fetchAnalyticsData()
  }, [timeRange])

  const fetchAnalyticsData = async () => {
    try {
      setLoading(true)
      setError(null)
      
      // Fetch overview metrics
      const overviewResponse = await analyticsApi.getOverview(timeRange)
      setOverviewData(overviewResponse.data)
      
      // Fetch channel metrics
      const channelResponse = await analyticsApi.getChannelMetrics()
      setChannelData(channelResponse.data)
      
      // Fetch some conversation samples
      try {
        const conversationResponse = await botApi.getConversationHistory('user_001', 10)
        setConversationSamples(conversationResponse.data?.messages || [])
      } catch (e) {
        // Conversation data is optional
        setConversationSamples([])
      }
      
    } catch (err) {
      console.error('Analytics fetch error:', err)
      setError('Ошибка загрузки аналитики. Показаны тестовые данные.')
      
      // Fallback to mock data
      setOverviewData({
        total_messages: 1250,
        unique_users: 340,
        daily_breakdown: [
          { date: '2024-01-15', messages: 180, unique_users: 45, channels: { web: 120, whatsapp: 60 } },
          { date: '2024-01-16', messages: 220, unique_users: 58, channels: { web: 140, whatsapp: 80 } },
          { date: '2024-01-17', messages: 195, unique_users: 52, channels: { web: 130, whatsapp: 65 } },
          { date: '2024-01-18', messages: 240, unique_users: 61, channels: { web: 160, whatsapp: 80 } },
          { date: '2024-01-19', messages: 210, unique_users: 55, channels: { web: 145, whatsapp: 65 } },
          { date: '2024-01-20', messages: 185, unique_users: 48, channels: { web: 125, whatsapp: 60 } },
          { date: '2024-01-21', messages: 160, unique_users: 42, channels: { web: 110, whatsapp: 50 } }
        ],
        channels: {
          web: 890,
          whatsapp: 360
        }
      })
      
      setChannelData({
        web: { messages_received: 890, messages_sent: 885 },
        whatsapp: { messages_received: 360, messages_sent: 358 }
      })
    } finally {
      setLoading(false)
    }
  }

  const formatDateForChart = (dateStr) => {
    const date = new Date(dateStr)
    return date.toLocaleDateString('ru', { month: 'short', day: 'numeric' })
  }

  const getChannelChartData = () => {
    if (!channelData) return []
    
    return Object.entries(channelData).map(([channel, data]) => ({
      channel: channel.charAt(0).toUpperCase() + channel.slice(1),
      received: data.messages_received || 0,
      sent: data.messages_sent || 0,
      engagement: Math.round(((data.messages_sent || 0) / (data.messages_received || 1)) * 100)
    }))
  }
  
  const getChannelPieData = () => {
    if (!overviewData?.channels) return []
    
    const colors = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884D8']
    return Object.entries(overviewData.channels).map(([channel, value], index) => ({
      name: channel.charAt(0).toUpperCase() + channel.slice(1),
      value,
      color: colors[index % colors.length]
    }))
  }
  
  const getDailyActivityData = () => {
    if (!overviewData?.daily_breakdown) return []
    
    return overviewData.daily_breakdown.map(day => ({
      date: formatDateForChart(day.date),
      messages: day.messages || 0,
      users: day.unique_users || 0,
      engagement: day.messages && day.unique_users ? 
        Math.round((day.messages / day.unique_users) * 10) / 10 : 0
    }))
  }
  
  const channelChartData = getChannelChartData()
  const channelPieData = getChannelPieData()
  const dailyActivityData = getDailyActivityData()

  return (
    <Box>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h4">
          Аналитика
        </Typography>
        <FormControl size="small">
          <InputLabel>Период</InputLabel>
          <Select
            value={timeRange}
            onChange={(e) => setTimeRange(e.target.value)}
            sx={{ minWidth: 120 }}
          >
            <MenuItem value={1}>1 день</MenuItem>
            <MenuItem value={7}>7 дней</MenuItem>
            <MenuItem value={30}>30 дней</MenuItem>
            <MenuItem value={90}>90 дней</MenuItem>
          </Select>
        </FormControl>
      </Box>

      {error && (
        <Alert severity="info" sx={{ mb: 3 }}>
          {error}
        </Alert>
      )}

      {loading ? (
        <Box display="flex" justifyContent="center" mt={4}>
          <CircularProgress />
        </Box>
      ) : (
        <>
          {/* Overview Cards */}
          <Grid container spacing={3} mb={4}>
            <Grid item xs={12} sm={6} md={3}>
              <Card>
                <CardContent>
                  <Typography color="textSecondary" gutterBottom>
                    Всего сообщений
                  </Typography>
                  <Typography variant="h4">
                    {overviewData?.total_messages?.toLocaleString() || '0'}
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
            <Grid item xs={12} sm={6} md={3}>
              <Card>
                <CardContent>
                  <Typography color="textSecondary" gutterBottom>
                    Уникальных пользователей
                  </Typography>
                  <Typography variant="h4">
                    {overviewData?.unique_users?.toLocaleString() || '0'}
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
            <Grid item xs={12} sm={6} md={3}>
              <Card>
                <CardContent>
                  <Typography color="textSecondary" gutterBottom>
                    Ср. сообщений/пользователь
                  </Typography>
                  <Typography variant="h4">
                    {overviewData && overviewData.total_messages && overviewData.unique_users ?
                      Math.round((overviewData.total_messages / overviewData.unique_users) * 10) / 10 :
                      '0'
                    }
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
            <Grid item xs={12} sm={6} md={3}>
              <Card>
                <CardContent>
                  <Typography color="textSecondary" gutterBottom>
                    Активных каналов
                  </Typography>
                  <Typography variant="h4">
                    {channelData ? Object.keys(channelData).length : '0'}
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
          </Grid>

          {/* Charts */}
          <Grid container spacing={3} mb={4}>
            {/* Daily Activity */}
            <Grid item xs={12} lg={8}>
              <Paper sx={{ p: 2 }}>
                <Typography variant="h6" gutterBottom>
                  Активность по дням
                </Typography>
                <Box sx={{ height: 300 }}>
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={dailyActivityData}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="date" />
                      <YAxis />
                      <Tooltip />
                      <Legend />
                      <Area
                        type="monotone"
                        dataKey="messages"
                        stackId="1"
                        stroke="#1976d2"
                        fill="#1976d2"
                        name="Сообщения"
                      />
                      <Area
                        type="monotone"
                        dataKey="users"
                        stackId="2"
                        stroke="#2e7d32"
                        fill="#2e7d32"
                        name="Пользователи"
                      />
                    </AreaChart>
                  </ResponsiveContainer>
                </Box>
              </Paper>
            </Grid>

            {/* Channel Distribution */}
            <Grid item xs={12} lg={4}>
              <Paper sx={{ p: 2 }}>
                <Typography variant="h6" gutterBottom>
                  Распределение по каналам
                </Typography>
                <Box sx={{ height: 300 }}>
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie
                        data={channelPieData}
                        cx="50%"
                        cy="50%"
                        innerRadius={50}
                        outerRadius={100}
                        paddingAngle={5}
                        dataKey="value"
                        label={({ name, percent }) => `${name}: ${(percent * 100).toFixed(0)}%`}
                      >
                        {channelPieData.map((entry, index) => (
                          <Cell key={`cell-${index}`} fill={entry.color} />
                        ))}
                      </Pie>
                      <Tooltip />
                    </PieChart>
                  </ResponsiveContainer>
                </Box>
              </Paper>
            </Grid>
          </Grid>

          {/* Channel Performance */}
          <Grid container spacing={3} mb={4}>
            <Grid item xs={12}>
              <Paper sx={{ p: 2 }}>
                <Typography variant="h6" gutterBottom>
                  Продуктивность каналов
                </Typography>
                <Box sx={{ height: 300 }}>
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={channelChartData}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="channel" />
                      <YAxis />
                      <Tooltip />
                      <Legend />
                      <Bar dataKey="received" fill="#1976d2" name="Получено" />
                      <Bar dataKey="sent" fill="#2e7d32" name="Отправлено" />
                    </BarChart>
                  </ResponsiveContainer>
                </Box>
              </Paper>
            </Grid>
          </Grid>

          {/* Channel Details Table */}
          <Grid container spacing={3} mb={4}>
            <Grid item xs={12}>
              <Paper sx={{ p: 2 }}>
                <Typography variant="h6" gutterBottom>
                  Детали по каналам
                </Typography>
                <TableContainer>
                  <Table>
                    <TableHead>
                      <TableRow>
                        <TableCell>Канал</TableCell>
                        <TableCell align="right">Получено</TableCell>
                        <TableCell align="right">Отправлено</TableCell>
                        <TableCell align="right">Ответов %</TableCell>
                        <TableCell align="center">Статус</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {channelChartData.map((row) => (
                        <TableRow key={row.channel}>
                          <TableCell component="th" scope="row">
                            {row.channel}
                          </TableCell>
                          <TableCell align="right">{row.received.toLocaleString()}</TableCell>
                          <TableCell align="right">{row.sent.toLocaleString()}</TableCell>
                          <TableCell align="right">{row.engagement}%</TableCell>
                          <TableCell align="center">
                            <Chip
                              label={row.engagement > 90 ? 'Отлично' : row.engagement > 80 ? 'Хорошо' : 'Нужно улучшение'}
                              color={row.engagement > 90 ? 'success' : row.engagement > 80 ? 'primary' : 'warning'}
                              size="small"
                            />
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </TableContainer>
              </Paper>
            </Grid>
          </Grid>

          {/* Recent Conversations Sample */}
          {conversationSamples.length > 0 && (
            <Grid container spacing={3}>
              <Grid item xs={12}>
                <Paper sx={{ p: 2 }}>
                  <Typography variant="h6" gutterBottom>
                    Последние диалоги (образец)
                  </Typography>
                  <TableContainer>
                    <Table>
                      <TableHead>
                        <TableRow>
                          <TableCell>Время</TableCell>
                          <TableCell>Пользователь</TableCell>
                          <TableCell>Сообщение</TableCell>
                          <TableCell>Ответ</TableCell>
                          <TableCell>Канал</TableCell>
                        </TableRow>
                      </TableHead>
                      <TableBody>
                        {conversationSamples.slice(0, 5).map((conv) => (
                          <TableRow key={conv.id}>
                            <TableCell>
                              {new Date(conv.timestamp).toLocaleString('ru')}
                            </TableCell>
                            <TableCell>{conv.user_id}</TableCell>
                            <TableCell sx={{ maxWidth: 200 }}>
                              {conv.message?.substring(0, 100)}
                              {conv.message?.length > 100 ? '...' : ''}
                            </TableCell>
                            <TableCell sx={{ maxWidth: 200 }}>
                              {conv.response?.substring(0, 100)}
                              {conv.response?.length > 100 ? '...' : ''}
                            </TableCell>
                            <TableCell>
                              <Chip label={conv.channel} size="small" />
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </TableContainer>
                </Paper>
              </Grid>
            </Grid>
          )}
        </>
      )}
    </Box>
  )
}
