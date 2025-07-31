/**
 * Главная страница - полный функционал с динамической формой
 */

// Глобальные переменные
let formBuilder = null;
let searchManager = null;

/**
 * Инициализация при загрузке страницы
 */
document.addEventListener('DOMContentLoaded', function() {
    console.log('=== ИНИЦИАЛИЗАЦИЯ СТРАНИЦЫ ГЕНЕРАТОРОВ ===');
    
    // Инициализируем менеджеры
    try {
        formBuilder = new DynamicFormBuilder('dynamic-form-container');
        console.log('FormBuilder инициализирован');
    } catch (e) {
        console.error('Ошибка инициализации FormBuilder:', e);
    }
    
    try {
        searchManager = new SearchManager();
        console.log('SearchManager инициализирован');
    } catch (e) {
        console.error('Ошибка инициализации SearchManager:', e);
    }
    
    // Настраиваем обработчики событий
    setupEventListeners();
    console.log('Generator select handler set');
    
    // Добавляем кнопку перезагрузки если её нет
    addReloadButton();
    
    // Загружаем список генераторов
    updateGeneratorsList().then(count => {
        console.log(`Initial load: ${count} generators from API`);
    }).catch(error => {
        console.error('Error during initial load:', error);
    });
    
    console.log('Инициализация завершена');
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

/**
 * Добавляет кнопку перезагрузки если её нет
 */
function addReloadButton() {
    const generatorSelect = document.getElementById('generator-select');
    if (!generatorSelect) return;
    
    const existingBtn = document.getElementById('reload-generators-btn');
    if (existingBtn) return; // Кнопка уже есть
    
    // Создаем кнопку перезагрузки
    const reloadBtn = document.createElement('button');
    reloadBtn.id = 'reload-generators-btn';
    reloadBtn.type = 'button';
    reloadBtn.className = 'btn btn-outline-secondary btn-sm ms-2';
    reloadBtn.innerHTML = '<i class="fas fa-sync-alt me-1"></i> Обновить';
    reloadBtn.title = 'Перезагрузить список генераторов';
    
    // Добавляем обработчик
    reloadBtn.addEventListener('click', reloadGenerators);
    
    // Вставляем кнопку рядом с селектом
    const formGroup = generatorSelect.closest('.mb-4');
    if (formGroup) {
        const wrapper = document.createElement('div');
        wrapper.className = 'd-flex align-items-center';
        
        generatorSelect.parentNode.insertBefore(wrapper, generatorSelect);
        wrapper.appendChild(generatorSelect);
        wrapper.appendChild(reloadBtn);
        
        // Добавляем flex-grow к селекту
        generatorSelect.classList.add('flex-grow-1');
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
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            return response.json();
        })
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

                console.log(`Updated generators list: ${data.generators.length} generators`);
                return data.generators.length;
            } else {
                throw new Error(data.message || 'Failed to get generators');
            }
        })
        .catch(error => {
            console.error('Error updating generators list:', error);
            showNotification('error', `Ошибка загрузки генераторов: ${error.message}`);
            return 0;
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
    .then(response => {
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        return response.json();
    })
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
    
    const dynamicFormContainer = document.getElementById('dynamic-form-container');
    const emptyState = document.getElementById('empty-state');
    const loadingSpinner = document.getElementById('loading-spinner');
    const formActions = document.getElementById('form-actions');
    
    if (!generatorType) {
        // Скрываем форму и показываем пустое состояние
        if (dynamicFormContainer && emptyState) {
            dynamicFormContainer.innerHTML = '';
            dynamicFormContainer.appendChild(emptyState);
            emptyState.classList.remove('d-none');
        }
        if (formActions) formActions.classList.add('d-none');
        return;
    }

    // Используем встроенный метод DynamicFormBuilder
    if (formBuilder) {
        formBuilder.loadGeneratorForm(generatorType);
        
        // Показываем кнопки действий
        if (formActions) formActions.classList.remove('d-none');
        
        // Настраиваем обработчики кнопок формы
        setupFormButtons(generatorType);
    } else {
        console.error('FormBuilder not available');
        showNotification('error', 'FormBuilder не инициализирован');
    }
}

/**
 * Настройка обработчиков кнопок формы
 */
function setupFormButtons(generatorType) {
    const previewBtn = document.getElementById('preview-btn');
    const generateBtn = document.querySelector('#form-actions button[type="submit"]');
    
    if (previewBtn) {
        // Удаляем предыдущие обработчики
        previewBtn.onclick = null;
        previewBtn.addEventListener('click', () => {
            if (formBuilder) {
                formBuilder.previewDAG();
            } else {
                handlePreview(generatorType);
            }
        });
    }
    
    if (generateBtn) {
        // Удаляем предыдущие обработчики
        generateBtn.onclick = null;
        generateBtn.addEventListener('click', (e) => {
            e.preventDefault();
            if (formBuilder) {
                formBuilder.generateDAG();
            } else {
                handleGenerate(generatorType);
            }
        });
    }
}

/**
 * Обработка предпросмотра
 */
function handlePreview(generatorType) {
    if (!formBuilder) {
        showNotification('error', 'FormBuilder не инициализирован');
        return;
    }
    
    const formData = formBuilder.getFormData();
    
    if (!formData) {
        showNotification('error', 'Пожалуйста, заполните все обязательные поля');
        return;
    }
    
    // Показываем загрузку
    const previewBtn = document.getElementById('preview-btn');
    const originalContent = previewBtn.innerHTML;
    previewBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Генерация...';
    previewBtn.disabled = true;
    
    fetch('/dag-generator/api/preview', { // Добавлен /api/
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCsrfToken()
        },
        body: JSON.stringify({
            generator_type: generatorType,
            config: formData // Изменено с form_data на config
        })
    })
    .then(response => {
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        // Проверяем Content-Type перед парсингом JSON
        const contentType = response.headers.get('content-type');
        if (!contentType || !contentType.includes('application/json')) {
            return response.text().then(text => {
                console.error('Non-JSON response:', text.substring(0, 500));
                throw new Error('Сервер вернул не JSON ответ');
            });
        }
        
        return response.json();
    })
    .then(data => {
        if (data.success) {
            showPreviewModal(data.preview_code);
        } else {
            throw new Error(data.error || 'Preview generation failed');
        }
    })
    .catch(error => {
        console.error('Preview error:', error);
        showNotification('error', `Ошибка генерации предпросмотра: ${error.message}`);
    })
    .finally(() => {
        previewBtn.innerHTML = originalContent;
        previewBtn.disabled = false;
    });
}

