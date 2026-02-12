/**
 * Composable for user-facing notifications
 * 
 * Provides toast notifications for order submissions, errors,
 * and other important user feedback.
 */

export type NotificationType = 'success' | 'error' | 'warning' | 'info'

export interface Notification {
  id: string
  type: NotificationType
  title: string
  message?: string
  duration: number
  timestamp: number
  dismissible: boolean
}

export interface NotificationOptions {
  title: string
  message?: string
  duration?: number
  dismissible?: boolean
}

const DEFAULT_DURATIONS: Record<NotificationType, number> = {
  success: 5000,
  error: 10000,   // Errors stay longer
  warning: 7000,
  info: 5000,
}

export const useNotifications = () => {
  const notifications = useState<Notification[]>('notifications', () => [])
  
  const generateId = (): string => {
    return `notif-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`
  }
  
  const addNotification = (type: NotificationType, options: NotificationOptions): string => {
    const id = generateId()
    const notification: Notification = {
      id,
      type,
      title: options.title,
      message: options.message,
      duration: options.duration ?? DEFAULT_DURATIONS[type],
      timestamp: Date.now(),
      dismissible: options.dismissible ?? true,
    }
    
    notifications.value.push(notification)
    
    // Auto-remove after duration
    if (notification.duration > 0) {
      setTimeout(() => {
        removeNotification(id)
      }, notification.duration)
    }
    
    return id
  }
  
  const removeNotification = (id: string): void => {
    const index = notifications.value.findIndex(n => n.id === id)
    if (index !== -1) {
      notifications.value.splice(index, 1)
    }
  }
  
  const clearAll = (): void => {
    notifications.value = []
  }
  
  // Convenience methods
  const success = (options: NotificationOptions | string): string => {
    const opts = typeof options === 'string' ? { title: options } : options
    return addNotification('success', opts)
  }
  
  const error = (options: NotificationOptions | string): string => {
    const opts = typeof options === 'string' ? { title: options } : options
    return addNotification('error', opts)
  }
  
  const warning = (options: NotificationOptions | string): string => {
    const opts = typeof options === 'string' ? { title: options } : options
    return addNotification('warning', opts)
  }
  
  const info = (options: NotificationOptions | string): string => {
    const opts = typeof options === 'string' ? { title: options } : options
    return addNotification('info', opts)
  }
  
  // Specific trading notifications
  const orderSubmitted = (pair: string, side: string, size: string): string => {
    return success({
      title: 'Order Submitted',
      message: `${side.toUpperCase()} ${size} ${pair}`,
    })
  }
  
  const orderFailed = (errorMessage: string): string => {
    return error({
      title: 'Order Failed',
      message: errorMessage,
      duration: 15000, // Stay longer for errors
    })
  }
  
  const orderFilled = (pair: string, side: string, price: string): string => {
    return success({
      title: 'Order Filled',
      message: `${side.toUpperCase()} ${pair} @ ${price}`,
    })
  }
  
  const positionClosed = (pair: string, pnl: string): string => {
    const isProfit = !pnl.startsWith('-')
    const type = isProfit ? 'success' : 'warning'
    return addNotification(type, {
      title: 'Position Closed',
      message: `${pair}: ${isProfit ? '+' : ''}${pnl}`,
    })
  }
  
  const connectionError = (service: string): string => {
    return error({
      title: 'Connection Error',
      message: `Failed to connect to ${service}. Retrying...`,
    })
  }
  
  const riskLimitWarning = (message: string): string => {
    return warning({
      title: 'Risk Limit Warning',
      message,
      duration: 10000,
    })
  }
  
  const validationError = (message: string): string => {
    return error({
      title: 'Validation Error',
      message,
    })
  }
  
  return {
    // State
    notifications: readonly(notifications),
    
    // Generic methods
    addNotification,
    removeNotification,
    clearAll,
    
    // Convenience methods
    success,
    error,
    warning,
    info,
    
    // Trading-specific notifications
    orderSubmitted,
    orderFailed,
    orderFilled,
    positionClosed,
    connectionError,
    riskLimitWarning,
    validationError,
  }
}
