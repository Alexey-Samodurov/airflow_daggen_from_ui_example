/**
 * Главный JavaScript файл для DAG Generator
 * Алгоритм работы с формами и интеграция всех модулей
 */

// Глобальные переменные
let formBuilder;
let generatorsData = [];
let currentPageType = 'index'; // 'index' или 'form'

// Инициализация после загрузки DOM
document.addEventListener('DOMContentLoaded', function() {
    // Определяем тип страницы
    currentPageType = determinePageType();
    
    if (currentPageType === 'index') {
        initializeIndexPage();
    } else if (currentPageType === 'form') {
        initializeFormPage();
    }
});

function determinePageType() {
    // Определяем тип страницы по наличию элементов
    if (document.getElementById('dynamic-form-container')) {
        return document.getElementById('generator-info') ? 'index' : 'form';
    }
    return 'index';
}

// === ИНИЦИАЛИЗАЦИЯ ГЛАВНОЙ СТРАНИЦЫ ===
async function initializeIndexPage() {
    try {
        console.log('Initializing index page...');
        
        // Инициализируем форм билдер для главной страницы
        formBuilder = new DynamicFormBuilder('dynamic-form-container');
        
        // Загружаем список генераторов
        await loadGeneratorsList();
        
        // Проверяем статус hot reload
        await checkHotReloadStatus();
        
        // Настраиваем обработчики событий для главной страницы
        setupIndexPageEventHandlers();
        
        console.log('Index page initialized successfully');
        
    } catch (error) {
        console.error('Failed to initialize index page:', error);
        DagGeneratorUtils.showErrorMessage('Ошибка инициализации главной страницы');
    }
}

// === ИНИЦИАЛИЗАЦИЯ СТРАНИЦЫ ФОРМЫ ===
async function initializeFormPage() {
    try {
        console.log('Initializing form page...');
        
        // Инициализируем компоненты
        formBuilder = new DynamicFormBuilder('dynamic-form-container');
        
        // Загружаем список генераторов
        await loadGeneratorsList();
        
        // Проверяем статус hot reload
        await checkHotReloadStatus();
        
        // Настраиваем обработчики событий
        setupFormPageEventHandlers();
        
        // Автоматически загружаем форму если генератор указан в URL
        checkUrlForGenerator();
        
        console.log('Form page initialized successfully');
        
    } catch (error) {
        console.error('Failed to initialize form page:', error);
        DagGeneratorUtils.showErrorMessage('Ошибка инициализации страницы форм');
    }
}

// === ЗАГРУЗКА СПИСКА ГЕНЕРАТОРОВ ===
async function loadGeneratorsList() {
    try {
        console.log('Loading generators list...');
        
        const response = await apiClient.getGenerators();
        
        if (response.status === 'success' && response.generators) {
            generatorsData = response.generators;
            populateGeneratorSelect(response.generators);
            
            // Обновляем счетчики на главной странице
            updateGeneratorCounts(response.generators.length);
            
            console.log(`Loaded ${response.generators.length} generators:`, response.generators.map(g => g.name));
        } else {
            throw new Error(response.message || 'No generators found');
        }
    } catch (error) {
        console.error('Error loading generators:', error);
        DagGeneratorUtils.showErrorMessage('Не удалось загрузить список генераторов: ' + error.message);
    }
}

function populateGeneratorSelect(generators) {
    const select = document.getElementById('generator-select');
    if (!select) {
        console.warn('Generator select element not found');
        return;
    }

    // Очищаем существующие опции (кроме первой пустой)
    while (select.children.length > 1) {
        select.removeChild(select.lastChild);
    }

    // Проверяем формат данных
    if (!Array.isArray(generators)) {
        console.error('Generators is not an array:', generators);
        return;
    }

    // Сортируем генераторы по display_name для отображения
    const sortedGenerators = generators.slice().sort((a, b) => 
        a.display_name.localeCompare(b.display_name)
    );

    // Добавляем опции
    sortedGenerators.forEach((generator) => {
        const option = document.createElement('option');
        option.value = generator.name;
        option.textContent = generator.display_name;
        option.title = generator.description;
        select.appendChild(option);
    });

    console.log(`Populated generator select with ${sortedGenerators.length} options`);
}

function updateGeneratorCounts(count) {
    // Обновляем счетчики на странице
    const elements = document.querySelectorAll('#generators-count, #active-generators-count');
    elements.forEach(el => {
        if (el) el.textContent = count;
    });
}