/**
 * Обработка генерации DAG
 */
function handleGenerate(generatorType) {
    if (!formBuilder) {
        showNotification('error', 'FormBuilder не инициализирован');
        return;
    }
    
    const formData = formBuilder.getFormData();
    
    if (!formData) {
        showNotification('error', 'Пожалуйста, заполните все обязательные поля');
        return;
    }
    
    // Показываем загрузку
    const generateBtn = document.querySelector('#form-actions button[type="submit"]');
    const originalContent = generateBtn.innerHTML;
    generateBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Создание...';
    generateBtn.disabled = true;
    
    fetch('/dag-generator/api/generate', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCsrfToken()
        },
        body: JSON.stringify({
            generator_type: generatorType,
            config: formData
        })
    })
    .then(response => {
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const contentType = response.headers.get('content-type');
        if (!contentType || !contentType.includes('application/json')) {
            return response.text().then(text => {
                console.error('Non-JSON response:', text.substring(0, 500));
                throw new Error('Сервер вернул не JSON ответ');
            });
        }
        
        return response.json();
    })
    .then(data => {
        if (data.success) {
            // Показываем только уведомление, без кода
            showNotification('success', `✅ DAG "${data.dag_id}" успешно создан и сохранен в файл: ${data.dag_file_path}`);
        } else {
            throw new Error(data.error || 'DAG generation failed');
        }
    })
    .catch(error => {
        console.error('Generate error:', error);
        showNotification('error', `❌ Ошибка создания DAG: ${error.message}`);
    })
    .finally(() => {
        generateBtn.innerHTML = originalContent;
        generateBtn.disabled = false;
    });
}

/**
 * Показывает модальное окно с предпросмотром кода
 */
function showPreviewModal(code) {
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
                        <h5 class="modal-title">
                            <i class="fas fa-eye me-2"></i>Предпросмотр DAG
                        </h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                        <pre><code id="preview-code" class="language-python"></code></pre>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">
                            Закрыть
                        </button>
                        <button type="button" class="btn btn-primary" onclick="copyPreviewCode()">
                            <i class="fas fa-copy me-2"></i>Копировать код
                        </button>
                    </div>
                </div>
            </div>
        `;
        document.body.appendChild(modal);
    }
    
    // Обновляем код
    const codeElement = document.getElementById('preview-code');
    codeElement.textContent = code;
    
    // Показываем модальное окно
    const bootstrapModal = new bootstrap.Modal(modal);
    bootstrapModal.show();
}

/**
 * Копирует код предпросмотра в буфер обмена
 */
function copyPreviewCode() {
    const codeElement = document.getElementById('preview-code');
    if (codeElement) {
        navigator.clipboard.writeText(codeElement.textContent).then(() => {
            showNotification('success', 'Код скопирован в буфер обмена');
        }).catch(err => {
            console.error('Failed to copy code:', err);
            showNotification('error', 'Не удалось скопировать код');
        });
    }
}

/**
 * Показывает уведомление
 */
function showNotification(type, message) {
    // Создаем контейнер для уведомлений если его нет
    let container = document.getElementById('notifications-container');
    if (!container) {
        container = document.createElement('div');
        container.id = 'notifications-container';
        container.style.cssText = 'position: fixed; top: 20px; right: 20px; z-index: 1050; max-width: 400px;';
        document.body.appendChild(container);
    }
    
    // Создаем уведомление
    const notification = document.createElement('div');
    notification.className = `alert alert-${type === 'error' ? 'danger' : type} alert-dismissible fade show`;
    notification.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    container.appendChild(notification);
    
    // Автоматически удаляем через 5 секунд
    setTimeout(() => {
        if (notification.parentNode) {
            notification.remove();
        }
    }, 5000);
}
