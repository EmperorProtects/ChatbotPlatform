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
  FilterList,
  Refresh,
  Search
} from '@mui/icons-material'
import { botApi } from '../../services/api'

// Normalizes a raw conversation from the backend into a flat display-friendly object.
// Backend shape:
//   { conversation_id, user_id, channel, status, created_at, updated_at, messages[] }
// Each message: { id, sender_type ("user"|"bot"), message, timestamp }
function normalizeConversation(conv) {
  const messages = conv.messages || []

  // Pick the latest user message and the latest bot message for the table preview
  const userMessages = messages.filter(m => m.sender_type === 'user')
  const botMessages  = messages.filter(m => m.sender_type === 'bot')

  const lastUserMsg = userMessages[userMessages.length - 1]
  const lastBotMsg  = botMessages[botMessages.length - 1]

  return {
    id:          conv.conversation_id,
    user_id:     conv.user_id,
    channel:     conv.channel || 'unknown',
    status:      conv.status  || 'enabled',
    timestamp:   conv.updated_at || conv.created_at,
    message:     lastUserMsg?.message || '',
    response:    lastBotMsg?.message  || '',
    messages,    // keep full history for the detail dialog
  }
}

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

  // ─── Data fetching ──────────────────────────────────────────────────────────

  const fetchConversations = async () => {
    try {
      setLoading(true)
      setError(null)

      const response = await botApi.getAllConversations(100)
      const raw = response.data?.conversations || []
      const normalized = raw.map(normalizeConversation)

      setConversations(normalized)
      calculateStats(normalized)
    } catch (err) {
      console.error('Error fetching conversations:', err)
      setError('Ошибка загрузки диалогов')
    } finally {
      setLoading(false)
    }
  }

  const calculateStats = (convList) => {
    const totalLength = convList.reduce(
      (sum, conv) => sum + (conv.message?.length || 0) + (conv.response?.length || 0),
      0
    )

    const channelMap = {}
    convList.forEach(conv => {
      channelMap[conv.channel] = (channelMap[conv.channel] || 0) + 1
    })
    const topChannels = Object.entries(channelMap)
      .map(([name, count]) => ({ name, count }))
      .sort((a, b) => b.count - a.count)

    setStats({
      totalConversations: convList.length,
      averageLength: convList.length > 0 ? Math.round(totalLength / convList.length / 2) : 0,
      topChannels
    })
  }

  // ─── Enable / Disable ───────────────────────────────────────────────────────
  // Backend endpoints: POST /conversation/enable/{user_id}
  //                    POST /conversation/disable/{user_id}
  // Both return: { status: "success" | "error", message: string }
  // We use user_id (not conversation_id) because that's what the backend accepts.

  const enableDialog = async (userId, conversationId) => {
    try {
      const r = await botApi.enableDialog(userId)
      if (r.data?.status === 'success') {
        setConversations(prev =>
          prev.map(d => d.id === conversationId ? { ...d, status: 'enabled' } : d)
        )
      }
    } catch (e) {
      console.error('Error enabling dialog:', e)
    }
  }

  const disableDialog = async (userId, conversationId) => {
    try {
      const r = await botApi.disableDialog(userId)
      if (r.data?.status === 'success') {
        setConversations(prev =>
          prev.map(d => d.id === conversationId ? { ...d, status: 'disabled' } : d)
        )
      }
    } catch (e) {
      console.error('Error disabling dialog:', e)
    }
  }

  // ─── Filtering ──────────────────────────────────────────────────────────────

  const applyFilters = () => {
    let filtered = [...conversations]

    if (searchQuery) {
      const query = searchQuery.toLowerCase()
      filtered = filtered.filter(conv =>
        conv.message?.toLowerCase().includes(query) ||
        conv.response?.toLowerCase().includes(query) ||
        String(conv.user_id)?.toLowerCase().includes(query)
      )
    }

    if (channelFilter) {
      filtered = filtered.filter(conv => conv.channel === channelFilter)
    }

    if (dateFilter) {
      const filterDate = new Date()
      switch (dateFilter) {
        case '24h': filterDate.setHours(filterDate.getHours() - 24); break
        case '7d':  filterDate.setDate(filterDate.getDate() - 7);    break
        case '30d': filterDate.setDate(filterDate.getDate() - 30);   break
        default: break
      }
      filtered = filtered.filter(conv => new Date(conv.timestamp) >= filterDate)
    }

    filtered.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp))
    setFilteredConversations(filtered)
  }

  // ─── Helpers ────────────────────────────────────────────────────────────────

  const handleViewConversation = (conversation) => {
    setSelectedConversation(conversation)
    setOpenDialog(true)
  }

  const formatTimestamp = (timestamp) =>
    new Date(timestamp).toLocaleString('ru', {
      year: 'numeric', month: '2-digit', day: '2-digit',
      hour: '2-digit', minute: '2-digit'
    })

  const getStatusColor  = (status) => status === 'enabled' ? 'success' : 'default'
  const getStatusLabel  = (status) => status === 'enabled' ? 'Активен' : 'Закрыт'

  const paginatedConversations = filteredConversations.slice(
    page * rowsPerPage,
    page * rowsPerPage + rowsPerPage
  )

  // ─── Render ─────────────────────────────────────────────────────────────────

  return (
    <Box>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h4">Диалоги</Typography>
        <Button startIcon={<Refresh />} onClick={fetchConversations} disabled={loading}>
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
              <Typography color="textSecondary" gutterBottom>Всего диалогов</Typography>
              <Typography variant="h4">{stats.totalConversations}</Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={4}>
          <Card>
            <CardContent>
              <Typography color="textSecondary" gutterBottom>Ср. длина сообщения</Typography>
              <Typography variant="h4">{stats.averageLength}</Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={4}>
          <Card>
            <CardContent>
              <Typography color="textSecondary" gutterBottom>Активные каналы</Typography>
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
              fullWidth size="small" label="Поиск"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              InputProps={{ startAdornment: <Search sx={{ mr: 1, color: 'text.secondary' }} /> }}
            />
          </Grid>
          <Grid item xs={12} md={3}>
            <FormControl fullWidth size="small">
              <InputLabel>Канал</InputLabel>
              <Select value={channelFilter} onChange={(e) => setChannelFilter(e.target.value)}>
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
              <Select value={dateFilter} onChange={(e) => setDateFilter(e.target.value)}>
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

      {/* Table */}
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
                  <TableCell>Последнее сообщение</TableCell>
                  <TableCell>Последний ответ</TableCell>
                  <TableCell>Канал</TableCell>
                  <TableCell>Статус</TableCell>
                  <TableCell>Время</TableCell>
                  <TableCell align="center">Просмотр</TableCell>
                  <TableCell align="center">Управление</TableCell>
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
                      <Chip label={conversation.channel} size="small" variant="outlined" />
                    </TableCell>
                    <TableCell>
                      <Chip
                        label={getStatusLabel(conversation.status)}
                        size="small"
                        color={getStatusColor(conversation.status)}
                      />
                    </TableCell>
                    <TableCell>{formatTimestamp(conversation.timestamp)}</TableCell>
                    <TableCell align="center">
                      <IconButton size="small" onClick={() => handleViewConversation(conversation)}>
                        <Visibility fontSize="small" />
                      </IconButton>
                    </TableCell>
                    <TableCell align="center">
                      {conversation.status === 'enabled' ? (
                        <Button
                          size="small"
                          color="error"
                          onClick={() => disableDialog(conversation.user_id, conversation.id)}
                        >
                          Закрыть
                        </Button>
                      ) : (
                        <Button
                          size="small"
                          color="success"
                          onClick={() => enableDialog(conversation.user_id, conversation.id)}
                        >
                          Открыть
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

      {/* Detail Dialog */}
      <Dialog open={openDialog} onClose={() => setOpenDialog(false)} maxWidth="md" fullWidth>
        <DialogTitle>Детали диалога</DialogTitle>
        <DialogContent>
          {selectedConversation && (
            <Box sx={{ mt: 2 }}>
              <Grid container spacing={2} mb={2}>
                <Grid item xs={6} md={3}>
                  <Typography variant="subtitle2" color="textSecondary">Пользователь</Typography>
                  <Typography>{selectedConversation.user_id}</Typography>
                </Grid>
                <Grid item xs={6} md={3}>
                  <Typography variant="subtitle2" color="textSecondary">Канал</Typography>
                  <Chip label={selectedConversation.channel} size="small" />
                </Grid>
                <Grid item xs={6} md={3}>
                  <Typography variant="subtitle2" color="textSecondary">Статус</Typography>
                  <Chip
                    label={getStatusLabel(selectedConversation.status)}
                    size="small"
                    color={getStatusColor(selectedConversation.status)}
                  />
                </Grid>
                <Grid item xs={6} md={3}>
                  <Typography variant="subtitle2" color="textSecondary">Обновлён</Typography>
                  <Typography variant="body2">{formatTimestamp(selectedConversation.timestamp)}</Typography>
                </Grid>
              </Grid>

              {/* Full message history */}
              <Typography variant="subtitle2" gutterBottom>История сообщений</Typography>
              <Box sx={{ maxHeight: 400, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 1 }}>
                {(selectedConversation.messages || []).length === 0 ? (
                  <Typography color="textSecondary" variant="body2">Нет сообщений</Typography>
                ) : (
                  selectedConversation.messages.map((msg) => (
                    <Box
                      key={msg.id}
                      sx={{
                        p: 1.5,
                        borderRadius: 1,
                        bgcolor: msg.sender_type === 'user' ? '#f5f5f5' : '#e3f2fd',
                        alignSelf: msg.sender_type === 'user' ? 'flex-start' : 'flex-end',
                        maxWidth: '85%',
                      }}
                    >
                      <Typography variant="caption" color="textSecondary" display="block">
                        {msg.sender_type === 'user' ? 'Пользователь' : 'Бот'} · {formatTimestamp(msg.timestamp)}
                      </Typography>
                      <Typography variant="body2">{msg.message}</Typography>
                    </Box>
                  ))
                )}
              </Box>
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpenDialog(false)}>Закрыть</Button>
        </DialogActions>
      </Dialog>
    </Box>
  )
}
