/**
 * Главная страница - полный функционал с динамической формой
 */

// Глобальные переменные
let formBuilder = null;

/**
 * Инициализация при загрузке страницы
 */
document.addEventListener('DOMContentLoaded', function() {
    console.log('Initializing DAG Generator...');
    
    // Инициализируем форм-билдер
    formBuilder = new DynamicFormBuilder('dynamic-form-container');
    
    // Загружаем список генераторов
    updateGeneratorsList();
    
    // Настраиваем обработчики событий
    setupEventListeners();
});

/**
 * Настройка обработчиков событий
 */
function setupEventListeners() {
    // Обработчик выбора генератора
    const generatorSelect = document.getElementById('generator-select');
    if (generatorSelect) {
        generatorSelect.addEventListener('change', function() {
            const selectedGenerator = this.value;
            handleGeneratorSelection(selectedGenerator);
        });
    }

    // Кнопка перезагрузки генераторов
    const reloadBtn = document.getElementById('reload-generators-btn');
    if (reloadBtn) {
        reloadBtn.addEventListener('click', reloadGenerators);
    }
}

// Глобальные данные
window.GeneratorPageData = {
    templates: {},
    csrf_token: '',
    currentGenerator: null,
    currentFormFields: null
};

/**
 * Инициализация данных из шаблона
 */
function initializePageData() {
    try {
        const initialDataElement = document.getElementById('initial-data');
        if (initialDataElement) {
            const data = JSON.parse(initialDataElement.textContent);
            window.GeneratorPageData = {
                templates: data.templates || {},
                csrf_token: data.csrf_token || '',
                currentGenerator: null,
                currentFormFields: null
            };
            console.log('Page data initialized:', window.GeneratorPageData);
        }
    } catch (error) {
        console.error('Error initializing page data:', error);
    }
}

/**
 * Получение CSRF токена
 */
function getCsrfToken() {
    // Получаем CSRF токен из мета-тега или скрытого поля
    const meta = document.querySelector('meta[name="csrf-token"]');
    if (meta) return meta.getAttribute('content');
    
    const input = document.querySelector('input[name="csrf_token"]');
    if (input) return input.value;
    
    return '';
}

/**
 * Обновление списка генераторов
 */
function updateGeneratorsList() {
    console.log('Updating generators list...');
    
    return fetch('/dag-generator/api/generators')
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success' && data.generators) {
                const select = document.getElementById('generator-select');
                if (!select) {
                    console.error('Generator select not found');
                    return 0;
                }

                // Сохраняем текущий выбор
                const currentValue = select.value;

                // Очищаем список (оставляем первую опцию)
                while (select.children.length > 1) {
                    select.removeChild(select.lastChild);
                }

                // Добавляем новые генераторы
                data.generators.forEach(generator => {
                    const option = document.createElement('option');
                    option.value = generator.name;
                    option.textContent = generator.display_name;
                    option.title = generator.description;
                    select.appendChild(option);
                });

                // Восстанавливаем выбор если возможно
                if (currentValue && [...select.options].some(opt => opt.value === currentValue)) {
                    select.value = currentValue;
                    handleGeneratorSelection(currentValue);
                }

                // Обновляем счетчик
                const countElement = document.getElementById('generators-count');
                if (countElement) {
                    countElement.textContent = data.generators.length;
                }

                console.log(`Updated generators list: ${data.generators.length} generators`);
                return data.generators.length;
            } else {
                throw new Error(data.message || 'Failed to get generators');
            }
        })
        .catch(error => {
            console.error('Error updating generators list:', error);
            showNotification('error', `Ошибка загрузки генераторов: ${error.message}`);
        });
}

/**
 * Перезагрузка генераторов
 */
function reloadGenerators() {
    const reloadBtn = document.getElementById('reload-generators-btn');
    if (!reloadBtn) {
        console.error('Reload button not found');
        return;
    }

    const originalContent = reloadBtn.innerHTML;
    
    // Показываем состояние загрузки
    reloadBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Перезагрузка...';
    reloadBtn.disabled = true;

    console.log('Starting manual reload...');

    // Выполняем перезагрузку
    fetch('/dag-generator/api/reload/manual', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCsrfToken()
        }
    })
    .then(response => response.json())
    .then(data => {
        console.log('Reload response:', data);
        
        if (data.success) {
            showNotification('success', `✅ ${data.message}`);
            
            // Обновляем список генераторов
            return updateGeneratorsList();
        } else {
            throw new Error(data.error || 'Unknown error during reload');
        }
    })
    .then(count => {
        console.log(`Reload completed: ${count} generators loaded`);
    })
    .catch(error => {
        console.error('Reload error:', error);
        showNotification('error', `❌ Ошибка перезагрузки: ${error.message}`);
    })
    .finally(() => {
        // Восстанавливаем кнопку
        reloadBtn.innerHTML = originalContent;
        reloadBtn.disabled = false;
    });
}

