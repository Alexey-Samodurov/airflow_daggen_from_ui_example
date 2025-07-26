/**
 * Утилитарные функции для DAG Generator
 */

// CSRF Token управление
let csrfToken = null;

async function getCSRFToken() {
    if (csrfToken) {
        return csrfToken;
    }

    try {
        // ВАЖНО: URL должен соответствовать вашему Blueprint
        const response = await fetch('/dag-generator/api/csrf-token', {  // ← Исправлено
            credentials: 'include'
        });
        const data = await response.json();
        csrfToken = data.csrf_token;
        return csrfToken;
    } catch (error) {
        console.error('Error getting CSRF token:', error);
        return null;
    }
}

// Управление алертами
function showAlert(message, type = 'info', autoHide = true) {
    const alertContainer = document.getElementById('alert-container');
    const alertId = 'alert-' + Date.now();

    const alertHtml = `
        <div id="${alertId}" class="alert alert-${type} alert-dismissible fade show" role="alert">
            <i class="fas fa-${getAlertIcon(type)}"></i>
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
    `;

    alertContainer.insertAdjacentHTML('beforeend', alertHtml);

    if (autoHide && type !== 'danger') {
        setTimeout(() => {
            const alert = document.getElementById(alertId);
            if (alert) {
                const bsAlert = new bootstrap.Alert(alert);
                bsAlert.close();
            }
        }, 5000);
    }
}

function getAlertIcon(type) {
    const icons = {
        'success': 'check-circle',
        'danger': 'exclamation-triangle',
        'warning': 'exclamation-circle',
        'info': 'info-circle',
        'primary': 'info-circle'
    };
    return icons[type] || 'info-circle';
}

function showSuccessMessage(message) {
    showAlert(message, 'success');
}

function showErrorMessage(message) {
    showAlert(message, 'danger', false);
}

function showWarningMessage(message) {
    showAlert(message, 'warning');
}

function showInfoMessage(message) {
    showAlert(message, 'info');
}

// Копирование в буфер обмена
async function copyToClipboard(selector) {
    try {
        const element = document.querySelector(selector);
        const text = element.textContent || element.innerText;

        await navigator.clipboard.writeText(text);
        showSuccessMessage('Код скопирован в буфер обмена!');
    } catch (error) {
        console.error('Error copying to clipboard:', error);
        showErrorMessage('Ошибка при копировании в буфер обмена');
    }
}

// Загрузка с индикатором
function showLoading(containerId) {
    const container = document.getElementById(containerId);
    if (container) {
        container.classList.add('loading-overlay');
    }

    const spinner = document.getElementById('loading-spinner');
    if (spinner) {
        spinner.classList.remove('d-none');
    }
}

function hideLoading(containerId) {
    const container = document.getElementById(containerId);
    if (container) {
        container.classList.remove('loading-overlay');
    }

    const spinner = document.getElementById('loading-spinner');
    if (spinner) {
        spinner.classList.add('d-none');
    }
}

// Валидация форм
function validateForm(formId) {
    const form = document.getElementById(formId);
    if (!form) return false;

    let isValid = true;
    const requiredFields = form.querySelectorAll('[required]');

    requiredFields.forEach(field => {
        if (!field.value.trim()) {
            field.classList.add('is-invalid');
            isValid = false;
        } else {
            field.classList.remove('is-invalid');
            field.classList.add('is-valid');
        }
    });

    return isValid;
}

// Дебаунс функция
function debounce(func, wait) {
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

// Форматирование данных
function formatBytes(bytes, decimals = 2) {
    if (bytes === 0) return '0 Bytes';

    const k = 1024;
    const dm = decimals < 0 ? 0 : decimals;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];

    const i = Math.floor(Math.log(bytes) / Math.log(k));

    return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
}

function formatDate(date) {
    return new Intl.DateTimeFormat('ru-RU', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit'
    }).format(new Date(date));
}

// Анимации
function fadeIn(element, duration = 300) {
    element.style.opacity = 0;
    element.style.display = 'block';

    const start = performance.now();

    function animate(currentTime) {
        const elapsed = currentTime - start;
        const progress = elapsed / duration;

        if (progress < 1) {
            element.style.opacity = progress;
            requestAnimationFrame(animate);
        } else {
            element.style.opacity = 1;
        }
    }

    requestAnimationFrame(animate);
}

function fadeOut(element, duration = 300) {
    const start = performance.now();
    const startOpacity = parseFloat(element.style.opacity) || 1;

    function animate(currentTime) {
        const elapsed = currentTime - start;
        const progress = elapsed / duration;

        if (progress < 1) {
            element.style.opacity = startOpacity * (1 - progress);
            requestAnimationFrame(animate);
        } else {
            element.style.opacity = 0;
            element.style.display = 'none';
        }
    }

    requestAnimationFrame(animate);
}

// Экспорт для использования в других модулях
window.DagGeneratorUtils = {
    getCSRFToken,
    showAlert,
    showSuccessMessage,
    showErrorMessage,
    showWarningMessage,
    showInfoMessage,
    copyToClipboard,
    showLoading,
    hideLoading,
    validateForm,
    debounce,
    formatBytes,
    formatDate,
    fadeIn,
    fadeOut
};
