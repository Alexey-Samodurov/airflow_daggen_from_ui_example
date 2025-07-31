/**
 * Модуль для поиска и загрузки существующих DAG'ов
 */

class SearchManager {
    constructor() {
        this.searchInput = null;
        this.suggestionsContainer = null;
        this.searchTimeout = null;
        this.notificationContainer = null;

        this.init();
    }

    init() {
        console.log('SearchManager initialized');
        this.createElements();
        this.initEventListeners();
    }

    createElements() {
        // Создаем контейнер для уведомлений если его нет
        if (!document.getElementById('notifications-container')) {
            const container = document.createElement('div');
            container.id = 'notifications-container';
            container.style.cssText = 'position: fixed; top: 20px; right: 20px; z-index: 1050; max-width: 400px;';
            document.body.appendChild(container);
        }
        this.notificationContainer = document.getElementById('notifications-container');
    }

    initEventListeners() {
        // Поиск DAG'ов
        this.searchInput = document.getElementById('dag-search-input');
        this.suggestionsContainer = document.getElementById('search-suggestions');

        if (this.searchInput) {
            this.searchInput.addEventListener('input', (e) => {
                this.handleSearchInput(e.target.value);
            });

            this.searchInput.addEventListener('focus', (e) => {
                if (e.target.value.length >= 2) {
                    this.handleSearchInput(e.target.value);
                }
            });

            // Скрываем подсказки при клике вне поля
            document.addEventListener('click', (e) => {
                if (!e.target.closest('.search-container')) {
                    this.hideSuggestions();
                }
            });
        }
    }

    handleSearchInput(query) {
        // Очищаем предыдущий таймер
        if (this.searchTimeout) {
            clearTimeout(this.searchTimeout);
        }

        if (query.length < 2) {
            this.hideSuggestions();
            return;
        }

        // Задержка для уменьшения количества запросов
        this.searchTimeout = setTimeout(() => {
            this.searchDAGs(query);
        }, 300);
    }

    async searchDAGs(query) {
        try {
            this.showSearchLoading();

            const response = await fetch(`/dag-generator/api/search-dags?q=${encodeURIComponent(query)}`);
            const data = await response.json();

            if (data.success) {
                this.showSuggestions(data.suggestions);
            } else {
                throw new Error(data.error || 'Ошибка поиска');
            }

        } catch (error) {
            console.error('Search error:', error);
            this.showSuggestions([]);
            this.showNotification('error', `Ошибка поиска: ${error.message}`);
        }
    }

    showSearchLoading() {
        if (this.suggestionsContainer) {
            this.suggestionsContainer.innerHTML = `
                <div class="suggestion-item loading">
                    <i class="fas fa-spinner fa-spin me-2"></i>
                    Поиск...
                </div>
            `;
            this.suggestionsContainer.classList.add('show');
        }
    }

    showSuggestions(suggestions) {
        if (!this.suggestionsContainer) return;

        if (suggestions.length === 0) {
            this.suggestionsContainer.innerHTML = `
                <div class="suggestion-item no-results">
                    <i class="fas fa-info-circle me-2 text-muted"></i>
                    Не найдено DAG'ов с такими параметрами
                </div>
            `;
        } else {
            this.suggestionsContainer.innerHTML = suggestions.map(dag => `
                <div class="suggestion-item" data-dag-id="${dag.dag_id}">
                    <div class="suggestion-header">
                        <strong>${dag.dag_id}</strong>
                        <span class="suggestion-meta">${dag.generator_type}</span>
                    </div>
                    <div class="suggestion-description">${dag.description || 'Без описания'}</div>
                    <div class="suggestion-footer">
                        <small class="text-muted">Изменён: ${dag.last_modified}</small>
                    </div>
                </div>
            `).join('');

            // Добавляем обработчики кликов
            this.suggestionsContainer.querySelectorAll('[data-dag-id]').forEach(item => {
                item.addEventListener('click', (e) => {
                    const dagId = e.currentTarget.getAttribute('data-dag-id');
                    this.loadDAGForEdit(dagId);
                });
            });
        }

        this.suggestionsContainer.classList.add('show');
    }

    hideSuggestions() {
        if (this.suggestionsContainer) {
            this.suggestionsContainer.classList.remove('show');
        }
    }

