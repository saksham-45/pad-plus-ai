import { useState, useEffect } from 'react';
import { Button } from '../components/ui/Button';
import { Card, CardContent } from '../components/ui/Card';
import { apiFetch } from '../services/api';

export default function HistoryPage() {
  const [dialogs, setDialogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedDialog, setSelectedDialog] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [isSearching, setIsSearching] = useState(false);
  const [stats, setStats] = useState(null);
  const [message, setMessage] = useState({ type: '', text: '' });
  const [offset, setOffset] = useState(0);
  const [hasMore, setHasMore] = useState(true);
  const [sortBy, setSortBy] = useState('updated_at');
  const [sortOrder, setSortOrder] = useState('desc');
  const [filterFavorite, setFilterFavorite] = useState(null);

  // Загрузка диалогов с кешированием в sessionStorage
  const loadDialogs = async (reset = false) => {
    setLoading(true);
    const currentOffset = reset ? 0 : offset;

    // При сбросе показываем кеш сразу
    if (reset) {
      try {
        const cached = sessionStorage.getItem('historyDialogs');
        if (cached) {
          const parsed = JSON.parse(cached);
          setDialogs(parsed.data || []);
          setHasMore(parsed.has_more !== false);
          setStats(parsed.stats || null);
        }
      } catch (_) {}
    }

    try {
      const params = new URLSearchParams({
        offset: currentOffset,
        limit: 20,
        sort_by: sortBy,
        sort_order: sortOrder,
      });

      if (filterFavorite !== null) {
        params.append('is_favorite', filterFavorite);
      }

      const res = await apiFetch(`/api/v1/dialogs?${params}`);

      if (res.ok) {
        const data = await res.json();
        if (reset) {
          setDialogs(data.data);
          // Кешируем в sessionStorage
          sessionStorage.setItem('historyDialogs', JSON.stringify({ data: data.data, has_more: data.has_more }));
        } else {
          setDialogs(prev => [...prev, ...data.data]);
        }
        setHasMore(data.has_more);
        setOffset(currentOffset + data.limit);
      } else {
        const err = await res.json().catch(() => ({ detail: `Ошибка ${res.status}` }));
        showMessage('error', err.detail || 'Ошибка загрузки истории');
      }
    } catch (error) {
      console.error('Ошибка загрузки диалогов:', error);
      showMessage('error', 'Не удалось загрузить историю. Проверьте подключение.');
    } finally {
      setLoading(false);
    }
  };

  // Загрузка статистики
  const loadStats = async () => {
    try {
      const res = await apiFetch('/api/v1/dialogs/stats');
      if (res.ok) {
        const data = await res.json();
        setStats(data);
        // Обновляем кеш со статистикой
        try {
          const cached = sessionStorage.getItem('historyDialogs');
          if (cached) {
            const parsed = JSON.parse(cached);
            parsed.stats = data;
            sessionStorage.setItem('historyDialogs', JSON.stringify(parsed));
          }
        } catch (_) {}
      }
    } catch (error) {
      console.error('Ошибка загрузки статистики:', error);
    }
  };

  useEffect(() => {
    loadDialogs(true);
    loadStats();
  }, [sortBy, sortOrder, filterFavorite]);

  const handleSearch = async () => {
    if (!searchQuery.trim()) {
      setIsSearching(false);
      setSearchResults([]);
      return;
    }

    setIsSearching(true);

    try {
      const res = await apiFetch(`/api/v1/dialogs/search?query=${encodeURIComponent(searchQuery)}`);

      if (res.ok) {
        const data = await res.json();
        setSearchResults(data);
      }
    } catch (error) {
      console.error('Ошибка поиска:', error);
      showMessage('error', 'Ошибка поиска');
    }
  };

  const selectDialog = async (dialogId) => {
    try {
      const res = await apiFetch(`/api/v1/dialogs/${dialogId}`);

      if (res.ok) {
        const data = await res.json();
        setSelectedDialog(data);
      }
    } catch (error) {
      console.error('Ошибка загрузки диалога:', error);
      showMessage('error', 'Ошибка загрузки диалога');
    }
  };

  const deleteDialog = async (dialogId) => {
    if (!confirm('Вы уверены, что хотите удалить этот диалог?')) return;

    try {
      const res = await apiFetch(`/api/v1/dialogs/${dialogId}`, {
        method: 'DELETE',
      });

      if (res.ok) {
        showMessage('success', 'Диалог удалён');
        setDialogs(dialogs.filter((d) => d.id !== dialogId));
        if (selectedDialog?.id === dialogId) {
          setSelectedDialog(null);
        }
        loadStats();
      }
    } catch (error) {
      showMessage('error', 'Ошибка удаления диалога');
    }
  };

  const toggleFavorite = async (dialogId) => {
    try {
      const res = await apiFetch(`/api/v1/dialogs/${dialogId}/favorite`, {
        method: 'POST',
      });

      if (res.ok) {
        const data = await res.json();
        setDialogs(
          dialogs.map((d) =>
            d.id === dialogId ? { ...d, is_favorite: data.is_favorite } : d
          )
        );
        showMessage('success', data.is_favorite ? 'Добавлено в избранное' : 'Удалено из избранного');
        loadStats();
      }
    } catch (error) {
      showMessage('error', 'Ошибка обновления избранного');
    }
  };

  const exportDialog = async (dialogId, format) => {
    try {
      const res = await apiFetch(`/api/v1/dialogs/${dialogId}/export?format=${format}`);

      if (res.ok) {
        const blob = await res.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `dialog_${dialogId}.${format}`;
        a.click();
        window.URL.revokeObjectURL(url);
        showMessage('success', 'Диалог экспортирован');
      }
    } catch (error) {
      showMessage('error', 'Ошибка экспорта диалога');
    }
  };

  const clearAllHistory = async () => {
    if (!confirm('Вы уверены, что хотите удалить ВСЮ историю диалогов? Это действие нельзя отменить.')) return;

    try {
      const res = await apiFetch('/api/v1/dialogs', {
        method: 'DELETE',
      });

      if (res.ok) {
        showMessage('success', 'История очищена');
        setDialogs([]);
        setSelectedDialog(null);
        loadStats();
      }
    } catch (error) {
      showMessage('error', 'Ошибка очистки истории');
    }
  };

  const showMessage = (type, text) => {
    setMessage({ type, text });
    setTimeout(() => setMessage({ type: '', text: '' }), 3000);
  };

  const formatDate = (dateString) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('ru-RU', {
      day: '2-digit',
      month: 'short',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const displayDialogs = isSearching ? searchResults.data : dialogs;

  return (
    <div className="h-[calc(100vh-120px)] flex">
      {/* Боковая панель со списком диалогов */}
      <div className="w-80 border-r border-border flex flex-col">
        {/* Заголовок и поиск */}
        <div className="p-4 border-b border-border">
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-lg font-semibold text-text-primary">История</h2>
            <Button
              variant="outline"
              size="sm"
              onClick={clearAllHistory}
              className="text-red-400 hover:text-red-300 hover:bg-red-900/20"
            >
              Очистить
            </Button>
          </div>

          {/* Поиск */}
          <div className="flex gap-2">
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
              placeholder="Поиск по диалогам..."
              className="flex-1 px-3 py-2 bg-input border border-border rounded-lg text-text-primary text-sm focus:outline-none focus:ring-2 focus:ring-primary"
            />
            <Button size="sm" onClick={handleSearch}>
              🔍
            </Button>
          </div>

          {/* Фильтры */}
          <div className="flex gap-2 mt-3">
            <select
              value={filterFavorite === null ? '' : filterFavorite}
              onChange={(e) =>
                setFilterFavorite(e.target.value === '' ? null : e.target.value === 'true')
              }
              className="flex-1 px-2 py-1 bg-input border border-border rounded-lg text-text-primary text-xs focus:outline-none"
            >
              <option value="">Все</option>
              <option value="true">Избранные</option>
              <option value="false">Обычные</option>
            </select>

            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value)}
              className="flex-1 px-2 py-1 bg-input border border-border rounded-lg text-text-primary text-xs focus:outline-none"
            >
              <option value="updated_at">По дате</option>
              <option value="created_at">По созданию</option>
              <option value="message_count">По количеству</option>
            </select>
          </div>
        </div>

        {/* Статистика */}
        {stats && (
          <div className="px-4 py-2 border-b border-border bg-card/50">
            <div className="flex justify-between text-xs text-text-secondary">
              <span>Диалогов: {stats.total_dialogs}</span>
              <span>Сообщений: {stats.total_messages}</span>
              <span>⭐ {stats.favorite_dialogs}</span>
            </div>
          </div>
        )}

        {/* Список диалогов */}
        <div className="flex-1 overflow-y-auto">
          {loading && dialogs.length === 0 ? (
            <div className="flex items-center justify-center h-32">
              <div className="text-text-secondary text-sm">Загрузка...</div>
            </div>
          ) : displayDialogs.length === 0 ? (
            <div className="flex items-center justify-center h-32">
              <div className="text-text-secondary text-sm">Диалогов нет</div>
            </div>
          ) : (
            displayDialogs.map((dialog) => (
              <div
                key={dialog.id}
                onClick={() => selectDialog(dialog.id)}
                className={`p-3 border-b border-border cursor-pointer transition-colors ${
                  selectedDialog?.id === dialog.id
                    ? 'bg-primary/20 border-primary'
                    : 'hover:bg-card'
                }`}
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1 min-w-0">
                    <h3 className="text-sm font-medium text-text-primary truncate">
                      {dialog.title || 'Без названия'}
                    </h3>
                    <p className="text-xs text-text-secondary mt-1">
                      {dialog.message_count} сообщений
                    </p>
                  </div>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      toggleFavorite(dialog.id);
                    }}
                    className={`ml-2 ${
                      dialog.is_favorite ? 'text-yellow-400' : 'text-gray-600'
                    }`}
                  >
                    ★
                  </button>
                </div>
                <div className="flex items-center justify-between mt-2">
                  <span className="text-xs text-text-secondary">
                    {formatDate(dialog.updated_at || dialog.created_at)}
                  </span>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      deleteDialog(dialog.id);
                    }}
                    className="text-xs text-red-400 hover:text-red-300"
                  >
                    Удалить
                  </button>
                </div>
              </div>
            ))
          )}

          {/* Кнопка загрузки ещё */}
          {hasMore && !isSearching && (
            <div className="p-3 text-center">
              <Button
                variant="outline"
                size="sm"
                onClick={() => loadDialogs()}
                disabled={loading}
              >
                {loading ? 'Загрузка...' : 'Загрузить ещё'}
              </Button>
            </div>
          )}
        </div>
      </div>

      {/* Основная область - просмотр диалога */}
      <div className="flex-1 flex flex-col">
        {message.text && (
          <div
            className={`p-3 ${
              message.type === 'success'
                ? 'bg-green-900/30 text-green-400'
                : 'bg-red-900/30 text-red-400'
            }`}
          >
            {message.text}
          </div>
        )}

        {selectedDialog ? (
          <>
            {/* Заголовок диалога */}
            <div className="p-4 border-b border-border flex items-center justify-between">
              <div>
                <h2 className="text-lg font-semibold text-text-primary">
                  {selectedDialog.title || 'Без названия'}
                </h2>
                <p className="text-xs text-text-secondary">
                  {selectedDialog.message_count} сообщений |{' '}
                  {formatDate(selectedDialog.created_at)}
                </p>
              </div>
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => exportDialog(selectedDialog.id, 'json')}
                >
                  Экспорт JSON
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => exportDialog(selectedDialog.id, 'txt')}
                >
                  Экспорт TXT
                </Button>
              </div>
            </div>

            {/* Сообщения */}
            <div className="flex-1 overflow-y-auto p-4 space-y-4">
              {selectedDialog.messages.map((msg) => (
                <div
                  key={msg.id}
                  className={`flex ${
                    msg.role === 'user' ? 'justify-end' : 'justify-start'
                  }`}
                >
                  <div
                    className={`max-w-[80%] p-3 rounded-lg ${
                      msg.role === 'user'
                        ? 'bg-primary/20 text-text-primary'
                        : 'bg-card text-text-primary'
                    }`}
                  >
                    <p className="text-sm whitespace-pre-wrap">{msg.content}</p>
                    <p className="text-xs text-text-secondary mt-2">
                      {formatDate(msg.created_at)}
                      {msg.model && ` · ${msg.model}`}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </>
        ) : (
          <div className="flex-1 flex items-center justify-center">
            <div className="text-center text-text-secondary">
              <p className="text-xl mb-2">📜</p>
              <p>Выберите диалог для просмотра</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}