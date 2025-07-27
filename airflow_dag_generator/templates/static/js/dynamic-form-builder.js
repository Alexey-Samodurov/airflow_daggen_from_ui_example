/**
 * Конструктор динамических форм для генераторов DAG
 */
class DynamicFormBuilder {
    constructor(containerId) {
        this.container = document.getElementById(containerId);
        this.currentGeneratorType = null;
        this.fieldsConfig = null;
        this.validationRules = {};
    }

    async loadGeneratorForm(generatorType) {
        if (!generatorType) {
            this._showEmptyState();
            return;
        }

        this.currentGeneratorType = generatorType;
        this._showLoading();

        try {
            const response = await fetch(`/dag-generator/api/generators/${generatorType}/fields`);
            const data = await response.json();

            if (data.success) {
                this.fieldsConfig = data.fields;
                this.validationRules = data.validation_rules || {};
                this._buildForm(data);
            } else {
                this._showError(data.error || 'Ошибка загрузки конфигурации');
            }
        } catch (error) {
            console.error('Error loading generator form:', error);
            this._showError('Не удалось загрузить конфигурацию генератора');
        } finally {
            this._hideLoading();
        }
    }

    _buildForm(generatorData) {
        this.container.innerHTML = '';
        this.container.className = 'dynamic-form fade-in';

        // Заголовок формы
        const header = this._createFormHeader(generatorData);
        this.container.appendChild(header);

        // Создаем форму
        const form = document.createElement('form');
        form.id = 'dynamic-generator-form';
        form.className = 'needs-validation';
        form.noValidate = true;

        // Группируем поля по типам
        const fieldGroups = this._groupFields(this.fieldsConfig);

        // Создаем группы полей
        for (const [groupName, fields] of Object.entries(fieldGroups)) {
            const groupElement = this._createFieldGroup(groupName, fields);
            form.appendChild(groupElement);
        }

        // Кнопки действий
        const actionsDiv = this._createFormActions();
        form.appendChild(actionsDiv);

        this.container.appendChild(form);

        // Инициализируем валидацию
        this._initializeValidation();

        // Добавляем обработчики событий
        this._attachEventListeners();
    }

    _createFormHeader(generatorData) {
        const header = document.createElement('div');
        header.className = 'form-header mb-4';
        header.innerHTML = `
        <div class="d-flex align-items-center">
            <i class="fas fa-magic fa-2x me-3 text-primary"></i>
            <div>
                <h3 class="mb-1">${generatorData.display_name}</h3>
                <p class="mb-0 text-dark">${generatorData.description}</p>
            </div>
        </div>
    `;
        return header;
    }

    _groupFields(fields) {
        const groups = {
            'Основные параметры': [],
            'Дополнительные настройки': [],
            'Расширенные параметры': []
        };

        const requiredFields = ['dag_id', 'schedule_interval', 'owner', 'description'];
        const advancedFields = ['catchup', 'max_active_runs', 'depends_on_past', 'retries'];

        fields.forEach(field => {
            if (requiredFields.includes(field.name) || field.required) {
                groups['Основные параметры'].push(field);
            } else if (advancedFields.includes(field.name)) {
                groups['Расширенные параметры'].push(field);
            } else {
                groups['Дополнительные настройки'].push(field);
            }
        });

        // Удаляем пустые группы
        Object.keys(groups).forEach(key => {
            if (groups[key].length === 0) {
                delete groups[key];
            }
        });

        return groups;
    }

    _createFieldGroup(groupName, fields) {
        if (fields.length === 0) return document.createElement('div');

        const groupDiv = document.createElement('div');
        groupDiv.className = 'field-group mb-4';

        const titleDiv = document.createElement('div');
        titleDiv.className = 'field-group-title mb-3';
        titleDiv.innerHTML = `
            <h5 class="text-primary mb-0">
                <i class="fas fa-${this._getGroupIcon(groupName)} me-2"></i>
                ${groupName}
            </h5>
        `;
        groupDiv.appendChild(titleDiv);

        const fieldsContainer = document.createElement('div');
        fieldsContainer.className = 'row';

        fields.forEach(field => {
            const fieldElement = this._createField(field);
            fieldsContainer.appendChild(fieldElement);
        });

        groupDiv.appendChild(fieldsContainer);
        return groupDiv;
    }