/**
 * ОСНОВНАЯ функция обработки выбора генератора
 */
function handleGeneratorSelection(generatorType) {
    console.log('Generator selected:', generatorType);
    
    const infoContainer = document.getElementById('generator-info');
    const dynamicFormContainer = document.getElementById('dynamic-form-container');
    const emptyState = document.getElementById('empty-state');
    const loadingSpinner = document.getElementById('loading-spinner');
    
    if (!generatorType) {
        // Скрываем информацию и форму
        if (infoContainer) infoContainer.classList.add('d-none');
        if (dynamicFormContainer) {
            dynamicFormContainer.innerHTML = '';
            if (emptyState) {
                dynamicFormContainer.appendChild(emptyState);
                emptyState.classList.remove('d-none');
            }
        }
        
        window.GeneratorPageData.currentGenerator = null;
        window.GeneratorPageData.currentFormFields = null;
        return;
    }

    // Показываем загрузку
    if (loadingSpinner) loadingSpinner.classList.remove('d-none');
    if (emptyState) emptyState.classList.add('d-none');
    if (infoContainer) infoContainer.classList.add('d-none');

    // Загружаем поля генератора
    fetch(`/dag-generator/api/generators/${generatorType}/fields`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Обновляем информацию о генераторе
                updateGeneratorInfo(data);
                
                // Строим динамическую форму
                buildDynamicForm(data.fields);
                
                // Сохраняем данные генератора
                window.GeneratorPageData.currentGenerator = generatorType;
                window.GeneratorPageData.currentFormFields = data.fields;
                
                console.log('Generator fields loaded:', data.fields.length, 'fields');
            } else {
                throw new Error(data.error || 'Failed to load generator fields');
            }
        })
        .catch(error => {
            console.error('Error loading generator fields:', error);
            showNotification('error', `Ошибка загрузки полей генератора: ${error.message}`);
            
            // Показываем пустое состояние при ошибке
            if (dynamicFormContainer && emptyState) {
                dynamicFormContainer.innerHTML = '';
                dynamicFormContainer.appendChild(emptyState);
                emptyState.classList.remove('d-none');
            }
        })
        .finally(() => {
            // Скрываем загрузку
            if (loadingSpinner) loadingSpinner.classList.add('d-none');
        });
}

/**
 * Обновление информации о генераторе
 */
function updateGeneratorInfo(data) {
    const infoContainer = document.getElementById('generator-info');
    const displayNameEl = document.getElementById('generator-display-name');
    const descriptionEl = document.getElementById('generator-description');
    const requiredCountEl = document.getElementById('required-fields-count');
    const optionalCountEl = document.getElementById('optional-fields-count');
    
    if (displayNameEl && descriptionEl && data) {
        displayNameEl.textContent = data.display_name || 'Неизвестный генератор';
        descriptionEl.textContent = data.description || 'Описание недоступно';
        
        // Подсчитываем поля
        const requiredFields = data.fields ? data.fields.filter(f => f.required).length : 0;
        const optionalFields = data.fields ? data.fields.filter(f => !f.required).length : 0;
        
        if (requiredCountEl) requiredCountEl.textContent = requiredFields;
        if (optionalCountEl) optionalCountEl.textContent = optionalFields;
        
        if (infoContainer) {
            infoContainer.classList.remove('d-none');
        }
    }
}

/**
 * Построение динамической формы
 */
