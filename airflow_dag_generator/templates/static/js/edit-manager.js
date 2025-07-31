
/**
 * Модуль для управления редактированием DAG'ов
 */

class EditManager {
    constructor() {
        this.isEditMode = false;
        this.currentDAGId = null;
        this.originalData = null;
        this.notificationContainer = null;

        this.init();
    }

    init() {
        console.log('EditManager initialized');
        this.createNotificationContainer();
        this.initEventListeners();
        this.loadQuickStats();
        this.checkInitialEditMode();
    }

    createNotificationContainer() {
        if (!document.getElementById('notifications-container')) {
            const container = document.createElement('div');
            container.id = 'notifications-container';
            container.style.cssText = 'position: fixed; top: 20px; right: 20px; z-index: 1050; max-width: 400px;';
            document.body.appendChild(container);
        }
        this.notificationContainer = document.getElementById('notifications-container');
    }

    initEventListeners() {
        // Обработчик выпадающего меню быстрого редактирования
        const quickEditDropdown = document.getElementById('quickEditDropdown');
        if (quickEditDropdown) {
            quickEditDropdown.addEventListener('click', () => {
                this.loadRecentDAGs();
            });
        }

        // Обработчик кнопки сброса
        const resetBtn = document.getElementById('reset-form-btn');
        if (resetBtn) {
            resetBtn.addEventListener('click', () => {
                this.exitEditMode();
            });
        }

        // Глобальные обработчики для кнопок редактирования
        document.addEventListener('click', (e) => {
            if (e.target.matches('[data-edit-dag]')) {
                e.preventDefault();
                const dagId = e.target.getAttribute('data-edit-dag');
                this.editDAG(dagId);
            }
        });
    }

    async loadRecentDAGs() {
        const menu = document.getElementById('quick-edit-menu');
        if (!menu) return;

        menu.innerHTML = '<li><a class="dropdown-item" href="#"><i class="fas fa-spinner fa-spin me-2"></i>Загрузка...</a></li>';

        try {
            const response = await fetch('/dag-generator/api/recent-dags');
            const data = await response.json();

            if (data.success && data.dags.length > 0) {
                menu.innerHTML = data.dags.map(dag => `
                    <li>
                        <a class="dropdown-item" href="#" data-edit-dag="${dag.dag_id}">
                            <i class="fas fa-edit me-2"></i>${dag.dag_id}
                            <small class="text-muted d-block">${dag.generator_type}</small>
                        </a>
                    </li>
                `).join('') + `
                    <li><hr class="dropdown-divider"></li>
                    <li><a class="dropdown-item" href="/dag-generator/manage">
                        <i class="fas fa-cogs me-2"></i>Все DAG'и
                    </a></li>
                `;
            } else {
                menu.innerHTML = `
                    <li><a class="dropdown-item text-muted" href="#">
                        <i class="fas fa-info-circle me-2"></i>Нет DAG'ов для редактирования
                    </a></li>
                    <li><hr class="dropdown-divider"></li>
                    <li><a class="dropdown-item" href="/dag-generator/manage">
                        <i class="fas fa-cogs me-2"></i>Управление DAG'ами
                    </a></li>
                `;
            }
        } catch (error) {
            console.error('Error loading recent DAGs:', error);
            menu.innerHTML = `
                <li><a class="dropdown-item text-danger" href="#">
                    <i class="fas fa-exclamation-triangle me-2"></i>Ошибка загрузки
                </a></li>
            `;
        }
    }

    async editDAG(dagId) {
        try {
            this.showLoadingSpinner();

            const response = await fetch(`/dag-generator/api/dag/${dagId}`);
            const data = await response.json();

            if (data.success) {
                this.enterEditMode(dagId, data.dag_info);
            } else {
                throw new Error(data.error || 'DAG не найден');
            }
        } catch (error) {
            console.error('Error loading DAG for editing:', error);
            this.showNotification('error', `Ошибка загрузки DAG'а: ${error.message}`);
            this.hideLoadingSpinner();
        }
    }

    enterEditMode(dagId, dagInfo) {
        this.isEditMode = true;
        this.currentDAGId = dagId;
        this.originalData = dagInfo;

        // Обновляем скрытые поля
        const editModeField = document.getElementById('edit-mode');
        const editingDAGIdField = document.getElementById('editing-dag-id');
        const originalDataField = document.getElementById('original-dag-data');

        if (editModeField) editModeField.value = 'true';
        if (editingDAGIdField) editingDAGIdField.value = dagId;
        if (originalDataField) originalDataField.value = JSON.stringify(dagInfo);

        // Обновляем заголовок
        const formTitle = document.getElementById('form-title');
        const formSubtitle = document.getElementById('form-subtitle');
        if (formTitle) formTitle.textContent = `Редактирование DAG: ${dagId}`;
        if (formSubtitle) formSubtitle.textContent = 'Внесите изменения и сохраните обновленную версию';

        // Показываем индикатор режима редактирования
        const editIndicator = document.getElementById('edit-mode-indicator');
        const resetBtn = document.getElementById('reset-form-btn');
        if (editIndicator) editIndicator.classList.remove('d-none');
        if (resetBtn) resetBtn.classList.remove('d-none');

        // Выбираем правильный генератор
        const generatorSelect = document.getElementById('generator-select');
        if (generatorSelect && dagInfo.gen) {
            generatorSelect.value = dagInfo.gen;

            // Запускаем событие изменения для загрузки формы
            const event = new Event('change', { bubbles: true });
            generatorSelect.dispatchEvent(event);
        }

        // Заполняем форму данными после загрузки полей
        setTimeout(() => {
            this.fillFormWithData(dagInfo.cfg || {});
            this.hideLoadingSpinner();
        }, 1500);

        this.showNotification('info', `Загружен DAG "${dagId}" для редактирования`);
    }

