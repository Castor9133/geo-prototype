/**
 * GEOrank 自定义首页菜单栏运行时。
 * 自定义首页经过安全清洗后只允许加载这段同源平台脚本。
 */
(function() {
    'use strict';

    const DEFAULT_MENU_ITEMS = [
        { id: 'suite', label: 'GEO Suite', url: '/suite', target: '_self', enabled: true },
        { id: 'diagnostic', label: '诊断', url: '/diagnostic', target: '_blank', enabled: true },
        { id: 'keywords', label: '拓词', url: '/keywords', target: '_blank', enabled: true },
        { id: 'measure', label: '观测', url: '/suite?step=measure', target: '_self', enabled: true },
        { id: 'config', label: '配置', url: '/admin/settings', target: '_blank', enabled: true },
    ];

    function apiBase() {
        return '';
    }

    function normalizeUrl(value) {
        const url = String(value || '').trim();
        if (!url) return '';
        if (url.startsWith('/') && !url.startsWith('//')) return url;
        if (url.startsWith('#') && url.length > 1) return url;
        try {
            const parsed = new URL(url);
            return ['http:', 'https:'].includes(parsed.protocol) && parsed.hostname ? url : '';
        } catch (_) {
            return '';
        }
    }

    function ensureSuiteItem(items) {
        if (items.some(item => item.id === 'suite' || item.url === '/suite')) {
            return items.slice(0, 12);
        }
        return [
            { id: 'suite', label: 'GEO Suite', url: '/suite', target: '_self', enabled: true },
            ...items,
        ].slice(0, 12);
    }

    function normalizeMenu(value) {
        const source = Array.isArray(value?.items) && value.items.length
            ? value.items
            : DEFAULT_MENU_ITEMS;
        const items = source.slice(0, 12).map((item, index) => ({
            id: String(item?.id || `menu-${index + 1}`),
            label: String(item?.label || '').trim().slice(0, 40),
            url: normalizeUrl(item?.url),
            target: item?.target === '_self' ? '_self' : '_blank',
            enabled: item?.enabled !== false,
        })).filter(item => item.enabled && item.label && item.url)
            .filter(item => {
                const id = String(item.id || '').toLowerCase();
                const url = String(item.url || '').toLowerCase();
                if (id === 'companies' || id === 'experts' || id === 'tutorial' || id === 'github' || id === 'solutions' || id === 'plans' || id === 'tools') return false;
                if (url === '/companies' || url.startsWith('/companies/') || url === '/company' || url.startsWith('/company/')) return false;
                if (url === '/submit-company' || url === '/company-submit' || url.startsWith('/c/')) return false;
                if (url === '/experts' || url.startsWith('/experts/')) return false;
                if (url === '/tutorial' || url.startsWith('/tutorial/')) return false;
                if (url === '/solutions' || url.startsWith('/solutions/') || url === '/plans' || url.startsWith('/plans/') || url === '/qa' || url.startsWith('/qa/')) return false;
                if (url === '/tools' || url.startsWith('/tools/')) return false;
                if (url.includes('github.com/yaojingang/georank')) return false;
                return true;
            });
        return ensureSuiteItem(items.length ? items : DEFAULT_MENU_ITEMS.map(item => ({...item})));
    }

    function createLink(item) {
        const link = document.createElement('a');
        link.href = item.url;
        link.textContent = item.label;
        link.dataset.navigationItem = item.id;
        link.target = item.target;
        if (item.target === '_blank') link.rel = 'noopener noreferrer';
        return link;
    }

    function renderMenu(items) {
        if (!items.length) return;
        const containers = new Set([
            ...document.querySelectorAll('[data-site-navigation]'),
            ...document.querySelectorAll('#navMenu'),
        ]);
        containers.forEach(container => {
            const isList = ['UL', 'OL'].includes(container.tagName);
            const fragment = document.createDocumentFragment();
            items.forEach(item => {
                const link = createLink(item);
                if (isList) {
                    const listItem = document.createElement('li');
                    listItem.appendChild(link);
                    fragment.appendChild(listItem);
                } else {
                    fragment.appendChild(link);
                }
            });
            container.replaceChildren(fragment);
        });
    }

    function applyFallback() {
        renderMenu(normalizeMenu(null));
    }

    fetch(`${apiBase()}/api/settings/public`, {cache: 'default'})
        .then(response => response.ok ? response.json() : null)
        .then(settings => renderMenu(normalizeMenu(settings?.navigation_menu)))
        .catch(applyFallback);

    function initReveal() {
        const nodes = document.querySelectorAll('.reveal');
        if (!nodes.length) return;
        if (!('IntersectionObserver' in window)) {
            nodes.forEach(node => node.classList.add('visible'));
            return;
        }
        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (!entry.isIntersecting) return;
                entry.target.classList.add('visible');
                observer.unobserve(entry.target);
            });
        }, { rootMargin: '0px 0px -8% 0px', threshold: 0.08 });
        nodes.forEach(node => observer.observe(node));
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initReveal, { once: true });
    } else {
        initReveal();
    }
})();
