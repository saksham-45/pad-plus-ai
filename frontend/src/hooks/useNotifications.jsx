import { useState, useCallback, createContext, useContext, useEffect } from 'react';

// Контекст для уведомлений
const NotificationContext = createContext(null);

// Типы уведомлений
const NOTIFICATION_TYPES = {
  SUCCESS: 'success',
  ERROR: 'error',
  WARNING: 'warning',
  INFO: 'info',
};

// Позиции для уведомлений
const POSITIONS = {
  TOP_RIGHT: 'top-right',
  TOP_LEFT: 'top-left',
  BOTTOM_RIGHT: 'bottom-right',
  BOTTOM_LEFT: 'bottom-left',
  TOP_CENTER: 'top-center',
  BOTTOM_CENTER: 'bottom-center',
};

// Провайдер уведомлений
export function NotificationProvider({ children, position = POSITIONS.TOP_RIGHT, maxNotifications = 5 }) {
  const [notifications, setNotifications] = useState([]);

  // Добавление уведомления
  const addNotification = useCallback((notification) => {
    const id = Date.now() + Math.random();
    const newNotification = {
      id,
      type: NOTIFICATION_TYPES.INFO,
      duration: 5000, // 5 секунд по умолчанию
      position,
      ...notification,
    };

    setNotifications((prev) => {
      const updated = [...prev, newNotification];
      // Ограничиваем количество уведомлений
      if (updated.length > maxNotifications) {
        return updated.slice(-maxNotifications);
      }
      return updated;
    });

    // Автоматическое удаление через duration
    if (newNotification.duration > 0) {
      setTimeout(() => {
        removeNotification(id);
      }, newNotification.duration);
    }

    return id;
  }, [position, maxNotifications]);

  // Удаление уведомления
  const removeNotification = useCallback((id) => {
    setNotifications((prev) => prev.filter((n) => n.id !== id));
  }, []);

  // Очистка всех уведомлений
  const clearNotifications = useCallback(() => {
    setNotifications([]);
  }, []);

  // Уведомления для конкретной позиции
  const positionNotifications = notifications.filter((n) => n.position === position);

  return (
    <NotificationContext.Provider
      value={{
        notifications,
        addNotification,
        removeNotification,
        clearNotifications,
        NOTIFICATION_TYPES,
      }}
    >
      {children}
      <NotificationContainer notifications={positionNotifications} onRemove={removeNotification} />
    </NotificationContext.Provider>
  );
}

// Контейнер для уведомлений
function NotificationContainer({ notifications, onRemove }) {
  return (
    <div className="fixed z-50 flex flex-col gap-2 p-4 pointer-events-none">
      {notifications.map((notification) => (
        <Notification
          key={notification.id}
          notification={notification}
          onRemove={() => onRemove(notification.id)}
        />
      ))}
    </div>
  );
}

// Компонент отдельного уведомления
function Notification({ notification, onRemove }) {
  const { type, title, message, icon, duration } = notification;

  const typeStyles = {
    success: 'bg-green-900/90 border-green-700 text-green-100',
    error: 'bg-red-900/90 border-red-700 text-red-100',
    warning: 'bg-yellow-900/90 border-yellow-700 text-yellow-100',
    info: 'bg-blue-900/90 border-blue-700 text-blue-100',
  };

  const typeIcons = {
    success: '✅',
    error: '❌',
    warning: '⚠️',
    info: 'ℹ️',
  };

  return (
    <div
      className={`pointer-events-auto min-w-[300px] max-w-md p-4 rounded-lg border shadow-lg backdrop-blur-sm animate-slide-in ${
        typeStyles[type] || typeStyles.info
      }`}
      style={{
        animation: 'slideIn 0.3s ease-out',
      }}
    >
      <div className="flex items-start gap-3">
        <span className="text-xl">{icon || typeIcons[type]}</span>
        <div className="flex-1">
          {title && <div className="font-semibold mb-1">{title}</div>}
          {message && <div className="text-sm opacity-90">{message}</div>}
        </div>
        <button
          onClick={onRemove}
          className="text-current opacity-60 hover:opacity-100 transition-opacity"
        >
          ✕
        </button>
      </div>

      {/* Прогресс бар для автоматического закрытия */}
      {duration > 0 && (
        <div className="mt-2 h-1 bg-current opacity-20 rounded-full overflow-hidden">
          <div
            className="h-full bg-current opacity-50"
            style={{
              animation: `progress ${duration}ms linear forwards`,
            }}
          />
        </div>
      )}
    </div>
  );
}

// Хук для использования уведомлений
export function useNotifications() {
  const context = useContext(NotificationContext);
  if (!context) {
    throw new Error('useNotifications must be used within a NotificationProvider');
  }
  return context;
}

// Утилиты для быстрого создания уведомлений
export const notify = {
  success: (message, title) => {
    // Эта функция должна вызываться внутри компонента с useNotifications
    console.warn('notify.success should be used with useNotifications hook');
  },
  error: (message, title) => {
    console.warn('notify.error should be used with useNotifications hook');
  },
  warning: (message, title) => {
    console.warn('notify.warning should be used with useNotifications hook');
  },
  info: (message, title) => {
    console.warn('notify.info should be used with useNotifications hook');
  },
};

// CSS анимации для уведомлений (добавить в index.css)
const notificationStyles = `
@keyframes slideIn {
  from {
    transform: translateX(100%);
    opacity: 0;
  }
  to {
    transform: translateX(0);
    opacity: 1;
  }
}

@keyframes slideOut {
  from {
    transform: translateX(0);
    opacity: 1;
  }
  to {
    transform: translateX(100%);
    opacity: 0;
  }
}

@keyframes progress {
  from {
    width: 100%;
  }
  to {
    width: 0%;
  }
}
`;

// Функция для добавления стилей
export function injectNotificationStyles() {
  if (!document.getElementById('notification-styles')) {
    const style = document.createElement('style');
    style.id = 'notification-styles';
    style.textContent = notificationStyles;
    document.head.appendChild(style);
  }
}