    exitEditMode() {
        this.isEditMode = false;
        this.currentDAGId = null;
        this.originalData = null;

        // Сбрасываем скрытые поля
        const editModeField = document.getElementById('edit-mode');
        const editingDAGIdField = document.getElementById('editing-dag-id');
        const originalDataField = document.getElementById('original-dag-data');

        if (editModeField) editModeField.value = 'false';
        if (editingDAGIdField) editingDAGIdField.value = '';
        if (originalDataField) originalDataField.value = '';

        // Возвращаем заголовок
        const formTitle = document.getElementById('form-title');
        const formSubtitle = document.getElementById('form-subtitle');
        if (formTitle) formTitle.textContent = 'Создать новый DAG';
        if (formSubtitle) formSubtitle.textContent = 'Выберите подходящий шаблон для генерации DAG';

        // Скрываем индикатор режима редактирования
        const editIndicator = document.getElementById('edit-mode-indicator');
        const resetBtn = document.getElementById('reset-form-btn');
        if (editIndicator) editIndicator.classList.add('d-none');
        if (resetBtn) resetBtn.classList.add('d-none');

        // Сбрасываем форму
        const generatorSelect = document.getElementById('generator-select');
        if (generatorSelect) generatorSelect.value = '';

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

        this.showNotification('info', 'Возврат к созданию нового DAG');
    }

    fillFormWithData(data) {
        for (const [key, value] of Object.entries(data)) {
            const field = document.querySelector(`[name="${key}"]`);
            if (field) {
                if (field.type === 'checkbox') {
                    field.checked = Boolean(value);
                } else if (field.type === 'radio') {
                    const radioField = document.querySelector(`[name="${key}"][value="${value}"]`);
                    if (radioField) radioField.checked = true;
                } else {
                    field.value = value;
                }

                // Запускаем событие change для обновления зависимых полей
                const event = new Event('change', { bubbles: true });
                field.dispatchEvent(event);
            }
        }
    }

    async loadQuickStats() {
        try {
            const response = await fetch('/dag-generator/api/stats');
            const stats = await response.json();

            if (stats.success) {
                const totalElement = document.getElementById('total-dags-count');
                const outdatedElement = document.getElementById('outdated-count');
                const recentElement = document.getElementById('recent-activity');

                if (totalElement) totalElement.textContent = stats.total_generated_dags || 0;
                if (outdatedElement) outdatedElement.textContent = stats.outdated_count || 0;
                if (recentElement) recentElement.textContent = stats.recent_activity || 0;
            }
        } catch (error) {
            console.error('Error loading stats:', error);
        }
    }

    checkInitialEditMode() {
        // Проверяем, не передан ли DAG для редактирования через данные
        try {
            const initialDataElement = document.getElementById('initial-data');
            if (initialDataElement) {
                const initialData = JSON.parse(initialDataElement.textContent);
                if (initialData.edit_dag_id && initialData.edit_data && Object.keys(initialData.edit_data).length > 0) {
                    setTimeout(() => {
                        this.enterEditMode(initialData.edit_dag_id, initialData.edit_data);
                    }, 500);
                }
            }
        } catch (error) {
            console.error('Error checking initial edit mode:', error);
        }
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

        // Автоматически убираем через 5 секунд
        setTimeout(() => {
            if (notification.parentNode) {
                notification.remove();
            }
        }, 5000);
    }

    showLoadingSpinner() {
        const spinner = document.getElementById('loading-spinner');
        const container = document.getElementById('dynamic-form-container');

        if (spinner) spinner.classList.remove('d-none');
        if (container) container.classList.add('d-none');
    }

    hideLoadingSpinner() {
        const spinner = document.getElementById('loading-spinner');
        const container = document.getElementById('dynamic-form-container');

        if (spinner) spinner.classList.add('d-none');
        if (container) container.classList.remove('d-none');
    }

    // Геттеры для проверки состояния
    getEditMode() {
        return this.isEditMode;
    }

    getCurrentDAGId() {
        return this.currentDAGId;
    }

    getOriginalData() {
        return this.originalData;
    }
}

// Инициализация при загрузке страницы
document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM loaded, initializing EditManager...');
    window.editManager = new EditManager();
});

// Экспортируем класс для глобального использования
window.EditManager = EditManager;
