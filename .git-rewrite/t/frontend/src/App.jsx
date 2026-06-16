import { useState, useEffect } from 'react';
import Auth from './components/Auth';
import Dashboard from './components/Dashboard';
import ChatInterface from './components/ChatInterface';
import InstructionsPage from './pages/InstructionsPage';
import ProvidersPage from './pages/ProvidersPage';
import ConnectedProvidersPage from './pages/ConnectedProvidersPage';
import XRayPage from './pages/XRayPage';
import SettingsPage from './pages/SettingsPage';
import HistoryPage from './pages/HistoryPage';
import DocumentsPage from './pages/DocumentsPage';
import MobileMenu from './components/MobileMenu';
import { LeftSidebar } from './components/LeftSidebar';
import { RightSidebar } from './components/RightSidebar';
import { Button } from './components/ui/Button';
import { NotificationProvider } from './hooks/useNotifications';

// Вкладки навигации
const tabs = [
  { id: 'home', label: '🏠 Главная', icon: '🏠' },
  { id: 'chat', label: '💬 Чат', icon: '💬' },
  { id: 'documents', label: '📄 Документы', icon: '📄' },
  { id: 'history', label: '📜 История', icon: '📜' },
  { id: 'xray', label: '🔬 X-Ray', icon: '🔬' },
  { id: 'settings', label: '⚙️ Настройки', icon: '⚙️' },
  { id: 'instructions', label: '📖 Инструкции', icon: '📖' },
  { id: 'providers', label: '⚡ Провайдеры', icon: '⚡' },
  { id: 'connected-providers', label: '', icon: '', page: true }, // Скрытая вкладка для маршрута
];

