import React, { useState, useEffect, useRef} from 'react'
import {
  Box,
  Typography,
  Paper,
  Button,
  TextField,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Grid,
  Card,
  CardContent,
  CardActions,
  Chip,
  IconButton,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Alert,
  CircularProgress,
  Tabs,
  Tab,
  Divider,
  LinearProgress
} from '@mui/material'
import {
  Add,
  Edit,
  Delete,
  Search,
  Category,
  Business,
  UploadFile,
  TableChart,
  Refresh,
  CheckCircle
} from '@mui/icons-material'
import { knowledgeApi } from '../../services/api'

export default function KnowledgePage() {
  const [activeTab, setActiveTab] = useState(1)
  const [businessItems, setBusinessItems] = useState([])
  const [userItems, setUserItems] = useState([])
  const [businessStats, setBusinessStats] = useState(null)
  const [userStats, setUserStats] = useState(null)
  const [categories, setCategories] = useState([])
  const [user_ids, setUserIds] = useState([])
  const [briefs, setBriefs] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  
  // Dialog states
  const [openDialog, setOpenDialog] = useState(false)
  const [dialogType, setDialogType] = useState('add') // 'add' or 'edit'
  const [selectedItem, setSelectedItem] = useState(null)
  //excelUploading
  const [openExcelDialog, setOpenExcelDialog] = useState(false)
  const [excelFile, setExcelFile] = useState(null)
  const [excelBriefId, setExcelBriefId] = useState(1)
  const [excelUploading, setExcelUploading] = useState(false)
  const [excelSuccess, setExcelSuccess] = useState(null)
  const fileInputRef = useRef(null)
  
  // Form states
  const [formData, setFormData] = useState({
    text: '',
    category: 'general',
    title: '',
    brief_id: '',
    user_id: ''
  })
  
  // Search states
  const [searchQuery, setSearchQuery] = useState('')
  const [searchResults, setSearchResults] = useState([])
  const [searching, setSearching] = useState(false)

  useEffect(() => {
    fetchData()
  }, [activeTab])

const fetchData = async (tab = activeTab) => {
  try {
    setLoading(true)
    setError(null)

    const collection = tab === 0 ? 'business' : 'user'
    console.log('Fetched items:', collection)
    console.log('Fetching data for:', tab )

    // Fetch items
    const itemsResponse = await knowledgeApi.listItems({
      which: collection
      // limit: 100
    })

    console.log('Items response:', itemsResponse)

    const items = itemsResponse.data?.items || []

    if (tab === 0) {
      setBusinessItems(items)
    } else {
      setUserItems(items)
    }

    // Stats
    const statsResponse =
      tab === 0
        ? await knowledgeApi.getBusinessStats()
        : await knowledgeApi.getUserStats()

    if (tab === 0) {
      setBusinessStats(statsResponse.data)
    } else {
      setUserStats(statsResponse.data)
    }

    // Categories + briefs
    if (tab === 0) {
      const categoriesResponse =
        await knowledgeApi.getCategories('business')

      setCategories(categoriesResponse.data?.categories || [])

      const briefsResponse =
        await knowledgeApi.getBriefs('business')

      setBriefs(briefsResponse.data?.brief_ids || [])
    }
    if (tab === 1) {
      const userIdResponse = await knowledgeApi.getCategories('user')
      console.log('User IDs response:', userIdResponse)
      setUserIds(userIdResponse.data?.categories || [])
    }

  } catch (err) {
    setError('Ошибка загрузки данных: ' +
      (err.response?.data?.detail || err.message))
  } finally {
    setLoading(false)
  }
}

  const handleSearch = async () => {
    if (!searchQuery.trim()) return
    
    try {
      setSearching(true)
      const collection = activeTab === 0 ? 'business' : 'user'
      const response = await knowledgeApi.search(searchQuery, {
        top_k: 10,
        brief_id: formData.brief_id || undefined,
        category: formData.category !== 'general' ? formData.category : undefined,
        user_id: activeTab === 1 ? formData.user_id || undefined : undefined
      })
      setSearchResults(response.data?.sources || [])
    } catch (err) {
      setError('Ошибка поиска: ' + (err.response?.data?.detail || err.message))
    } finally {
      setSearching(false)
    }
  }
  
  const handleAddItem = () => {
    setDialogType('add')
    setSelectedItem(null)
    setFormData({
      text: '',
      category: 'general',
      title: '',
      brief_id: '',
      user_id: activeTab === 1 ? 'user_001' : ''
    })
    setOpenDialog(true)
  }
  
  const handleEditItem = (item) => {
    setDialogType('edit')
    setSelectedItem(item)
    setFormData({
      text: item.text || '',
      category: item.metadata?.category || 'general',
      title: item.metadata?.title || '',
      brief_id: item.metadata?.brief_id?.toString() || '',
      user_id: item.metadata?.user_id || ''
    })
    setOpenDialog(true)
  }
  
  const handleDeleteItem = async (itemId) => {
    if (!confirm('Вы уверены, что хотите удалить этот элемент?')) return
    
    try {
      const collection = activeTab === 0 ? 'business' : 'user'
      await knowledgeApi.deleteItem(itemId, collection)
      await fetchData() // Refresh data
    } catch (err) {
      setError('Ошибка удаления: ' + (err.response?.data?.detail || err.message))
    }
  }
  
  const handleSubmitForm = async () => {
    try {
      const collection = activeTab === 0 ? 'business' : 'user'
      const data = {
        text: formData.text,
        category: formData.category,
        title: formData.title || undefined,
        brief_id: formData.brief_id ? parseInt(formData.brief_id) : undefined,
        metadata: {}
      }
      
      if (activeTab === 1 && formData.user_id) {
        data.user_id = formData.user_id
      }
      
      if (dialogType === 'add') {
        if (activeTab === 0) {
          await knowledgeApi.addBusiness(data)
        } else {
          await knowledgeApi.addUser(data)
        }
      } else {
        await knowledgeApi.updateItem(selectedItem.id, data, collection)
      }
      
      setOpenDialog(false)
      await fetchData() // Refresh data
    } catch (err) {
      setError('Ошибка сохранения: ' + (err.response?.data?.detail || err.message))
    }
  }
  
  const handleSeedData = async () => {
    try {
      setLoading(true)
      await knowledgeApi.adminSeed(false)
      await fetchData()
      alert('Данные успешно добавлены')
    } catch (err) {
      setError('Ошибка добавления тестовых данных: ' + (err.response?.data?.detail || err.message))
    } finally {
      setLoading(false)
    }
  }
 // ── Excel upload ──────────────────────────────────────────────────────────

  const handleOpenExcelDialog = () => {
    setExcelFile(null)
    setExcelSuccess(null)
    setOpenExcelDialog(true)
  }

  const handleExcelFileChange = (e) => {
    const file = e.target.files?.[0]
    if (!file) return
    if (!file.name.endsWith('.xlsx')) {
      setError('Поддерживаются только файлы .xlsx')
      return
    }
    setExcelFile(file)
    setExcelSuccess(null)
  }

  const handleExcelUpload = async () => {
    if (!excelFile) return

    try {
      setExcelUploading(true)
      setError(null)

      const formData= new FormData()
      formData.append("file", excelFile, excelFile.name)

      const response = await knowledgeApi.addExcelProducts(formData)

      setExcelSuccess(
        `Успешно добавлено ${response.data.added_count} продуктов из файла «${excelFile.name}»`
      )
      await fetchData()
    } catch (err) {
      setError(
        'Ошибка загрузки Excel: ' + (err.response?.data?.detail || err.message)
      )
    } finally {
      setExcelUploading(false)
    }
  }

  const handleExcelClose = () => {
    if (excelUploading) return
    setOpenExcelDialog(false)
  }

  // ─────────────────────────────────────────────────────────────────────────
  
  const currentItems = activeTab === 0 ? businessItems : userItems
  const currentStats = activeTab === 0 ? businessStats : userStats
  
  return (
    <Box>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h4">
          База знаний
        </Typography>
        <Box>
          <Button
            startIcon={<Refresh />}
            onClick={() => fetchData()}
            sx={{ mr: 1 }}
          >
            Обновить
          </Button>
          <Button
            startIcon={<Add />}
            variant="contained"
            onClick={handleAddItem}
            sx={{ mr: 1 }}
          >
            Добавить
          </Button>
          {activeTab === 0 && (
            <Button
              startIcon={<TableChart />}
              variant="contained"
              color="success"
              onClick={handleOpenExcelDialog}
            >
              Загрузить Excel
            </Button>
          )}
          <Button
            startIcon={<Category />}
            variant="outlined"
            onClick={handleSeedData}
          >
            Тестовые данные
          </Button>
        </Box>
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 3 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      {/* Tabs */}
      <Paper sx={{ mb: 3 }}>
        <Tabs value={activeTab} onChange={(e, v) => {
          setActiveTab(v) 
          }}>
          <Tab label="Бизнес знания" />
          <Tab label="Пользовательские данные" />
        </Tabs>
      </Paper>

      {/* Search */}
      <Paper sx={{ p: 2, mb: 3 }}>
        <Grid container spacing={2} alignItems="center">
          <Grid item xs={12} md={6}>
            <TextField
              fullWidth
              label="Поиск"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
              InputProps={{
                endAdornment: (
                  <IconButton onClick={handleSearch} disabled={searching}>
                    {searching ? <CircularProgress size={20} /> : <Search />}
                  </IconButton>
                )
              }}
            />
          </Grid>
          <Grid item xs={12} md={3}>
            <FormControl fullWidth>
              <InputLabel>Категория</InputLabel>
              <Select
                value={formData.category}
                onChange={activeTab === 0 ?(
                (e) => setFormData({...formData, category: e.target.value}))
                :((e) => setFormData({...formData, user_id: e.target.value}))}
              >
                <MenuItem value="general">Общая</MenuItem>
                {activeTab === 0 ? ( 
                  categories.map(cat => (
                  <MenuItem key={cat} value={cat}>{cat}</MenuItem>
                ))):(user_ids.map(user_id=> (
                  <MenuItem key={user_id} value={user_id}>{user_id}</MenuItem>
                )))}
              </Select>
            </FormControl>
          </Grid>
          <Grid item xs={12} md={3}>
            <FormControl fullWidth>
              <InputLabel>Бриф</InputLabel>
              <Select
                value={formData.brief_id}
                onChange={(e) => setFormData({...formData, brief_id: e.target.value})}
              >
                <MenuItem value="">Все</MenuItem>
                {briefs.map(brief => (
                  <MenuItem key={brief} value={brief}>{brief}</MenuItem>
                ))}
              </Select>
            </FormControl>
          </Grid>
        </Grid>
        
        {/* Search Results */}
        {searchResults.length > 0 && (
          <Box mt={2}>
            <Typography variant="h6" gutterBottom>
              Результаты поиска ({searchResults.length})
            </Typography>
            <Grid container spacing={2}>
              {searchResults.map((result, index) => (
                <Grid item xs={12} md={6} key={index}>
                  <Card variant="outlined">
                    <CardContent>
                      <Typography variant="body2" gutterBottom>
                        <strong>Оценка:</strong> {(result.score * 100).toFixed(1)}%
                      </Typography>
                      <Typography variant="body2" paragraph>
                        {result.text}
                      </Typography>
                      <Box>
                        <Chip
                          size="small"
                          label={result.metadata?.category || 'general'}
                          sx={{ mr: 1 }}
                        />
                        <Chip
                          size="small"
                          label={result.collection}
                          color="secondary"
                        />
                      </Box>
                    </CardContent>
                  </Card>
                </Grid>
              ))}
            </Grid>
            <Divider sx={{ my: 2 }} />
          </Box>
        )}
      </Paper>

      {/* Stats */}
      {currentStats && (
        <Grid container spacing={3} mb={3}>
          <Grid item xs={12} md={3}>
            <Card>
              <CardContent>
                <Typography color="textSecondary" gutterBottom>
                  Всего документов
                </Typography>
                <Typography variant="h4">
                  {currentStats.total_documents}
                </Typography>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={12} md={4}>
            <Card>
              <CardContent>
                <Typography color="textSecondary" gutterBottom>
                  Категории
                </Typography>
                <Box display="flex" flexWrap="wrap" gap={0.5}>
                  {Object.entries(currentStats.categories || {}).map(([cat, count]) => (
                    <Chip key={cat} label={`${cat} (${count})`} size="small" />
                  ))}
                </Box>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={12} md={5}>
            <Card>
              <CardContent>
                <Typography color="textSecondary" gutterBottom>
                  Брифы
                </Typography>
                <Box display="flex" flexWrap="wrap" gap={0.5}>
                  {Object.entries(currentStats.briefs || {}).map(([brief, count]) => (
                    <Chip key={brief} label={`Бриф ${brief} (${count})`} size="small" color="primary" />
                  ))}
                </Box>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      )}

      {/* Items Grid */}
      {loading ? (
        <Box display="flex" justifyContent="center" mt={4}>
          <CircularProgress />
        </Box>
      ) : (
        <Grid container spacing={3}>
          {currentItems.map((item) => (
            <Grid item xs={12} md={6} lg={4} key={item.id}>
              <Card>
                <CardContent>
                  <Typography variant="h6" gutterBottom noWrap>
                    {item.metadata?.title || 'Без названия'}
                  </Typography>
                  <Typography variant="body2" color="textSecondary" paragraph>
                    {item.text?.substring(0, 200)}{item.text?.length > 200 ? '...' : ''}
                  </Typography>
                  <Box display="flex" flexWrap="wrap" gap={0.5} mb={1}>
                    <Chip
                      size="small"
                      label={item.metadata?.category || 'general'}
                    />
                    {item.metadata?.brief_id && (
                      <Chip
                        size="small"
                        label={`Бриф ${item.metadata.brief_id}`}
                        color="primary"
                      />
                    )}
                    {item.metadata?.user_id && (
                      <Chip
                        size="small"
                        label={item.metadata.user_id}
                        color="secondary"
                      />
                    )}
                  </Box>
                </CardContent>
                <CardActions>
                  <IconButton
                    size="small"
                    onClick={() => handleEditItem(item)}
                  >
                    <Edit fontSize="small" />
                  </IconButton>
                  <IconButton
                    size="small"
                    onClick={() => handleDeleteItem(item.id)}
                  >
                    <Delete fontSize="small" />
                  </IconButton>
                </CardActions>
              </Card>
            </Grid>
          ))}
        </Grid>
      )}

      {/* Add/Edit Dialog */}
      <Dialog open={openDialog} onClose={() => setOpenDialog(false)} maxWidth="md" fullWidth>
        <DialogTitle>
          {dialogType === 'add' ? 'Добавить элемент' : 'Редактировать элемент'}
        </DialogTitle>
        <DialogContent>
          <Grid container spacing={2} sx={{ mt: 1 }}>
            <Grid item xs={12}>
              <TextField
                fullWidth
                label="Название"
                value={formData.title}
                onChange={(e) => setFormData({...formData, title: e.target.value})}
              />
            </Grid>
            <Grid item xs={12}>
              <TextField
                fullWidth
                multiline
                rows={4}
                label="Текст"
                value={formData.text}
                onChange={(e) => setFormData({...formData, text: e.target.value})}
                required
              />
            </Grid>
            <Grid item xs={12} md={6}>
              <FormControl fullWidth>
                <InputLabel>Категория</InputLabel>
                <Select
                  value={formData.category}
                  onChange={(e) => setFormData({...formData, category: e.target.value})}
                >
                  <MenuItem value="general">Общая</MenuItem>
                  <MenuItem value="faq">FAQ</MenuItem>
                  <MenuItem value="product">Продукт</MenuItem>
                  <MenuItem value="price">Цена</MenuItem>
                  <MenuItem value="company">Компания</MenuItem>
                  <MenuItem value="objection">Возражение</MenuItem>
                  <MenuItem value="usp">USP</MenuItem>
                </Select>
              </FormControl>
            </Grid>
            <Grid item xs={12} md={6}>
              <TextField
                fullWidth
                label="ID брифа"
                value={formData.brief_id}
                onChange={(e) => setFormData({...formData, brief_id: e.target.value})}
                type="number"
              />
            </Grid>
            {activeTab === 1 && (
              <Grid item xs={12}>
                <TextField
                  fullWidth
                  label="ID пользователя"
                  value={formData.user_id}
                  onChange={(e) => setFormData({...formData, user_id: e.target.value})}
                  required
                />
              </Grid>
            )}
          </Grid>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpenDialog(false)}>
            Отмена
          </Button>
          <Button
            onClick={handleSubmitForm}
            variant="contained"
            disabled={!formData.text.trim()}
          >
            {dialogType === 'add' ? 'Добавить' : 'Сохранить'}
          </Button>
        </DialogActions>
      </Dialog>
      {/* ── Excel Upload Dialog ───────────────────────────────────────────── */}
      <Dialog open={openExcelDialog} onClose={handleExcelClose} maxWidth="sm" fullWidth>
        <DialogTitle sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <TableChart color="success" />
          Загрузка продуктов из Excel
        </DialogTitle>

        <DialogContent>
          <Typography variant="body2" color="textSecondary" sx={{ mb: 3 }}>
            Файл должен быть в формате <strong>.xlsx</strong>. Колонки: <em>Название</em>,{' '}
            <em>Описание</em>, <em>Цена</em> (начиная со 2-й строки).
          </Typography>

          {/* File drop zone */}
          <Box
            onClick={() => !excelUploading && fileInputRef.current?.click()}
            sx={{
              border: '2px dashed',
              borderColor: excelFile ? 'success.main' : 'divider',
              borderRadius: 2,
              p: 4,
              textAlign: 'center',
              cursor: excelUploading ? 'not-allowed' : 'pointer',
              bgcolor: excelFile ? 'success.50' : 'action.hover',
              transition: 'all 0.2s',
              '&:hover': {
                borderColor: excelUploading ? 'divider' : 'primary.main',
                bgcolor: excelUploading ? 'action.hover' : 'action.selected'
              }
            }}
          >
            <input
              ref={fileInputRef}
              type="file"
              accept=".xlsx"
              style={{ display: 'none' }}
              onChange={handleExcelFileChange}
            />
            {excelFile ? (
              <Box>
                <CheckCircle color="success" sx={{ fontSize: 40, mb: 1 }} />
                <Typography variant="subtitle1" fontWeight="bold">
                  {excelFile.name}
                </Typography>
                <Typography variant="body2" color="textSecondary">
                  {(excelFile.size / 1024).toFixed(1)} KB — нажмите, чтобы заменить
                </Typography>
              </Box>
            ) : (
              <Box>
                <UploadFile sx={{ fontSize: 40, mb: 1, color: 'text.secondary' }} />
                <Typography variant="subtitle1">
                  Нажмите для выбора файла
                </Typography>
                <Typography variant="body2" color="textSecondary">
                  Поддерживается только .xlsx
                </Typography>
              </Box>
            )}
          </Box>

          {/* Upload progress */}
          {excelUploading && (
            <Box sx={{ mt: 3 }}>
              <Typography variant="body2" color="textSecondary" gutterBottom>
                Загрузка и обработка файла…
              </Typography>
              <LinearProgress />
            </Box>
          )}

          {/* Success message */}
          {excelSuccess && (
            <Alert severity="success" sx={{ mt: 3 }} icon={<CheckCircle />}>
              {excelSuccess}
            </Alert>
          )}
        </DialogContent>

        <DialogActions>
          <Button onClick={handleExcelClose} disabled={excelUploading}>
            {excelSuccess ? 'Закрыть' : 'Отмена'}
          </Button>
          <Button
            onClick={handleExcelUpload}
            variant="contained"
            color="success"
            startIcon={excelUploading ? <CircularProgress size={18} color="inherit" /> : <UploadFile />}
            disabled={!excelFile || excelUploading}
          >
            {excelUploading ? 'Загружается…' : 'Загрузить'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  )
}