    _getGroupIcon(groupName) {
        const icons = {
            'Основные параметры': 'cog',
            'Дополнительные настройки': 'sliders-h',
            'Расширенные параметры': 'tools'
        };
        return icons[groupName] || 'folder';
    }

    _createField(fieldConfig) {
        const colDiv = document.createElement('div');
        colDiv.className = this._getFieldColumnClass(fieldConfig);

        const fieldDiv = document.createElement('div');
        fieldDiv.className = 'mb-3';

        // Label
        if (fieldConfig.type !== 'checkbox') {
            const label = this._createLabel(fieldConfig);
            fieldDiv.appendChild(label);
        }

        // Input field
        const input = this._createInput(fieldConfig);
        fieldDiv.appendChild(input);

        // Help text
        if (fieldConfig.help_text) {
            const helpText = this._createHelpText(fieldConfig.help_text);
            fieldDiv.appendChild(helpText);
        }

        // Validation feedback
        const feedback = this._createValidationFeedback();
        fieldDiv.appendChild(feedback);

        colDiv.appendChild(fieldDiv);
        return colDiv;
    }

    _getFieldColumnClass(fieldConfig) {
        // Определяем ширину поля на основе его типа
        if (fieldConfig.type === 'textarea' || fieldConfig.name === 'description') {
            return 'col-12';
        }
        if (['text', 'email', 'password'].includes(fieldConfig.type)) {
            return 'col-md-6';
        }
        return 'col-md-4';
    }

    _createLabel(fieldConfig) {
        const label = document.createElement('label');
        label.className = 'form-label fw-medium';
        label.setAttribute('for', fieldConfig.name);

        let labelText = fieldConfig.label;
        if (fieldConfig.required) {
            labelText += ' <span class="text-danger">*</span>';
        }

        if (fieldConfig.help_text) {
            labelText += ` <i class="fas fa-question-circle text-muted ms-1" 
                           title="${fieldConfig.help_text}" 
                           data-bs-toggle="tooltip"></i>`;
        }

        label.innerHTML = labelText;
        return label;
    }

    _createInput(fieldConfig) {
        switch (fieldConfig.type) {
            case 'textarea':
                return this._createTextarea(fieldConfig);
            case 'select':
                return this._createSelect(fieldConfig);
            case 'checkbox':
                return this._createCheckbox(fieldConfig);
            case 'number':
                return this._createNumberInput(fieldConfig);
            default:
                return this._createTextInput(fieldConfig);
        }
    }

    _createTextInput(fieldConfig) {
        const input = document.createElement('input');
        input.type = fieldConfig.type || 'text';
        input.className = 'form-control';
        input.name = fieldConfig.name;
        input.id = fieldConfig.name;

        this._setCommonInputAttributes(input, fieldConfig);

        if (fieldConfig.pattern) input.pattern = fieldConfig.pattern;

        return input;
    }

    _createTextarea(fieldConfig) {
        const textarea = document.createElement('textarea');
        textarea.className = 'form-control';
        textarea.name = fieldConfig.name;
        textarea.id = fieldConfig.name;
        textarea.rows = fieldConfig.rows || 3;

        this._setCommonInputAttributes(textarea, fieldConfig);

        return textarea;
    }

    _createSelect(fieldConfig) {
        const select = document.createElement('select');
        select.className = 'form-select';
        select.name = fieldConfig.name;
        select.id = fieldConfig.name;

        this._setCommonInputAttributes(select, fieldConfig);

        // Добавляем пустую опцию для необязательных полей
        if (!fieldConfig.required) {
            const emptyOption = document.createElement('option');
            emptyOption.value = '';
            emptyOption.textContent = 'Выберите значение...';
            select.appendChild(emptyOption);
        }

        // Добавляем опции
        if (fieldConfig.options) {
            fieldConfig.options.forEach(option => {
                const optionElement = document.createElement('option');
                optionElement.value = option.value;
                // Поддерживаем и 'label' и 'text' для обратной совместимости
                optionElement.textContent = option.label || option.text || option.value;

                if (fieldConfig.default_value === option.value) {
                    optionElement.selected = true;
                }

                select.appendChild(optionElement);
            });
        }

        return select;
    }

    _createNumberInput(fieldConfig) {
        const input = document.createElement('input');
        input.type = 'number';
        input.className = 'form-control';
        input.name = fieldConfig.name;
        input.id = fieldConfig.name;

        this._setCommonInputAttributes(input, fieldConfig);

        if (fieldConfig.min !== undefined) input.min = fieldConfig.min;
        if (fieldConfig.max !== undefined) input.max = fieldConfig.max;
        if (fieldConfig.step !== undefined) input.step = fieldConfig.step;

        return input;
    }