    async loadDAGForEdit(dagId) {
        try {
            this.hideSuggestions();
            this.showLoadingSpinner();

            const response = await fetch(`/dag-generator/api/dag/${dagId}`);
            const data = await response.json();

            if (data.success) {
                // Очищаем поисковое поле
                if (this.searchInput) {
                    this.searchInput.value = '';
                }

                // Переключаемся в режим редактирования
                this.switchToEditMode(dagId, data.dag_info);
            } else {
                throw new Error(data.error || 'DAG не найден');
            }

        } catch (error) {
            console.error('Error loading DAG:', error);
            this.showNotification('error', `Ошибка загрузки: ${error.message}`);
        } finally {
            this.hideLoadingSpinner();
        }
    }

    switchToEditMode(dagId, dagInfo) {
        // Переключаем активную панель
        const createPanel = document.getElementById('create-panel');
        const editPanel = document.getElementById('edit-panel');

        if (createPanel) createPanel.classList.remove('active');
        if (editPanel) editPanel.classList.add('active');

        // Обновляем заголовки
        const editTitle = document.getElementById('edit-panel-title');
        if (editTitle) editTitle.textContent = `Редактирование: ${dagId}`;

        // Выбираем правильный генератор
        const generatorSelect = document.getElementById('generator-select');
        if (generatorSelect && dagInfo.gen) {
            generatorSelect.value = dagInfo.gen;

            // Запускаем событие изменения для загрузки формы
            const event = new Event('change', { bubbles: true });
            generatorSelect.dispatchEvent(event);

            // Заполняем форму данными после небольшой задержки
            setTimeout(() => {
                this.fillFormWithData(dagInfo.cfg || {}, dagId);
            }, 500);
        }

        this.showNotification('info', `Загружен DAG "${dagId}" для редактирования`);
    }

    fillFormWithData(data, originalDagId) {
        // Устанавливаем скрытое поле с оригинальным ID
        const originalIdField = document.getElementById('original-dag-id');
        if (originalIdField) {
            originalIdField.value = originalDagId;
        }

        // Заполняем поля формы
        for (const [key, value] of Object.entries(data)) {
            const field = document.querySelector(`[name="${key}"]`);
            if (field) {
                if (field.type === 'checkbox') {
                    field.checked = Boolean(value);
                } else if (field.type === 'radio') {
                    const radioField = document.querySelector(`[name="${key}"][value="${value}"]`);
                    if (radioField) radioField.checked = true;
                } else {
                    field.value = value || '';
                }

                // Запускаем событие change
                const event = new Event('change', { bubbles: true });
                field.dispatchEvent(event);
            }
        }
    }

    // Методы переключения панелей
    switchToCreateMode() {
        const createPanel = document.getElementById('create-panel');
        const editPanel = document.getElementById('edit-panel');

        if (createPanel) createPanel.classList.add('active');
        if (editPanel) editPanel.classList.remove('active');

        // Очищаем форму
        this.clearForm();
        this.showNotification('info', 'Переключение в режим создания нового DAG');
    }

    clearForm() {
        const generatorSelect = document.getElementById('generator-select');
        if (generatorSelect) generatorSelect.value = '';

        const originalIdField = document.getElementById('original-dag-id');
        if (originalIdField) originalIdField.value = '';

        // Очищаем динамическую форму
        const formContainer = document.getElementById('dynamic-form-container');
        if (formContainer) {
            formContainer.innerHTML = `
                <div id="empty-state" class="empty-state text-center py-5">
                    <div class="empty-icon mb-3">
                        <i class="fas fa-arrow-up fa-4x text-muted opacity-50"></i>
                    </div>
                    <h5 class="text-muted mb-2">Выберите тип генератора</h5>
                    <p class="text-muted mb-0">
                        Для настройки параметров DAG выберите подходящий генератор из списка выше
                    </p>
                </div>
            `;
        }
    }

    showLoadingSpinner() {
        const spinner = document.getElementById('loading-spinner');
        if (spinner) spinner.classList.remove('d-none');
    }

    hideLoadingSpinner() {
        const spinner = document.getElementById('loading-spinner');
        if (spinner) spinner.classList.add('d-none');
    }

    showNotification(type, message) {
        const alertClass = type === 'success' ? 'alert-success' :
                          type === 'warning' ? 'alert-warning' :
                          type === 'info' ? 'alert-info' : 'alert-danger';

        const notification = document.createElement('div');
        notification.className = `alert ${alertClass} alert-dismissible fade show`;
        notification.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;

        this.notificationContainer.appendChild(notification);

        setTimeout(() => {
            if (notification.parentNode) {
                notification.remove();
            }
        }, 5000);
    }
}

// Инициализация при загрузке страницы
document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM loaded, initializing SearchManager...');
    window.searchManager = new SearchManager();
});

window.SearchManager = SearchManager;