// === ОБРАБОТЧИКИ СОБЫТИЙ ДЛЯ ГЛАВНОЙ СТРАНИЦЫ ===
function setupIndexPageEventHandlers() {
    const generatorSelect = document.getElementById('generator-select');
    if (generatorSelect) {
        generatorSelect.addEventListener('change', onIndexGeneratorSelect);
    }
    
    // Глобальные обработчики
    setupGlobalEventHandlers();
}

async function onIndexGeneratorSelect(event) {
    const generatorType = event.target.value;
    
    console.log(`Generator selected on index page: ${generatorType}`);
    
    if (generatorType) {
        // Показываем информацию о генераторе
        await showGeneratorInfoOnIndex(generatorType);
        
        // Загружаем форму генератора
        await formBuilder.loadGeneratorForm(generatorType);
        
        // Скрываем пустое состояние
        hideEmptyState();
        
    } else {
        // Скрываем информацию и показываем пустое состояние
        hideGeneratorInfoOnIndex();
        showEmptyState();
        formBuilder.loadGeneratorForm(null);
    }
}

async function showGeneratorInfoOnIndex(generatorType) {
    try {
        // Ищем генератор в локальных данных
        const generator = generatorsData.find(g => g.name === generatorType);
        
        if (generator) {
            // Обновляем информацию о генераторе
            const elements = {
                'generator-display-name': generator.display_name,
                'generator-description': generator.description,
                'required-fields-count': generator.required_fields?.length || 0,
                'optional-fields-count': Object.keys(generator.optional_fields || {}).length
            };
            
            Object.entries(elements).forEach(([id, value]) => {
                const element = document.getElementById(id);
                if (element) element.textContent = value;
            });
            
            // Показываем блок с информацией
            const infoBlock = document.getElementById('generator-info');
            if (infoBlock) {
                infoBlock.classList.remove('d-none');
            }
        }
        
    } catch (error) {
        console.error('Error loading generator info:', error);
        DagGeneratorUtils.showWarningMessage('Не удалось загрузить информацию о генераторе');
    }
}

function hideGeneratorInfoOnIndex() {
    const infoBlock = document.getElementById('generator-info');
    if (infoBlock) {
        infoBlock.classList.add('d-none');
    }
}

function showEmptyState() {
    const container = document.getElementById('dynamic-form-container');
    const emptyState = document.getElementById('empty-state');
    
    if (container && emptyState) {
        // Очищаем контейнер и показываем пустое состояние
        container.innerHTML = emptyState.outerHTML;
    }
}

function hideEmptyState() {
    const emptyState = document.getElementById('empty-state');
    if (emptyState) {
        emptyState.style.display = 'none';
    }
}

// === ОБРАБОТЧИКИ СОБЫТИЙ ДЛЯ СТРАНИЦЫ ФОРМЫ ===
function setupFormPageEventHandlers() {
    const generatorSelect = document.getElementById('generator-select');
    if (generatorSelect) {
        generatorSelect.addEventListener('change', onFormGeneratorSelect);
    }
    
    // Глобальные обработчики
    setupGlobalEventHandlers();
}

async function onFormGeneratorSelect(event) {
    const generatorType = event.target.value;
    
    console.log(`Generator selected on form page: ${generatorType}`);
    
    if (generatorType && formBuilder) {
        await formBuilder.loadGeneratorForm(generatorType);
        
        // Обновляем URL для удобства
        updateUrlWithGenerator(generatorType);
    } else {
        formBuilder?.loadGeneratorForm(null);
        clearUrlGenerator();
    }
}

// === ГЛОБАЛЬНЫЕ ОБРАБОТЧИКИ СОБЫТИЙ ===
function setupGlobalEventHandlers() {
    // Глобальные обработчики клавиатуры
    document.addEventListener('keydown', function(e) {
        // Ctrl+Enter для генерации
        if (e.ctrlKey && e.key === 'Enter') {
            e.preventDefault();
            if (formBuilder && formBuilder.currentGeneratorType) {
                formBuilder.generateDAG();
            }
        }
        
        // Escape для сброса формы
        if (e.key === 'Escape') {
            const modal = document.querySelector('.modal.show');
            if (!modal && formBuilder) {
                formBuilder.resetForm();
            }
        }
    });

    // Обработчик изменения размера окна
    window.addEventListener('resize', DagGeneratorUtils.debounce(() => {
        handleWindowResize();
    }, 250));

    // Автосохранение формы в localStorage
    document.addEventListener('input', DagGeneratorUtils.debounce(() => {
        if (formBuilder && formBuilder.currentGeneratorType) {
            saveFormState();
        }
    }, 1000));
}

