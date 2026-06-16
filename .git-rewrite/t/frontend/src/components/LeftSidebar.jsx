import { useState } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from './ui/Card';
import { Button } from './ui/Button';

// Вкладки левой панели
const tabs = [
  { id: 'instructions', label: 'Инструкции', icon: '📖', page: '/instructions' },
  { id: 'providers', label: 'Провайдеры', icon: '⚡', page: '/connected-providers' },
  { id: 'documents', label: 'Документы', icon: '📄', page: '/documents' },
  { id: 'settings', label: 'Настройки', icon: '⚙️', page: '/settings' },
  { id: 'history', label: 'История', icon: '📜', page: '/history' },
];

export function LeftSidebar({ isOpen, onToggle, onNavigate }) {
  const [activeTab, setActiveTab] = useState('instructions');

  if (!isOpen) {
    return (
      <button
        onClick={onToggle}
        className="fixed left-0 top-1/2 -translate-y-1/2 z-40 bg-[#1F2937] text-white p-2 rounded-r-lg hover:bg-[#374151] transition-colors"
      >
        <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
        </svg>
      </button>
    );
  }

  return (
    <aside className="fixed left-0 top-0 h-full w-72 bg-[#111827] border-r border-[#1F2937] z-40 flex flex-col transition-transform duration-300">
      {/* Header */}
      <div className="p-4 border-b border-[#1F2937] flex items-center justify-between">
        <h2 className="text-lg font-semibold text-white">Меню</h2>
        <button
          onClick={onToggle}
          className="p-1 hover:bg-[#1F2937] rounded-lg transition-colors"
        >
          <svg className="w-5 h-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
          </svg>
        </button>
      </div>

      {/* Вкладки */}
      <div className="p-2 space-y-1">
        {tabs.map(tab => (
          <button
            key={tab.id}
            onClick={() => {
              setActiveTab(tab.id);
              if (tab.page && onNavigate) {
                onNavigate(tab.page);
              }
            }}
            className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg text-sm transition-colors ${
              activeTab === tab.id
                ? 'bg-[#6366F1] text-white'
                : 'text-gray-400 hover:text-white hover:bg-[#1F2937]'
            }`}
          >
            <span className="text-lg">{tab.icon}</span>
            {tab.label}
          </button>
        ))}
      </div>

      {/* Контент вкладок */}
      <div className="flex-1 overflow-y-auto p-4">
        {activeTab === 'instructions' && (
          <div className="space-y-4">
            <p className="text-sm text-gray-400">
              Полная документация по использованию PAD+ AI
            </p>
            <Button 
              size="sm" 
              className="w-full"
              onClick={() => onNavigate && onNavigate('/instructions')}
            >
              Открыть инструкции
            </Button>
          </div>
        )}

        {activeTab === 'providers' && (
          <div className="space-y-4">
            <p className="text-sm text-gray-400">
              Управление подключенными провайдерами
            </p>
            <Button 
              size="sm" 
              className="w-full"
              onClick={() => onNavigate && onNavigate('/connected-providers')}
            >
              Открыть провайдеры
            </Button>
          </div>
        )}

        {activeTab === 'documents' && (
          <div className="space-y-4">
            <p className="text-sm text-gray-400">
              Загрузка и обработка документов для RAG
            </p>
            <Button size="sm" className="w-full">
              Загрузить документ
            </Button>
          </div>
        )}

        {activeTab === 'settings' && (
          <div className="space-y-4">
            <p className="text-sm text-gray-400">
              Настройки профиля и приложения
            </p>
            <Button 
              size="sm" 
              className="w-full"
              onClick={() => {
                if (onNavigate) onNavigate('/settings');
              }}
            >
              Открыть настройки
            </Button>
          </div>
        )}

        {activeTab === 'history' && (
          <div className="space-y-4">
            <p className="text-sm text-gray-400">
              История диалогов и переписки
            </p>
            <Button 
              size="sm" 
              className="w-full"
              onClick={() => {
                if (onNavigate) onNavigate('/history');
              }}
            >
              Открыть историю
            </Button>
          </div>
        )}
      </div>
    </aside>
  );
}
