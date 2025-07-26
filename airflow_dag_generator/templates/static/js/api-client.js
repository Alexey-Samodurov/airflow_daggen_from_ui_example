/**
 * API клиент для DAG Generator
 * Очищено от hot-reload рудиментов
 */

class DagGeneratorApiClient {
    constructor() {
        this.baseUrl = '/dag-generator/api';
        this.defaultHeaders = {
            'Content-Type': 'application/json',
        };
    }

    /**
     * Получение CSRF токена
     */
    getCsrfToken() {
        // Пробуем получить из мета-тега
        const metaTag = document.querySelector('meta[name="csrf-token"]');
        if (metaTag) {
            return metaTag.getAttribute('content');
        }
        
        // Пробуем получить из глобальных данных
        if (window.INITIAL_DATA && window.INITIAL_DATA.csrf_token) {
            return window.INITIAL_DATA.csrf_token;
        }
        
        console.warn('CSRF token not found');
        return '';
    }

    /**
     * Базовый метод для запросов
     */
    async _makeRequest(endpoint, options = {}) {
        const url = `${this.baseUrl}${endpoint}`;
        
        const headers = {
            ...this.defaultHeaders,
            ...options.headers
        };

        // Добавляем CSRF токен для POST запросов
        if (options.method === 'POST') {
            headers['X-CSRFToken'] = this.getCsrfToken();
        }

        const requestOptions = {
            ...options,
            headers
        };

        try {
            const response = await fetch(url, requestOptions);
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            return await response.json();
        } catch (error) {
            console.error(`API request failed: ${url}`, error);
            throw error;
        }
    }

    /**
     * Получение списка генераторов
     */
    async getGenerators() {
        return this._makeRequest('/generators');
    }

    /**
     * Получение полей генератора
     */
    async getGeneratorFields(generatorName) {
        return this._makeRequest(`/generator/${generatorName}/fields`);
    }

    /**
     * Ручная перезагрузка генераторов
     */
    async manualReload() {
        return this._makeRequest('/reload/manual', {
            method: 'POST'
        });
    }

    /**
     * Получение статистики обнаружения
     */
    async getDiscoveryStats() {
        return this._makeRequest('/discovery/stats');
    }

    /**
     * Статус системы перезагрузки
     */
    async getReloadStatus() {
        return this._makeRequest('/reload/status');
    }

    /**
     * Предварительный просмотр DAG
     */
    async previewDag(generatorName, config) {
        return this._makeRequest('/preview', {
            method: 'POST',
            body: JSON.stringify({
                generator_type: generatorName,
                config: config
            })
        });
    }

    /**
     * Генерация DAG
     */
    async generateDag(generatorName, config) {
        return this._makeRequest('/generate', {
            method: 'POST',
            body: JSON.stringify({
                generator_type: generatorName,
                config: config
            })
        });
    }

    /**
     * Отладочная информация о реестре
     */
    async getRegistryDebug() {
        return this._makeRequest('/debug/registry');
    }
}

// Создаем глобальный экземпляр
window.dagGeneratorApi = new DagGeneratorApiClient();

// Экспортируем класс для модульного использования
if (typeof module !== 'undefined' && module.exports) {
    module.exports = DagGeneratorApiClient;
}