function handleWindowResize() {
    // Логика адаптации интерфейса при изменении размера
    const container = document.querySelector('.container-fluid');
    if (container) {
        if (window.innerWidth < 768) {
            container.classList.add('mobile-view');
        } else {
            container.classList.remove('mobile-view');
        }
    }
}

// === УПРАВЛЕНИЕ СОСТОЯНИЕМ И URL ===
function updateUrlWithGenerator(generatorType) {
    const url = new URL(window.location);
    url.searchParams.set('generator', generatorType);
    window.history.replaceState({}, '', url);
}

function clearUrlGenerator() {
    const url = new URL(window.location);
    url.searchParams.delete('generator');
    window.history.replaceState({}, '', url);
}

function checkUrlForGenerator() {
    const url = new URL(window.location);
    const generator = url.searchParams.get('generator');
    
    if (generator) {
        const select = document.getElementById('generator-select');
        if (select) {
            select.value = generator;
            select.dispatchEvent(new Event('change'));
        }
    }
}

// === СОХРАНЕНИЕ И ВОССТАНОВЛЕНИЕ СОСТОЯНИЯ ===
function saveFormState() {
    try {
        const form = document.querySelector('#dynamic-form-container form');
        if (!form || !formBuilder.currentGeneratorType) return;

        const formData = new FormData(form);
        const data = Object.fromEntries(formData.entries());
        
        const stateKey = `dag-generator-form-${formBuilder.currentGeneratorType}`;
        localStorage.setItem(stateKey, JSON.stringify(data));
        
        console.log('Form state saved for', formBuilder.currentGeneratorType);
    } catch (error) {
        console.warn('Failed to save form state:', error);
    }
}

function restoreFormState(generatorType) {
    try {
        const stateKey = `dag-generator-form-${generatorType}`;
        const savedData = localStorage.getItem(stateKey);
        
        if (savedData) {
            const data = JSON.parse(savedData);
            const form = document.querySelector('#dynamic-form-container form');
            
            if (form) {
                Object.entries(data).forEach(([name, value]) => {
                    const field = form.querySelector(`[name="${name}"]`);
                    if (field) {
                        if (field.type === 'checkbox') {
                            field.checked = value === 'on';
                        } else {
                            field.value = value;
                        }
                    }
                });
                
                console.log('Form state restored for', generatorType);
            }
        }
    } catch (error) {
        console.warn('Failed to restore form state:', error);
    }
}

// === УТИЛИТЫ И ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ===
async function checkHotReloadStatus() {
    try {
        // Проверяем статус hot reload через API
        const response = await fetch('/dag-generator/api/hot-reload-status');
        const data = await response.json();
        
        const statusElement = document.getElementById('hot-reload-status');
        if (statusElement) {
            if (data.active) {
                statusElement.textContent = 'Активен';
                statusElement.className = 'badge bg-success';
            } else {
                statusElement.textContent = 'Выключен';
                statusElement.className = 'badge bg-secondary';
            }
        }
    } catch (error) {
        console.warn('Failed to check hot reload status:', error);
        const statusElement = document.getElementById('hot-reload-status');
        if (statusElement) {
            statusElement.textContent = 'Ошибка';
            statusElement.className = 'badge bg-danger';
        }
    }
}

// === ЭКСПОРТИРУЕМЫЕ ФУНКЦИИ ===
window.populateGeneratorSelect = populateGeneratorSelect;
window.reloadGenerators = async function() {
    await loadGeneratorsList();
    DagGeneratorUtils.showSuccessMessage('Список генераторов обновлен');
};

window.toggleHotReload = async function() {
    try {
        const response = await fetch('/dag-generator/api/toggle-hot-reload', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': window.apiClient?.csrfToken || ''
            }
        });
        
        const data = await response.json();
        
        if (data.success) {
            await checkHotReloadStatus();
            const status = data.active ? 'включен' : 'выключен';
            DagGeneratorUtils.showSuccessMessage(`Hot Reload ${status}`);
        } else {
            throw new Error(data.message);
        }
    } catch (error) {
        console.error('Failed to toggle hot reload:', error);
        DagGeneratorUtils.showErrorMessage('Ошибка переключения Hot Reload');
    }
};
