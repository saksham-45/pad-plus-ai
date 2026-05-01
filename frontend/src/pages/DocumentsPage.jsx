import { useState, useEffect, useCallback } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { useNotifications } from '../hooks/useNotifications';

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
  const [settings, setSettings] = useState({
    chunk_size: 800,
    chunk_overlap: 80,
    auto_summarize: true,
    auto_tag: true,
    summary_language: 'ru',
  });

  // Временное решение пока не настроен NotificationProvider
  const notifySuccess = (message) => console.log('✅', message);
  const notifyError = (message) => console.error('❌', message);

  const getToken = () => localStorage.getItem('access_token');

  const fetchData = useCallback(async () => {
    const token = getToken();
    if (!token) return;

    try {
      const [docsRes, collsRes, statsRes] = await Promise.all([
        fetch('/api/v1/documents', { headers: { Authorization: `Bearer ${token}` } }),
        fetch('/api/v1/collections', { headers: { Authorization: `Bearer ${token}` } }),
        fetch('/api/v1/documents/stats', { headers: { Authorization: `Bearer ${token}` } }),
      ]);

      if (docsRes.ok) {
        const data = await docsRes.json();
        setDocuments(data.data || []);
      }
      if (collsRes.ok) {
        const data = await collsRes.json();
        setCollections(data.data || []);
      }
      if (statsRes.ok) {
        setStats(await statsRes.json());
      }
    } catch (e) {
      console.error('Failed to fetch documents:', e);
      notifyError('Не удалось загрузить документы');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleSearch = async () => {
    if (!searchQuery.trim()) {
      setSearchResults([]);
      return;
    }
    const token = getToken();
    try {
      const res = await fetch(`/api/v1/documents/search?q=${encodeURIComponent(searchQuery)}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const data = await res.json();
        setSearchResults(data.results || []);
      }
    } catch (e) {
      console.error('Search failed:', e);
    }
  };

  const handleCreateCollection = async () => {
    if (!newCollectionName.trim()) return;
    
    const token = getToken();
    try {
      const res = await fetch('/api/v1/collections', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          name: newCollectionName,
          description: newCollectionDesc
        }),
      });
      
      if (res.ok) {
        notifySuccess('Коллекция создана');
        setShowCreateCollection(false);
        setNewCollectionName('');
        setNewCollectionDesc('');
        fetchData();
      } else {
        notifyError('Ошибка создания коллекции');
      }
    } catch (e) {
      notifyError('Ошибка создания коллекции');
    }
  };

  const handleFileUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    setUploading(true);
    const token = getToken();
    const formData = new FormData();
    formData.append('file', file);
    if (uploadCollectionId && uploadCollectionId !== 'null') {
      formData.append('collection_id', uploadCollectionId);
    }

    try {
      const res = await fetch('/api/v1/documents/upload', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`
        },
        body: formData,
      });
      if (res.ok) {
        notifySuccess('Документ загружен');
        fetchData();
        setShowUpload(false);
        setUploadCollectionId(null);
      } else {
        notifyError('Ошибка загрузки документа');
      }
    } catch (e) {
      console.error('Upload failed:', e);
      notifyError('Ошибка загрузки документа');
    } finally {
      setUploading(false);
    }
  };

  const handleUrlUpload = async () => {
    if (!url.trim()) return;
    setUploading(true);
    const token = getToken();

    try {
      const res = await fetch('/api/v1/documents/from-url', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ url }),
      });
      if (res.ok) {
        notifySuccess('Документ загружен из URL');
        fetchData();
        setShowUrlUpload(false);
        setUrl('');
      } else {
        notifyError('Ошибка загрузки по ссылке');
      }
    } catch (e) {
      console.error('URL upload failed:', e);
      notifyError('Ошибка загрузки по ссылке');
    } finally {
      setUploading(false);
    }
  };

  const handleDelete = async (id) => {
    if (!confirm('Удалить документ?')) return;
    const token = getToken();
    try {
      const res = await fetch(`/api/v1/documents/${id}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        notifySuccess('Документ удалён');
        fetchData();
      }
    } catch (e) {
      console.error('Delete failed:', e);
      notifyError('Ошибка удаления документа');
    }
  };

  const handleMoveToCollection = async (documentId, collectionId) => {
    const token = getToken();
    try {
      const formData = new FormData();
      formData.append('collection_id', collectionId);
      
      const res = await fetch(`/api/v1/documents/${documentId}`, {
        method: 'PATCH',
        headers: { Authorization: `Bearer ${token}` },
        body: formData,
      });
      
      if (res.ok) {
        notifySuccess('Документ перемещён');
        fetchData();
      }
    } catch (e) {
      notifyError('Ошибка перемещения документа');
    }
  };

  const handleView = async (doc) => {
    setSelectedDoc(doc);
  };

  const filteredDocuments = selectedCollection 
    ? documents.filter(d => d.collection_id === selectedCollection)
    : documents;

  const formatSize = (bytes) => {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return '';
    return new Date(dateStr).toLocaleDateString('ru-RU');
  };

  if (loading) {
    return <div className="flex items-center justify-center h-screen text-gray-400">Загрузка...</div>;
  }

  return (
    <div className="min-h-screen bg-[#0B0F14] text-white">
      <div className="flex h-full">
        
        {/* Левая панель с коллекциями */}
        <div className="w-64 border-r border-[#1F2937] p-4 bg-[#111827]">
          <h3 className="text-sm font-semibold mb-4 text-gray-300">📁 Коллекции</h3>
          
          <div 
            className={`p-2 rounded-lg cursor-pointer mb-2 ${!selectedCollection ? 'bg-[#6366F1]/20 text-[#6366F1]' : 'hover:bg-[#1F2937]'}`}
            onClick={() => setSelectedCollection(null)}
          >
            📄 Все документы
            <span className="text-xs text-gray-400 ml-2">({documents.length})</span>
          </div>

          {collections.map(coll => (
            <div 
              key={coll.id}
              className={`p-2 rounded-lg cursor-pointer mb-1 ${selectedCollection === coll.id ? 'bg-[#6366F1]/20 text-[#6366F1]' : 'hover:bg-[#1F2937]'}`}
              onClick={() => setSelectedCollection(coll.id)}
            >
              📁 {coll.name}
              <span className="text-xs text-gray-400 ml-2">({coll.document_count})</span>
            </div>
          ))}

          <Button 
            variant="outline" 
            size="sm" 
            className="w-full mt-4"
            onClick={() => setShowCreateCollection(true)}
          >
            ➕ Создать коллекцию
          </Button>
        </div>

        {/* Основной контент */}
        <div className="flex-1 p-6 overflow-auto">
          <div className="max-w-6xl mx-auto">
            {/* Header */}
            <div className="flex items-center justify-between mb-6">
              <h1 className="text-2xl font-semibold">
                📄 {selectedCollection 
                  ? collections.find(c => c.id === selectedCollection)?.name || 'Документы' 
                  : 'Все документы'}
              </h1>
              <div className="flex gap-2">
                <Button onClick={() => setShowUpload(true)}>📎 Загрузить файл</Button>
                <Button variant="outline" onClick={() => setShowUrlUpload(true)}>🌐 Из URL</Button>
                <Button variant="outline" onClick={() => setShowSettings(true)}>⚙️ Настройки</Button>
              </div>
            </div>

            {/* Stats */}
            {stats && (
              <div className="grid grid-cols-4 gap-4 mb-6">
                <Card className="bg-[#111827] border border-[#1F2937]">
                  <CardContent className="p-4">
                    <p className="text-xs text-gray-400">Всего документов</p>
                    <p className="text-2xl font-bold">{stats.total_documents}</p>
                  </CardContent>
                </Card>
                <Card className="bg-[#111827] border border-[#1F2937]">
                  <CardContent className="p-4">
                    <p className="text-xs text-gray-400">Обработано</p>
                    <p className="text-2xl font-bold text-green-500">{stats.completed_documents}</p>
                  </CardContent>
                </Card>
                <Card className="bg-[#111827] border border-[#1F2937]">
                  <CardContent className="p-4">
                    <p className="text-xs text-gray-400">Общий размер</p>
                    <p className="text-2xl font-bold">{stats.total_size_mb} MB</p>
                  </CardContent>
                </Card>
                <Card className="bg-[#111827] border border-[#1F2937]">
                  <CardContent className="p-4">
                    <p className="text-xs text-gray-400">Коллекции</p>
                    <p className="text-2xl font-bold">{stats.total_collections}</p>
                  </CardContent>
                </Card>
              </div>
            )}

            {/* Search */}
            <div className="flex gap-2 mb-6">
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
                placeholder="Поиск по документам..."
                className="flex-1 px-4 py-2 bg-[#1F2937] border border-[#374151] rounded-lg text-white"
              />
              <Button onClick={handleSearch}>🔍 Поиск</Button>
            </div>

            {/* Search Results */}
            {searchResults.length > 0 && (
              <Card className="bg-[#111827] border border-[#1F2937] mb-6">
                <CardHeader>
                  <CardTitle>Результаты поиска ({searchResults.length})</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-3">
                    {searchResults.map((result, i) => (
                      <div key={i} className="p-3 bg-[#1F2937] rounded-lg">
                        <div className="flex items-center justify-between mb-2">
                          <span className="font-medium">{result.document_title}</span>
                          <span className="text-xs text-green-500">{(result.relevance * 100).toFixed(0)}%</span>
                        </div>
                        <p className="text-sm text-gray-400 line-clamp-2">{result.chunk_text}</p>
                        {result.tags && result.tags.length > 0 && (
                          <div className="flex gap-1 mt-2">
                            {result.tags.map((tag, j) => (
                              <span key={j} className="text-xs px-2 py-0.5 bg-[#6366F1]/20 text-[#6366F1] rounded">{tag}</span>
                            ))}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            )}

            {/* Documents Table */}
            <Card className="bg-[#111827] border border-[#1F2937]">
              <CardHeader>
                <CardTitle>Документы ({filteredDocuments.length})</CardTitle>
              </CardHeader>
              <CardContent>
                {filteredDocuments.length === 0 ? (
                  <div className="text-center text-gray-500 py-8">Нет документов. Загрузите первый.</div>
                ) : (
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="border-b border-[#374151]">
                          <th className="text-left py-2 px-3 text-gray-400">Название</th>
                          <th className="text-left py-2 px-3 text-gray-400">Тип</th>
                          <th className="text-left py-2 px-3 text-gray-400">Размер</th>
                          <th className="text-left py-2 px-3 text-gray-400">Дата</th>
                          <th className="text-left py-2 px-3 text-gray-400">Статус</th>
                          <th className="text-left py-2 px-3 text-gray-400">Коллекция</th>
                          <th className="text-left py-2 px-3 text-gray-400">Теги</th>
                          <th className="text-right py-2 px-3 text-gray-400">Действия</th>
                        </tr>
                      </thead>
                      <tbody>
                        {filteredDocuments.map((doc) => (
                          <tr key={doc.id} className="border-b border-[#1F2937] hover:bg-[#1F2937]/50">
                            <td className="py-2 px-3">{doc.title}</td>
                            <td className="py-2 px-3 text-gray-400">{doc.file_type?.split('/')[1] || doc.file_type}</td>
                            <td className="py-2 px-3 text-gray-400">{formatSize(doc.file_size)}</td>
                            <td className="py-2 px-3 text-gray-400">{formatDate(doc.created_at)}</td>
                            <td className="py-2 px-3">
                              <span className={`text-xs px-2 py-0.5 rounded ${
                                doc.status === 'completed' ? 'bg-green-500/20 text-green-500' :
                                doc.status === 'failed' ? 'bg-red-500/20 text-red-500' :
                                'bg-yellow-500/20 text-yellow-500'
                              }`}>
                                {doc.status}
                              </span>
                            </td>
                            <td className="py-2 px-3">
                              <select 
                                className="bg-transparent text-gray-400 text-xs border-none outline-none cursor-pointer"
                                value={doc.collection_id || ''}
                                onChange={(e) => handleMoveToCollection(doc.id, e.target.value || null)}
                              >
                                <option value="">Без коллекции</option>
                                {collections.map(c => (
                                  <option key={c.id} value={c.id}>{c.name}</option>
                                ))}
                              </select>
                            </td>
                            <td className="py-2 px-3">
                              <div className="flex gap-1 flex-wrap">
                                {doc.tags?.slice(0, 2).map((tag, i) => (
                                  <span key={i} className="text-xs px-2 py-0.5 bg-[#6366F1]/20 text-[#6366F1] rounded">{tag}</span>
                                ))}
                              </div>
                            </td>
                            <td className="py-2 px-3 text-right">
                              <div className="flex gap-1 justify-end">
                                <Button size="sm" variant="outline" onClick={() => handleView(doc)}>👁️</Button>
                                <Button size="sm" variant="outline" onClick={() => handleDelete(doc.id)}>🗑️</Button>
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
          </div>
        </div>
      </div>

      {/* Модалка создания коллекции */}
      {showCreateCollection && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <Card className="bg-[#111827] border border-[#1F2937] w-full max-w-md mx-4">
            <CardHeader>
              <CardTitle>Создать коллекцию</CardTitle>
            </CardHeader>
            <CardContent>
              <input
                type="text"
                value={newCollectionName}
                onChange={(e) => setNewCollectionName(e.target.value)}
                placeholder="Название коллекции"
                className="w-full px-3 py-2 bg-[#1F2937] border border-[#374151] rounded-lg text-white mb-3"
              />
              <textarea
                value={newCollectionDesc}
                onChange={(e) => setNewCollectionDesc(e.target.value)}
                placeholder="Описание (необязательно)"
                className="w-full px-3 py-2 bg-[#1F2937] border border-[#374151] rounded-lg text-white mb-4"
                rows={3}
              />
              <Button onClick={handleCreateCollection}>Создать</Button>
              <Button variant="outline" className="ml-2" onClick={() => setShowCreateCollection(false)}>Отмена</Button>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Upload Modal */}
      {showUpload && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <Card className="bg-[#111827] border border-[#1F2937] w-full max-w-md mx-4">
            <CardHeader>
              <CardTitle>Загрузить файл</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="mb-4">
                <label className="block text-xs text-gray-400 mb-1">Коллекция</label>
                <select 
                  className="w-full px-3 py-2 bg-[#1F2937] border border-[#374151] rounded-lg text-white"
                  value={uploadCollectionId || ''}
                  onChange={(e) => setUploadCollectionId(e.target.value || null)}
                >
                  <option value="">Без коллекции</option>
                  {collections.map(c => (
                    <option key={c.id} value={c.id}>{c.name}</option>
                  ))}
                </select>
              </div>
              <input
                type="file"
                onChange={handleFileUpload}
                className="w-full"
                accept=".pdf,.docx,.doc,.txt,.md,.csv,.json,.xml,.html"
              />
              {uploading && <p className="text-sm text-gray-400 mt-2">Загрузка...</p>}
              <Button variant="outline" className="mt-4" onClick={() => setShowUpload(false)}>Отмена</Button>
            </CardContent>
          </Card>
        </div>
      )}

      {/* URL Upload Modal */}
      {showUrlUpload && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <Card className="bg-[#111827] border border-[#1F2937] w-full max-w-md mx-4">
            <CardHeader>
              <CardTitle>Загрузить из интернета</CardTitle>
            </CardHeader>
            <CardContent>
              <input
                type="text"
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                placeholder="https://example.com/document.pdf"
                className="w-full px-3 py-2 bg-[#1F2937] border border-[#374151] rounded-lg text-white mb-4"
              />
              <Button onClick={handleUrlUpload} loading={uploading}>Загрузить</Button>
              <Button variant="outline" className="ml-2" onClick={() => setShowUrlUpload(false)}>Отмена</Button>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Settings Modal */}
      {showSettings && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <Card className="bg-[#111827] border border-[#1F2937] w-full max-w-md mx-4">
            <CardHeader>
              <CardTitle>Настройки обработки</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div>
                  <label className="block text-sm text-gray-400 mb-1">Размер чанка (токены)</label>
                  <input
                    type="number"
                    value={settings.chunk_size}
                    onChange={(e) => setSettings({...settings, chunk_size: parseInt(e.target.value)})}
                    className="w-full px-3 py-2 bg-[#1F2937] border border-[#374151] rounded-lg text-white"
                  />
                </div>
                <div className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={settings.auto_summarize}
                    onChange={(e) => setSettings({...settings, auto_summarize: e.target.checked})}
                  />
                  <label className="text-sm">Авто-суммаризация</label>
                </div>
                <div className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={settings.auto_tag}
                    onChange={(e) => setSettings({...settings, auto_tag: e.target.checked})}
                  />
                  <label className="text-sm">Авто-тегирование</label>
                </div>
                <Button onClick={() => setShowSettings(false)}>Сохранить</Button>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Document Viewer Modal */}
      {selectedDoc && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <Card className="bg-[#111827] border border-[#1F2937] w-full max-w-4xl max-h-[80vh] overflow-y-auto">
            <CardHeader>
              <CardTitle className="flex items-center justify-between">
                <span>{selectedDoc.title}</span>
                <Button variant="outline" onClick={() => setSelectedDoc(null)}>✕</Button>
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 gap-4 mb-4">
                <div>
                  <p className="text-xs text-gray-400">Тип</p>
                  <p className="text-sm">{selectedDoc.file_type}</p>
                </div>
                <div>
                  <p className="text-xs text-gray-400">Размер</p>
                  <p className="text-sm">{formatSize(selectedDoc.file_size)}</p>
                </div>
                <div>
                  <p className="text-xs text-gray-400">Статус</p>
                  <p className="text-sm">{selectedDoc.status}</p>
                </div>
                <div>
                  <p className="text-xs text-gray-400">Дата</p>
                  <p className="text-sm">{formatDate(selectedDoc.created_at)}</p>
                </div>
              </div>

              {selectedDoc.summary && (
                <div className="mb-4 p-3 bg-[#1F2937] rounded-lg">
                  <p className="text-xs text-gray-400 mb-1">Суммаризация</p>
                  <p className="text-sm">{selectedDoc.summary}</p>
                </div>
              )}

              {selectedDoc.tags && selectedDoc.tags.length > 0 && (
                <div className="mb-4">
                  <p className="text-xs text-gray-400 mb-1">Теги</p>
                  <div className="flex gap-1 flex-wrap">
                    {selectedDoc.tags.map((tag, i) => (
                      <span key={i} className="text-xs px-2 py-0.5 bg-[#6366F1]/20 text-[#6366F1] rounded">{tag}</span>
                    ))}
                  </div>
                </div>
              )}

              {selectedDoc.metadata && (
                <div className="mb-4 p-3 bg-[#1F2937] rounded-lg">
                  <p className="text-xs text-gray-400 mb-1">Метаданные</p>
                  <pre className="text-xs text-gray-300 overflow-auto max-h-40">
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