    _createCheckbox(fieldConfig) {
        const div = document.createElement('div');
        div.className = 'form-check';

        const input = document.createElement('input');
        input.type = 'checkbox';
        input.className = 'form-check-input';
        input.name = fieldConfig.name;
        input.id = fieldConfig.name;

        if (fieldConfig.default_value) input.checked = fieldConfig.default_value;
        if (fieldConfig.required) input.required = true;

        const label = document.createElement('label');
        label.className = 'form-check-label';
        label.setAttribute('for', fieldConfig.name);
        label.textContent = fieldConfig.label;

        if (fieldConfig.required) {
            label.innerHTML += ' <span class="text-danger">*</span>';
        }

        div.appendChild(input);
        div.appendChild(label);

        return div;
    }

    _setCommonInputAttributes(input, fieldConfig) {
        if (fieldConfig.placeholder) input.placeholder = fieldConfig.placeholder;
        if (fieldConfig.default_value !== undefined) {
            input.value = fieldConfig.default_value;
        }
        if (fieldConfig.required) input.required = true;
        if (fieldConfig.readonly) input.readOnly = true;
        if (fieldConfig.disabled) input.disabled = true;
    }

    _createHelpText(helpText) {
        const help = document.createElement('div');
        help.className = 'form-text';
        help.innerHTML = `<i class="fas fa-info-circle me-1"></i>${helpText}`;
        return help;
    }

    _createValidationFeedback() {
        const feedback = document.createElement('div');
        feedback.className = 'invalid-feedback';
        return feedback;
    }

    _createFormActions() {
        const actionsDiv = document.createElement('div');
        actionsDiv.className = 'form-actions d-flex gap-3 justify-content-center mt-4 pt-4 border-top';
        actionsDiv.innerHTML = `
            <button type="button" class="btn btn-outline-secondary btn-lg" onclick="formBuilder.resetForm()">
                <i class="fas fa-undo me-2"></i>Сбросить
            </button>
            <button type="button" class="btn btn-info btn-lg" onclick="formBuilder.previewDAG()">
                <i class="fas fa-eye me-2"></i>Предпросмотр
            </button>
            <button type="button" class="btn btn-success btn-lg" onclick="formBuilder.generateDAG()">
                <i class="fas fa-magic me-2"></i>Создать DAG
            </button>
        `;
        return actionsDiv;
    }

    _initializeValidation() {
        const form = document.getElementById('dynamic-generator-form');
        if (!form) return;

        // Инициализируем Bootstrap tooltips
        const tooltips = form.querySelectorAll('[data-bs-toggle="tooltip"]');
        tooltips.forEach(tooltip => {
            new bootstrap.Tooltip(tooltip);
        });

        // Добавляем кастомную валидацию
        form.addEventListener('submit', (event) => {
            event.preventDefault();
            event.stopPropagation();

            if (this._validateForm()) {
                this.generateDAG();
            }
        });
    }

    _attachEventListeners() {
        const form = document.getElementById('dynamic-generator-form');
        if (!form) return;

        // Валидация в реальном времени
        const inputs = form.querySelectorAll('input, select, textarea');
        inputs.forEach(input => {
            input.addEventListener('blur', () => {
                this._validateField(input);
            });

            input.addEventListener('input', this._debounce(() => {
                if (input.classList.contains('is-invalid')) {
                    this._validateField(input);
                }
            }, 300));
        });
    }

    _validateForm() {
        const form = document.getElementById('dynamic-generator-form');
        if (!form) return false;

        let isValid = true;
        const inputs = form.querySelectorAll('input, select, textarea');

        inputs.forEach(input => {
            if (!this._validateField(input)) {
                isValid = false;
            }
        });

        return isValid;
    }

