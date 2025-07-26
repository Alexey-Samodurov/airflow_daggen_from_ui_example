/**
 * API клиент для взаимодействия с бэкендом DAG Generator
 */

class ApiClient {
    constructor(baseUrl = '/dag-generator') {
        this.baseUrl = baseUrl;
        this.csrfToken = null;
    }

    async _makeRequest(url, options = {}) {
        const fullUrl = `${this.baseUrl}${url}`;

        // Всегда получаем свежий CSRF токен для POST/PUT/DELETE запросов
        if (['POST', 'PUT', 'DELETE'].includes(options.method?.toUpperCase())) {
            console.log('Getting fresh CSRF token...');
            this.csrfToken = await this.getCSRFToken();
            console.log(`CSRF token for ${options.method} request:`, this.csrfToken);
        }

        const defaultOptions = {
            headers: {
                'Content-Type': 'application/json',
                ...(this.csrfToken && { 'X-CSRF-Token': this.csrfToken })
            },
            credentials: 'include',
            ...options
        };

        // Объединяем заголовки правильно
        if (options.headers) {
            defaultOptions.headers = { ...defaultOptions.headers, ...options.headers };
        }

        // Логируем детали запроса
        console.log(`Making ${defaultOptions.method || 'GET'} request to:`, fullUrl);
        console.log('Request headers:', defaultOptions.headers);
        if (defaultOptions.body) {
            console.log('Request body:', defaultOptions.body);
        }

        try {
            const response = await fetch(fullUrl, defaultOptions);
        
            console.log(`Response status: ${response.status} ${response.statusText}`);
            console.log('Response headers:', Object.fromEntries(response.headers.entries()));
        
            if (!response.ok) {
                // Пытаемся получить детали ошибки
                let errorDetails = `HTTP ${response.status}: ${response.statusText}`;
                try {
                    const errorBody = await response.text();
                    console.log('Error response body:', errorBody);
                
                    // Пытаемся распарсить JSON с ошибкой
                    try {
                        const errorJson = JSON.parse(errorBody);
                        if (errorJson.error) {
                            errorDetails += ` - ${errorJson.error}`;
                        }
                    } catch (e) {
                        // Не JSON ошибка, добавляем просто текст
                        if (errorBody) {
                            errorDetails += ` - ${errorBody.substring(0, 200)}`;
                        }
                    }
                } catch (e) {
                    console.log('Could not read error response body:', e);
                }
            
                throw new Error(errorDetails);
            }

            const contentType = response.headers.get('content-type');
            if (contentType && contentType.includes('application/json')) {
                const data = await response.json();
                console.log('Response data:', data);
                return data;
            } else {
                const text = await response.text();
                console.log('Response text:', text);
                return { success: false, error: 'Unexpected response format', data: text };
            }
        } catch (error) {
            console.error(`API request failed: ${fullUrl}`, error);
            throw error;
        }
    }

    // Получение CSRF токена
async getCSRFToken() {
    try {
        console.log('=== GETTING CSRF TOKEN ===');
        
        // Приоритет 1: из INITIAL_DATA
        if (window.INITIAL_DATA && window.INITIAL_DATA.csrf_token) {
            console.log('✓ CSRF token from INITIAL_DATA:', window.INITIAL_DATA.csrf_token);
            return window.INITIAL_DATA.csrf_token;
        }
        console.log('✗ INITIAL_DATA not available');

        // Приоритет 2: из API эндпоинта
        try {
            console.log('Trying to get CSRF token from API...');
            const response = await fetch(`${this.baseUrl}/api/csrf-token`, {
                method: 'GET',
                credentials: 'include'
            });
            
            console.log('CSRF API response status:', response.status);
            
            if (response.ok) {
                const data = await response.json();
                console.log('CSRF API response data:', data);
                if (data.success && data.csrf_token) {
                    console.log('✓ CSRF token from API endpoint:', data.csrf_token);
                    return data.csrf_token;
                }
            }
        } catch (error) {
            console.warn('✗ Failed to get CSRF token from API:', error);
        }

        // Приоритет 3: из мета-тега
        const csrfMeta = document.querySelector('meta[name="csrf-token"]');
        if (csrfMeta) {
            const token = csrfMeta.getAttribute('content');
            console.log('✓ CSRF token from meta tag:', token);
            return token;
        }
        console.log('✗ Meta tag not found');

        console.error('❌ CSRF token not found anywhere!');
        return null;
    } catch (error) {
        console.error('❌ Error getting CSRF token:', error);
        return null;
    }
}


