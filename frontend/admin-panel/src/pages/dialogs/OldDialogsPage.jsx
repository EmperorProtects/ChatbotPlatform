import React, { useState, useEffect } from 'react'
import {
  Box,
  Typography,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TablePagination,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Chip,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Alert,
  CircularProgress,
  Grid,
  Card,
  CardContent
} from '@mui/material'
import {
  Visibility,
  ThumbUp,
  ThumbDown,
  FilterList,
  Refresh,
  Search
} from '@mui/icons-material'
import { botApi, analyticsApi } from '../../services/api'

export default function DialogsPage() {
  const [conversations, setConversations] = useState([])
  const [filteredConversations, setFilteredConversations] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [page, setPage] = useState(0)
  const [rowsPerPage, setRowsPerPage] = useState(25)
  
  const [selectedConversation, setSelectedConversation] = useState(null)
  const [openDialog, setOpenDialog] = useState(false)
  
  const [searchQuery, setSearchQuery] = useState('')
  const [channelFilter, setChannelFilter] = useState('')
  const [dateFilter, setDateFilter] = useState('')

  
  const [stats, setStats] = useState({
    totalConversations: 0,
    averageLength: 0,
    topChannels: []
  })

  useEffect(() => {
    fetchConversations()
  }, [])

  useEffect(() => {
    applyFilters()
  }, [conversations, searchQuery, channelFilter, dateFilter])

  const fetchConversations = async () => {
    try {
      setLoading(true)
      setError(null)
      
      const conversations = []
      
      // Try to get real conversation data
      try {
        // const sampleUsers = ['user_001', 'user_002', 'user_003', 'web-user-123', 'web-user-456']
        //
        // for (const userId of sampleUsers) {
        //   try {
        //     const response = await botApi.getConversationHistory(userId, 20)
        //     if (response.data?.messages && response.data.messages.length > 0) {
        //       response.data.messages.forEach((msg, index) => {
        //         mockConversations.push({
        //           id: `${userId}-${index}`,
        //           user_id: userId,
        //           message: msg.message,
        //           response: msg.response,
        //           timestamp: msg.timestamp,
        //           channel: msg.channel || 'web',
        //           rating: Math.random() > 0.7 ? (Math.random() > 0.5 ? 'positive' : 'negative') : null
        //         })
        //       })
        //     }
        //   } catch (e) {
        //     // Skip users with no conversation history
        //     continue
        //   }

        const r = await botApi.getAllConversations(100)
        conversations.push(...r.data.conversations)
        
        }
      } catch (e) {
        console.log('Could not fetch real conversations, using mock data')
      }
      
      // Add mock data if no real data was found
      if (mockConversations.length === 0) {
        const mockData = [
          {
            id: 'mock-1',
            user_id: 'user_001',
            message: 'Привет! Могу ли я узнать о ваших услугах?',
            response: 'Здравствуйте! Конечно, расскажу о наших услугах...',
            timestamp: new Date(Date.now() - 3600000).toISOString(),
            channel: 'web',
            rating: 'positive'
          },
          {
            id: 'mock-2',
            user_id: 'user_002',
            message: 'Какая стоимость ваших товаров?',
            response: 'Цены на нашу продукцию начинаются от...',
            timestamp: new Date(Date.now() - 7200000).toISOString(),
            channel: 'whatsapp',
            rating: null
          },
          {
            id: 'mock-3',
            user_id: 'user_003',
            message: 'Можно ли оформить заказ?',
            response: 'Конечно! Для оформления заказа мне понадобятся...',
            timestamp: new Date(Date.now() - 10800000).toISOString(),
            channel: 'instagram',
            rating: 'positive'
          }
        ]
        mockConversations.push(...mockData)
      }
      
      setConversations(mockConversations)
      
      // Calculate stats
      const stats = {
        totalConversations: mockConversations.length,
        averageLength: mockConversations.reduce((sum, conv) => 
          sum + (conv.message?.length || 0) + (conv.response?.length || 0), 0
        ) / mockConversations.length / 2,
        topChannels: [...new Set(mockConversations.map(c => c.channel))]
          .map(channel => ({
            name: channel,
            count: mockConversations.filter(c => c.channel === channel).length
          }))
          .sort((a, b) => b.count - a.count)
      }
      
      setStats(stats)
      
    } catch (err) {
      console.error('Error fetching conversations:', err)
      setError('Ошибка загрузки диалогов')
    } finally {
      setLoading(false)
    }
  }


  const enableDialog = async (conversationId) => {
    try {
      r =await botApi.enableDialog(conversationId)
      if (r.status === "enabled"){
        setConversations(prev => prev.map(d => d.id === conversationId ? {...d, status:'enabled'} : d ))
      }
    }
    catch (e) {
      console.error('Error enabling dialog:', e)
    }
    
  }

  const disableDialog = async (conversationId) => {
    try{
      r = await botApi.disableDialog(conversationId)
      if(r.status === "disabled"){
        setConversations(prev => prev.map(d => d.id === conversationId ? {...d, status:'disabled'} : d ))
      }
    }
    catch (e) {
      console.error('Error disabling dialog:', e)
    }
  }

  const applyFilters = () => {
    let filtered = [...conversations]
    
    // Search filter
    if (searchQuery) {
      const query = searchQuery.toLowerCase()
      filtered = filtered.filter(conv => 
        conv.message?.toLowerCase().includes(query) ||
        conv.response?.toLowerCase().includes(query) ||
        conv.user_id?.toLowerCase().includes(query)
      )
    }
    
    // Channel filter
    if (channelFilter) {
      filtered = filtered.filter(conv => conv.channel === channelFilter)
    }
    
    // Date filter (last 24h, 7 days, etc.)
    if (dateFilter) {
      const now = new Date()
      const filterDate = new Date()
      
      switch (dateFilter) {
        case '24h':
          filterDate.setHours(now.getHours() - 24)
          break
        case '7d':
          filterDate.setDate(now.getDate() - 7)
          break
        case '30d':
          filterDate.setDate(now.getDate() - 30)
          break
        default:
          break
      }
      
      filtered = filtered.filter(conv => 
        new Date(conv.timestamp) >= filterDate
      )
    }
    
    // Sort by timestamp (newest first)
    filtered.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp))
    
    setFilteredConversations(filtered)
  }

  const handleViewConversation = (conversation) => {
    setSelectedConversation(conversation)
    setOpenDialog(true)
  }

  

  const formatTimestamp = (timestamp) => {
    return new Date(timestamp).toLocaleString('ru', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  const getRatingColor = (rating) => {
    switch (rating) {
      case 'positive': return 'success'
      case 'negative': return 'error'
      default: return 'default'
    }
  }

  const getRatingLabel = (rating) => {
    switch (rating) {
      case 'positive': return 'Положительная'
      case 'negative': return 'Отрицательная'
      default: return 'Не оценено'
    }
  }

  const paginatedConversations = filteredConversations.slice(
    page * rowsPerPage,
    page * rowsPerPage + rowsPerPage
  )

  return (
    <Box>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h4">
          Диалоги
        </Typography>
        <Button
          startIcon={<Refresh />}
          onClick={fetchConversations}
          disabled={loading}
        >
          Обновить
        </Button>
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 3 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      {/* Stats */}
      <Grid container spacing={3} mb={3}>
        <Grid item xs={12} md={4}>
          <Card>
            <CardContent>
              <Typography color="textSecondary" gutterBottom>
                Всего диалогов
              </Typography>
              <Typography variant="h4">
                {stats.totalConversations}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={4}>
          <Card>
            <CardContent>
              <Typography color="textSecondary" gutterBottom>
                Ср. длина сообщения
              </Typography>
              <Typography variant="h4">
                {Math.round(stats.averageLength)}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={4}>
          <Card>
            <CardContent>
              <Typography color="textSecondary" gutterBottom>
                Активные каналы
              </Typography>
              <Box display="flex" flexWrap="wrap" gap={0.5} mt={1}>
                {stats.topChannels.map(channel => (
                  <Chip
                    key={channel.name}
                    label={`${channel.name} (${channel.count})`}
                    size="small"
                    color="primary"
                  />
                ))}
              </Box>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Filters */}
      <Paper sx={{ p: 2, mb: 3 }}>
        <Grid container spacing={2} alignItems="center">
          <Grid item xs={12} md={4}>
            <TextField
              fullWidth
              size="small"
              label="Поиск"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              InputProps={{
                startAdornment: <Search sx={{ mr: 1, color: 'text.secondary' }} />
              }}
            />
          </Grid>
          <Grid item xs={12} md={3}>
            <FormControl fullWidth size="small">
              <InputLabel>Канал</InputLabel>
              <Select
                value={channelFilter}
                onChange={(e) => setChannelFilter(e.target.value)}
              >
                <MenuItem value="">Все</MenuItem>
                {stats.topChannels.map(channel => (
                  <MenuItem key={channel.name} value={channel.name}>
                    {channel.name.charAt(0).toUpperCase() + channel.name.slice(1)}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          </Grid>
          <Grid item xs={12} md={3}>
            <FormControl fullWidth size="small">
              <InputLabel>Период</InputLabel>
              <Select
                value={dateFilter}
                onChange={(e) => setDateFilter(e.target.value)}
              >
                <MenuItem value="">Все время</MenuItem>
                <MenuItem value="24h">Последние 24 часа</MenuItem>
                <MenuItem value="7d">Последние 7 дней</MenuItem>
                <MenuItem value="30d">Последние 30 дней</MenuItem>
              </Select>
            </FormControl>
          </Grid>
          <Grid item xs={12} md={2}>
            <Typography variant="body2" color="textSecondary">
              Найдено: {filteredConversations.length}
            </Typography>
          </Grid>
        </Grid>
      </Paper>

      {/* Conversations Table */}
      {loading ? (
        <Box display="flex" justifyContent="center" mt={4}>
          <CircularProgress />
        </Box>
      ) : (
        <Paper>
          <TableContainer>
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell>Пользователь</TableCell>
                  <TableCell>Сообщение</TableCell>
                  <TableCell>Ответ</TableCell>
                  <TableCell>Канал</TableCell>
                  <TableCell>Оценка</TableCell>
                  <TableCell>Время</TableCell>
                  <TableCell align="center">Действия</TableCell>
                  <TableCell align="center">Статус диалога</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {paginatedConversations.map((conversation) => (
                  <TableRow key={conversation.id} hover>
                    <TableCell>{conversation.user_id}</TableCell>
                    <TableCell sx={{ maxWidth: 200 }}>
                      {conversation.message?.substring(0, 100)}
                      {conversation.message?.length > 100 ? '...' : ''}
                    </TableCell>
                    <TableCell sx={{ maxWidth: 200 }}>
                      {conversation.response?.substring(0, 100)}
                      {conversation.response?.length > 100 ? '...' : ''}
                    </TableCell>
                    <TableCell>
                      <Chip
                        label={conversation.channel}
                        size="small"
                        variant="outlined"
                      />
                    </TableCell>
                    <TableCell>
                      <Chip
                        label={getRatingLabel(conversation.rating)}
                        size="small"
                        color={getRatingColor(conversation.rating)}
                      />
                    </TableCell>
                    <TableCell>
                      {formatTimestamp(conversation.timestamp)}
                    </TableCell>
                    <TableCell align="center">
                      <IconButton
                        size="small"
                        onClick={() => handleViewConversation(conversation)}
                      >
                        <Visibility fontSize="small" />
                      </IconButton>
                    </TableCell>
                    <TableCell>
                        { conversation.status == "enabled" ? (
                         <Button color="error" onClick={()=> disableDialog(conversation.id)}>
                            Закрыть диалог
                         </Button>
                        ):(
                        <Button color="success" onClick={()=> enableDialog(conversation.id)}>
                            Открыть диалог
                        </Button>                  
                        )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
          <TablePagination
            component="div"
            count={filteredConversations.length}
            page={page}
            onPageChange={(e, newPage) => setPage(newPage)}
            rowsPerPage={rowsPerPage}
            onRowsPerPageChange={(e) => {
              setRowsPerPage(parseInt(e.target.value, 10))
              setPage(0)
            }}
            rowsPerPageOptions={[10, 25, 50, 100]}
            labelRowsPerPage="Строк на странице:"
          />
        </Paper>
      )}

      <Dialog
        open={openDialog}
        onClose={() => setOpenDialog(false)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>
          Детали диалога
        </DialogTitle>
        <DialogContent>
          {selectedConversation && (
            <Box sx={{ mt: 2 }}>
              <Grid container spacing={3}>
                <Grid item xs={12} md={6}>
                  <Typography variant="subtitle2" gutterBottom>
                    Пользователь:
                  </Typography>
                  <Typography>{selectedConversation.user_id}</Typography>
                  
                  <Typography variant="subtitle2" gutterBottom sx={{ mt: 2 }}>
                    Канал:
                  </Typography>
                  <Chip label={selectedConversation.channel} size="small" />
                  
                  <Typography variant="subtitle2" gutterBottom sx={{ mt: 2 }}>
                    Время:
                  </Typography>
                  <Typography>{formatTimestamp(selectedConversation.timestamp)}</Typography>
                  
                  <Typography variant="subtitle2" gutterBottom sx={{ mt: 2 }}>
                    Оценка:
                  </Typography>
                  <Chip
                    label={getRatingLabel(selectedConversation.rating)}
                    color={getRatingColor(selectedConversation.rating)}
                  />
                </Grid>
                
                <Grid item xs={12}>
                  <Typography variant="subtitle2" gutterBottom>
                    Сообщение пользователя:
                  </Typography>
                  <Paper sx={{ p: 2, bgcolor: '#f5f5f5' }}>
                    <Typography>{selectedConversation.message}</Typography>
                  </Paper>
                  
                  <Typography variant="subtitle2" gutterBottom sx={{ mt: 2 }}>
                    Ответ бота:
                  </Typography>
                  <Paper sx={{ p: 2, bgcolor: '#e3f2fd' }}>
                    <Typography>{selectedConversation.response}</Typography>
                  </Paper>
                </Grid>
              </Grid>
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpenDialog(false)}>
            Закрыть
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  )
}