function buildDynamicForm(fields) {
    const container = document.getElementById('dynamic-form-container');
    if (!container || !fields || fields.length === 0) {
        console.warn('Cannot build form: container or fields missing');
        return;
    }

    // Очищаем контейнер
    container.innerHTML = '';

    // Создаем форму
    const form = document.createElement('form');
    form.id = 'generator-form';
    form.className = 'needs-validation';
    form.noValidate = true;

    // Добавляем поля
    fields.forEach(field => {
        const fieldElement = createFormField(field);
        if (fieldElement) {
            form.appendChild(fieldElement);
        }
    });

    // Добавляем кнопки действий
    const actionsDiv = document.createElement('div');
    actionsDiv.className = 'form-actions mt-4 pt-4 border-top';
    actionsDiv.innerHTML = `
        <div class="d-flex gap-3 justify-content-center">
            <button type="button" id="preview-btn" class="btn btn-outline-primary btn-lg">
                <i class="fas fa-eye me-2"></i>
                Предпросмотр
            </button>
            <button type="button" id="generate-btn" class="btn btn-success btn-lg">
                <i class="fas fa-magic me-2"></i>
                Создать DAG
            </button>
        </div>
    `;
    form.appendChild(actionsDiv);

    // Добавляем форму в контейнер
    container.appendChild(form);

    // Настраиваем обработчики кнопок
    setupFormActions();
}

/**
 * Обработка выбора генератора
 */
function handleGeneratorSelection(generatorType) {
    console.log('Generator selected:', generatorType);
    
    const infoContainer = document.getElementById('generator-info');
    
    if (!generatorType) {
        // Скрываем информацию и показываем пустое состояние
        if (infoContainer) infoContainer.classList.add('d-none');
        formBuilder.loadGeneratorForm(null);
        return;
    }

    // Показываем информацию о генераторе
    updateGeneratorInfo(generatorType);
    
    // Загружаем форму через FormBuilder
    formBuilder.loadGeneratorForm(generatorType);
}

/**
 * Обновление информации о генераторе
 */
function updateGeneratorInfo(generatorType) {
    // Получаем информацию о генераторе
    fetch(`/dag-generator/api/generators/${generatorType}/info`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                const infoContainer = document.getElementById('generator-info');
                const displayNameEl = document.getElementById('generator-display-name');
                const descriptionEl = document.getElementById('generator-description');
                const requiredCountEl = document.getElementById('required-fields-count');
                const optionalCountEl = document.getElementById('optional-fields-count');
                
                if (displayNameEl && descriptionEl) {
                    displayNameEl.textContent = data.display_name || 'Неизвестный генератор';
                    descriptionEl.textContent = data.description || 'Описание недоступно';
                    
                    // Подсчитываем поля из required_fields и optional_fields
                    const requiredFields = data.required_fields ? data.required_fields.length : 0;
                    const optionalFields = data.optional_fields ? Object.keys(data.optional_fields).length : 0;
                    
                    if (requiredCountEl) requiredCountEl.textContent = requiredFields;
                    if (optionalCountEl) optionalCountEl.textContent = optionalFields;
                    
                    if (infoContainer) {
                        infoContainer.classList.remove('d-none');
                    }
                }
            }
        })
        .catch(error => {
            console.error('Error loading generator info:', error);
        });
}

/**
 * Создание поля формы
 */
function createFormField(field) {
    const fieldDiv = document.createElement('div');
    fieldDiv.className = 'mb-3';

    const label = document.createElement('label');
    label.className = 'form-label fw-bold';
    label.htmlFor = field.name;
    label.innerHTML = `
        ${field.label}
        ${field.required ? '<span class="text-danger">*</span>' : ''}
    `;

    let input;
    
    switch (field.type) {
        case 'text':
        case 'email':
        case 'url':
            input = document.createElement('input');
            input.type = field.type;
            input.className = 'form-control';
            input.name = field.name;
            input.id = field.name;
            input.required = field.required;
            if (field.default_value) input.value = field.default_value;
            if (field.placeholder) input.placeholder = field.placeholder;
            break;

        case 'textarea':
            input = document.createElement('textarea');
            input.className = 'form-control';
            input.name = field.name;
            input.id = field.name;
            input.required = field.required;
            input.rows = field.rows || 3;
            if (field.default_value) input.value = field.default_value;
            if (field.placeholder) input.placeholder = field.placeholder;
            break;

        case 'select':
            input = document.createElement('select');
            input.className = 'form-select';
            input.name = field.name;
            input.id = field.name;
            input.required = field.required;

            // Добавляем опции
            if (field.options) {
                if (!field.required) {
                    const emptyOption = document.createElement('option');
                    emptyOption.value = '';
                    emptyOption.textContent = 'Выберите...';
                    input.appendChild(emptyOption);
                }

                field.options.forEach(option => {
                    const optionEl = document.createElement('option');
                    optionEl.value = option.value;
                    optionEl.textContent = option.label;
                    if (option.value === field.default_value) {
                        optionEl.selected = true;
                    }
                    input.appendChild(optionEl);
                });
            }
            break;

        case 'checkbox':
            input = document.createElement('div');
            input.className = 'form-check';
            input.innerHTML = `
                <input class="form-check-input" type="checkbox" name="${field.name}" id="${field.name}" 
                       ${field.default_value ? 'checked' : ''}>
                <label class="form-check-label" for="${field.name}">
                    ${field.label}
                </label>
            `;
            // Для checkbox не нужен отдельный label
            fieldDiv.appendChild(input);
            return fieldDiv;

        case 'number':
            input = document.createElement('input');
            input.type = 'number';
            input.className = 'form-control';
            input.name = field.name;
            input.id = field.name;
            input.required = field.required;
            if (field.default_value !== undefined) input.value = field.default_value;
            if (field.min !== undefined) input.min = field.min;
            if (field.max !== undefined) input.max = field.max;
            if (field.step !== undefined) input.step = field.step;
            break;

        default:
            console.warn(`Unknown field type: ${field.type}`);
            return null;
    }

    // Добавляем описание поля если есть
    let helpText = '';
    if (field.help_text) {
        helpText = `<div class="form-text">${field.help_text}</div>`;
    }

    fieldDiv.appendChild(label);
    fieldDiv.appendChild(input);
    if (helpText) {
        fieldDiv.insertAdjacentHTML('beforeend', helpText);
    }

    return fieldDiv;
}

