/**
 * Общие функции для всех страниц DAG Generator
 * Очищено от hot-reload рудиментов
 */

/**
 * Инициализация страницы
 */
function initializePage() {
    console.log('Main.js initialized');
    
    // Проверяем наличие глобальных данных
    if (window.INITIAL_DATA) {
        console.log('INITIAL_DATA available:', window.INITIAL_DATA);
    }
}

/**
 * Обработка ошибок API
 */
function handleApiError(error, context = 'API call') {
    console.error(`${context} error:`, error);
    
    // Показываем уведомление если функция доступна
    if (typeof showNotification === 'function') {
        showNotification('error', `Ошибка: ${error.message}`);
    }
}

/**
 * Обработка успешных ответов API
 */
function handleApiSuccess(data, context = 'API call') {
    console.log(`${context} success:`, data);
    
    // Показываем уведомление если функция доступна
    if (typeof showNotification === 'function' && data.message) {
        showNotification('success', data.message);
    }
}

// Простая автоинициализация
document.addEventListener('DOMContentLoaded', initializePage);
