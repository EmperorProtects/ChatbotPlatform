import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Box,
  Button,
  Typography,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  IconButton,
  Chip,
  Alert,
  CircularProgress,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Grid,
  Card,
  CardContent,
  TextField,
  InputAdornment
} from '@mui/material'
import { Add, Edit, Delete, Visibility, Search, Refresh, Business } from '@mui/icons-material'
import { knowledgeApi } from '../../services/api'

export default function BriefsPage() {
  const navigate = useNavigate()
  const [briefs, setBriefs] = useState([])
  const [filteredBriefs, setFilteredBriefs] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [deleteDialog, setDeleteDialog] = useState({ open: false, brief: null })
  const [searchQuery, setSearchQuery] = useState('')
  const [stats, setStats] = useState({ totalBriefs: 0, activeBriefs: 0, knowledgeItems: 0 })

  useEffect(() => {
    fetchBriefs()
  }, [])
  
  useEffect(() => {
    applySearch()
  }, [briefs, searchQuery])

  const fetchBriefs = async () => {
    try {
      setLoading(true)
      setError(null)
      
      // Get briefs from knowledge service
      const response = await knowledgeApi.getBriefs('business')
      const briefIds = response.data?.brief_ids || []
      const companyNames = response.data?.company_names || {}
      
      // Get knowledge base stats to see brief details
      const statsResponse = await knowledgeApi.getBusinessStats()
      const briefsData = statsResponse.data?.briefs || {}
      
      // Create brief objects with additional data
      const briefsList = briefIds.map(briefId => {
        const knowledgeCount = briefsData[briefId] || 0
        return {
          id: briefId,
          company_name: companyNames[briefId] || "Бриф " + briefId,
          business_type: 'B2C', // Default type
          created_at: '2024-01-01', // Default date
          status: knowledgeCount > 0 ? 'active' : 'draft',
          knowledge_items: knowledgeCount
        }
      })
      
      // Add mock briefs if no real data
      // if (briefsList.length === 0) {
      //   const mockBriefs = [
      //     {
      //       id: 1,
      //       company_name: 'Hongqi Auto',
      //       business_type: 'B2C',
      //       created_at: '2024-01-15',
      //       status: 'active',
      //       knowledge_items: 25
      //     },
      //     {
      //       id: 2,
      //       company_name: 'CoffeeBar',
      //       business_type: 'B2C',
      //       created_at: '2024-01-20',
      //       status: 'active',
      //       knowledge_items: 18
      //     },
      //     {
      //       id: 3,
      //       company_name: 'Tech Solutions',
      //       business_type: 'B2B',
      //       created_at: '2024-01-22',
      //       status: 'draft',
      //       knowledge_items: 0
      //     }
      //   ]
      //   briefsList.push(...mockBriefs)
      // }
      //
      setBriefs(briefsList)
      
      // Calculate stats
      setStats({
        totalBriefs: briefsList.length,
        activeBriefs: briefsList.filter(b => b.status === 'active').length,
        knowledgeItems: briefsList.reduce((sum, b) => sum + b.knowledge_items, 0)
      })
      
    } catch (err) {
      console.error('Error fetching briefs:', err)
      setError('Ошибка загрузки брифов')
    } finally {
      setLoading(false)
    }
  }
  
  const getBriefName = (briefId) => {
    const briefNames = {
      1: 'Hongqi Auto',
      2: 'CoffeeBar',
      3: 'Tech Solutions'
    }
    return briefNames[briefId] || `Бриф ${briefId}`
  }
  
  const applySearch = () => {
    if (!searchQuery.trim()) {
      setFilteredBriefs(briefs)
      return
    }
    
    const query = searchQuery.toLowerCase()
    const filtered = briefs.filter(brief => 
      brief.company_name.toLowerCase().includes(query) ||
      brief.business_type.toLowerCase().includes(query) ||
      brief.id.toString().includes(query)
    )
    setFilteredBriefs(filtered)
  }
  
  const handleDeleteBrief = async (brief_id) => {
    try {
      setLoading(true)
      
      // In a real app, this would delete all knowledge items for this brief
      // For now, we'll just simulate the deletion
        
      // await new Promise(resolve => setTimeout(resolve, 1000))
      await knowledgeApi.deleteBrief(brief_id)
      
      setBriefs(prev => prev.filter(b => b.id !== brief.id))
      setDeleteDialog({ open: false, brief: null })
      
    } catch (err) {
      setError('Ошибка удаления брифа')
    } finally {
      setLoading(false)
    }
  }
  
  const getStatusColor = (status) => {
    switch (status) {
      case 'active': return 'success'
      case 'draft': return 'warning'
      default: return 'default'
    }
  }
  
  const getStatusLabel = (status) => {
    switch (status) {
      case 'active': return 'Активен'
      case 'draft': return 'Черновик'
      default: return 'Неизвестно'
    }
  }

  return (
    <Box>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h4">Брифы</Typography>
        <Box>
          <Button
            startIcon={<Refresh />}
            onClick={fetchBriefs}
            sx={{ mr: 1 }}
            disabled={loading}
          >
            Обновить
          </Button>
          <Button
            variant="contained"
            startIcon={<Add />}
            onClick={() => navigate('/briefs/new')}
          >
            Создать бриф
          </Button>
        </Box>
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 3 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      {/* Stats Cards */}
      <Grid container spacing={3} mb={3}>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography color="textSecondary" gutterBottom>
                Всего брифов
              </Typography>
              <Typography variant="h4">
                {stats.totalBriefs}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography color="textSecondary" gutterBottom>
                Активных
              </Typography>
              <Typography variant="h4">
                {stats.activeBriefs}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography color="textSecondary" gutterBottom>
                Элементов знаний
              </Typography>
              <Typography variant="h4">
                {stats.knowledgeItems}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography color="textSecondary" gutterBottom>
                Ср. элементов на бриф
              </Typography>
              <Typography variant="h4">
                {stats.totalBriefs > 0 ? Math.round(stats.knowledgeItems / stats.totalBriefs) : 0}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Search */}
      <Paper sx={{ p: 2, mb: 3 }}>
        <TextField
          fullWidth
          size="small"
          placeholder="Поиск по названию, типу или ID..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          InputProps={{
            startAdornment: (
              <InputAdornment position="start">
                <Search color="action" />
              </InputAdornment>
            )
          }}
        />
      </Paper>

      {/* Briefs Table */}
      {loading ? (
        <Box display="flex" justifyContent="center" mt={4}>
          <CircularProgress />
        </Box>
      ) : (
        <TableContainer component={Paper}>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>ID</TableCell>
                <TableCell>Компания</TableCell>
                <TableCell>Тип бизнеса</TableCell>
                <TableCell>Дата создания</TableCell>
                <TableCell>Статус</TableCell>
                <TableCell>Элементы знаний</TableCell>
                <TableCell align="right">Действия</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {filteredBriefs.map((brief) => (
                <TableRow key={brief.id} hover>
                  <TableCell>
                    <Box display="flex" alignItems="center" gap={1}>
                      <Business color="action" />
                      {brief.id}
                    </Box>
                  </TableCell>
                  <TableCell>
                    <Typography variant="subtitle2">
                      {brief.company_name}
                    </Typography>
                  </TableCell>
                  <TableCell>{brief.business_type}</TableCell>
                  <TableCell>
                    {new Date(brief.created_at).toLocaleDateString('ru')}
                  </TableCell>
                  <TableCell>
                    <Chip
                      label={getStatusLabel(brief.status)}
                      color={getStatusColor(brief.status)}
                      size="small"
                    />
                  </TableCell>
                  <TableCell>
                    <Chip
                      label={brief.knowledge_items}
                      size="small"
                      variant="outlined"
                    />
                  </TableCell>
                  <TableCell align="right">
                    <IconButton
                      size="small"
                      onClick={() => navigate(`/briefs/${brief.id}`)}
                      title="Просмотр"
                    >
                      <Visibility fontSize="small" />
                    </IconButton>
                    <IconButton
                      size="small"
                      onClick={() => navigate(`/briefs/${brief.id}`)}
                      title="Редактировать"
                    >
                      <Edit fontSize="small" />
                    </IconButton>
                    <IconButton
                      size="small"
                      color="error"
                      onClick={() => setDeleteDialog({ open: true, brief: brief.id })}
                      title="Удалить"
                    >
                      <Delete fontSize="small" />
                    </IconButton>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
          
          {filteredBriefs.length === 0 && !loading && (
            <Box p={4} textAlign="center">
              <Typography color="textSecondary">
                {searchQuery ? 'Ничего не найдено' : 'Нет брифов'}
              </Typography>
              {!searchQuery && (
                <Button
                  variant="contained"
                  startIcon={<Add />}
                  onClick={() => navigate('/briefs/new')}
                  sx={{ mt: 2 }}
                >
                  Создать первый бриф
                </Button>
              )}
            </Box>
          )}
        </TableContainer>
      )}

      {/* Delete Confirmation Dialog */}
      <Dialog
        open={deleteDialog.open}
        onClose={() => setDeleteDialog({ open: false, brief: null })}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>Удалить бриф?</DialogTitle>
        <DialogContent>
          <Typography>
            Вы уверены, что хотите удалить бриф "{deleteDialog.brief?.company_name}"? 
            Это также удалит все связанные с ним элементы знаний.
          </Typography>
          <Alert severity="warning" sx={{ mt: 2 }}>
            Это действие нельзя отменить!
          </Alert>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeleteDialog({ open: false, brief: null })}>
            Отмена
          </Button>
          <Button
            onClick={() => handleDeleteBrief(deleteDialog.brief)}
            color="error"
            variant="contained"
            disabled={loading}
          >
            Удалить
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  )
}
