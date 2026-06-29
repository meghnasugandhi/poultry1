export interface User {
  id: number
  email: string
  owner_name: string
  farm_name: string
  mobile_number: string
  state: string
  district: string
  address: string
  profile_photo: string | null
  farm_type: string
  total_capacity: number
  current_bird_count: number
  preferred_language: string
  preferred_theme: 'light' | 'dark'
  voice_enabled: boolean
  notifications_enabled: boolean
}

export interface DashboardData {
  total_birds: number
  feed_stock: number
  medicine_stock: number
  vaccine_stock: number
  monthly_revenue: number
  monthly_expenses: number
  profit_loss: number
  farm_name: string
  owner_name: string
}

export interface InventoryItem {
  id: number
  category: string
  product_name: string
  quantity: number
  unit: string
  is_low_stock: boolean
  is_expiring_soon: boolean
}

export interface ChatMessage {
  id?: number
  role: 'user' | 'assistant'
  content: string
}