/**
 * Настройка обработчиков действий формы
 */
function setupFormActions() {
    const previewBtn = document.getElementById('preview-btn');
    const generateBtn = document.getElementById('generate-btn');

    if (previewBtn) {
        previewBtn.addEventListener('click', handlePreview);
    }

    if (generateBtn) {
        generateBtn.addEventListener('click', handleGenerate);
    }
}

/**
 * Сбор данных формы
 */
function collectFormData() {
    const form = document.getElementById('generator-form');
    if (!form) return {};

    const formData = new FormData(form);
    const data = {};

    for (let [key, value] of formData.entries()) {
        data[key] = value;
    }

    // Обрабатываем checkbox'ы отдельно
    const checkboxes = form.querySelectorAll('input[type="checkbox"]');
    checkboxes.forEach(checkbox => {
        data[checkbox.name] = checkbox.checked;
    });

    return data;
}

/**
 * Обработка предпросмотра
 */
function handlePreview() {
    const formData = collectFormData();
    const generatorType = window.GeneratorPageData.currentGenerator;

    if (!generatorType) {
        showNotification('error', 'Не выбран генератор');
        return;
    }

    const previewBtn = document.getElementById('preview-btn');
    const originalContent = previewBtn.innerHTML;
    
    previewBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Предпросмотр...';
    previewBtn.disabled = true;

    fetch('/dag-generator/preview', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCsrfToken()
        },
        body: JSON.stringify({
            generator_type: generatorType,
            form_data: formData
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showPreviewModal(data.dag_code);
        } else {
            throw new Error(data.error || 'Preview failed');
        }
    })
    .catch(error => {
        console.error('Preview error:', error);
        showNotification('error', `Ошибка предпросмотра: ${error.message}`);
    })
    .finally(() => {
        previewBtn.innerHTML = originalContent;
        previewBtn.disabled = false;
    });
}

/**
 * Обработка генерации
 */
function handleGenerate() {
    const formData = collectFormData();
    const generatorType = window.GeneratorPageData.currentGenerator;

    if (!generatorType) {
        showNotification('error', 'Не выбран генератор');
        return;
    }

    const generateBtn = document.getElementById('generate-btn');
    const originalContent = generateBtn.innerHTML;
    
    generateBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Создание...';
    generateBtn.disabled = true;

    fetch('/dag-generator/generate', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCsrfToken()
        },
        body: JSON.stringify({
            generator_type: generatorType,
            form_data: formData
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showNotification('success', `✅ ${data.message}`);
            showGenerationResult(data);
        } else {
            throw new Error(data.error || 'Generation failed');
        }
    })
    .catch(error => {
        console.error('Generation error:', error);
        showNotification('error', `Ошибка генерации: ${error.message}`);
    })
    .finally(() => {
        generateBtn.innerHTML = originalContent;
        generateBtn.disabled = false;
    });
}

