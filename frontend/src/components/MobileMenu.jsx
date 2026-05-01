import { useState, useEffect } from 'react';
import { Button } from './ui/Button';

// Вкладки навигации
const tabs = [
  { id: 'home', label: 'Главная', icon: '🏠' },
  { id: 'chat', label: 'Чат', icon: '💬' },
  { id: 'documents', label: 'Документы', icon: '📄' },
  { id: 'history', label: 'История', icon: '📜' },
  { id: 'xray', label: 'X-Ray', icon: '🔬' },
  { id: 'settings', label: 'Настройки', icon: '⚙️' },
  { id: 'instructions', label: 'Инструкции', icon: '📖' },
  { id: 'providers', label: 'Провайдеры', icon: '⚡' },
];

export default function MobileMenu({ isOpen, onClose, activeTab, onTabChange }) {
  const [isVisible, setIsVisible] = useState(false);

  useEffect(() => {
    if (isOpen) {
      setIsVisible(true);
      document.body.style.overflow = 'hidden';
    } else {
      setTimeout(() => setIsVisible(false), 300);
      document.body.style.overflow = '';
    }

    return () => {
      document.body.style.overflow = '';
    };
  }, [isOpen]);

  if (!isVisible && !isOpen) return null;

  return (
    <>
      {/* Затемнение фона */}
      <div
        className={`fixed inset-0 bg-black/60 z-40 transition-opacity duration-300 ${
          isOpen ? 'opacity-100' : 'opacity-0'
        }`}
        onClick={onClose}
      />

      {/* Меню */}
      <div
        className={`fixed top-0 left-0 h-full w-72 bg-[#111827] z-50 transform transition-transform duration-300 ${
          isOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        {/* Header */}
        <div className="p-4 border-b border-[#1F2937] flex items-center justify-between">
          <h1 className="text-lg font-semibold text-white">
            PAD+ AI
            <span className="text-xs text-text-secondary ml-2">v3.5</span>
          </h1>
          <button
            onClick={onClose}
            className="p-2 hover:bg-[#1F2937] rounded-lg transition-colors"
          >
            <svg className="w-5 h-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Навигация */}
        <nav className="p-2 space-y-1 overflow-y-auto" style={{ maxHeight: 'calc(100vh - 80px)' }}>
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => {
                onTabChange(tab.id);
                onClose();
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
        </nav>
      </div>
    </>
  );
}