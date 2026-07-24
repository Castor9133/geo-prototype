/**
 * Index Page - 公司目录动态加载
 */
(window.GEOrank?.PageLifecycle?.run?.bind(window.GEOrank.PageLifecycle)
    || ((callback) => callback()))(() => {
    'use strict';

    const API_BASE = '';
    const Routes = window.GEOrank?.Routes;

    const state = {
        sort: 'newest',
        page: 1,
        pages: 1,
        items: [],
        tutorials: [],
        popularCompanies: [],
    };

    const elements = {
        companyList: document.getElementById('company-list'),
        loadMore: document.getElementById('company-load-more'),
        sortNewest: document.getElementById('company-sort-newest'),
        sortViews: document.getElementById('company-sort-views'),
        featuredTipTitle: document.getElementById('featured-tip-title'),
        featuredTipCopy: document.getElementById('featured-tip-copy'),
        featuredTipLink: document.getElementById('featured-tip-link'),
        hotGuidesList: document.getElementById('hot-guides-list'),
        hotCompaniesList: document.getElementById('hot-companies-list'),
        resourceLinks: document.getElementById('resource-links'),
    };

    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text == null ? '' : String(text);
        return div.innerHTML;
    }

    const PUBLIC_PLACEHOLDER_VALUES = new Set([
        '--',
        'n/a',
        'na',
        'none',
        'null',
        'unknown',
        '待补充',
        '未知',
    ]);

    function publicProfileValue(value) {
        const normalized = value == null ? '' : String(value).replace(/\s+/g, ' ').trim();
        return PUBLIC_PLACEHOLDER_VALUES.has(normalized.toLowerCase()) ? '' : normalized;
    }

    function request(path) {
        return fetch(`${API_BASE}${path}`).then(async (response) => {
            const data = await response.json().catch(() => ({}));
            if (!response.ok) {
                const message = data.detail || `请求失败 (${response.status})`;
                throw new Error(typeof message === 'string' ? message : JSON.stringify(message));
            }
            return data;
        });
    }

    function buildCompanyLink(company) {
        if (Routes?.buildCompanyDetail) {
            return Routes.buildCompanyDetail(company?.path_key || company?.id || '');
        }
        const url = new URL('/company', window.location.origin);
        url.searchParams.set('id', company?.id || '');
        return url.toString();
    }

    function renderCompanyLogo(company) {
        if (company.logo_url) {
            return `<img alt="${escapeHtml(company.name)} Logo" class="w-full h-full object-cover" src="${escapeHtml(company.logo_url)}">`;
        }
        const initials = String(company.name || '?')
            .split(/\s+/)
            .map((part) => part.slice(0, 1))
            .join('')
            .slice(0, 2)
            .toUpperCase();
        return `<div class="w-full h-full flex items-center justify-center text-sm font-extrabold text-primary">${escapeHtml(initials || '?')}</div>`;
    }

    function renderCompanyCard(company) {
        const tags = Array.isArray(company.tags)
            ? company.tags.map(publicProfileValue).filter(Boolean).slice(0, 3)
            : [];
        const metaTags = [company.category, company.funding_stage, company.headquarters]
            .map(publicProfileValue)
            .filter(Boolean);
        const description = publicProfileValue(company.short_description) || '该公司暂未补充简介';
        return `
            <div class="group flex items-start gap-4 md:gap-6 p-3 md:p-4 rounded-xl hover:bg-slate-50 transition-colors duration-300">
                <div class="w-14 h-14 md:w-20 md:h-20 rounded-xl overflow-hidden flex-shrink-0 bg-neutral-100 border border-slate-100">
                    ${renderCompanyLogo(company)}
                </div>
                <div class="flex-grow min-w-0">
                    <a href="${buildCompanyLink(company)}" class="company-card-link block rounded-lg focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/30">
                        <div class="flex items-center gap-2 mb-1">
                            <h3 class="text-base md:text-lg font-bold font-headline truncate group-hover:text-primary transition-colors">${escapeHtml(company.name)}</h3>
                            ${company.is_geo_certified ? '<span class="material-symbols-outlined text-primary text-sm filled">verified</span>' : ''}
                        </div>
                        <p class="text-on-surface-variant text-sm mb-3 line-clamp-2">${escapeHtml(description)}</p>
                    </a>
                    <div class="flex flex-wrap gap-2">
                        ${tags.map((tag) => `<span class="tag">${escapeHtml(tag)}</span>`).join('')}
                        ${!tags.length && metaTags.length ? metaTags.map((tag) => `<span class="tag">${escapeHtml(tag)}</span>`).join('') : ''}
                    </div>
                </div>
                <div title="公司详情页访问量" aria-label="公司详情页访问量 ${Number(company.view_count || 0).toLocaleString('zh-CN')}" class="flex min-w-[58px] flex-col items-center justify-center rounded-lg border border-slate-100 bg-white/80 px-3 py-2 text-slate-400">
                    <span class="material-symbols-outlined text-sm" aria-hidden="true">visibility</span>
                    <span class="mt-1 text-xs font-bold text-slate-500 md:text-sm">${Number(company.view_count || 0).toLocaleString('zh-CN')}</span>
                </div>
            </div>
        `;
    }

    function updateSortButtons() {
        [
            [elements.sortNewest, 'newest'],
            [elements.sortViews, 'views'],
        ].forEach(([button, value]) => {
            if (!button) return;
            const isActive = state.sort === value;
            button.setAttribute('aria-pressed', String(isActive));
            button.querySelector('[data-company-sort-indicator]')?.classList.toggle('hidden', !isActive);
            button.className = isActive
                ? 'company-sort-control text-sm font-semibold text-primary flex items-center gap-1'
                : 'company-sort-control text-sm font-semibold text-neutral-400 hover:text-neutral-900 transition-colors flex items-center gap-1';
        });
    }

    function renderCompanyList(append = false) {
        if (!elements.companyList) return;
        if (!state.items.length) {
            elements.companyList.innerHTML = `
                <div class="rounded-2xl border border-dashed border-slate-200 bg-slate-50/70 p-8 text-sm text-slate-400">
                    当前没有可展示的已发布公司，稍后再来查看。
                </div>
            `;
            return;
        }

        if (append) {
            elements.companyList.insertAdjacentHTML('beforeend', state.items.slice(-6).map(renderCompanyCard).join(''));
        } else {
            elements.companyList.innerHTML = state.items.map(renderCompanyCard).join('');
        }
    }

    function renderHotGuides() {
        // 教程频道已下线：保留静态常用入口（HTML 已写死），不再用教程 API 覆盖
        return;
    }

    function renderHotCompanies() {
        if (!elements.hotCompaniesList) return;
        const companies = state.popularCompanies.slice(0, 3);
        if (!companies.length) {
            elements.hotCompaniesList.innerHTML = '<span class="px-3 py-4 text-sm text-slate-400 border border-dashed border-slate-200 rounded-xl block">暂无热门公司</span>';
            return;
        }

        elements.hotCompaniesList.innerHTML = companies.map((company) => {
            const tags = Array.isArray(company.tags)
                ? company.tags.map(publicProfileValue).filter(Boolean).slice(0, 2)
                : [];
            const category = publicProfileValue(company.category) || 'GEO';
            const description = publicProfileValue(company.short_description)
                || '正在构建生成式搜索时代的 GEO 能力与内容分发体系。';
            return `
                <a href="${buildCompanyLink(company)}" class="flex items-start gap-3 rounded-2xl border border-slate-100 bg-white px-4 py-4 transition-all hover:border-primary/20 hover:bg-slate-50">
                    <div class="w-11 h-11 rounded-xl overflow-hidden flex-shrink-0 bg-slate-50 border border-slate-100">
                        ${renderCompanyLogo(company)}
                    </div>
                    <div class="min-w-0 flex-1">
                        <div class="flex items-center gap-2">
                            <p class="text-sm font-bold leading-6 text-slate-800 truncate">${escapeHtml(company.name)}</p>
                            ${company.is_geo_certified ? '<span class="material-symbols-outlined text-primary text-sm filled">verified</span>' : ''}
                        </div>
                        <p class="mt-1 text-xs leading-6 text-slate-500 line-clamp-2">${escapeHtml(description)}</p>
                        <div class="mt-2 flex flex-wrap gap-2">
                            ${(tags.length ? tags : [category]).map((tag) => `<span class="tag">${escapeHtml(tag)}</span>`).join('')}
                        </div>
                    </div>
                </a>
            `;
        }).join('');
    }

    function renderTutorialSidebar() {
        renderHotCompanies();
        if (!elements.resourceLinks) return;
        elements.resourceLinks.innerHTML = [
            { href: '/suite', title: 'GEO Suite 工作流', icon: 'hub' },
            { href: '/diagnostic', title: 'GEO 诊断', icon: 'analytics' },
            { href: '/keywords', title: '拓词工具', icon: 'travel_explore' },
        ].map((item) => `
            <a href="${item.href}" class="flex items-center gap-3 p-3 rounded-xl border border-slate-50 hover:bg-slate-50 hover:shadow-sm transition-all group">
                <div class="w-8 h-8 rounded-lg bg-blue-50 flex items-center justify-center text-primary">
                    <span class="material-symbols-outlined text-sm">${item.icon}</span>
                </div>
                <span class="text-sm font-semibold text-slate-700 group-hover:text-primary">${item.title}</span>
            </a>
        `).join('');
    }

    async function loadTutorialResources() {
        // 教程频道已下线：不再请求教程内容接口，仅渲染静态 Suite / 诊断入口
        renderTutorialSidebar();
    }

    async function loadPopularCompanies() {
        try {
            const payload = await request('/api/companies/?page=1&size=3&sort=views');
            state.popularCompanies = Array.isArray(payload.items) ? payload.items : [];
            renderHotCompanies();
        } catch (_) {
            renderHotCompanies();
        }
    }

    async function loadCompanies(options = {}) {
        const { append = false } = options;
        if (!elements.companyList) return;

        if (!append) {
            elements.companyList.innerHTML = `
                <div class="rounded-2xl border border-dashed border-slate-200 bg-slate-50/70 p-8 text-sm text-slate-400">
                    正在加载公司目录...
                </div>
            `;
        }

        const size = 6;
        try {
            const payload = await request(`/api/companies/?page=${state.page}&size=${size}&sort=${state.sort}`);
            state.pages = Number(payload.pages || 1);
            const incoming = Array.isArray(payload.items) ? payload.items : [];
            state.items = append ? state.items.concat(incoming) : incoming;
            renderCompanyList(append);
            renderHotCompanies();

            if (elements.loadMore) {
                const hasMore = state.page < state.pages;
                elements.loadMore.disabled = !hasMore;
                elements.loadMore.classList.toggle('hidden', !state.items.length);
                elements.loadMore.textContent = hasMore ? '加载更多发现' : '已经到底了';
            }
        } catch (error) {
            elements.companyList.innerHTML = `
                <div class="rounded-2xl border border-dashed border-red-200 bg-red-50/60 p-8 text-sm text-red-500">
                    加载公司目录失败：${escapeHtml(error.message)}
                </div>
            `;
            if (elements.loadMore) elements.loadMore.disabled = true;
        }
    }

    function bindEvents() {
        document.querySelectorAll('[data-company-sort]').forEach((button) => {
            button.addEventListener('click', async () => {
                const nextSort = button.dataset.companySort;
                if (!nextSort || nextSort === state.sort) return;
                state.sort = nextSort;
                state.page = 1;
                updateSortButtons();
                await loadCompanies();
            });
        });

        elements.loadMore?.addEventListener('click', async () => {
            if (state.page >= state.pages) return;
            state.page += 1;
            await loadCompanies({ append: true });
        });
    }

    async function init() {
        updateSortButtons();
        bindEvents();
        await Promise.all([
            loadCompanies(),
            loadTutorialResources(),
            loadPopularCompanies(),
        ]);
    }

    init();
});