    _validateField(field) {
        const fieldName = field.name;
        const value = field.type === 'checkbox' ? field.checked : field.value;
        let isValid = true;
        let errorMessage = '';

        // Обязательные поля
        if (field.required && (!value || (typeof value === 'string' && !value.trim()))) {
            isValid = false;
            errorMessage = 'Это поле обязательно для заполнения';
        }

        // Паттерны
        if (isValid && field.pattern && value) {
            const regex = new RegExp(field.pattern);
            if (!regex.test(value)) {
                isValid = false;
                errorMessage = 'Значение не соответствует требуемому формату';
            }
        }

        // Числовые ограничения
        if (isValid && field.type === 'number' && value !== '') {
            const numValue = parseFloat(value);
            if (field.min !== undefined && numValue < parseFloat(field.min)) {
                isValid = false;
                errorMessage = `Значение должно быть не менее ${field.min}`;
            }
            if (field.max !== undefined && numValue > parseFloat(field.max)) {
                isValid = false;
                errorMessage = `Значение должно быть не более ${field.max}`;
            }
        }

        // Обновляем визуальное состояние
        if (isValid) {
            field.classList.remove('is-invalid');
            field.classList.add('is-valid');
        } else {
            field.classList.remove('is-valid');
            field.classList.add('is-invalid');

            const feedback = field.parentNode.querySelector('.invalid-feedback');
            if (feedback) {
                feedback.textContent = errorMessage;
            }
        }

        return isValid;
    }

    getFormData() {
        const form = document.getElementById('dynamic-generator-form');
        if (!form) return {};

        const formData = new FormData(form);
        const data = {};

        // Обрабатываем обычные поля
        for (let [key, value] of formData.entries()) {
            data[key] = value;
        }

        // Обрабатываем checkbox'ы отдельно
        const checkboxes = form.querySelectorAll('input[type="checkbox"]');
        checkboxes.forEach(checkbox => {
            data[checkbox.name] = checkbox.checked;
        });

        // Преобразуем числовые поля
        const numberInputs = form.querySelectorAll('input[type="number"]');
        numberInputs.forEach(input => {
            if (data[input.name] !== '') {
                data[input.name] = parseFloat(data[input.name]);
            }
        });

        return data;
    }

    async generateDAG() {
        if (!this._validateForm()) {
            this._showNotification('error', 'Пожалуйста, исправьте ошибки в форме');
            return;
        }

        const formData = this.getFormData();
        const loadingBtn = document.querySelector('.btn-success');
        const originalText = loadingBtn.innerHTML;

        try {
            loadingBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Создание...';
            loadingBtn.disabled = true;

            const response = await fetch('/dag-generator/generate', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this._getCsrfToken()
                },
                body: JSON.stringify({
                    generator_type: this.currentGeneratorType,
                    form_data: formData
                })
            });

            const data = await response.json();

