/**
 * Сервис кэширования моделей провайдеров
 * Хранит список моделей в localStorage с TTL 24 часа
 */

const CACHE_KEY = 'provider_models_cache';
const CACHE_TTL = 24 * 60 * 60 * 1000; // 24 часа в миллисекундах

/**
 * Получить кэшированные модели для провайдера
 * @param {string} providerId - ID провайдера
 * @returns {{ models: Array, timestamp: number, isExpired: boolean } | null}
 */
export function getCachedModels(providerId) {
  try {
    const cacheJson = localStorage.getItem(CACHE_KEY);
    if (!cacheJson) return null;

    const cache = JSON.parse(cacheJson);
    const providerCache = cache[providerId];
    
    if (!providerCache) return null;

    return {
      models: providerCache.models,
      timestamp: providerCache.timestamp,
      isExpired: Date.now() - providerCache.timestamp > CACHE_TTL
    };
  } catch (error) {
    console.error('Failed to get cached models:', error);
    return null;
  }
}

/**
 * Сохранить модели в кэш
 * @param {string} providerId - ID провайдера
 * @param {Array} models - Массив моделей
 */
export function cacheModels(providerId, models) {
  try {
    const cacheJson = localStorage.getItem(CACHE_KEY);
    const cache = cacheJson ? JSON.parse(cacheJson) : {};

    cache[providerId] = {
      models,
      timestamp: Date.now()
    };

    localStorage.setItem(CACHE_KEY, JSON.stringify(cache));
  } catch (error) {
    console.error('Failed to cache models:', error);
  }
}

/**
 * Проверить валидность кэша для провайдера
 * @param {string} providerId - ID провайдера
 * @returns {boolean}
 */
export function isCacheValid(providerId) {
  const cached = getCachedModels(providerId);
  return cached !== null && !cached.isExpired;
}

/**
 * Получить статус кэша для отображения
 * @param {string} providerId - ID провайдера
 * @returns {{ status: 'fresh' | 'stale' | 'none', message: string }}
 */
export function getCacheStatus(providerId) {
  const cached = getCachedModels(providerId);
  
  if (!cached) {
    return {
      status: 'none',
      message: 'Нет кэша'
    };
  }

  if (cached.isExpired) {
    return {
      status: 'stale',
      message: 'Данные устарели'
    };
  }

  return {
    status: 'fresh',
    message: 'Актуальные данные'
  };
}

/**
 * Очистить кэш для провайдера
 * @param {string} providerId - ID провайдера
 */
export function clearCache(providerId) {
  try {
    const cacheJson = localStorage.getItem(CACHE_KEY);
    if (!cacheJson) return;

    const cache = JSON.parse(cacheJson);
    delete cache[providerId];
    localStorage.setItem(CACHE_KEY, JSON.stringify(cache));
  } catch (error) {
    console.error('Failed to clear cache:', error);
  }
}

/**
 * Очистить весь кэш моделей
 */
export function clearAllCache() {
  try {
    localStorage.removeItem(CACHE_KEY);
  } catch (error) {
    console.error('Failed to clear all cache:', error);
  }
}

/**
 * Получить отфильтрованные доступные модели
 * @param {Array} models - Массив всех моделей
 * @returns {Array} - Массив доступных моделей (бесплатные + в рамках лимита)
 */
export function getAvailableModels(models) {
  if (!Array.isArray(models)) return [];

  return models
    .filter(model => {
      // Показываем бесплатные модели или модели с низкой стоимостью
      const cost = model.cost?.toLowerCase() || '';
      return cost === 'free' || cost === 'low';
    })
    .sort((a, b) => {
      // Сначала бесплатные
      const aFree = (a.cost?.toLowerCase() || '') === 'free';
      const bFree = (b.cost?.toLowerCase() || '') === 'free';
      if (aFree && !bFree) return -1;
      if (!aFree && bFree) return 1;
      
      // Затем популярные (если есть метка)
      const aPopular = a.popular || false;
      const bPopular = b.popular || false;
      if (aPopular && !bPopular) return -1;
      if (!aPopular && bPopular) return 1;
      
      return 0;
    });
}

/**
 * Форматировать информацию о модели для отображения
 * @param {Object} model - Объект модели
 * @returns {string} - Форматированная строка
 */
export function formatModelInfo(model) {
  const parts = [model.name || model.id];
  
  if (model.max_tokens) {
    const tokensK = Math.round(model.max_tokens / 1000);
    parts.push(`${tokensK}K tokens`);
  }
  
  if (model.cost && model.cost.toLowerCase() === 'free') {
    parts.push('FREE');
  } else if (model.cost_per_1k) {
    parts.push(`$${model.cost_per_1k}/1K`);
  }
  
  return parts.join(' | ');
}

export default {
  getCachedModels,
  cacheModels,
  isCacheValid,
  getCacheStatus,
  clearCache,
  clearAllCache,
  getAvailableModels,
  formatModelInfo
};