function App() {
  const [user, setUser] = useState(null);
  const [activeTab, setActiveTab] = useState(() => {
    return localStorage.getItem('activeTab') || 'home';
  });
  const [showInstructions, setShowInstructions] = useState(false);
  const [keys, setKeys] = useState([]);
  const [selectedModel, setSelectedModel] = useState(() => {
    // Восстанавливаем модель из localStorage при загрузке
    const saved = localStorage.getItem('selectedModel');
    if (saved) {
      try {
        return JSON.parse(saved);
      } catch {
        return null;
      }
    }
    return null;
  });
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [loading, setLoading] = useState(true);
  
  // Состояние боковых панелей
  const [leftSidebarOpen, setLeftSidebarOpen] = useState(() => {
    return localStorage.getItem('leftSidebarOpen') !== 'false';
  });
  const [rightSidebarOpen, setRightSidebarOpen] = useState(() => {
    return localStorage.getItem('rightSidebarOpen') !== 'false';
  });
  const [rightSidebarWidth, setRightSidebarWidth] = useState(() => {
    return parseInt(localStorage.getItem('rightSidebarWidth') || '640');
  });

  // Состояние мобильного меню
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [isMobile, setIsMobile] = useState(false);

  // Определение мобильного устройства
  useEffect(() => {
    const checkMobile = () => {
      const mobile = window.innerWidth < 1024;
      setIsMobile(mobile);
      
      // На мобильных скрываем левую панель
      if (mobile) {
        setLeftSidebarOpen(false);
      } else {
        setMobileMenuOpen(false);
      }
    };

    checkMobile();
    window.addEventListener('resize', checkMobile);
    return () => window.removeEventListener('resize', checkMobile);
  }, []);

  // Сохраняем активную вкладку
  useEffect(() => {
    localStorage.setItem('activeTab', activeTab);
  }, [activeTab]);

  // Сохраняем выбранную модель в localStorage
  useEffect(() => {
    if (selectedModel) {
      localStorage.setItem('selectedModel', JSON.stringify(selectedModel));
    }
  }, [selectedModel]);

  // Сохраняем состояние боковых панелей
  useEffect(() => {
    localStorage.setItem('leftSidebarOpen', leftSidebarOpen);
  }, [leftSidebarOpen]);

  useEffect(() => {
    localStorage.setItem('rightSidebarOpen', rightSidebarOpen);
  }, [rightSidebarOpen]);

  // Сохраняем ширину правой панели
  useEffect(() => {
    localStorage.setItem('rightSidebarWidth', rightSidebarWidth);
  }, [rightSidebarWidth]);

  // Проверка аутентификации
  useEffect(() => {
    const storedUser = localStorage.getItem('user');
    const token = localStorage.getItem('access_token');
    
    if (storedUser && token) {
      setUser(JSON.parse(storedUser));
    }
    setLoading(false);
  }, []);

  const fetchKeys = async () => {
    try {
      const token = localStorage.getItem('access_token');
      if (!token) {
        // Нет токена - пользователь не аутентифицирован
        setKeys([]);
        return;
      }

      const response = await fetch('/api/v1/keys?offset=0&limit=100', {
        headers: { 'Authorization': `Bearer ${token}` },
      });

      // Обработка 401 ошибки - токен невалиден или истек
      if (response.status === 401) {
        console.warn('Токен невалиден, выполнен выход из системы');
        handleLogout();
        return;
      }

      if (response.ok) {
        const result = await response.json();
        // Обработка пагинации: result.data или result (если старый формат)
        const keysData = result.data || result;
        setKeys(Array.isArray(keysData) ? keysData : []);

        // Выбираем модель по умолчанию
        const defaultKey = (keysData || []).find(k => k.is_default);
        if (defaultKey && !selectedModel) {
          setSelectedModel({
            id: defaultKey.model_preference || 'auto',
            name: defaultKey.model_preference === 'auto'
              ? `${defaultKey.provider_display_name} (Auto)`
              : defaultKey.model_preference,
            keyId: defaultKey.id,
            provider: defaultKey.provider,
            providerName: defaultKey.provider_display_name,
            isDefault: defaultKey.is_default,
          });
        }
      } else {
        // Другие ошибки - просто устанавливаем пустой список
        console.warn('Не удалось загрузить ключи, статус:', response.status);
        setKeys([]);
      }
    } catch (err) {
      console.error('Failed to fetch keys:', err);
      setKeys([]);
    }
  };

  // Загрузка ключей и авто-выбор модели
  useEffect(() => {
    if (user) {
      fetchKeys();
    }
  }, [user]);

  // Авто-выбор модели при загрузке ключей (если ещё не выбрана)
  useEffect(() => {
    if (keys.length > 0 && !selectedModel) {
      const defaultKey = keys.find(k => k.is_default);
      if (defaultKey) {
        setSelectedModel({
          id: defaultKey.model_preference || 'auto',
          name: defaultKey.model_preference === 'auto'
            ? `${defaultKey.provider_display_name} (Auto)`
            : defaultKey.model_preference,
          keyId: defaultKey.id,
          provider: defaultKey.provider,
          providerName: defaultKey.provider_display_name,
          isDefault: defaultKey.is_default,
        });
      }
    }
  }, [keys]);

  // Слушатель событий обновления ключей от других компонентов
  useEffect(() => {
    const handleKeysUpdated = () => {
      console.log('🔄 Keys updated event received, refreshing...');
      fetchKeys();
    };

    const handleModelChanged = (event) => {
      console.log('🔄 Model changed event received:', event.detail);
      if (event.detail) {
        setSelectedModel(event.detail);
      }
    };

    window.addEventListener('keys-updated', handleKeysUpdated);
    window.addEventListener('model-changed', handleModelChanged);

    return () => {
      window.removeEventListener('keys-updated', handleKeysUpdated);
      window.removeEventListener('model-changed', handleModelChanged);
    };
  }, []);


  const handleLogout = () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    localStorage.removeItem('user');
    setUser(null);
    setActiveTab('home');
    setShowInstructions(false);
  };

  // Обработчик навигации из левой панели
  const handleNavigate = (page) => {
    // Сопоставление путей и вкладок
    const pageToTab = {
      '/instructions': 'instructions',
      '/connected-providers': 'connected-providers',
      '/providers': 'providers',
      '/documents': 'documents',
      '/settings': 'settings',
      '/history': 'history',
    };

    const tab = pageToTab[page];
    if (tab) {
      setShowInstructions(page === '/instructions');
      setActiveTab(tab);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="text-text-primary">Загрузка...</div>
      </div>
    );
  }

  if (!user) {
    return <Auth onAuthSuccess={setUser} />;
  }

  return (
    <NotificationProvider>
      <div className="min-h-screen bg-background">
      {/* Мобильное меню */}
      <MobileMenu
        isOpen={mobileMenuOpen}
        onClose={() => setMobileMenuOpen(false)}
        activeTab={activeTab}
        onTabChange={setActiveTab}
      />

      {/* Боковые панели */}
      <LeftSidebar 
        isOpen={leftSidebarOpen} 
        onToggle={() => setLeftSidebarOpen(!leftSidebarOpen)} 
        onNavigate={handleNavigate}
      />
      <RightSidebar 
        isOpen={rightSidebarOpen} 
        onToggle={() => setRightSidebarOpen(!rightSidebarOpen)}
        width={rightSidebarWidth}
        onWidthChange={setRightSidebarWidth}
      />

      {/* Header */}
      <header className="border-b border-border bg-card fixed top-0 left-0 right-0 z-30">
        <div className="px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-4">
            {/* Кнопка hamburger для мобильных */}
            {isMobile && (
              <button
                onClick={() => setMobileMenuOpen(true)}
                className="lg:hidden p-2 hover:bg-gray-800 rounded-lg transition-colors"
              >
                <svg className="w-6 h-6 text-text-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
                </svg>
              </button>
            )}

            <h1 className="text-xl font-bold text-text-primary">
              PAD+ AI
              <span className="text-xs text-text-secondary ml-2">v3.5</span>
            </h1>
            
            {/* Навигация - скрываем на мобильных */}
            <nav className="hidden lg:flex gap-1 ml-6">
              {tabs.map(tab => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`px-4 py-2 rounded-lg text-sm transition-colors ${
                    activeTab === tab.id
                      ? 'bg-primary text-white'
                      : 'text-text-secondary hover:text-text-primary hover:bg-gray-800'
                  }`}
                >
                  {tab.label}
                </button>
              ))}
            </nav>
          </div>

          <div className="flex items-center gap-4">
            {/* Текущая модель — только отображение */}
            {selectedModel && (
              <div className="text-xs text-text-secondary flex items-center gap-1">
                <span className="text-primary font-medium">{selectedModel.name}</span>
              </div>
            )}
            
            <div className="flex items-center gap-2">
              <span className="text-sm text-text-secondary">
                {user.email}
              </span>
              <Button
                variant="outline"
                size="sm"
                onClick={handleLogout}
              >
                Выйти
              </Button>
            </div>
          </div>
        </div>
      </header>

      {/* Content */}
      <main 
        className={`pt-16 pb-4 transition-all duration-300 ${
          leftSidebarOpen ? 'ml-72' : 'ml-0'
        } ${
          rightSidebarOpen ? 'mr-0' : 'mr-0'
        }`}
        style={{
          marginRight: rightSidebarOpen ? `${rightSidebarWidth}px` : '0'
        }}
      >
        <div className="px-4">
          {activeTab === 'home' && (
            <Dashboard />
          )}

          {activeTab === 'chat' && (
            <div className="h-[calc(100vh-120px)]">
              <ChatInterface
                selectedModel={selectedModel}
                user={user}
              />
            </div>
          )}

          {activeTab === 'instructions' && (
            <InstructionsPage />
          )}

          {activeTab === 'providers' && (
            <ProvidersPage />
          )}

          {activeTab === 'connected-providers' && (
            <ConnectedProvidersPage />
          )}

          {activeTab === 'xray' && (
            <XRayPage />
          )}

          {activeTab === 'settings' && (
            <SettingsPage />
          )}

          {activeTab === 'history' && (
            <HistoryPage />
          )}

          {activeTab === 'documents' && (
            <DocumentsPage />
          )}
        </div>
      </main>
      </div>
    </NotificationProvider>
  );
}

export default App;