/**
 * Показ модального окна предпросмотра
 */
function showPreviewModal(dagCode) {
    // Создаем модальное окно если его нет
    let modal = document.getElementById('preview-modal');
    if (!modal) {
        modal = document.createElement('div');
        modal.id = 'preview-modal';
        modal.className = 'modal fade';
        modal.innerHTML = `
            <div class="modal-dialog modal-xl">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">Предпросмотр DAG</h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                        <pre><code id="preview-code" class="language-python"></code></pre>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Закрыть</button>
                    </div>
                </div>
            </div>
        `;
        document.body.appendChild(modal);
    }

    // Обновляем содержимое
    const codeElement = modal.querySelector('#preview-code');
    if (codeElement) {
        codeElement.textContent = dagCode;
    }

    // Показываем модальное окно
    const bootstrapModal = new bootstrap.Modal(modal);
    bootstrapModal.show();
}

/**
 * Показ результата генерации
 */
function showGenerationResult(data) {
    const resultContainer = document.getElementById('result-container');
    if (!resultContainer) return;

    resultContainer.innerHTML = `
        <div class="card shadow-sm">
            <div class="card-header bg-success text-white">
                <h5 class="mb-0">
                    <i class="fas fa-check-circle me-2"></i>
                    DAG успешно создан
                </h5>
            </div>
            <div class="card-body">
                <div class="row">
                    <div class="col-md-6">
                        <h6>Информация о DAG:</h6>
                        <ul class="list-unstyled">
                            <li><strong>Имя:</strong> ${data.generator_info.display_name}</li>
                            <li><strong>Файл:</strong> <code>${data.dag_file_path}</code></li>
                        </ul>
                    </div>
                    <div class="col-md-6">
                        <h6>Действия:</h6>
                        <div class="d-flex gap-2">
                            <button class="btn btn-outline-primary btn-sm" onclick="showPreviewModal(\`${data.dag_code.replace(/`/g, '\\`')}\`)">
                                <i class="fas fa-eye me-1"></i> Просмотр кода
                            </button>
                            <button class="btn btn-outline-success btn-sm" onclick="copyToClipboard(\`${data.dag_code.replace(/`/g, '\\`')}\`)">
                                <i class="fas fa-copy me-1"></i> Копировать код
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `;

    resultContainer.classList.remove('d-none');
    resultContainer.scrollIntoView({ behavior: 'smooth' });
}

/**
 * Заполнение начальных данных из шаблона
 */
function populateInitialData() {
    const select = document.getElementById('generator-select');
    const templates = window.GeneratorPageData.templates;
    
    if (select && templates && Object.keys(templates).length > 0) {
        // Добавляем генераторы из начальных данных
        Object.entries(templates).forEach(([key, name]) => {
            const option = document.createElement('option');
            option.value = key;
            option.textContent = name;
            select.appendChild(option);
        });
        
        // Обновляем счетчик
        const countElement = document.getElementById('generators-count');
        if (countElement) {
            countElement.textContent = Object.keys(templates).length;
        }
        
        console.log(`Populated ${Object.keys(templates).length} initial generators`);
    }
}

/**
 * Настройка обработчиков событий
 */
function setupEventHandlers() {
    // Кнопка перезагрузки генераторов
    const reloadBtn = document.getElementById('reload-generators-btn');
    if (reloadBtn) {
        reloadBtn.addEventListener('click', reloadGenerators);
        console.log('Reload button handler set');
    }

    // Селект генераторов
    const generatorSelect = document.getElementById('generator-select');
    if (generatorSelect) {
        generatorSelect.addEventListener('change', (e) => {
            handleGeneratorSelection(e.target.value);
        });
        console.log('Generator select handler set');
    }
}

/**
 * Инициализация страницы
 */
function initializePage() {
    console.log('=== ИНИЦИАЛИЗАЦИЯ СТРАНИЦЫ ГЕНЕРАТОРОВ ===');
    
    // Инициализируем данные
    initializePageData();
    
    // Заполняем начальные данные
    populateInitialData();
    
    // Настраиваем обработчики
    setupEventHandlers();
    
    // Сразу обновляем список генераторов
    updateGeneratorsList()
        .then(count => {
            console.log(`Initial load: ${count} generators from API`);
        })
        .catch(error => {
            console.log('API not available, using initial data only:', error.message);
        });
    
    console.log('Инициализация завершена');
}