    // Получение списка генераторов
    async getGenerators() {
        return this._makeRequest('/api/generators');
    }

    // Получение информации о конкретном генераторе
    async getGeneratorInfo(generatorType) {
        return this._makeRequest(`/api/generators/${generatorType}`);
    }

    // Получение полей формы для генератора
    async getGeneratorFields(generatorType) {
        return this._makeRequest(`/api/generators/${generatorType}/fields`);
    }

    // Генерация DAG
    async generateDAG(generatorType, formData) {
        console.log('=== GENERATE DAG REQUEST ===');
        console.log('Generator type:', generatorType);
        console.log('Form data:', formData);
        
        // Получаем свежий токен
        const csrfToken = await this.getCSRFToken();
        console.log('CSRF token:', csrfToken);
        
        const requestBody = {
            generator_type: generatorType,
            form_data: formData,
            csrf_token: csrfToken  // Добавляем токен в тело запроса
        };
        
        console.log('Request body JSON:', JSON.stringify(requestBody, null, 2));
        
        return this._makeRequest('/generate', {
            method: 'POST',
            body: JSON.stringify(requestBody)
        });
    }

    // Предпросмотр DAG
    async previewDAG(generatorType, formData) {
        console.log('=== PREVIEW DAG REQUEST ===');
        console.log('Generator type:', generatorType);
        console.log('Form data:', formData);
        
        // Получаем свежий токен
        const csrfToken = await this.getCSRFToken();
        console.log('CSRF token:', csrfToken);
        
        const requestBody = {
            generator_type: generatorType,
            form_data: formData,
            csrf_token: csrfToken  // В теле запроса
        };
        
        console.log('Request body JSON:', JSON.stringify(requestBody, null, 2));
        
        return this._makeRequest('/preview', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRF-Token': csrfToken,      // В заголовке
                'X-CSRFToken': csrfToken,       // Альтернативный заголовок
                'csrf-token': csrfToken,        // Еще один вариант
            },
            body: JSON.stringify(requestBody)
        });
    }

    // Валидация конфигурации
    async validateConfig(generatorType, formData) {
        return this._makeRequest('/api/validate', {
            method: 'POST',
            body: JSON.stringify({
                generator_type: generatorType,
                form_data: formData
            })
        });
    }

    // Перезагрузка генераторов
    async reloadGenerators() {
        return this._makeRequest('/api/reload', {
            method: 'POST'
        });
    }

    // Hot reload управление
    async startHotReload() {
        return this._makeRequest('/api/hot-reload/start', {
            method: 'POST'
        });
    }

    async stopHotReload() {
        return this._makeRequest('/api/hot-reload/stop', {
            method: 'POST'
        });
    }

    async getHotReloadStatus() {
        return this._makeRequest('/api/hot-reload-status');
    }

    // Получение шаблонов и расписаний
    async getTemplatesAndSchedules() {
        return this._makeRequest('/api/templates-and-schedules');
    }

    // Проверка здоровья API
    async healthCheck() {
        return this._makeRequest('/api/health');
    }
}

// Создаем глобальный экземпляр API клиента
window.apiClient = new ApiClient();

// Инициализация при загрузке DOM
document.addEventListener('DOMContentLoaded', function() {
    console.log('API Client initialized');
});