            if (data.success) {
                this._showNotification('success', '✅ DAG успешно создан!');
                this._showGeneratedCode(data.dag_code, data.dag_file_path);
            } else {
                throw new Error(data.error || 'Ошибка создания DAG');
            }
        } catch (error) {
            console.error('Error generating DAG:', error);
            this._showNotification('error', `❌ Ошибка создания: ${error.message}`);
        } finally {
            loadingBtn.innerHTML = originalText;
            loadingBtn.disabled = false;
        }
    }

    async previewDAG() {
        if (!this._validateForm()) {
            this._showNotification('error', 'Пожалуйста, исправьте ошибки в форме');
            return;
        }

        const formData = this.getFormData();
        const loadingBtn = document.querySelector('.btn-info');
        const originalText = loadingBtn.innerHTML;

        try {
            loadingBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Предпросмотр...';
            loadingBtn.disabled = true;

            const response = await fetch('/dag-generator/preview', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this._getCsrfToken()
                },
                body: JSON.stringify({
                    generator_type: this.currentGeneratorType,
                    form_data: formData
                })
            });

            const data = await response.json();

            if (data.success) {
                this._showGeneratedCode(data.dag_code, null, true);
            } else {
                throw new Error(data.error || 'Ошибка предпросмотра');
            }
        } catch (error) {
            console.error('Error previewing DAG:', error);
            this._showNotification('error', `❌ Ошибка предпросмотра: ${error.message}`);
        } finally {
            loadingBtn.innerHTML = originalText;
            loadingBtn.disabled = false;
        }
    }

    resetForm() {
        const form = document.getElementById('dynamic-generator-form');
        if (!form) return;

        form.reset();

        // Убираем классы валидации
        const inputs = form.querySelectorAll('.is-valid, .is-invalid');
        inputs.forEach(input => {
            input.classList.remove('is-valid', 'is-invalid');
        });

        // Устанавливаем значения по умолчанию
        this.fieldsConfig?.forEach(field => {
            if (field.default_value !== undefined) {
                const input = form.querySelector(`[name="${field.name}"]`);
                if (input) {
                    if (input.type === 'checkbox') {
                        input.checked = field.default_value;
                    } else {
                        input.value = field.default_value;
                    }
                }
            }
        });

        this._showNotification('info', '📝 Форма сброшена');
    }

    _showGeneratedCode(code, filePath = null, isPreview = false) {
        let resultContainer = document.getElementById('result-container');

        if (!resultContainer) {
            resultContainer = document.createElement('div');
            resultContainer.id = 'result-container';
            resultContainer.className = 'mt-4';
            this.container.parentNode.appendChild(resultContainer);
        }

        const title = isPreview ? 'Предпросмотр DAG' : 'Сгенерированный DAG';
        const statusClass = isPreview ? 'info' : 'success';
        const statusText = isPreview ? 'Предпросмотр готов' : 'DAG успешно создан';

        resultContainer.innerHTML = `
            <div class="card shadow-sm slide-up">
                <div class="card-header d-flex justify-content-between align-items-center">
                    <h5 class="mb-0">
                        <i class="fas fa-code me-2"></i>${title}
                    </h5>
                    <div class="d-flex gap-2">
                        <span class="badge bg-${statusClass}">${statusText}</span>
                        <button type="button" class="btn btn-sm btn-outline-secondary" 
                                onclick="navigator.clipboard.writeText(document.getElementById('generated-code').textContent)">
                            <i class="fas fa-copy me-1"></i>Копировать
                        </button>
                    </div>
                </div>
                <div class="card-body p-0">
                    ${filePath ? `<div class="bg-light px-3 py-2 border-bottom">
                        <small class="text-muted">
                            <i class="fas fa-file-code me-2"></i>Файл: ${filePath}
                        </small>
                    </div>` : ''}
                    <pre class="mb-0 p-3"><code id="generated-code" class="language-python">${this._escapeHtml(code)}</code></pre>
                </div>
            </div>
        `;

        resultContainer.classList.remove('d-none');
        resultContainer.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }

    _showEmptyState() {
        this.container.innerHTML = `
            <div class="text-center text-muted py-5">
                <i class="fas fa-arrow-up fa-3x mb-3 opacity-50"></i>
                <h5>Выберите тип генератора</h5>
                <p>Для настройки параметров DAG выберите подходящий генератор из списка выше</p>
            </div>
        `;
        this.container.className = '';
    }

    _showError(message) {
        this.container.innerHTML = `
            <div class="alert alert-danger fade-in" role="alert">
                <i class="fas fa-exclamation-triangle me-2"></i>
                <strong>Ошибка:</strong> ${message}
            </div>
        `;
        this.container.className = '';
    }

    _showLoading() {
        const loadingDiv = document.createElement('div');
        loadingDiv.id = 'form-loading';
        loadingDiv.className = 'text-center py-4';
        loadingDiv.innerHTML = `
            <div class="spinner-border text-primary" role="status">
                <span class="visually-hidden">Загрузка...</span>
            </div>
            <p class="mt-3 text-muted">Загрузка конфигурации генератора...</p>
        `;
        this.container.innerHTML = '';
        this.container.appendChild(loadingDiv);
    }

    _hideLoading() {
        const loading = document.getElementById('form-loading');
        if (loading) {
            loading.remove();
        }
    }

    _getCsrfToken() {
        // Получаем CSRF токен из мета-тега или скрытого поля
        const meta = document.querySelector('meta[name="csrf-token"]');
        if (meta) return meta.getAttribute('content');
        
        const input = document.querySelector('input[name="csrf_token"]');
        if (input) return input.value;
        
        return '';
    }

    _showNotification(type, message) {
        // Простая реализация уведомлений
        const toast = document.createElement('div');
        toast.className = `alert alert-${type === 'error' ? 'danger' : type} alert-dismissible fade show position-fixed`;
        toast.style.cssText = 'top: 20px; right: 20px; z-index: 1055; min-width: 300px;';
        toast.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        document.body.appendChild(toast);
        
        // Автоматически скрываем через 5 секунд
        setTimeout(() => {
            if (toast.parentNode) {
                toast.remove();
            }
        }, 5000);
    }

    _escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    _debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }
}

// Экспорт для глобального использования
window.DynamicFormBuilder = DynamicFormBuilder;
