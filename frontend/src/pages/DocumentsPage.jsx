import { useState, useEffect, useRef } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { useNotifications } from '../hooks/useNotifications';
import { apiFetch } from '../services/api';

export default function DocumentsPage() {
  const [documents, setDocuments] = useState([]);
  const [collections, setCollections] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [selectedDoc, setSelectedDoc] = useState(null);
  const [showUpload, setShowUpload] = useState(false);
  const [showUrlUpload, setShowUrlUpload] = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  const [showCreateCollection, setShowCreateCollection] = useState(false);
  const [url, setUrl] = useState('');
  const [uploading, setUploading] = useState(false);
  const [selectedCollection, setSelectedCollection] = useState(null);
  const [newCollectionName, setNewCollectionName] = useState('');
  const [newCollectionDesc, setNewCollectionDesc] = useState('');
  const [uploadCollectionId, setUploadCollectionId] = useState(null);
  const [creatingCollection, setCreatingCollection] = useState(false);
  const [savingSettings, setSavingSettings] = useState(false);
  const [view, setView] = useState('documents'); // 'documents' | 'trash'
  const [trashDocs, setTrashDocs] = useState([]);
  const [settings, setSettings] = useState({
    chunk_size: 800,
    chunk_overlap: 80,
    auto_summarize: true,
    auto_tag: true,
    summary_language: 'ru',
  });

  const { addNotification } = useNotifications();
  const notify = useRef({ success: () => {}, error: () => {} });
  const searchAbortRef = useRef(null);

  // Обновляем notify после монтирования — стабильная ссылка без замыканий
  useEffect(() => {
    notify.current = {
      success: (msg) => addNotification({ type: 'success', message: msg, duration: 4000 }),
      error: (msg) => addNotification({ type: 'error', message: msg, duration: 5000 }),
    };
  }, [addNotification]);

  // === Закрытие модалок по Escape ===
  useEffect(() => {
    const onKey = (e) => {
      if (e.key !== 'Escape') return;
      if (selectedDoc) setSelectedDoc(null);
      else if (showUpload) setShowUpload(false);
      else if (showUrlUpload) setShowUrlUpload(false);
      else if (showSettings) setShowSettings(false);
      else if (showCreateCollection) setShowCreateCollection(false);
    };
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, [selectedDoc, showUpload, showUrlUpload, showSettings, showCreateCollection]);

  // === Загрузка данных (один раз) ===
  const fetchedRef = useRef(false);
  useEffect(() => {
    if (fetchedRef.current) return;
    fetchedRef.current = true;

    (async () => {
      try {
        setLoading(true);
        const [docsRes, collsRes, statsRes] = await Promise.allSettled([
          apiFetch('/api/v1/documents'),
          apiFetch('/api/v1/collections'),
          apiFetch('/api/v1/documents/stats'),
        ]);

        if (docsRes.status === 'fulfilled' && docsRes.value.ok) {
          const data = await docsRes.value.json();
          setDocuments(data.data || []);
        }
        if (collsRes.status === 'fulfilled' && collsRes.value.ok) {
          const data = await collsRes.value.json();
          setCollections(data.data || []);
        }
        if (statsRes.status === 'fulfilled' && statsRes.value.ok) {
          setStats(await statsRes.value.json());
        }
      } catch (e) {
        console.error('Failed to fetch documents:', e);
        notify.current.error('Не удалось загрузить документы');
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  // === Общая перезагрузка (вызывается после изменений) ===
  const reload = async () => {
    setLoading(true);
    try {
      const [docsRes, collsRes, statsRes] = await Promise.allSettled([
        apiFetch('/api/v1/documents'),
        apiFetch('/api/v1/collections'),
        apiFetch('/api/v1/documents/stats'),
      ]);
      if (docsRes.status === 'fulfilled' && docsRes.value.ok) {
        const data = await docsRes.value.json();
        setDocuments(data.data || []);
      }
      if (collsRes.status === 'fulfilled' && collsRes.value.ok) {
        const data = await collsRes.value.json();
        setCollections(data.data || []);
      }
      if (statsRes.status === 'fulfilled' && statsRes.value.ok) {
        setStats(await statsRes.value.json());
      }
    } catch {
      notify.current.error('Не удалось загрузить документы');
    } finally {
      setLoading(false);
    }
  };

  const handleSearch = async () => {
    if (!searchQuery.trim()) {
      setSearchResults([]);
      return;
    }
    if (searchAbortRef.current) searchAbortRef.current.abort();
    searchAbortRef.current = new AbortController();

    try {
      const res = await apiFetch(
        `/api/v1/documents/search?q=${encodeURIComponent(searchQuery)}`,
        { signal: searchAbortRef.current.signal }
      );
      if (res.ok) {
        const data = await res.json();
        setSearchResults(data.results || []);
      }
    } catch (e) {
      if (e.name !== 'AbortError') {
        console.error('Search failed:', e);
        notify.current.error('Ошибка поиска');
      }
    }
  };

  const handleSaveSettings = async () => {
    setSavingSettings(true);
    try {
      const res = await apiFetch('/api/v1/settings', {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(settings),
      });
      if (res.ok) {
        notify.current.success('Настройки сохранены');
        setShowSettings(false);
      } else {
        notify.current.error('Ошибка сохранения настроек');
      }
    } catch {
      notify.current.error('Ошибка сохранения настроек');
    } finally {
      setSavingSettings(false);
    }
  };

  const handleCreateCollection = async () => {
    if (!newCollectionName.trim()) return;
    setCreatingCollection(true);
    try {
      const res = await apiFetch('/api/v1/collections', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: newCollectionName, description: newCollectionDesc }),
      });
      if (res.ok) {
        notify.current.success('Коллекция создана');
        setShowCreateCollection(false);
        setNewCollectionName('');
        setNewCollectionDesc('');
        reload();
      } else {
        notify.current.error('Ошибка создания коллекции');
      }
    } catch {
      notify.current.error('Ошибка создания коллекции');
    } finally {
      setCreatingCollection(false);
    }
  };

  const handleFileUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    setUploading(true);
    const formData = new FormData();
    formData.append('file', file);
    if (uploadCollectionId && uploadCollectionId !== 'null') {
      formData.append('collection_id', uploadCollectionId);
    }
    try {
      const res = await apiFetch('/api/v1/documents/upload', { method: 'POST', body: formData });
      if (res.ok) {
        notify.current.success('Документ загружен');
        reload();
        setShowUpload(false);
        setUploadCollectionId(null);
      } else {
        const err = await res.json().catch(() => null);
        notify.current.error(err?.detail || 'Ошибка загрузки документа');
      }
    } catch {
      notify.current.error('Ошибка загрузки документа');
    } finally {
      setUploading(false);
    }
  };

  const handleUrlUpload = async () => {
    if (!url.trim()) return;
    setUploading(true);
    try {
      const res = await apiFetch('/api/v1/documents/from-url', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url }),
      });
      if (res.ok) {
        notify.current.success('Документ загружен из URL');
        reload();
        setShowUrlUpload(false);
        setUrl('');
      } else {
        const err = await res.json().catch(() => null);
        notify.current.error(err?.detail || 'Ошибка загрузки по ссылке');
      }
    } catch {
      notify.current.error('Ошибка загрузки по ссылке');
    } finally {
      setUploading(false);
    }
  };

  const handleDelete = async (id) => {
    if (!confirm('Переместить документ в корзину?')) return;
    try {
      const res = await apiFetch(`/api/v1/documents/${id}`, { method: 'DELETE' });
      if (res.ok) {
        notify.current.success('Документ в корзине');
        reload();
      } else {
        notify.current.error('Ошибка удаления документа');
      }
    } catch {
      notify.current.error('Ошибка удаления документа');
    }
  };

  const handleRestore = async (id) => {
    try {
      const res = await apiFetch(`/api/v1/documents/${id}/restore`, { method: 'POST' });
      if (res.ok) {
        notify.current.success('Документ восстановлен');
        loadTrash();
        reload();
      } else {
        notify.current.error('Ошибка восстановления');
      }
    } catch {
      notify.current.error('Ошибка восстановления');
    }
  };

  const handlePermanentDelete = async (id) => {
    if (!confirm('Удалить документ навсегда? Это действие необратимо.')) return;
    try {
      const res = await apiFetch(`/api/v1/documents/trash/clear?document_id=${id}`, { method: 'DELETE' });
      if (res.ok) {
        notify.current.success('Документ удалён навсегда');
        loadTrash();
        reload();
      } else {
        notify.current.error('Ошибка удаления');
      }
    } catch {
      notify.current.error('Ошибка удаления');
    }
  };

  const handleClearTrash = async () => {
    if (!confirm('Очистить корзину? Все документы будут удалены навсегда.')) return;
    try {
      const res = await apiFetch('/api/v1/documents/trash/clear', { method: 'DELETE' });
      if (res.ok) {
        notify.current.success('Корзина очищена');
        loadTrash();
        reload();
      } else {
        notify.current.error('Ошибка очистки корзины');
      }
    } catch {
      notify.current.error('Ошибка очистки корзины');
    }
  };

  const loadTrash = async () => {
    try {
      const res = await apiFetch('/api/v1/documents/trash');
      if (res.ok) {
        const data = await res.json();
        setTrashDocs(data.data || []);
      }
    } catch {
      notify.current.error('Ошибка загрузки корзины');
    }
  };

  const handleMoveToCollection = async (documentId, collectionId) => {
    try {
      const formData = new FormData();
      formData.append('collection_id', collectionId);
      const res = await apiFetch(`/api/v1/documents/${documentId}`, { method: 'PATCH', body: formData });
      if (res.ok) {
        notify.current.success('Документ перемещён');
        reload();
      }
    } catch {
      notify.current.error('Ошибка перемещения документа');
    }
  };

  const filteredDocuments = selectedCollection
    ? documents.filter((d) => d.collection_id === selectedCollection)
    : documents;

  const formatSize = (bytes) => {
    if (!bytes) return '—';
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return '';
    return new Date(dateStr).toLocaleDateString('ru-RU');
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full text-text-muted">
        Загрузка...
      </div>
    );
  }

  return (
    <div className="h-full bg-background text-text-primary">
      <div className="flex h-full">
        {/* Левая панель с коллекциями */}
        <div className="w-64 border-r border-border bg-card p-4 overflow-y-auto shrink-0">
          <h3 className="text-sm font-semibold mb-4 text-text-secondary">📁 Коллекции</h3>
          <div
            className={`p-2 rounded-lg cursor-pointer mb-1 ${
              view === 'documents' && !selectedCollection ? 'bg-primary/20 text-primary' : 'hover:bg-card-hover'
            }`}
            onClick={() => {
              setView('documents');
              setSelectedCollection(null);
              setSearchResults([]);
            }}
          >
            📄 Все документы
            <span className="text-xs text-text-muted ml-2">({documents.length})</span>
          </div>
          {collections.map((coll) => (
            <div
              key={coll.id}
              className={`p-2 rounded-lg cursor-pointer mb-1 ${
                selectedCollection === coll.id ? 'bg-primary/20 text-primary' : 'hover:bg-card-hover'
              }`}
              onClick={() => setSelectedCollection(coll.id)}
            >
              📁 {coll.name}
              <span className="text-xs text-text-muted ml-2">({coll.document_count})</span>
            </div>
          ))}
          <div
            className={`p-2 rounded-lg cursor-pointer mb-1 mt-2 ${
              view === 'trash' ? 'bg-red-900/30 text-red-400' : 'hover:bg-card-hover'
            }`}
            onClick={() => {
              setView('trash');
              setSelectedCollection(null);
              setSearchResults([]);
              loadTrash();
            }}
          >
            🗑️ Корзина
            {stats?.trash_count > 0 && (
              <span className="text-xs text-red-400 ml-2">({stats.trash_count})</span>
            )}
          </div>
          <Button variant="outline" size="sm" className="w-full mt-4" onClick={() => setShowCreateCollection(true)}>
            ➕ Создать коллекцию
          </Button>
        </div>

        {/* Основной контент */}
        <div className="flex-1 p-6 overflow-auto">
          <div className="max-w-6xl mx-auto">
            {/* Header */}
            <div className="flex items-center justify-between mb-6">
              <h1 className="text-2xl font-semibold">
                {view === 'trash' ? '🗑️ Корзина' : '📄 '}
                {view === 'trash' ? '' : (selectedCollection
                  ? collections.find((c) => c.id === selectedCollection)?.name || 'Документы'
                  : 'Все документы')}
              </h1>
              <div className="flex gap-2">
                {view === 'trash' ? (
                  trashDocs.length > 0 && (
                    <Button variant="outline" className="text-red-400 border-red-800" onClick={handleClearTrash}>
                      🗑️ Очистить корзину
                    </Button>
                  )
                ) : (
                  <>
                    <Button onClick={() => setShowUpload(true)}>📎 Загрузить файл</Button>
                    <Button variant="outline" onClick={() => setShowUrlUpload(true)}>
                      🌐 Из URL
                    </Button>
                    <Button variant="outline" onClick={() => setShowSettings(true)}>
                      ⚙️ Настройки
                    </Button>
                  </>
                )}
              </div>
            </div>

            {/* Stats */}
            {stats && view !== 'trash' && (
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
                <Card className="bg-card border border-border">
                  <CardContent className="p-4">
                    <p className="text-xs text-text-muted">Всего документов</p>
                    <p className="text-2xl font-bold">{stats.total_documents}</p>
                  </CardContent>
                </Card>
                <Card className="bg-card border border-border">
                  <CardContent className="p-4">
                    <p className="text-xs text-text-muted">Обработано</p>
                    <p className="text-2xl font-bold text-green-500">{stats.completed_documents}</p>
                  </CardContent>
                </Card>
                <Card className="bg-card border border-border">
                  <CardContent className="p-4">
                    <p className="text-xs text-text-muted">Общий размер</p>
                    <p className="text-2xl font-bold">{stats.total_size_mb} MB</p>
                  </CardContent>
                </Card>
                <Card className="bg-card border border-border">
                  <CardContent className="p-4">
                    <p className="text-xs text-text-muted">Коллекции</p>
                    <p className="text-2xl font-bold">{stats.total_collections}</p>
                  </CardContent>
                </Card>
              </div>
            )}

            {view !== 'trash' && (
              <div className="flex gap-2 mb-6">
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
                  placeholder="Поиск по документам..."
                  className="flex-1 px-4 py-2 bg-card-hover border border-border rounded-lg text-text-primary placeholder-text-muted"
                />
                <Button onClick={handleSearch}>🔍 Поиск</Button>
              </div>
            )}

            {/* Search Results */}
            {searchResults.length > 0 && (
              <Card className="bg-card border border-border mb-6">
                <CardHeader>
                  <CardTitle>Результаты поиска ({searchResults.length})</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-3">
                    {searchResults.map((result, i) => (
                      <div key={i} className="p-3 bg-card-hover rounded-lg">
                        <div className="flex items-center justify-between mb-2">
                          <span className="font-medium">{result.document_title}</span>
                          <span className="text-xs text-green-500">
                            {(result.relevance * 100).toFixed(0)}%
                          </span>
                        </div>
                        <p className="text-sm text-text-secondary line-clamp-2">{result.chunk_text}</p>
                        {result.tags?.length > 0 && (
                          <div className="flex gap-1 mt-2">
                            {result.tags.map((tag, j) => (
                              <span key={j} className="text-xs px-2 py-0.5 bg-primary/20 text-primary rounded">
                                {tag}
                              </span>
                            ))}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            )}

            {/* Documents Table / Trash View */}
            {view === 'trash' ? (
              <Card className="bg-card border border-border">
                <CardHeader>
                  <CardTitle>Корзина ({trashDocs.length})</CardTitle>
                </CardHeader>
                <CardContent className="p-0">
                  {trashDocs.length === 0 ? (
                    <div className="text-center text-text-muted py-8">Корзина пуста.</div>
                  ) : (
                    <div className="overflow-x-auto max-h-[calc(100vh-380px)] overflow-y-auto">
                      <table className="w-full text-sm">
                        <thead className="sticky top-0 bg-card z-10">
                          <tr className="border-b border-border">
                            <th className="text-left py-2 px-3 text-text-muted">Название</th>
                            <th className="text-left py-2 px-3 text-text-muted">Тип</th>
                            <th className="text-left py-2 px-3 text-text-muted">Размер</th>
                            <th className="text-left py-2 px-3 text-text-muted">Дата удаления</th>
                            <th className="text-right py-2 px-3 text-text-muted">Действия</th>
                          </tr>
                        </thead>
                        <tbody>
                          {trashDocs.map((doc) => (
                            <tr key={doc.id} className="border-b border-border/50 hover:bg-card-hover">
                              <td className="py-2 px-3 max-w-[200px] truncate" title={doc.title}>
                                {doc.title}
                              </td>
                              <td className="py-2 px-3 text-text-secondary">
                                {doc.file_type?.split('/')[1] || doc.file_type}
                              </td>
                              <td className="py-2 px-3 text-text-secondary">{formatSize(doc.file_size)}</td>
                              <td className="py-2 px-3 text-text-secondary">{formatDate(doc.created_at)}</td>
                              <td className="py-2 px-3 text-right">
                                <div className="flex gap-1 justify-end">
                                  <Button size="sm" variant="outline" className="text-green-400 border-green-800" onClick={() => handleRestore(doc.id)}>
                                    ↩️ Восстановить
                                  </Button>
                                  <Button size="sm" variant="outline" className="text-red-400 border-red-800" onClick={() => handlePermanentDelete(doc.id)}>
                                    🗑️ Удалить
                                  </Button>
                                </div>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </CardContent>
              </Card>
            ) : (
              <Card className="bg-card border border-border">
                <CardHeader>
                  <CardTitle>Документы ({filteredDocuments.length})</CardTitle>
                </CardHeader>
                <CardContent className="p-0">
                  {filteredDocuments.length === 0 ? (
                    <div className="text-center text-text-muted py-8">Нет документов. Загрузите первый.</div>
                  ) : (
                    <div className="overflow-x-auto max-h-[calc(100vh-380px)] overflow-y-auto">
                      <table className="w-full text-sm">
                        <thead className="sticky top-0 bg-card z-10">
                          <tr className="border-b border-border">
                            <th className="text-left py-2 px-3 text-text-muted">Название</th>
                            <th className="text-left py-2 px-3 text-text-muted">Тип</th>
                            <th className="text-left py-2 px-3 text-text-muted">Размер</th>
                            <th className="text-left py-2 px-3 text-text-muted">Дата</th>
                            <th className="text-left py-2 px-3 text-text-muted">Статус</th>
                            <th className="text-left py-2 px-3 text-text-muted">Коллекция</th>
                            <th className="text-left py-2 px-3 text-text-muted">Теги</th>
                            <th className="text-right py-2 px-3 text-text-muted">Действия</th>
                          </tr>
                        </thead>
                        <tbody>
                          {filteredDocuments.map((doc) => (
                            <tr key={doc.id} className="border-b border-border/50 hover:bg-card-hover">
                              <td className="py-2 px-3 max-w-[200px] truncate" title={doc.title}>
                                {doc.title}
                              </td>
                              <td className="py-2 px-3 text-text-secondary">
                                {doc.file_type?.split('/')[1] || doc.file_type}
                              </td>
                              <td className="py-2 px-3 text-text-secondary">{formatSize(doc.file_size)}</td>
                              <td className="py-2 px-3 text-text-secondary">{formatDate(doc.created_at)}</td>
                              <td className="py-2 px-3">
                                <span
                                  className={`text-xs px-2 py-0.5 rounded ${
                                    doc.status === 'completed'
                                      ? 'bg-green-500/20 text-green-500'
                                      : doc.status === 'failed'
                                      ? 'bg-red-500/20 text-red-500'
                                      : 'bg-yellow-500/20 text-yellow-500'
                                  }`}
                                >
                                  {doc.status}
                                </span>
                              </td>
                              <td className="py-2 px-3">
                                <select
                                  className="bg-transparent text-text-secondary text-xs border-none outline-none cursor-pointer"
                                  value={doc.collection_id || ''}
                                  onChange={(e) => handleMoveToCollection(doc.id, e.target.value || null)}
                                >
                                  <option value="">Без коллекции</option>
                                  {collections.map((c) => (
                                    <option key={c.id} value={c.id}>
                                      {c.name}
                                    </option>
                                  ))}
                                </select>
                              </td>
                              <td className="py-2 px-3">
                                <div className="flex gap-1 flex-wrap">
                                  {doc.tags?.slice(0, 2).map((tag, i) => (
                                    <span key={i} className="text-xs px-2 py-0.5 bg-primary/20 text-primary rounded">
                                      {tag}
                                    </span>
                                  ))}
                                </div>
                              </td>
                              <td className="py-2 px-3 text-right">
                                <div className="flex gap-1 justify-end">
                                  <Button size="sm" variant="outline" onClick={() => setSelectedDoc(doc)}>
                                    👁️
                                  </Button>
                                  <Button size="sm" variant="outline" onClick={() => handleDelete(doc.id)}>
                                    🗑️
                                  </Button>
                                </div>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </CardContent>
              </Card>
            )}
          </div>
        </div>
      </div>

      {/* Модалка создания коллекции */}
      {showCreateCollection && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <Card className="bg-card border border-border w-full max-w-md mx-4 max-h-[90vh] overflow-y-auto">
            <CardHeader>
              <CardTitle>Создать коллекцию</CardTitle>
            </CardHeader>
            <CardContent>
              <input
                type="text"
                value={newCollectionName}
                onChange={(e) => setNewCollectionName(e.target.value)}
                placeholder="Название коллекции"
                className="w-full px-3 py-2 bg-card-hover border border-border rounded-lg text-text-primary mb-3"
                autoFocus
              />
              <textarea
                value={newCollectionDesc}
                onChange={(e) => setNewCollectionDesc(e.target.value)}
                placeholder="Описание (необязательно)"
                className="w-full px-3 py-2 bg-card-hover border border-border rounded-lg text-text-primary mb-4"
                rows={3}
              />
              <Button onClick={handleCreateCollection} loading={creatingCollection}>
                Создать
              </Button>
              <Button variant="outline" className="ml-2" onClick={() => setShowCreateCollection(false)}>
                Отмена
              </Button>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Upload Modal */}
      {showUpload && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <Card className="bg-card border border-border w-full max-w-md mx-4 max-h-[90vh] overflow-y-auto">
            <CardHeader>
              <CardTitle>Загрузить файл</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="mb-4">
                <label className="block text-xs text-text-muted mb-1">Коллекция</label>
                <select
                  className="w-full px-3 py-2 bg-card-hover border border-border rounded-lg text-text-primary"
                  value={uploadCollectionId || ''}
                  onChange={(e) => setUploadCollectionId(e.target.value || null)}
                >
                  <option value="">Без коллекции</option>
                  {collections.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.name}
                    </option>
                  ))}
                </select>
              </div>
              <input
                type="file"
                onChange={handleFileUpload}
                className="w-full file:mr-4 file:px-4 file:py-2 file:rounded-lg file:border-0 file:bg-primary file:text-white file:font-medium file:cursor-pointer file:text-sm"
                accept=".pdf,.docx,.doc,.txt,.md,.csv,.json,.xml,.html"
              />
              {uploading && <p className="text-sm text-text-muted mt-2">Загрузка...</p>}
              <Button variant="outline" className="mt-4" onClick={() => setShowUpload(false)}>
                Отмена
              </Button>
            </CardContent>
          </Card>
        </div>
      )}

      {/* URL Upload Modal */}
      {showUrlUpload && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <Card className="bg-card border border-border w-full max-w-md mx-4 max-h-[90vh] overflow-y-auto">
            <CardHeader>
              <CardTitle>Загрузить из интернета</CardTitle>
            </CardHeader>
            <CardContent>
              <input
                type="text"
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                placeholder="https://example.com/document.pdf"
                className="w-full px-3 py-2 bg-card-hover border border-border rounded-lg text-text-primary mb-4"
                autoFocus
              />
              <Button onClick={handleUrlUpload} loading={uploading}>
                Загрузить
              </Button>
              <Button variant="outline" className="ml-2" onClick={() => setShowUrlUpload(false)}>
                Отмена
              </Button>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Settings Modal */}
      {showSettings && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <Card className="bg-card border border-border w-full max-w-md mx-4 max-h-[90vh] overflow-y-auto">
            <CardHeader>
              <CardTitle>Настройки обработки</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div>
                  <label className="block text-sm text-text-muted mb-1">Размер чанка (токены)</label>
                  <input
                    type="number"
                    value={settings.chunk_size}
                    onChange={(e) => setSettings({ ...settings, chunk_size: parseInt(e.target.value) || 0 })}
                    className="w-full px-3 py-2 bg-card-hover border border-border rounded-lg text-text-primary"
                  />
                </div>
                <div>
                  <label className="block text-sm text-text-muted mb-1">Перекрытие чанков (токены)</label>
                  <input
                    type="number"
                    value={settings.chunk_overlap}
                    onChange={(e) => setSettings({ ...settings, chunk_overlap: parseInt(e.target.value) || 0 })}
                    className="w-full px-3 py-2 bg-card-hover border border-border rounded-lg text-text-primary"
                  />
                </div>
                <div className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={settings.auto_summarize}
                    onChange={(e) => setSettings({ ...settings, auto_summarize: e.target.checked })}
                    className="accent-primary"
                  />
                  <label className="text-sm">Авто-суммаризация</label>
                </div>
                <div className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={settings.auto_tag}
                    onChange={(e) => setSettings({ ...settings, auto_tag: e.target.checked })}
                    className="accent-primary"
                  />
                  <label className="text-sm">Авто-тегирование</label>
                </div>
                <Button onClick={handleSaveSettings} loading={savingSettings}>
                  Сохранить
                </Button>
                <Button variant="outline" className="ml-2" onClick={() => setShowSettings(false)}>
                  Отмена
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Document Viewer Modal */}
      {selectedDoc && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <Card className="bg-card border border-border w-full max-w-4xl max-h-[80vh] overflow-y-auto">
            <CardHeader>
              <CardTitle className="flex items-center justify-between">
                <span className="truncate mr-2">{selectedDoc.title}</span>
                <Button variant="outline" onClick={() => setSelectedDoc(null)}>
                  ✕
                </Button>
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 gap-4 mb-4">
                <div>
                  <p className="text-xs text-text-muted">Тип</p>
                  <p className="text-sm">{selectedDoc.file_type}</p>
                </div>
                <div>
                  <p className="text-xs text-text-muted">Размер</p>
                  <p className="text-sm">{formatSize(selectedDoc.file_size)}</p>
                </div>
                <div>
                  <p className="text-xs text-text-muted">Статус</p>
                  <p className="text-sm">{selectedDoc.status}</p>
                </div>
                <div>
                  <p className="text-xs text-text-muted">Дата</p>
                  <p className="text-sm">{formatDate(selectedDoc.created_at)}</p>
                </div>
              </div>
              {selectedDoc.summary && (
                <div className="mb-4 p-3 bg-card-hover rounded-lg">
                  <p className="text-xs text-text-muted mb-1">Суммаризация</p>
                  <p className="text-sm">{selectedDoc.summary}</p>
                </div>
              )}
              {selectedDoc.tags?.length > 0 && (
                <div className="mb-4">
                  <p className="text-xs text-text-muted mb-1">Теги</p>
                  <div className="flex gap-1 flex-wrap">
                    {selectedDoc.tags.map((tag, i) => (
                      <span key={i} className="text-xs px-2 py-0.5 bg-primary/20 text-primary rounded">
                        {tag}
                      </span>
                    ))}
                  </div>
                </div>
              )}
              {selectedDoc.metadata && (
                <div className="mb-4 p-3 bg-card-hover rounded-lg">
                  <p className="text-xs text-text-muted mb-1">Метаданные</p>
                  <pre className="text-xs text-text-secondary overflow-auto max-h-40">
                    {JSON.stringify(selectedDoc.metadata, null, 2)}
                  </pre>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}