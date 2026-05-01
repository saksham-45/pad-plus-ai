import { useState, useEffect } from 'react';
import { Button } from '../components/ui/Button';
import { Card, CardHeader, CardTitle, CardContent } from '../components/ui/Card';

// Вкладки настроек
const tabs = [
  { id: 'profile', label: 'Профиль', icon: '👤' },
  { id: 'persona', label: 'Persona', icon: '🤖' },
  { id: 'notifications', label: 'Уведомления', icon: '🔔' },
  { id: 'appearance', label: 'Внешний вид', icon: '🎨' },
];

export default function SettingsPage() {
  const [activeTab, setActiveTab] = useState('profile');
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState({ type: '', text: '' });

  // Состояние профиля
  const [profile, setProfile] = useState({
    email: '',
    full_name: '',
    avatar_url: '',
  });

  // Состояние настроек persona
  const [persona, setPersona] = useState({
    tone: 'friendly',
    detail_level: 'moderate',
    emotion_level: 'balanced',
    specialization: 'general',
  });

  // Состояние настроек уведомлений
  const [notifications, setNotifications] = useState({
    email: true,
    push: false,
    sound: true,
    frequency: 'immediate',
  });

  // Состояние настроек внешнего вида
  const [appearance, setAppearance] = useState({
    theme: 'dark',
    font_size: 'medium',
    compact_mode: false,
  });

  // Состояние для смены пароля
  const [passwords, setPasswords] = useState({
    current: '',
    new: '',
    confirm: '',
  });

  // Загрузка данных
  useEffect(() => {
    loadSettings();
  }, []);

  const loadSettings = async () => {
    setLoading(true);
    const token = localStorage.getItem('access_token');

    try {
      // Загружаем профиль
      const profileRes = await fetch('/api/v1/user/profile', {
        headers: { 'Authorization': `Bearer ${token}` },
      });
      if (profileRes.ok) {
        const profileData = await profileRes.json();
        setProfile(profileData);
      }

      // Загружаем все настройки
      const settingsRes = await fetch('/api/v1/user/settings', {
        headers: { 'Authorization': `Bearer ${token}` },
      });
      if (settingsRes.ok) {
        const settingsData = await settingsRes.json();
        setPersona(settingsData.persona);
        setNotifications(settingsData.notifications);
        setAppearance(settingsData.appearance);
      }
    } catch (error) {
      console.error('Ошибка загрузки настроек:', error);
    } finally {
      setLoading(false);
    }
  };

  const showMessage = (type, text) => {
    setMessage({ type, text });
    setTimeout(() => setMessage({ type: '', text: '' }), 3000);
  };

  // Сохранение профиля
  const saveProfile = async () => {
    setSaving(true);
    const token = localStorage.getItem('access_token');

    try {
      const res = await fetch('/api/v1/user/profile', {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({
          full_name: profile.full_name,
          email: profile.email,
        }),
      });

      if (res.ok) {
        showMessage('success', 'Профиль обновлён');
      } else {
        const error = await res.json();
        showMessage('error', error.detail || 'Ошибка обновления');
      }
    } catch (error) {
      showMessage('error', 'Ошибка обновления профиля');
    } finally {
      setSaving(false);
    }
  };

  // Смена пароля
  const changePassword = async () => {
    if (passwords.new !== passwords.confirm) {
      showMessage('error', 'Пароли не совпадают');
      return;
    }

    if (passwords.new.length < 6) {
      showMessage('error', 'Пароль должен быть не менее 6 символов');
      return;
    }

    setSaving(true);
    const token = localStorage.getItem('access_token');

    try {
      const res = await fetch('/api/v1/user/password', {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({
          current_password: passwords.current,
          new_password: passwords.new,
        }),
      });

      if (res.ok) {
        showMessage('success', 'Пароль изменён');
        setPasswords({ current: '', new: '', confirm: '' });
      } else {
        const error = await res.json();
        showMessage('error', error.detail || 'Ошибка смены пароля');
      }
    } catch (error) {
      showMessage('error', 'Ошибка смены пароля');
    } finally {
      setSaving(false);
    }
  };

  // Сохранение настроек persona
  const savePersona = async () => {
    setSaving(true);
    const token = localStorage.getItem('access_token');

    try {
      const res = await fetch('/api/v1/user/persona', {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify(persona),
      });

      if (res.ok) {
        showMessage('success', 'Настройки Persona обновлены');
      } else {
        showMessage('error', 'Ошибка обновления настроек');
      }
    } catch (error) {
      showMessage('error', 'Ошибка обновления настроеk');
    } finally {
      setSaving(false);
    }
  };

  // Сохранение настроек уведомлений
  const saveNotifications = async () => {
    setSaving(true);
    const token = localStorage.getItem('access_token');

    try {
      const res = await fetch('/api/v1/user/notifications', {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify(notifications),
      });

      if (res.ok) {
        showMessage('success', 'Настройки уведомлений обновлены');
      } else {
        showMessage('error', 'Ошибка обновления настроек');
      }
    } catch (error) {
      showMessage('error', 'Ошибка обновления настроек');
    } finally {
      setSaving(false);
    }
  };

  // Сохранение настроек внешнего вида
  const saveAppearance = async () => {
    setSaving(true);
    const token = localStorage.getItem('access_token');

    try {
      const res = await fetch('/api/v1/user/appearance', {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify(appearance),
      });

      if (res.ok) {
        showMessage('success', 'Настройки внешнего вида обновлены');
        // Применяем тему
        applyTheme(appearance.theme);
      } else {
        showMessage('error', 'Ошибка обновления настроек');
      }
    } catch (error) {
      showMessage('error', 'Ошибка обновления настроек');
    } finally {
      setSaving(false);
    }
  };

  const applyTheme = (theme) => {
    const root = document.documentElement;
    if (theme === 'dark') {
      root.classList.add('dark');
    } else if (theme === 'light') {
      root.classList.remove('dark');
    } else {
      // Auto - определяем по системным настройкам
      if (window.matchMedia('(prefers-color-scheme: dark)').matches) {
        root.classList.add('dark');
      } else {
        root.classList.remove('dark');
      }
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-text-secondary">Загрузка...</div>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto p-4">
      <h1 className="text-2xl font-bold text-text-primary mb-6">Настройки</h1>

      {/* Сообщение */}
      {message.text && (
        <div
          className={`p-3 rounded-lg mb-4 ${
            message.type === 'success'
              ? 'bg-green-900/30 text-green-400 border border-green-800'
              : 'bg-red-900/30 text-red-400 border border-red-800'
          }`}
        >
          {message.text}
        </div>
      )}

      {/* Вкладки */}
      <div className="flex gap-2 mb-6 border-b border-border">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`px-4 py-2 text-sm transition-colors ${
              activeTab === tab.id
                ? 'text-primary border-b-2 border-primary'
                : 'text-text-secondary hover:text-text-primary'
            }`}
          >
            <span className="mr-2">{tab.icon}</span>
            {tab.label}
          </button>
        ))}
      </div>

      {/* Контент вкладок */}
      <Card>
        <CardContent className="p-6">
          {/* Профиль */}
          {activeTab === 'profile' && (
            <div className="space-y-6">
              <h2 className="text-lg font-semibold text-text-primary">
                Редактирование профиля
              </h2>

              <div className="space-y-4">
                <div>
                  <label className="block text-sm text-text-secondary mb-2">
                    Email
                  </label>
                  <input
                    type="email"
                    value={profile.email}
                    onChange={(e) =>
                      setProfile({ ...profile, email: e.target.value })
                    }
                    className="w-full px-3 py-2 bg-white border border-gray-300 rounded-lg text-black placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-primary"
                  />
                </div>

                <div>
                  <label className="block text-sm text-text-secondary mb-2">
                    Имя
                  </label>
                  <input
                    type="text"
                    value={profile.full_name || ''}
                    onChange={(e) =>
                      setProfile({ ...profile, full_name: e.target.value })
                    }
                    className="w-full px-3 py-2 bg-gray-100 dark:bg-input border border-gray-300 dark:border-border rounded-lg text-gray-900 dark:text-text-primary focus:outline-none focus:ring-2 focus:ring-primary"
                    placeholder="Введите ваше имя"
                  />
                </div>

                <Button onClick={saveProfile} disabled={saving}>
                  {saving ? 'Сохранение...' : 'Сохранить изменения'}
                </Button>
              </div>

              <hr className="border-border my-6" />

              <h3 className="text-lg font-semibold text-text-primary">
                Смена пароля
              </h3>

              <div className="space-y-4">
                <div>
                  <label className="block text-sm text-text-secondary mb-2">
                    Текущий пароль
                  </label>
                  <input
                    type="password"
                    value={passwords.current}
                    onChange={(e) =>
                      setPasswords({ ...passwords, current: e.target.value })
                    }
className="w-full px-3 py-2 bg-gray-100 dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-primary"
                  />
                </div>

                <div>
                  <label className="block text-sm text-text-secondary mb-2">
                    Новый пароль
                  </label>
                  <input
                    type="password"
                    value={passwords.new}
                    onChange={(e) =>
                      setPasswords({ ...passwords, new: e.target.value })
                    }
                    className="w-full px-3 py-2 bg-input border border-border rounded-lg text-text-primary focus:outline-none focus:ring-2 focus:ring-primary"
                  />
                </div>

                <div>
                  <label className="block text-sm text-text-secondary mb-2">
                    Подтвердите новый пароль
                  </label>
                  <input
                    type="password"
                    value={passwords.confirm}
                    onChange={(e) =>
                      setPasswords({ ...passwords, confirm: e.target.value })
                    }
                    className="w-full px-3 py-2 bg-input border border-border rounded-lg text-text-primary focus:outline-none focus:ring-2 focus:ring-primary"
                  />
                </div>

                <Button onClick={changePassword} disabled={saving}>
                  {saving ? 'Сохранение...' : 'Сменить пароль'}
                </Button>
              </div>
            </div>
          )}

          {/* Persona */}
          {activeTab === 'persona' && (
            <div className="space-y-6">
              <h2 className="text-lg font-semibold text-text-primary">
                Настройки Persona
              </h2>
              <p className="text-sm text-text-secondary">
                Настройте стиль общения AI ассистента
              </p>

              <div className="space-y-4">
                <div>
                  <label className="block text-sm text-text-secondary mb-2">
                    Тон общения
                  </label>
                  <select
                    value={persona.tone}
                    onChange={(e) =>
                      setPersona({ ...persona, tone: e.target.value })
                    }
                    className="w-full px-3 py-2 bg-input border border-border rounded-lg text-text-primary focus:outline-none focus:ring-2 focus:ring-primary"
                  >
                    <option value="friendly">Дружелюбный</option>
                    <option value="serious">Серьёзный</option>
                    <option value="neutral">Нейтральный</option>
                  </select>
                </div>

                <div>
                  <label className="block text-sm text-text-secondary mb-2">
                    Уровень детализации
                  </label>
                  <select
                    value={persona.detail_level}
                    onChange={(e) =>
                      setPersona({ ...persona, detail_level: e.target.value })
                    }
                    className="w-full px-3 py-2 bg-input border border-border rounded-lg text-text-primary focus:outline-none focus:ring-2 focus:ring-primary"
                  >
                    <option value="brief">Кратко</option>
                    <option value="moderate">Умеренно</option>
                    <option value="detailed">Подробно</option>
                  </select>
                </div>

                <div>
                  <label className="block text-sm text-text-secondary mb-2">
                    Эмоциональная окраска
                  </label>
                  <select
                    value={persona.emotion_level}
                    onChange={(e) =>
                      setPersona({ ...persona, emotion_level: e.target.value })
                    }
                    className="w-full px-3 py-2 bg-input border border-border rounded-lg text-text-primary focus:outline-none focus:ring-2 focus:ring-primary"
                  >
                    <option value="restrained">Сдержанная</option>
                    <option value="balanced">Сбалансированная</option>
                    <option value="expressive">Выраженная</option>
                  </select>
                </div>

                <div>
                  <label className="block text-sm text-text-secondary mb-2">
                    Специализация
                  </label>
                  <select
                    value={persona.specialization}
                    onChange={(e) =>
                      setPersona({ ...persona, specialization: e.target.value })
                    }
                    className="w-full px-3 py-2 bg-input border border-border rounded-lg text-text-primary focus:outline-none focus:ring-2 focus:ring-primary"
                  >
                    <option value="general">Универсальный</option>
                    <option value="technical">Технический</option>
                    <option value="creative">Творческий</option>
                  </select>
                </div>

                <Button onClick={savePersona} disabled={saving}>
                  {saving ? 'Сохранение...' : 'Сохранить настройки'}
                </Button>
              </div>
            </div>
          )}

          {/* Уведомления */}
          {activeTab === 'notifications' && (
            <div className="space-y-6">
              <h2 className="text-lg font-semibold text-text-primary">
                Настройки уведомлений
              </h2>

              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-text-primary">Email уведомления</p>
                    <p className="text-sm text-text-secondary">
                      Получать уведомления на email
                    </p>
                  </div>
                  <button
                    onClick={() =>
                      setNotifications({ ...notifications, email: !notifications.email })
                    }
                    className={`w-12 h-6 rounded-full transition-colors ${
                      notifications.email ? 'bg-primary' : 'bg-gray-600'
                    }`}
                  >
                    <div
                      className={`w-5 h-5 bg-white rounded-full transition-transform ${
                        notifications.email ? 'translate-x-6' : 'translate-x-1'
                      }`}
                    />
                  </button>
                </div>

                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-text-primary">Push уведомления</p>
                    <p className="text-sm text-text-secondary">
                      Получать push уведомления в браузере
                    </p>
                  </div>
                  <button
                    onClick={() =>
                      setNotifications({ ...notifications, push: !notifications.push })
                    }
                    className={`w-12 h-6 rounded-full transition-colors ${
                      notifications.push ? 'bg-primary' : 'bg-gray-600'
                    }`}
                  >
                    <div
                      className={`w-5 h-5 bg-white rounded-full transition-transform ${
                        notifications.push ? 'translate-x-6' : 'translate-x-1'
                      }`}
                    />
                  </button>
                </div>

                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-text-primary">Звуковые уведомления</p>
                    <p className="text-sm text-text-secondary">
                      Воспроизводить звук при уведомлениях
                    </p>
                  </div>
                  <button
                    onClick={() =>
                      setNotifications({
                        ...notifications,
                        sound: !notifications.sound,
                      })
                    }
                    className={`w-12 h-6 rounded-full transition-colors ${
                      notifications.sound ? 'bg-primary' : 'bg-gray-600'
                    }`}
                  >
                    <div
                      className={`w-5 h-5 bg-white rounded-full transition-transform ${
                        notifications.sound ? 'translate-x-6' : 'translate-x-1'
                      }`}
                    />
                  </button>
                </div>

                <div>
                  <label className="block text-sm text-text-secondary mb-2">
                    Частота уведомлений
                  </label>
                  <select
                    value={notifications.frequency}
                    onChange={(e) =>
                      setNotifications({
                        ...notifications,
                        frequency: e.target.value,
                      })
                    }
                    className="w-full px-3 py-2 bg-input border border-border rounded-lg text-text-primary focus:outline-none focus:ring-2 focus:ring-primary"
                  >
                    <option value="immediate">Сразу</option>
                    <option value="hourly">Раз в час</option>
                    <option value="daily">Раз в день</option>
                  </select>
                </div>

                <Button onClick={saveNotifications} disabled={saving}>
                  {saving ? 'Сохранение...' : 'Сохранить настройки'}
                </Button>
              </div>
            </div>
          )}

          {/* Внешний вид */}
          {activeTab === 'appearance' && (
            <div className="space-y-6">
              <h2 className="text-lg font-semibold text-text-primary">
                Настройки внешнего вида
              </h2>

              <div className="space-y-4">
                <div>
                  <label className="block text-sm text-text-secondary mb-2">
                    Тема
                  </label>
                  <select
                    value={appearance.theme}
                    onChange={(e) =>
                      setAppearance({ ...appearance, theme: e.target.value })
                    }
                    className="w-full px-3 py-2 bg-input border border-border rounded-lg text-text-primary focus:outline-none focus:ring-2 focus:ring-primary"
                  >
                    <option value="dark">Тёмная</option>
                    <option value="light">Светлая</option>
                    <option value="auto">Автоматически</option>
                  </select>
                </div>

                <div>
                  <label className="block text-sm text-text-secondary mb-2">
                    Размер шрифта
                  </label>
                  <select
                    value={appearance.font_size}
                    onChange={(e) =>
                      setAppearance({ ...appearance, font_size: e.target.value })
                    }
                    className="w-full px-3 py-2 bg-input border border-border rounded-lg text-text-primary focus:outline-none focus:ring-2 focus:ring-primary"
                  >
                    <option value="small">Маленький</option>
                    <option value="medium">Средний</option>
                    <option value="large">Большой</option>
                  </select>
                </div>

                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-text-primary">Компактный режим</p>
                    <p className="text-sm text-text-secondary">
                      Уменьшить отступы и размеры элементов
                    </p>
                  </div>
                  <button
                    onClick={() =>
                      setAppearance({
                        ...appearance,
                        compact_mode: !appearance.compact_mode,
                      })
                    }
                    className={`w-12 h-6 rounded-full transition-colors ${
                      appearance.compact_mode ? 'bg-primary' : 'bg-gray-600'
                    }`}
                  >
                    <div
                      className={`w-5 h-5 bg-white rounded-full transition-transform ${
                        appearance.compact_mode ? 'translate-x-6' : 'translate-x-1'
                      }`}
                    />
                  </button>
                </div>

                <Button onClick={saveAppearance} disabled={saving}>
                  {saving ? 'Сохранение...' : 'Сохранить настройки'}
                </Button>
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}