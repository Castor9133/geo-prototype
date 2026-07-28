/**
 * GEOrank - 拓词工具 JavaScript
 * 调用后端 AI API 生成 8 维拓词结果
 */
(window.GEOrank?.PageLifecycle?.run?.bind(window.GEOrank.PageLifecycle)
    || ((callback) => callback()))(() => {
    'use strict';

    const API_BASE = '';
    const Auth = window.GEOrank?.Auth;
    const Workflow = window.GEOrank?.SuiteWorkflow;
    const PREVIEW_COUNT = 8;
    /** 演示默认：对齐知识库「中文产品演示包·DJI Mini 5 Pro」与 probe-questions.md */
    const DEMO_SEEDS = ['DJI Mini 5 Pro', '大疆 Mini 5 Pro', 'Mini 5 Pro 续航'];
    const SAMPLE_PAYLOAD = {
        seeds: DEMO_SEEDS,
        profile: {
            name: '消费电子 · 航拍',
            company_hint: '围绕 DJI Mini 5 Pro（大疆迷你航拍机）的产品规格、场景与选型问答，对齐演示知识库事实卡',
            business_model: '偏 B2C / 消费电子 / 产品参数与购买决策',
            target_users: ['旅行创作者', '航拍入门用户', '内容运营', '电商选品'],
            keyword_strategy: '优先覆盖定义、关键参数、续航/图传/避障、与 Mini 4 Pro 对比、旅行夜景场景与购买决策；对齐 probe Q1–Q12。',
        },
        summary: {
            total_keywords: 64,
            average_recommendation_score: 78,
            average_business_score: 72,
            high_recommendation_ratio: 36,
            high_business_ratio: 28,
        },
        dimensions: [
            {
                key: 'semantic',
                name: '语义拓展',
                icon: 'hub',
                description: '同义词、相关术语、长尾变体',
                count: 8,
                items: [
                    { keyword: 'DJI Mini 5 Pro', recommendation_score: 88, business_score: 80 },
                    { keyword: '大疆 Mini 5 Pro', recommendation_score: 86, business_score: 78 },
                    { keyword: '一英寸大底迷你航拍机', recommendation_score: 82, business_score: 74 },
                    { keyword: 'Mini 5 Pro 航拍无人机', recommendation_score: 84, business_score: 76 },
                    { keyword: '大疆迷你机 Mini 5 Pro', recommendation_score: 80, business_score: 72 },
                    { keyword: 'Mini5 Pro 规格参数', recommendation_score: 79, business_score: 70 },
                    { keyword: 'DJI 迷你航拍机系列', recommendation_score: 77, business_score: 71 },
                    { keyword: '小有底气 Mini 5 Pro', recommendation_score: 74, business_score: 68 },
                ],
            },
            {
                key: 'scenario',
                name: '场景覆盖',
                icon: 'category',
                description: '真实使用场景与任务语境',
                count: 8,
                items: [
                    { keyword: '旅行航拍选 Mini 5 Pro', recommendation_score: 85, business_score: 78 },
                    { keyword: 'Mini 5 Pro 夜景航拍怎么拍', recommendation_score: 83, business_score: 74 },
                    { keyword: 'Mini 5 Pro 运动跟拍适合吗', recommendation_score: 81, business_score: 73 },
                    { keyword: '城市轻便航拍用 Mini 5 Pro', recommendation_score: 80, business_score: 76 },
                    { keyword: 'Mini 5 Pro 竖拍短视频怎么拍', recommendation_score: 79, business_score: 72 },
                    { keyword: '第一次飞 Mini 5 Pro 要注意什么', recommendation_score: 78, business_score: 70 },
                    { keyword: '周末郊游带 Mini 5 Pro', recommendation_score: 77, business_score: 75 },
                    { keyword: '便携旅行怎么带 Mini 5 Pro', recommendation_score: 76, business_score: 71 },
                ],
            },
            {
                key: 'commercial',
                name: '商业意图',
                icon: 'shopping_cart',
                description: '购买信号、比较、定价查询',
                count: 8,
                items: [
                    { keyword: 'Mini 5 Pro 多少钱', recommendation_score: 84, business_score: 88 },
                    { keyword: 'Mini 5 Pro 套装怎么选', recommendation_score: 82, business_score: 85 },
                    { keyword: 'Mini 5 Pro 哪里买靠谱', recommendation_score: 80, business_score: 84 },
                    { keyword: '长续航电池要不要买', recommendation_score: 78, business_score: 82 },
                    { keyword: 'Mini 5 Pro 配件清单', recommendation_score: 77, business_score: 80 },
                    { keyword: 'Mini 5 Pro 国行价格', recommendation_score: 81, business_score: 86 },
                    { keyword: '入门航拍预算 Mini 5 Pro', recommendation_score: 79, business_score: 83 },
                    { keyword: 'Mini 5 Pro 以旧换新值不值', recommendation_score: 75, business_score: 79 },
                ],
            },
            {
                key: 'ranking',
                name: '推荐榜单',
                icon: 'emoji_events',
                description: '最佳、推荐、Top 类查询',
                count: 8,
                items: [
                    { keyword: '2026 迷你航拍机推荐', recommendation_score: 83, business_score: 78 },
                    { keyword: '轻便无人机哪款好', recommendation_score: 82, business_score: 77 },
                    { keyword: '入门航拍机 Top 推荐', recommendation_score: 81, business_score: 76 },
                    { keyword: '旅行无人机推荐榜', recommendation_score: 80, business_score: 75 },
                    { keyword: '一英寸 CMOS 迷你机推荐', recommendation_score: 79, business_score: 74 },
                    { keyword: '大疆迷你系列怎么选', recommendation_score: 84, business_score: 79 },
                    { keyword: '249g 档航拍机推荐', recommendation_score: 78, business_score: 73 },
                    { keyword: '夜景航拍机推荐', recommendation_score: 77, business_score: 72 },
                ],
            },
            {
                key: 'review',
                name: '产品评测',
                icon: 'rate_review',
                description: '评测、对比、优缺点查询',
                count: 8,
                items: [
                    { keyword: 'Mini 5 Pro 评测', recommendation_score: 86, business_score: 78 },
                    { keyword: 'Mini 5 Pro vs Mini 4 Pro', recommendation_score: 88, business_score: 82 },
                    { keyword: 'Mini 5 Pro 优缺点', recommendation_score: 84, business_score: 76 },
                    { keyword: 'Mini 5 Pro 画质实测', recommendation_score: 82, business_score: 74 },
                    { keyword: 'Mini 5 Pro 避障体验', recommendation_score: 81, business_score: 73 },
                    { keyword: 'Mini 5 Pro 续航实测', recommendation_score: 85, business_score: 77 },
                    { keyword: 'Mini 5 Pro 图传距离体验', recommendation_score: 80, business_score: 72 },
                    { keyword: 'Mini 5 Pro 值不值得买', recommendation_score: 83, business_score: 80 },
                ],
            },
            {
                key: 'brand',
                name: '品牌关联',
                icon: 'business',
                description: '品牌名、产品名、替代方案',
                count: 8,
                items: [
                    { keyword: '大疆官网 Mini 5 Pro', recommendation_score: 85, business_score: 76 },
                    { keyword: 'DJI Mini 系列对比', recommendation_score: 83, business_score: 75 },
                    { keyword: 'Mini 5 Pro 竞品对比', recommendation_score: 81, business_score: 74 },
                    { keyword: '大疆 Fly App Mini 5 Pro', recommendation_score: 78, business_score: 70 },
                    { keyword: 'DJI Care Mini 5 Pro', recommendation_score: 76, business_score: 72 },
                    { keyword: 'Mini 4 Pro 升级 Mini 5 Pro', recommendation_score: 84, business_score: 78 },
                    { keyword: '大疆迷你航拍机生态', recommendation_score: 77, business_score: 71 },
                    { keyword: '入门航拍选大疆还是竞品', recommendation_score: 80, business_score: 77 },
                ],
            },
            {
                key: 'question',
                name: '问答长尾',
                icon: 'help',
                description: '如何、怎么、为什么类查询',
                count: 8,
                items: [
                    { keyword: 'DJI Mini 5 Pro 是什么产品？', recommendation_score: 87, business_score: 68 },
                    { keyword: 'Mini 5 Pro 起飞重量是多少？', recommendation_score: 86, business_score: 70 },
                    { keyword: 'Mini 5 Pro 续航和抗风怎么样？', recommendation_score: 85, business_score: 74 },
                    { keyword: 'O4+ 图传中国大陆能飞多远？', recommendation_score: 84, business_score: 72 },
                    { keyword: 'Mini 5 Pro 夜景避障有什么条件？', recommendation_score: 83, business_score: 71 },
                    { keyword: '和 Mini 4 Pro 比提升在哪？', recommendation_score: 88, business_score: 78 },
                    { keyword: 'Mini 5 Pro 防水吗用什么 App？', recommendation_score: 82, business_score: 69 },
                    { keyword: '旅行航拍为什么选 Mini 5 Pro？', recommendation_score: 81, business_score: 76 },
                ],
            },
            {
                key: 'technical',
                name: '技术方案',
                icon: 'engineering',
                description: '部署、集成、API、架构类查询',
                count: 8,
                items: [
                    { keyword: 'Mini 5 Pro 1 英寸 CMOS 参数', recommendation_score: 84, business_score: 70 },
                    { keyword: 'Mini 5 Pro O4+ 图传规格', recommendation_score: 83, business_score: 69 },
                    { keyword: '夜景级全向主动避障原理', recommendation_score: 80, business_score: 66 },
                    { keyword: '智能飞行电池 vs 长续航电池', recommendation_score: 82, business_score: 74 },
                    { keyword: 'Mini 5 Pro 云台 225° 横滚', recommendation_score: 79, business_score: 65 },
                    { keyword: '欧盟 C0 与 249.9g 起飞重量', recommendation_score: 81, business_score: 68 },
                    { keyword: '增强图传赠送流量说明', recommendation_score: 76, business_score: 67 },
                    { keyword: 'Mini 5 Pro 事实卡知识库切片', recommendation_score: 78, business_score: 72 },
                ],
            },
        ],
    };

    const DIM_MAP = {
        semantic: { key: 'semantic', name: '语义拓展', icon: 'hub', desc: '同义词、相关术语、长尾变体' },
        scenario: { key: 'scenario', name: '场景覆盖', icon: 'category', desc: '真实使用场景与任务语境' },
        commercial: { key: 'commercial', name: '商业意图', icon: 'shopping_cart', desc: '购买信号、比较、定价查询' },
        ranking: { key: 'ranking', name: '推荐榜单', icon: 'emoji_events', desc: '最佳、推荐、Top 类查询' },
        review: { key: 'review', name: '产品评测', icon: 'rate_review', desc: '评测、对比、优缺点查询' },
        brand: { key: 'brand', name: '品牌关联', icon: 'business', desc: '品牌名、产品名、替代方案' },
        question: { key: 'question', name: '问答长尾', icon: 'help', desc: '如何、怎么、为什么类查询' },
        technical: { key: 'technical', name: '技术方案', icon: 'engineering', desc: '部署、集成、API、架构类查询' },
    };

    const inputEl = document.getElementById('keyword-input');
    const wrapperEl = document.getElementById('tag-input-wrapper');
    const generateBtn = document.getElementById('generate-btn');
    const resultsPanel = document.getElementById('results-panel');
    const skeletonEl = document.getElementById('skeleton-loading');
    const dimGrid = document.getElementById('dim-grid');
    const downloadBtn = document.getElementById('download-csv-btn');
    const refineBtn = document.getElementById('refine-btn');
    const sendGeoflowBtn = document.getElementById('send-geoflow-btn');
    const openContentEngineBtn = document.getElementById('open-content-engine-btn');
    const backSuiteDistributeBtn = document.getElementById('back-suite-distribute-btn');
    let contentBackendNative = true;

    async function resolveContentBackendMode() {
        try {
            const res = await fetch('/api/settings/content-backend');
            if (!res.ok) return;
            const data = await res.json();
            contentBackendNative = data.mode !== 'legacy-flow' && data.native !== false;
        } catch (_) {
            contentBackendNative = true;
        }
        document.querySelectorAll('[data-mode-native]').forEach((el) => {
            el.style.display = contentBackendNative ? '' : 'none';
        });
        document.querySelectorAll('[data-mode-legacy]').forEach((el) => {
            el.style.display = contentBackendNative ? 'none' : '';
        });
    }
    const feedbackEl = document.getElementById('keyword-feedback');
    const totalCountEl = document.getElementById('total-kw-count');
    const seedDisplayEl = document.getElementById('seed-kw-display');
    const profileCardEl = document.getElementById('keyword-profile-card');
    const profileNameEl = document.getElementById('keyword-profile-name');
    const profileHintEl = document.getElementById('keyword-profile-hint');
    const profileStrategyEl = document.getElementById('keyword-profile-strategy');
    const profileModelEl = document.getElementById('keyword-profile-model');
    const profileAudienceEl = document.getElementById('keyword-profile-audience');
    const statTotalEl = document.getElementById('stat-total');
    const statAvgRecEl = document.getElementById('stat-avg-rec');
    const statAvgBizEl = document.getElementById('stat-avg-biz');
    const statHighRecEl = document.getElementById('stat-high-rec');
    const statHighBizEl = document.getElementById('stat-high-biz');

    let tags = [];
    let currentDimensions = [];
    let flatList = [];
    let composing = false;
    let loading = false;

    function esc(str) {
        const d = document.createElement('div');
        d.textContent = String(str ?? '');
        return d.innerHTML;
    }

    function setLoading(next) {
        loading = next;
        generateBtn.disabled = next;
        refineBtn.disabled = next;
        downloadBtn.disabled = next || !flatList.length;
        if (sendGeoflowBtn) sendGeoflowBtn.disabled = next || !flatList.length;
        if (next) {
            generateBtn.innerHTML = '<span class="material-symbols-outlined animate-spin text-sm">progress_activity</span><span>生成中...</span>';
            skeletonEl.classList.remove('hidden');
            resultsPanel.classList.add('hidden');
        } else {
            generateBtn.textContent = '生成词包';            skeletonEl.classList.add('hidden');
        }
    }

    function setFeedback(message = '', type = 'error') {
        if (!feedbackEl) return;
        feedbackEl.textContent = message;
        feedbackEl.classList.toggle('hidden', !message);
        feedbackEl.classList.toggle('text-rose-500', type !== 'success');
        feedbackEl.classList.toggle('text-emerald-600', type === 'success');
        wrapperEl.classList.toggle('is-invalid', Boolean(message && type !== 'success'));
    }

    function clonePayload(payload) {
        return JSON.parse(JSON.stringify(payload));
    }

    async function request(path, options = {}) {
        const headers = {
            'Content-Type': 'application/json',
            ...(options.headers || {}),
        };
        const token = Auth?.getToken?.()
            || localStorage.getItem('georank_user_token')
            || localStorage.getItem('georank_token')
            || '';
        if (token) {
            headers.Authorization = `Bearer ${token}`;
        }
        Object.assign(headers, window.GEOrank?.APIKeyStore?.getHeaders?.() || {});
        const response = await fetch(`${API_BASE}${path}`, {
            ...options,
            headers,
        });
        const data = await response.json().catch(() => ({}));
        if (!response.ok) {
            const message = formatApiError(data.detail, response.status);
            throw new Error(typeof message === 'string' ? message : JSON.stringify(message));
        }
        return data;
    }

    function formatApiError(detail, status) {
        if (detail && typeof detail === 'object') {
            return detail.message || JSON.stringify(detail);
        }
        return detail || `请求失败 (${status})`;
    }

    function addTag(text) {
        const value = String(text || '').trim();
        if (!value || tags.includes(value)) return;
        tags.push(value.slice(0, 40));
        renderTags();
        setFeedback('');
    }

    function removeTag(text) {
        tags = tags.filter((item) => item !== text);
        renderTags();
    }

    function renderTags() {
        wrapperEl.querySelectorAll('.keyword-tag').forEach((el) => el.remove());
        tags.forEach((tag) => {
            const span = document.createElement('span');
            span.className = 'keyword-tag';
            span.innerHTML = `${esc(tag)}<button type="button" aria-label="删除">&times;</button>`;
            span.querySelector('button').addEventListener('click', () => removeTag(tag));
            wrapperEl.insertBefore(span, inputEl);
        });
    }

    function consumeDraftInput() {
        const draft = String(inputEl.value || '').trim();
        if (!draft) return;
        draft
            .split(/[,，\n\r\t]+/)
            .forEach((item) => addTag(item));
        inputEl.value = '';
    }

    function rebuildFlatList() {
        flatList = [];
        currentDimensions.forEach((dimension) => {
            (dimension.items || []).forEach((item) => {
                flatList.push({
                    dim: dimension.key,
                    kw: item.keyword,
                    rec: item.recommendation_score,
                    biz: item.business_score,
                });
            });
        });
    }

    function renderProfile(profile) {
        if (!profileCardEl) return;
        if (!profile) {
            profileCardEl.classList.add('hidden');
            return;
        }
        profileNameEl.textContent = profile.name || '业务画像';
        profileHintEl.textContent = profile.company_hint || '';
        profileStrategyEl.textContent = profile.keyword_strategy || '';
        profileModelEl.textContent = profile.business_model || '';
        profileAudienceEl.innerHTML = '';
        (profile.target_users || []).forEach((user) => {
            const chip = document.createElement('span');
            chip.className = 'kw-audience-chip';
            chip.textContent = user;
            profileAudienceEl.appendChild(chip);
        });
        profileCardEl.classList.remove('hidden');
    }

    function updateStats(summary, options = {}) {
        statTotalEl.textContent = summary.total_keywords || 0;
        statAvgRecEl.textContent = summary.average_recommendation_score || 0;
        statAvgBizEl.textContent = summary.average_business_score || 0;
        statHighRecEl.textContent = summary.high_recommendation_ratio || 0;
        statHighBizEl.textContent = summary.high_business_ratio || 0;
        totalCountEl.textContent = summary.total_keywords || 0;
        seedDisplayEl.textContent = options.seedLabel || tags.join('、');
    }

    function renderGrid() {
        dimGrid.innerHTML = '';

        currentDimensions.forEach((dimension) => {
            const meta = DIM_MAP[dimension.key] || {};
            const items = Array.isArray(dimension.items) ? dimension.items : [];
            const card = document.createElement('div');
            card.className = 'dim-card';

            const renderRows = (rows) => rows.map((item) => `
                <div class="dim-table-row">
                    <div class="kw-name">
                        <div>${esc(item.keyword)}</div>
                    </div>
                    <div class="score-cell"><div class="score-bar"><div class="score-bar-fill rec" style="width:${item.recommendation_score}%"></div></div><span class="score-num rec">${item.recommendation_score}</span></div>
                    <div class="score-cell"><div class="score-bar"><div class="score-bar-fill biz" style="width:${item.business_score}%"></div></div><span class="score-num biz">${item.business_score}</span></div>
                </div>
            `).join('');

            const preview = items.slice(0, PREVIEW_COUNT);
            card.innerHTML = `
                <div class="dim-card-header">
                    <div class="flex items-center gap-2">
                        <span class="dim-icon"><span class="material-symbols-outlined text-base">${esc(meta.icon || dimension.icon || 'category')}</span></span>
                        <div><span class="text-sm font-bold">${esc(meta.name || dimension.name)}</span><span class="text-xs text-on-surface-variant ml-2">${items.length} 词</span></div>
                    </div>
                    <span class="text-[10px] text-on-surface-variant">${esc(meta.desc || dimension.description || '')}</span>
                </div>
                <div class="dim-table-header"><div>关键词</div><div>推荐</div><div>商业</div></div>
                <div class="dim-table-body">${renderRows(preview)}</div>
            `;

            if (items.length > PREVIEW_COUNT) {
                const btn = document.createElement('button');
                btn.className = 'dim-show-more';
                btn.textContent = `展开全部 ${items.length} 条`;
                let expanded = false;
                btn.addEventListener('click', () => {
                    expanded = !expanded;
                    card.querySelector('.dim-table-body').innerHTML = renderRows(expanded ? items : preview);
                    btn.textContent = expanded ? '收起' : `展开全部 ${items.length} 条`;
                });
                card.appendChild(btn);
            }

            dimGrid.appendChild(card);
        });
    }

    function renderResults(payload, options = {}) {
        currentDimensions = Array.isArray(payload.dimensions) ? payload.dimensions : [];
        rebuildFlatList();
        renderProfile(payload.profile);
        updateStats(payload.summary || {}, {
            seedLabel: options.seedLabel || tags.join('、'),
        });
        renderGrid();
        resultsPanel.classList.remove('hidden');
        refineBtn.disabled = Boolean(options.disableRefine);
        if (!options.isExample) {
            guideSuiteAfterKeywords(options.seedLabel || tags.join('、'));
        }
    }

    function guideSuiteAfterKeywords(seedLabel) {
        if (!Workflow || !flatList.length) return;
        Workflow.markComplete('keywords', {
            seed: seedLabel || '',
            count: flatList.length,
        });
        Workflow.setCurrent(contentBackendNative ? 'distribute' : 'handoff');
        if (contentBackendNative) {
            Workflow.mountBar({
                stepId: 'keywords',
                force: true,
                hint: '拓词已完成：可打开内容引擎生成正文，或回 Suite 分发步。',
                nextHref: '/suite?step=distribute',
                nextLabel: '回 Suite · 分发',
            });
            Workflow.mountNextCard(resultsPanel, {
                id: 'suite-wf-next-keywords',
                prepend: true,
                stepId: 'keywords',
                title: '拓词完成 · 写入内容引擎',
                copy: '词包已记入 GEO Suite。下一步在内容引擎绑定知识库与提示词生成草稿，再用五渠道壳预览。',
                primaryHref: '/admin/content-engine?tab=tasks',
                primaryLabel: '打开内容引擎',
                secondaryHref: '/suite?step=distribute',
                secondaryLabel: '返回 Suite · 分发',
            });
            return;
        }
        Workflow.mountBar({
            stepId: 'keywords',
            force: true,
            hint: '拓词已完成：可发送到 GEOFlow，或回 Suite 查看进度。',
            nextHref: '/suite?step=handoff',
            nextLabel: '回 Suite · 移交',
        });
        Workflow.mountNextCard(resultsPanel, {
            id: 'suite-wf-next-keywords',
            prepend: true,
            stepId: 'keywords',
            title: '拓词完成 · 发送到 GEOFlow',
            copy: '词包已记入 GEO Suite。点击「发送到 GEOFlow」创建内容任务（preview 也可演示），完成后回 Suite 回看。',
            primaryHref: '#send-geoflow-btn',
            primaryLabel: '发送到 GEOFlow',
            secondaryHref: '/suite?step=review',
            secondaryLabel: '返回 Suite',
        });
        const primary = document.querySelector('#suite-wf-next-keywords a.suite-wf-next__btn--primary');
        if (primary) {
            primary.addEventListener('click', (event) => {
                event.preventDefault();
                void sendToGeoflow();
            });
        }
    }

    async function generate() {
        if (loading) return;
        consumeDraftInput();
        if (!tags.length) {
            setFeedback('请输入至少一个关键词，再生成词包。');
            inputEl.focus();
            return;
        }
        if (Auth && !Auth.requireAuth({ reasonKey: 'auth.reasonKeywords' })) {
            return;
        }

        setFeedback('');
        setLoading(true);
        try {
            const payload = await request('/api/keywords/expand', {
                method: 'POST',
                body: JSON.stringify({ seeds: tags }),
            });
            renderResults(payload, {
                isExample: false,
                seedLabel: tags.join('、'),
                disableRefine: false,
            });
        } catch (error) {
            setFeedback(error.message || '生成词包失败，请稍后重试。');
            if (window.GEOrank?.APIKeyStore?.shouldPromptForError?.(error)) {
                window.GEOrank.APIKeyStore.openModal(error.message);
            }
        } finally {
            setLoading(false);
        }
    }

    function downloadCSV() {
        if (!flatList.length) return;
        const BOM = '\uFEFF';
        const rows = ['维度,关键词,推荐指数,商业指数'];
        flatList.forEach((item) => {
            const dim = DIM_MAP[item.dim];
            rows.push(`${dim ? dim.name : ''},${item.kw},${item.rec},${item.biz}`);
        });
        const blob = new Blob([BOM + rows.join('\n')], { type: 'text/csv;charset=utf-8' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `GEOrank_词包_${tags.join('_')}.csv`;
        a.click();
        URL.revokeObjectURL(url);
    }

    async function sendToGeoflow() {
        if (contentBackendNative) {
            window.location.href = '/admin/content-engine?tab=tasks';
            return;
        }
        if (!flatList.length) {
            setFeedback('请先生成词包，再发送到 GEOFlow。');
            return;
        }
        const handoff = window.GEOrank?.GeoflowHandoff;
        if (!handoff) {
            setFeedback('GEOFlow 集成脚本未加载。');
            return;
        }
        const keywords = flatList
            .slice()
            .sort((a, b) => (b.rec || 0) - (a.rec || 0))
            .map((item) => item.kw)
            .filter(Boolean)
            .slice(0, 12);
        const seedLabel = tags.join('、') || keywords[0] || 'GEO 拓词';
        if (sendGeoflowBtn) {
            sendGeoflowBtn.disabled = true;
            sendGeoflowBtn.innerHTML = '<span class="material-symbols-outlined animate-spin text-sm">progress_activity</span>发送中…';
        }
        try {
            const result = await handoff.send({
                source: 'keywords',
                task_name: `GEORank 拓词 · ${seedLabel}`.slice(0, 120),
                keywords,
                brief: [
                    `# GEORank 拓词移交`,
                    ``,
                    `种子词：${seedLabel}`,
                    ``,
                    `## 推荐关键词`,
                    ...keywords.map((item) => `- ${item}`),
                    ``,
                    `请据此生成适合 AI 搜索引用的 GEO 内容资产。`,
                ].join('\n'),
            });
            setFeedback(handoff.formatResultMessage(result), 'success');
            handoff.openResult(result);
        } catch (error) {
            setFeedback(error.message || '发送到 GEOFlow 失败。');
        } finally {
            if (sendGeoflowBtn) {
                sendGeoflowBtn.disabled = !flatList.length;
                sendGeoflowBtn.innerHTML = '<span class="material-symbols-outlined text-sm">sync_alt</span>发送到 GEOFlow';
            }
        }
    }

    inputEl.addEventListener('compositionstart', () => { composing = true; });
    inputEl.addEventListener('compositionend', () => { composing = false; });
    inputEl.addEventListener('keydown', (event) => {
        if (composing) return;
        if (event.key === 'Enter' || event.key === ',') {
            event.preventDefault();
            addTag(inputEl.value);
            inputEl.value = '';
            return;
        }
        if (event.key === 'Backspace' && !inputEl.value && tags.length) {
            removeTag(tags[tags.length - 1]);
        }
    });
    inputEl.addEventListener('paste', (event) => {
        event.preventDefault();
        (event.clipboardData || window.clipboardData).getData('text')
            .split(/[,，\n\r\t]+/)
            .forEach((item) => addTag(item));
        inputEl.value = '';
    });
    inputEl.addEventListener('input', () => {
        if (inputEl.value.trim()) {
            setFeedback('');
        }
    });

    generateBtn.addEventListener('click', generate);
    inputEl.addEventListener('keydown', (event) => {
        if (!composing && event.key === 'Enter' && !inputEl.value && tags.length) {
            generate();
        }
    });
    downloadBtn.addEventListener('click', downloadCSV);
    refineBtn.addEventListener('click', generate);
    sendGeoflowBtn?.addEventListener('click', () => { void sendToGeoflow(); });

    void resolveContentBackendMode().then(() => {
        Workflow?.mountBar({
            stepId: 'keywords',
            nextHref: contentBackendNative ? '/suite?step=distribute' : '/suite?step=handoff',
            nextLabel: contentBackendNative ? '下一步：分发' : '下一步：移交 Flow',
            hint: contentBackendNative
                ? '全套工作流第 3 步：围绕 Mini 5 Pro 生成词包后进入内容引擎 / Suite 分发。'
                : '全套工作流第 3 步：围绕 Mini 5 Pro 生成词包后发送到 GEOFlow。',
        });
    });

    DEMO_SEEDS.forEach((seed) => addTag(seed));
    renderResults(clonePayload(SAMPLE_PAYLOAD), {
        isExample: true,
        seedLabel: DEMO_SEEDS.join('、'),
        disableRefine: false,
    });
});
