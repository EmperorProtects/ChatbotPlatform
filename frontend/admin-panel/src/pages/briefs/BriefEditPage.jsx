import React, { useState, useEffect } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import {
  Box,
  Paper,
  Typography,
  TextField,
  Button,
  Grid,
  MenuItem,
  Divider,
  Alert,
  CircularProgress,
  Card,
  CardContent,
  CardHeader,
  Chip,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  List,
  ListItem,
  ListItemText,
  ListItemSecondaryAction,
  Tabs,
  Tab,
  Accordion,
  AccordionSummary,
  AccordionDetails
} from '@mui/material'
import { 
  Save, 
  ArrowBack, 
  Add, 
  Edit, 
  Delete, 
  ExpandMore, 
  Visibility,
  Psychology,
  Business,
  Groups,
  Schema,
} from '@mui/icons-material'
import { knowledgeApi } from '../../services/api'

export default function BriefEditPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const isNew = id === 'new'
  const [activeTab, setActiveTab] = useState(0)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [success, setSuccess] = useState(null)
  
  // Brief data
  const [formData, setFormData] = useState({
    company_name: '',
    contact_phone: '',
    manager_name: '',
    business_type: 'B2C',
    business_description: '',
    products: [],
    target_audience: '',
    usp: '',
    communication_style: 'friendly',
    objections: [],
    faq: [],
    company_info: '',
    brief_id: '',
    system_prompt:[], 
  })
  
  // Knowledge items related to this brief
  const [knowledgeItems, setKnowledgeItems] = useState([])
  const [knowledgeStats, setKnowledgeStats] = useState(null)
  
  // Dialog states
  const [productDialog, setProductDialog] = useState({ open: false, editing: null })
  const [objectionDialog, setObjectionDialog] = useState({ open: false, editing: null })
  const [faqDialog, setFaqDialog] = useState({ open: false, editing: null })
  
  // Form states for dialogs
  const [productForm, setProductForm] = useState({ name: '', description: '', price: '' })
  const [objectionForm, setObjectionForm] = useState({ text: '', response: '' })
  const [faqForm, setFaqForm] = useState({ question: '', answer: '' })

  //prompt page
  const [promptForm, setPromptForm] = useState({ type: 'message', content: '' })

  useEffect(() => {
    if (!isNew) {
      loadBriefData()
      loadKnowledgeItems()
    }
  }, [id, isNew])



  
  
  const loadBriefData = async () => {
    try {
      setLoading(true)
      // Load brief data from knowledge items
      const response = await knowledgeApi.listItems({ 
        which: 'business', 
        brief_id: parseInt(id),
        limit: 100 
      })
      
      if (response.data?.items) {
        // Parse knowledge items to reconstruct brief data
        const items = response.data.items
        const brief = {
          company_name: await getBriefName(id),
          contact_phone: '+7 (XXX) XXX-XX-XX',
          manager_name: 'Менеджер',
          business_type: 'B2C',
          business_description: '',
          products: [],
          target_audience: '',
          usp: '',
          communication_style: 'friendly',
          objections: [],
          faq: [],
          company_info: '',
          system_prompt: [],
          brief_id: parseInt(id),
        }
        
        // Extract data from knowledge items
        items.forEach(item => {
          const category = item.metadata?.category || 'general'
          const title = item.metadata?.title || ''
          const text = item.text || ''
          
          switch (category) {
            case 'system_prompt':
              brief.system_prompt = text.split("\n")
            case 'company':
              brief.business_description = text
              brief.company_info = text
              break
            case 'product':
              const productMatch = text.match(/^(.*?):\s*(.*?)\s*-\s*(.*?)$/)
              if (productMatch) {
                brief.products.push({
                  id: Date.now() + Math.random(),
                  name: productMatch[1],
                  description: productMatch[2],
                  price: productMatch[3]
                })
              }
              break
            case 'usp':
              brief.usp = text.replace('Уникальное торговое предложение: ', '')
              break
            case 'objection':
              const objectionMatch = text.match(/^Возражение: (.*?)\. Ответ: (.*)$/)
              if (objectionMatch) {
                brief.objections.push({
                  id: Date.now() + Math.random(),
                  text: objectionMatch[1],
                  response: objectionMatch[2]
                })
              }
              break
            case 'faq':
              const faqLines = text.split('\n')
              if (faqLines.length >= 2) {
                brief.faq.push({
                  id: Date.now() + Math.random(),
                  question: faqLines[0],
                  answer: faqLines[1]
                })
              }
              break
          }
        })
        
        setFormData(brief)
      }
    } catch (err) {
      console.error('Error loading brief:', err)
      setError('Ошибка загрузки брифа')
    } finally {
      setLoading(false)
    }
  }
  
  const loadKnowledgeItems = async () => {
    try {
      const [itemsResponse, statsResponse] = await Promise.all([
        knowledgeApi.listItems({ which: 'business', brief_id: parseInt(id), limit: 100 }),
        knowledgeApi.getBusinessStats()
      ])
      
      setKnowledgeItems(itemsResponse.data?.items || [])
      setKnowledgeStats(statsResponse.data)
    } catch (err) {
      console.error('Error loading knowledge items:', err)
    }
  }
  
  const getBriefName = async (briefId) => {
    // const briefNames = {
    //
    const r = await knowledgeApi.getBriefs('business')
    const company_names = r.data?.company_names || {}
    console.log('Available brief names:', company_names)
    //   '1': 'Hongqi Auto',
    //   '2': 'CoffeeBar',
    //   '3': 'Tech Solutions'
    // }
    return company_names[briefId] || `Бриф #${briefId}`
  }

  const handleChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value,
    })
  }
  
  // Product management
  const handleAddProduct = () => {
    setProductForm({ name: '', description: '', price: '' })
    setProductDialog({ open: true, editing: null })
  }
  
  const handleEditProduct = (product) => {
    setProductForm(product)
    setProductDialog({ open: true, editing: product })
  }
  
  const handleSaveProduct = () => {
    const products = [...formData.products]
    if (productDialog.editing) {
      const index = products.findIndex(p => p.id === productDialog.editing.id)
      products[index] = { ...productForm, id: productDialog.editing.id }
    } else {
      products.push({ ...productForm, id: Date.now() })
    }
    setFormData({ ...formData, products })
    setProductDialog({ open: false, editing: null })
  }
  
  const handleDeleteProduct = (productId) => {
    setFormData({
      ...formData,
      products: formData.products.filter(p => p.id !== productId)
    })
  }
  
  // Similar handlers for objections and FAQ
  const handleAddObjection = () => {
    setObjectionForm({ text: '', response: '' })
    setObjectionDialog({ open: true, editing: null })
  }
  
  const handleSaveObjection = () => {
    const objections = [...formData.objections]
    if (objectionDialog.editing) {
      const index = objections.findIndex(o => o.id === objectionDialog.editing.id)
      objections[index] = { ...objectionForm, id: objectionDialog.editing.id }
    } else {
      objections.push({ ...objectionForm, id: Date.now() })
    }
    setFormData({ ...formData, objections })
    setObjectionDialog({ open: false, editing: null })
  }
  
  const handleAddFaq = () => {
    setFaqForm({ question: '', answer: '' })
    setFaqDialog({ open: true, editing: null })
  }

  
  const handleSaveFaq = () => {
    const faq = [...formData.faq]
    if (faqDialog.editing) {
      const index = faq.findIndex(f => f.id === faqDialog.editing.id)
      faq[index] = { ...faqForm, id: faqDialog.editing.id }
    } else {
      faq.push({ ...faqForm, id: Date.now() })
    }
    setFormData({ ...formData, faq })
    setFaqDialog({ open: false, editing: null })
  }

  const handleAddPrompt = () => {
    setFormData({...formData, system_prompt: [...formData.system_prompt, ''] })
    // formData.system_prompt.push('')
    // setPromptForm({ type: 'message', content: '' })
  }
  
  const handleEditPrompt = (index,value) => {
    setFormData(prev=> {
      const newPrompts = [...prev.system_prompt]
      newPrompts[index] = value
      return {...prev, system_prompt: newPrompts}
    })
    console.log('Updated system prompts:', formData.system_prompt)
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    
    try {
      setLoading(true)
      setError(null)
      
      // Create knowledge items from form data
      const knowledgeItems = []
      
      // Company info
      if (formData.business_description) {
        knowledgeItems.push({
          text: formData.business_description,
          category: 'company',
          title: 'Company Description',
          company_name:formData.company_name,
          brief_id: formData.brief_id, 
        })
      }

      if(formData.company_info){
        knowledgeItems.push({
          text: formData.company_info,
          category: 'company',
          title: 'Company info',
          company_name:formData.company_name,
          brief_id: formData.brief_id
        
        })
      }
      
      
      // Products
      formData.products.forEach(product => {
        knowledgeItems.push({
          text: `${product.name}: ${product.description} - ${product.price}`,
          category: 'product',
          title: product.name,
          company_name:formData.company_name,
          brief_id: formData.brief_id
        })
      })
      
      // USP
      if (formData.usp) {
        knowledgeItems.push({
          text: `Уникальное торговое предложение: ${formData.usp}`,
          category: 'usp',
          title: 'USP',
          company_name:formData.company_name,
          brief_id: formData.brief_id
        })
      }
      
      // Objections
      formData.objections.forEach(objection => {
        knowledgeItems.push({
          text: `Возражение: ${objection.text}. Ответ: ${objection.response}`,
          category: 'objection',
          title: objection.text,
          company_name:formData.company_name,
          brief_id: formData.brief_id
        })
      })
      
      // FAQ
      formData.faq.forEach(item => {
        knowledgeItems.push({
          text: `${item.question}\n${item.answer}`,
          category: 'faq',
          title: item.question,
          company_name:formData.company_name,
          brief_id: formData.brief_id
        })
      })
      const system_prompt = formData.system_prompt.filter(line => line.trim() !== '').join("\n")
      knowledgeItems.push({
        text: system_prompt,
        category: 'system_prompt',
        title: 'System Prompt',
        company_name:formData.company_name,
        brief_id: formData.brief_id
      })
        
      
      
      // Save to knowledge base
      if (knowledgeItems.length > 0) {
        console.log('Saving knowledge items:', knowledgeItems)
        await knowledgeApi.deleteBrief(formData.brief_id)
        await knowledgeApi.bulkAddBusiness({ items: knowledgeItems })
      }
      
      setSuccess('Бриф успешно сохранен!')
      
      setTimeout(() => {
        navigate('/briefs')
      }, 2000)
      
    } catch (err) {
      console.error('Error saving brief:', err)
      setError('Ошибка сохранения брифа: ' + (err.response?.data?.detail || err.message))
    } finally {
      setLoading(false)
    }
  }

  if (loading && !formData.company_name) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="50vh">
        <CircularProgress />
      </Box>
    )
  }

  return (
    <Box>
      <Button
        startIcon={<ArrowBack />}
        onClick={() => navigate('/briefs')}
        sx={{ mb: 2 }}
      >
        Назад к брифам
      </Button>

      {error && (
        <Alert severity="error" sx={{ mb: 3 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}
      
      {success && (
        <Alert severity="success" sx={{ mb: 3 }}>
          {success}
        </Alert>
      )}

      <Paper sx={{ mb: 3 }}>
        <Tabs value={activeTab} onChange={(e, v) => setActiveTab(v)}>
          <Tab label="Основное" icon={<Business />} iconPosition="start" />
          <Tab label="Продукты" icon={<Visibility />} iconPosition="start" />
          <Tab label="Возражения & FAQ" icon={<Psychology />} iconPosition="start" />
          <Tab label="Flow Engine" icon={<Schema />} iconPosition="start" />
          {!isNew && <Tab label="База знаний" icon={<Groups />} iconPosition="start" />}
        </Tabs>
      </Paper>

      <Paper sx={{ p: 3 }}>
        <Typography variant="h5" gutterBottom>
          {isNew ? 'Новый бриф' : `Редактирование брифа "${formData.company_name}"`}
        </Typography>

        <Box component="form" onSubmit={handleSubmit} sx={{ mt: 3 }}>
          {/* Basic Information Tab */}
          {activeTab === 0 && (
            <>
              <Card sx={{ mb: 3 }}>
                <CardHeader title="1. Основная информация" />
                <CardContent>
                  <Grid container spacing={3}>
                    <Grid item xs={12} md={6}>
                      <TextField
                        fullWidth
                        label="Название компании"
                        name="company_name"
                        value={formData.company_name}
                        onChange={handleChange}
                        required
                      />
                    </Grid>
                    
                    <Grid item xs={12} md={6}>
                      <TextField
                        fullWidth
                        label="Контактный телефон"
                        name="contact_phone"
                        value={formData.contact_phone}
                        onChange={handleChange}
                        required
                      />
                    </Grid>
                    
                    <Grid item xs={12} md={6}>
                      <TextField
                        fullWidth
                        label="Имя менеджера"
                        name="manager_name"
                        value={formData.manager_name}
                        onChange={handleChange}
                        required
                      />
                    </Grid>
                    
                    <Grid item xs={12} md={6}>
                      <TextField
                        fullWidth
                        select
                        label="Тип бизнеса"
                        name="business_type"
                        value={formData.business_type}
                        onChange={handleChange}
                      >
                        <MenuItem value="B2C">B2C</MenuItem>
                        <MenuItem value="B2B">B2B</MenuItem>
                        <MenuItem value="B2B+B2C">B2B + B2C</MenuItem>
                      </TextField>
                    </Grid>
                                        
                    <Grid item xs={12} md={6}>
                      <TextField
                        fullWidth
                        label="Бриф ID (для связи с базой знаний)"
                        name="brief_id"
                        value={formData.brief_id}
                        onChange={handleChange}
                      />
                    </Grid>

                  </Grid>
                </CardContent>
              </Card>

              <Card sx={{ mb: 3 }}>
                <CardHeader title="2. Описание бизнеса" />
                <CardContent>
                  <Grid container spacing={3}>
                    <Grid item xs={12}>
                      <TextField
                        fullWidth
                        multiline
                        rows={4}
                        label="Чем занимается компания"
                        name="business_description"
                        value={formData.business_description}
                        onChange={handleChange}
                        required
                      />
                    </Grid>
                    
                    <Grid item xs={12}>
                      <TextField
                        fullWidth
                        multiline
                        rows={3}
                        label="Целевая аудитория"
                        name="target_audience"
                        value={formData.target_audience}
                        onChange={handleChange}
                      />
                    </Grid>
                    
                    <Grid item xs={12}>
                      <TextField
                        fullWidth
                        multiline
                        rows={3}
                        label="УТП (уникальное торговое предложение)"
                        name="usp"
                        value={formData.usp}
                        onChange={handleChange}
                      />
                    </Grid>
                  </Grid>
                </CardContent>
              </Card>

              <Card>
                <CardHeader title="3. Настройки бота" />
                <CardContent>
                  <Grid container spacing={3}>
                    <Grid item xs={12} md={6}>
                      <TextField
                        fullWidth
                        select
                        label="Стиль общения"
                        name="communication_style"
                        value={formData.communication_style}
                        onChange={handleChange}
                      >
                        <MenuItem value="formal">Формальный</MenuItem>
                        <MenuItem value="neutral">Нейтральный</MenuItem>
                        <MenuItem value="friendly">Дружелюбный</MenuItem>
                      </TextField>
                    </Grid>
                  </Grid>
                </CardContent>
              </Card>
            </>
          )}

          {/* Products Tab */}
          {activeTab === 1 && (
            <Card>
              <CardHeader 
                title="Продукты и услуги"
                action={
                  <Button startIcon={<Add />} onClick={handleAddProduct}>
                    Добавить
                  </Button>
                }
              />
              <CardContent>
                {formData.products.length === 0 ? (
                  <Typography color="textSecondary" align="center" sx={{ py: 4 }}>
                    Нет добавленных продуктов
                  </Typography>
                ) : (
                  <List>
                    {formData.products.map((product, index) => (
                      <ListItem key={product.id} divider={index < formData.products.length - 1}>
                        <ListItemText
                          primary={product.name}
                          secondary={`${product.description} - ${product.price}`}
                        />
                        <ListItemSecondaryAction>
                          <IconButton onClick={() => handleEditProduct(product)}>
                            <Edit />
                          </IconButton>
                          <IconButton onClick={() => handleDeleteProduct(product.id)} color="error">
                            <Delete />
                          </IconButton>
                        </ListItemSecondaryAction>
                      </ListItem>
                    ))}
                  </List>
                )}
              </CardContent>
            </Card>
          )}

          {/* Objections & FAQ Tab */}
          {activeTab === 2 && (
            <>
              <Card sx={{ mb: 3 }}>
                <CardHeader 
                  title="Возражения"
                  action={
                    <Button startIcon={<Add />} onClick={handleAddObjection}>
                      Добавить
                    </Button>
                  }
                />
                <CardContent>
                  {formData.objections.length === 0 ? (
                    <Typography color="textSecondary" align="center" sx={{ py: 2 }}>
                      Нет добавленных возражений
                    </Typography>
                  ) : (
                    formData.objections.map((objection, index) => (
                      <Accordion key={objection.id}>
                        <AccordionSummary expandIcon={<ExpandMore />}>
                          <Typography>{objection.text}</Typography>
                        </AccordionSummary>
                        <AccordionDetails>
                          <Box display="flex" justifyContent="space-between" alignItems="flex-start">
                            <Typography variant="body2">
                              {objection.response}
                            </Typography>
                            <Box>
                              <IconButton size="small" onClick={() => {
                                setObjectionForm(objection)
                                setObjectionDialog({ open: true, editing: objection })
                              }}>
                                <Edit fontSize="small" />
                              </IconButton>
                              <IconButton size="small" color="error" onClick={() => {
                                setFormData({
                                  ...formData,
                                  objections: formData.objections.filter(o => o.id !== objection.id)
                                })
                              }}>
                                <Delete fontSize="small" />
                              </IconButton>
                            </Box>
                          </Box>
                        </AccordionDetails>
                      </Accordion>
                    ))
                  )}
                </CardContent>
              </Card>

              <Card>
                <CardHeader 
                  title="FAQ (часто задаваемые вопросы)"
                  action={
                    <Button startIcon={<Add />} onClick={handleAddFaq}>
                      Добавить
                    </Button>
                  }
                />
                <CardContent>
                  {formData.faq.length === 0 ? (
                    <Typography color="textSecondary" align="center" sx={{ py: 2 }}>
                      Нет добавленных вопросов
                    </Typography>
                  ) : (
                    formData.faq.map((item) => (
                      <Accordion key={item.id}>
                        <AccordionSummary expandIcon={<ExpandMore />}>
                          <Typography>{item.question}</Typography>
                        </AccordionSummary>
                        <AccordionDetails>
                          <Box display="flex" justifyContent="space-between" alignItems="flex-start">
                            <Typography variant="body2">
                              {item.answer}
                            </Typography>
                            <Box>
                              <IconButton size="small" onClick={() => {
                                setFaqForm(item)
                                setFaqDialog({ open: true, editing: item })
                              }}>
                                <Edit fontSize="small" />
                              </IconButton>
                              <IconButton size="small" color="error" onClick={() => {
                                setFormData({
                                  ...formData,
                                  faq: formData.faq.filter(f => f.id !== item.id)
                                })
                              }}>
                                <Delete fontSize="small" />
                              </IconButton>
                            </Box>
                          </Box>
                        </AccordionDetails>
                      </Accordion>
                    ))
                  )}
                </CardContent>
              </Card>
            </>
          )}
          

          {activeTab === 3 && (
            <Card>
              <CardHeader title="Конструктор Промпта"
                action={
                  <Button startIcon={<Add/>} onClick={() => {handleAddPrompt()}}>
                    Добавить элемент
                  </Button>
                }
              />
              <CardContent>
                {formData.system_prompt.length === 0  ? (
                <Typography variant="body1" sx={{ whiteSpace: 'pre-wrap' }}>
                  Системный промпт не задан
                </Typography>
                ):(
                  <Grid container direction="column" >
                  {formData.system_prompt.map((item, index) => (
                    <Grid item xs ={12} key={index} sx={{ m: 1 }}>
                        <TextField value={item} fullWidth onChange={(e) => handleEditPrompt(index, e.target.value)}/>
                              <IconButton size="small" color="error" onClick={() => {
                                setFormData({
                                  ...formData,
                                  system_prompt: formData.system_prompt.filter((_, i) => i !== index)
                                })
                              }}>
                                <Delete fontSize="small" />
                              </IconButton>
                    </Grid>    

                  ))}
                  </Grid>
                )}
              </CardContent>
                
            </Card>
          )}
          {/* Knowledge Base Tab */}
          {!isNew && activeTab === 4 && (
            <Card>
              <CardHeader title="Связанные элементы базы знаний" />
              <CardContent>
                {knowledgeItems.length === 0 ? (
                  <Typography color="textSecondary" align="center" sx={{ py: 4 }}>
                    Нет связанных элементов знаний
                  </Typography>
                ) : (
                  <Grid container spacing={2}>
                    {knowledgeItems.map((item) => (
                      <Grid item xs={12} md={6} key={item.id}>
                        <Paper sx={{ p: 2 }} variant="outlined">
                          <Box display="flex" justifyContent="space-between" alignItems="flex-start" mb={1}>
                            <Chip
                              label={item.metadata?.category || 'general'}
                              size="small"
                              color="primary"
                            />
                            <Typography variant="caption" color="textSecondary">
                              {item.metadata?.title}
                            </Typography>
                          </Box>
                          <Typography variant="body2">
                            {item.text?.substring(0, 150)}
                            {item.text?.length > 150 ? '...' : ''}
                          </Typography>
                        </Paper>
                      </Grid>
                    ))}
                  </Grid>
                )}
              </CardContent>
            </Card>
          )}

          <Box sx={{ mt: 4, display: 'flex', gap: 2 }}>
            <Button
              type="submit"
              variant="contained"
              startIcon={<Save />}
              disabled={loading}
              size="large"
            >
              {loading ? 'Сохранение...' : 'Сохранить бриф'}
            </Button>
            <Button
              variant="outlined"
              onClick={() => navigate('/briefs')}
              disabled={loading}
              size="large"
            >
              Отмена
            </Button>
          </Box>
        </Box>
      </Paper>

      {/* Dialogs */}
      <Dialog open={productDialog.open} onClose={() => setProductDialog({ open: false, editing: null })} maxWidth="md" fullWidth>
        <DialogTitle>
          {productDialog.editing ? 'Редактировать продукт' : 'Добавить продукт'}
        </DialogTitle>
        <DialogContent>
          <Grid container spacing={2} sx={{ mt: 1 }}>
            <Grid item xs={12}>
              <TextField
                fullWidth
                label="Название"
                value={productForm.name}
                onChange={(e) => setProductForm({ ...productForm, name: e.target.value })}
              />
            </Grid>
            <Grid item xs={12}>
              <TextField
                fullWidth
                multiline
                rows={3}
                label="Описание"
                value={productForm.description}
                onChange={(e) => setProductForm({ ...productForm, description: e.target.value })}
              />
            </Grid>
            <Grid item xs={12}>
              <TextField
                fullWidth
                label="Цена"
                value={productForm.price}
                onChange={(e) => setProductForm({ ...productForm, price: e.target.value })}
              />
            </Grid>
          </Grid>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setProductDialog({ open: false, editing: null })}>
            Отмена
          </Button>
          <Button onClick={handleSaveProduct} variant="contained">
            Сохранить
          </Button>
        </DialogActions>
      </Dialog>

      <Dialog open={objectionDialog.open} onClose={() => setObjectionDialog({ open: false, editing: null })} maxWidth="md" fullWidth>
        <DialogTitle>
          {objectionDialog.editing ? 'Редактировать возражение' : 'Добавить возражение'}
        </DialogTitle>
        <DialogContent>
          <Grid container spacing={2} sx={{ mt: 1 }}>
            <Grid item xs={12}>
              <TextField
                fullWidth
                label="Возражение"
                value={objectionForm.text}
                onChange={(e) => setObjectionForm({ ...objectionForm, text: e.target.value })}
              />
            </Grid>
            <Grid item xs={12}>
              <TextField
                fullWidth
                multiline
                rows={4}
                label="Ответ на возражение"
                value={objectionForm.response}
                onChange={(e) => setObjectionForm({ ...objectionForm, response: e.target.value })}
              />
            </Grid>
          </Grid>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setObjectionDialog({ open: false, editing: null })}>
            Отмена
          </Button>
          <Button onClick={handleSaveObjection} variant="contained">
            Сохранить
          </Button>
        </DialogActions>
      </Dialog>

      <Dialog open={faqDialog.open} onClose={() => setFaqDialog({ open: false, editing: null })} maxWidth="md" fullWidth>
        <DialogTitle>
          {faqDialog.editing ? 'Редактировать FAQ' : 'Добавить FAQ'}
        </DialogTitle>
        <DialogContent>
          <Grid container spacing={2} sx={{ mt: 1 }}>
            <Grid item xs={12}>
              <TextField
                fullWidth
                label="Вопрос"
                value={faqForm.question}
                onChange={(e) => setFaqForm({ ...faqForm, question: e.target.value })}
              />
            </Grid>
            <Grid item xs={12}>
              <TextField
                fullWidth
                multiline
                rows={4}
                label="Ответ"
                value={faqForm.answer}
                onChange={(e) => setFaqForm({ ...faqForm, answer: e.target.value })}
              />
            </Grid>
          </Grid>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setFaqDialog({ open: false, editing: null })}>
            Отмена
          </Button>
          <Button onClick={handleSaveFaq} variant="contained">
            Сохранить
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  )
}
