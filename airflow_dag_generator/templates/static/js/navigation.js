/**
 * Функции для работы с навигацией и интерфейсом
 */

class NavigationManager {
    constructor() {
        this.init();
    }

    init() {
        this.initTooltips();
        this.initMobileNavigation();
        this.initScrollEffects();
        this.highlightActiveNavigation();
    }

    /**
     * Инициализация Bootstrap tooltips
     */
    initTooltips() {
        const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
        tooltipTriggerList.map(function (tooltipTriggerEl) {
            return new bootstrap.Tooltip(tooltipTriggerEl);
        });
    }

    /**
     * Настройка мобильной навигации
     */
    initMobileNavigation() {
        const navbarToggler = document.querySelector('.navbar-toggler');
        const navbarCollapse = document.querySelector('#navbarNav');

        if (navbarToggler && navbarCollapse) {
            // Закрытие меню при клике на ссылку
            const navLinks = navbarCollapse.querySelectorAll('.nav-link');
            navLinks.forEach(link => {
                link.addEventListener('click', () => {
                    if (window.innerWidth < 992) {
                        const bsCollapse = new bootstrap.Collapse(navbarCollapse, {
                            toggle: true
                        });
                    }
                });
            });
        }
    }

    /**
     * Эффекты прокрутки
     */
    initScrollEffects() {
        let lastScrollTop = 0;
        const header = document.querySelector('.main-header');

        window.addEventListener('scroll', () => {
            const scrollTop = window.pageYOffset || document.documentElement.scrollTop;

            // Добавляем тень при прокрутке
            if (scrollTop > 10) {
                header.style.boxShadow = '0 4px 12px rgba(0, 0, 0, 0.15)';
            } else {
                header.style.boxShadow = '0 4px 6px rgba(0, 0, 0, 0.1)';
            }

            lastScrollTop = scrollTop;
        });
    }

    /**
     * Подсветка активного пункта навигации
     */
    highlightActiveNavigation() {
        const currentPath = window.location.pathname;
        const navLinks = document.querySelectorAll('.navbar-nav .nav-link');

        navLinks.forEach(link => {
            const href = link.getAttribute('href');
            if (href && (currentPath === href || (href !== '/' && currentPath.startsWith(href)))) {
                link.classList.add('active');
            }
        });
    }

    /**
     * Функция для мобильного переключения панелей
     */
    toggleMobilePanels() {
        const createPanel = document.getElementById('create-panel');
        const editPanel = document.getElementById('edit-panel');

        if (!createPanel || !editPanel) return;

        if (createPanel.classList.contains('d-md-block')) {
            createPanel.classList.add('d-none', 'd-md-block');
            editPanel.classList.remove('d-none');
        } else {
            createPanel.classList.remove('d-none');
            editPanel.classList.add('d-none', 'd-md-block');
        }
    }

    /**
     * Плавная прокрутка к элементу
     */
    smoothScrollTo(elementId) {
        const element = document.getElementById(elementId);
        if (element) {
            element.scrollIntoView({
                behavior: 'smooth',
                block: 'start'
            });
        }
    }

    /**
     * Показать уведомление
     */
    showNotification(message, type = 'info') {
        // Создаем контейнер для уведомлений если его нет
        let container = document.getElementById('notifications-container');
        if (!container) {
            container = document.createElement('div');
            container.id = 'notifications-container';
            container.className = 'position-fixed top-0 end-0 p-3';
            container.style.zIndex = '1055';
            document.body.appendChild(container);
        }

        // Создаем уведомление
        const alertId = 'alert-' + Date.now();
        const alert = document.createElement('div');
        alert.id = alertId;
        alert.className = `alert alert-${type} alert-dismissible fade show`;
        alert.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;

        container.appendChild(alert);

        // Автоматически скрываем через 5 секунд
        setTimeout(() => {
            const alertElement = document.getElementById(alertId);
            if (alertElement) {
                const bsAlert = new bootstrap.Alert(alertElement);
                bsAlert.close();
            }
        }, 5000);
    }

    /**
     * Обработка ошибок загрузки изображений
     */
    handleImageErrors() {
        const images = document.querySelectorAll('img');
        images.forEach(img => {
            img.addEventListener('error', () => {
                img.style.display = 'none';
                console.warn('Failed to load image:', img.src);
            });
        });
    }
}

// Глобальные функции для обратной совместимости
function toggleMobilePanels() {
    if (window.navigationManager) {
        window.navigationManager.toggleMobilePanels();
    }
}

// Инициализация при загрузке DOM
document.addEventListener('DOMContentLoaded', function() {
    window.navigationManager = new NavigationManager();
});