// Автоматическая инициализация при загрузке DOM
document.addEventListener('DOMContentLoaded', initializePage);
/**
 * Создание поля select - обновленная версия
 */
function createSelectField(field, wrapper) {
    let optionsHtml = '';
    
    if (!field.required) {
        optionsHtml += '<option value="">Выберите...</option>';
    }

    if (field.options) {
        field.options.forEach(option => {
            // Поддерживаем и 'label' и 'text' для обратной совместимости
            const label = option.label || option.text || option.value;
            const isSelected = option.value === field.default_value ? 'selected' : '';
            optionsHtml += `<option value="${option.value}" ${isSelected}>${label}</option>`;
        });
    }

    wrapper.innerHTML = `
        <label for="${field.name}" class="form-label">
            ${field.label}
            ${field.required ? '<span class="text-danger">*</span>' : ''}
        </label>
        <select 
            class="form-select" 
            id="${field.name}" 
            name="${field.name}" 
            ${field.required ? 'required' : ''}
        >
            ${optionsHtml}
        </select>
        ${field.help_text ? `<div class="form-text">${field.help_text}</div>` : ''}
        <div class="invalid-feedback"></div>
    `;
    return wrapper;
}
/**
 * Создание текстового поля - обновленная версия
 */
function createInputField(field, wrapper) {
    wrapper.innerHTML = `
        <label for="${field.name}" class="form-label">
            ${field.label}
            ${field.required ? '<span class="text-danger">*</span>' : ''}
        </label>
        <input 
            type="${field.type}" 
            class="form-control" 
            id="${field.name}" 
            name="${field.name}" 
            ${field.required ? 'required' : ''}
            ${field.placeholder ? `placeholder="${field.placeholder}"` : ''}
            ${field.default_value ? `value="${field.default_value}"` : ''}
            ${field.pattern ? `pattern="${field.pattern}"` : ''}
        >
        ${field.help_text ? `<div class="form-text">${field.help_text}</div>` : ''}
        <div class="invalid-feedback"></div>
    `;
    return wrapper;
}

/**
 * Создание поля textarea - обновленная версия
 */
function createTextareaField(field, wrapper) {
    wrapper.innerHTML = `
        <label for="${field.name}" class="form-label">
            ${field.label}
            ${field.required ? '<span class="text-danger">*</span>' : ''}
        </label>
        <textarea 
            class="form-control" 
            id="${field.name}" 
            name="${field.name}" 
            rows="${field.rows || 3}"
            ${field.required ? 'required' : ''}
            ${field.placeholder ? `placeholder="${field.placeholder}"` : ''}
        >${field.default_value || ''}</textarea>
        ${field.help_text ? `<div class="form-text">${field.help_text}</div>` : ''}
        <div class="invalid-feedback"></div>
    `;
    return wrapper;
}

/**
 * Создание поля checkbox - обновленная версия
 */
function createCheckboxField(field, wrapper) {
    wrapper.innerHTML = `
        <div class="form-check">
            <input 
                class="form-check-input" 
                type="checkbox" 
                id="${field.name}" 
                name="${field.name}" 
                ${field.default_value ? 'checked' : ''}
            >
            <label class="form-check-label" for="${field.name}">
                ${field.label}
                ${field.required ? '<span class="text-danger">*</span>' : ''}
            </label>
            ${field.help_text ? `<div class="form-text">${field.help_text}</div>` : ''}
        </div>
    `;
    return wrapper;
}

/**
 * Создание числового поля - обновленная версия
 */
function createNumberField(field, wrapper) {
    wrapper.innerHTML = `
        <label for="${field.name}" class="form-label">
            ${field.label}
            ${field.required ? '<span class="text-danger">*</span>' : ''}
        </label>
        <input 
            type="number" 
            class="form-control" 
            id="${field.name}" 
            name="${field.name}" 
            ${field.required ? 'required' : ''}
            ${field.min !== undefined ? `min="${field.min}"` : ''}
            ${field.max !== undefined ? `max="${field.max}"` : ''}
            ${field.step !== undefined ? `step="${field.step}"` : ''}
            ${field.default_value !== undefined ? `value="${field.default_value}"` : ''}
        >
        ${field.help_text ? `<div class="form-text">${field.help_text}</div>` : ''}
        <div class="invalid-feedback"></div>
    `;
    return wrapper;
}

/**
 * Показ уведомлений
 */
function showNotification(type, message) {
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
