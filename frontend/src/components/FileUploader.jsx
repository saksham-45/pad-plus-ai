import { useState, useRef } from 'react';
import { Button } from './ui/Button';

export default function FileUploader({ 
  onUpload, 
  acceptedTypes = ['*/*'], 
  maxSize = 10 * 1024 * 1024, // 10MB по умолчанию
  multiple = false,
  className = ''
}) {
  const [files, setFiles] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState(null);
  const fileInputRef = useRef(null);

  // Обработка выбора файлов
  const handleFileSelect = (event) => {
    const selectedFiles = Array.from(event.target.files);
    setError(null);

    // Проверка размера
    for (const file of selectedFiles) {
      if (file.size > maxSize) {
        setError(`Файл "${file.name}" слишком большой. Максимальный размер: ${formatSize(maxSize)}`);
        return;
      }
    }

    // Проверка типа
    for (const file of selectedFiles) {
      if (!acceptedTypes.includes('*/*') && !acceptedTypes.some(type => {
        if (type.endsWith('/*')) {
          return file.type.startsWith(type.slice(0, -2));
        }
        return file.type === type || file.name.endsWith(type.slice(1));
      })) {
        setError(`Файл "${file.name}" имеет недопустимый тип`);
        return;
      }
    }

    if (multiple) {
      setFiles(prev => [...prev, ...selectedFiles]);
    } else {
      setFiles([selectedFiles[0]]);
    }

    // Сбрасываем input
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  // Удаление файла
  const removeFile = (index) => {
    setFiles(prev => prev.filter((_, i) => i !== index));
  };

  // Загрузка файлов
  const uploadFiles = async () => {
    if (files.length === 0) return;

    setUploading(true);
    setProgress(0);
    setError(null);

    try {
      const token = localStorage.getItem('access_token');
      const uploadedFiles = [];

      for (const file of files) {
        const formData = new FormData();
        formData.append('file', file);

        const result = await fetch('/api/v1/files/upload', {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${token}`,
          },
          body: formData,
        });

        if (!result.ok) {
          throw new Error('Ошибка загрузки файла');
        }

        const data = await result.json();
        uploadedFiles.push(data);

        // Обновляем прогресс
        setProgress(Math.round((uploadedFiles.length / files.length) * 100));
      }

      // Вызываем колбэк
      if (onUpload) {
        onUpload(uploadedFiles);
      }

      // Очищаем список
      setFiles([]);

    } catch (err) {
      setError(err.message);
    } finally {
      setUploading(false);
    }
  };

  // Форматирование размера
  const formatSize = (bytes) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
  };

  // Получение иконки для типа файла
  const getFileIcon = (file) => {
    if (file.type.startsWith('image/')) return '🖼️';
    if (file.type === 'application/pdf') return '📄';
    if (file.type.includes('document')) return '📝';
    if (file.type.includes('spreadsheet')) return '📊';
    if (file.type.includes('presentation')) return '📊';
    if (file.type.includes('zip') || file.type.includes('rar')) return '📦';
    if (file.type.startsWith('text/')) return '📃';
    return '📎';
  };

  return (
    <div className={`space-y-4 ${className}`}>
      {/* Кнопка выбора файлов */}
      <div className="flex items-center gap-4">
        <input
          ref={fileInputRef}
          type="file"
          multiple={multiple}
          accept={acceptedTypes.join(',')}
          onChange={handleFileSelect}
          className="hidden"
        />
        
        <Button
          variant="outline"
          onClick={() => fileInputRef.current?.click()}
          disabled={uploading}
        >
          📎 Выбрать файл{multiple && 'ы'}
        </Button>

        {files.length > 0 && (
          <Button
            onClick={uploadFiles}
            disabled={uploading}
          >
            {uploading ? 'Загрузка...' : `Загрузить (${files.length})`}
          </Button>
        )}
      </div>

      {/* Прогресс бар */}
      {uploading && (
        <div className="w-full bg-gray-700 rounded-full h-2">
          <div
            className="bg-primary h-2 rounded-full transition-all"
            style={{ width: `${progress}%` }}
          />
        </div>
      )}

      {/* Сообщение об ошибке */}
      {error && (
        <div className="text-red-400 text-sm bg-red-900/20 p-2 rounded">
          {error}
        </div>
      )}

      {/* Список файлов */}
      {files.length > 0 && (
        <div className="space-y-2">
          {files.map((file, index) => (
            <div
              key={`${file.name}-${index}`}
              className="flex items-center justify-between p-3 bg-card border border-border rounded-lg"
            >
              <div className="flex items-center gap-3">
                <span className="text-xl">{getFileIcon(file)}</span>
                <div>
                  <p className="text-sm text-text-primary truncate max-w-xs">
                    {file.name}
                  </p>
                  <p className="text-xs text-text-secondary">
                    {formatSize(file.size)}
                  </p>
                </div>
              </div>
              <button
                onClick={() => removeFile(index)}
                className="text-text-secondary hover:text-red-400 transition-colors"
                disabled={uploading}
              >
                ✕
              </button>
            </div>
          ))}
        </div>
      )}

      {/* Подсказка */}
      <p className="text-xs text-text-secondary">
        Максимальный размер: {formatSize(maxSize)}
        {multiple ? '. Можно выбрать несколько файлов.' : ''}
      </p>
    </div>
  );
}