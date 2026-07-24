/**
 * GEO Suite 全套工作流 — localStorage 会话 + 模块回链条
 */
(function (global) {
    'use strict';

    var STORAGE_KEY = 'georank_suite_workflow_v1';
    var STYLE_ID = 'suite-workflow-bar-styles';

    var STEPS = [
        {
            id: 'diagnostic',
            label: '诊断',
            title: '诊断网站',
            desc: '检查 Schema、内容结构、Meta 与外链背书就绪信号（≠ AI 答案引用率），拿到优先修复清单。',
            href: '/diagnostic',
            cta: '开始诊断',
            icon: 'monitoring',
            next: 'solutions',
        },
        {
            id: 'solutions',
            label: '问答/方案',
            title: '问答与方案',
            desc: '围绕诊断结果生成可执行解释，或进入 30/60/90 天行动方案。',
            href: '/solutions',
            cta: '进入问答',
            icon: 'forum',
            next: 'keywords',
            altHref: '/plans',
            altCta: '生成方案',
        },
        {
            id: 'keywords',
            label: '拓词',
            title: '拓词沉淀',
            desc: '扩展问题词与场景词，形成可移交的内容选题资产。',
            href: '/keywords',
            cta: '开始拓词',
            icon: 'travel_explore',
            next: 'handoff',
        },
        {
            id: 'handoff',
            label: 'GEOFlow',
            title: '发送到 GEOFlow',
            desc: '把词包或问答简报 live 移交内容工厂，创建知识库、标题库与生成任务。',
            href: '/keywords',
            cta: '去拓词页移交',
            icon: 'sync_alt',
            next: 'review',
            altHref: '/solutions',
            altCta: '从问答移交',
        },
        {
            id: 'review',
            label: '回看',
            title: '回看状态与回调',
            desc: '确认 live 移交、任务状态与发布回调；可用 SSO 打开 GEOFlow。',
            href: '/suite?step=review',
            cta: '查看集成状态',
            icon: 'task_alt',
            next: 'knowledge',
        },
        {
            id: 'knowledge',
            label: '事实卡',
            title: '栏目事实卡看板',
            desc: '查看合成演示栏目的事实卡覆盖率、向量化率与证据摘要（知识工程资产）。',
            href: '/suite?step=knowledge',
            cta: '查看事实卡',
            icon: 'database',
            next: 'trust_asset',
            suitePanel: true,
        },
        {
            id: 'trust_asset',
            label: '信任素材',
            title: 'L3 模型可读样板',
            desc: '展示一条「人共鸣 + 模型可读」的图文信任素材样板（非视频管线）。',
            href: '/suite?step=trust_asset',
            cta: '查看信任素材',
            icon: 'auto_awesome',
            next: 'measure',
            suitePanel: true,
        },
        {
            id: 'measure',
            label: '可信观测',
            title: '答案抽样结果',
            desc: '展示最新一轮 API 自动探针结果（mention/citation/absent）；非网页抓取。',
            href: '/suite?step=measure',
            cta: '查看观测结果',
            icon: 'monitoring',
            next: null,
            suitePanel: true,
        },
    ];

    function defaultState() {
        return {
            currentStep: 'diagnostic',
            completed: {},
            meta: {},
            lastHandoff: null,
            updatedAt: null,
        };
    }

    function getStep(id) {
        return STEPS.find(function (step) {
            return step.id === id;
        }) || STEPS[0];
    }

    function stepIndex(id) {
        var idx = STEPS.findIndex(function (step) {
            return step.id === id;
        });
        return idx < 0 ? 0 : idx;
    }

    function normalizeStepId(raw) {
        var value = String(raw || '').trim().toLowerCase();
        if (!value) return null;
        var aliases = {
            diagnose: 'diagnostic',
            diagnosis: 'diagnostic',
            qa: 'solutions',
            solution: 'solutions',
            plans: 'solutions',
            plan: 'solutions',
            keyword: 'keywords',
            flow: 'handoff',
            geoflow: 'handoff',
            send: 'handoff',
            status: 'review',
            next: 'review',
            facts: 'knowledge',
            factcard: 'knowledge',
            kb: 'knowledge',
            trust: 'trust_asset',
            l3: 'trust_asset',
            obs: 'measure',
            trustobs: 'measure',
            measurement: 'measure',
        };
        if (aliases[value]) value = aliases[value];
        return STEPS.some(function (step) {
            return step.id === value;
        })
            ? value
            : null;
    }

    function load() {
        try {
            var raw = global.localStorage.getItem(STORAGE_KEY);
            if (!raw) return defaultState();
            var parsed = JSON.parse(raw);
            var state = defaultState();
            if (parsed && typeof parsed === 'object') {
                if (normalizeStepId(parsed.currentStep)) {
                    state.currentStep = normalizeStepId(parsed.currentStep);
                }
                if (parsed.completed && typeof parsed.completed === 'object') {
                    state.completed = parsed.completed;
                }
                if (parsed.meta && typeof parsed.meta === 'object') {
                    state.meta = parsed.meta;
                }
                if (parsed.lastHandoff && typeof parsed.lastHandoff === 'object') {
                    state.lastHandoff = parsed.lastHandoff;
                }
                state.updatedAt = parsed.updatedAt || null;
            }
            return state;
        } catch (error) {
            console.warn('[suite-workflow] load failed', error);
            return defaultState();
        }
    }

    function save(state) {
        var next = Object.assign(defaultState(), state || {}, {
            updatedAt: new Date().toISOString(),
        });
        try {
            global.localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
        } catch (error) {
            console.warn('[suite-workflow] save failed', error);
        }
        return next;
    }

    function setCurrent(stepId) {
        var id = normalizeStepId(stepId) || 'diagnostic';
        var state = load();
        state.currentStep = id;
        return save(state);
    }

    function markComplete(stepId, meta) {
        var id = normalizeStepId(stepId);
        if (!id) return load();
        var state = load();
        state.completed[id] = true;
        if (meta && typeof meta === 'object') {
            state.meta[id] = Object.assign({}, state.meta[id] || {}, meta);
        }
        var step = getStep(id);
        if (step.next && !state.completed[step.next]) {
            state.currentStep = step.next;
        } else if (step.next) {
            state.currentStep = step.next;
        } else {
            state.currentStep = id;
        }
        return save(state);
    }

    function saveHandoff(result) {
        var state = load();
        state.completed.handoff = true;
        state.currentStep = 'review';
        state.lastHandoff = {
            mode: result && result.mode ? result.mode : 'preview',
            message: result && result.message ? result.message : '已完成移交',
            source: result && result.source ? result.source : null,
            task_name: result && result.task_name ? result.task_name : null,
            task_id: result && result.task_id ? result.task_id : null,
            company_id: result && result.company_id ? result.company_id : null,
            geoflow_admin_url: result && (result.geoflow_task_url || result.geoflow_admin_url)
                ? (result.geoflow_task_url || result.geoflow_admin_url)
                : null,
            geoflow_task_url: result && (result.geoflow_task_url || result.geoflow_admin_url)
                ? (result.geoflow_task_url || result.geoflow_admin_url)
                : null,
            suite_path: result && result.suite_path ? result.suite_path : '/suite?step=review',
            preview: result && result.preview ? result.preview : null,
            at: new Date().toISOString(),
        };
        if (result && result.source === 'keywords') {
            state.completed.keywords = true;
        }
        if (result && result.source === 'solutions') {
            state.completed.solutions = true;
        }
        return save(state);
    }

    function clear() {
        try {
            global.localStorage.removeItem(STORAGE_KEY);
        } catch (error) {
            console.warn('[suite-workflow] clear failed', error);
        }
        return defaultState();
    }

    function buildHref(stepOrId, extras) {
        var step = typeof stepOrId === 'string' ? getStep(stepOrId) : stepOrId;
        var url = new URL(step.href, global.location.origin);
        url.searchParams.set('from', 'suite');
        url.searchParams.set('workflow', '1');
        url.searchParams.set('step', step.id);
        if (extras && typeof extras === 'object') {
            Object.keys(extras).forEach(function (key) {
                if (extras[key] == null || extras[key] === '') return;
                url.searchParams.set(key, String(extras[key]));
            });
        }
        return url.pathname + url.search;
    }

    function nextOf(stepId) {
        var step = getStep(stepId);
        return step.next ? getStep(step.next) : null;
    }

    function progressPercent(state) {
        var current = state || load();
        var doneCount = STEPS.filter(function (step) {
            return current.completed[step.id];
        }).length;
        if (doneCount >= STEPS.length) return 100;
        var idx = stepIndex(current.currentStep);
        return Math.round(((idx + (current.completed[current.currentStep] ? 1 : 0.35)) / STEPS.length) * 100);
    }

    function ensureStyles() {
        if (document.getElementById(STYLE_ID)) return;
        var style = document.createElement('style');
        style.id = STYLE_ID;
        style.textContent = [
            '.suite-wf-bar{position:sticky;top:0;z-index:45;margin:0;padding:0.65rem 1rem;display:flex;flex-wrap:wrap;align-items:center;justify-content:space-between;gap:0.65rem;background:linear-gradient(135deg,rgba(31,111,91,0.96),rgba(47,157,130,0.94));color:#f4faf7;box-shadow:0 10px 28px rgba(16,35,31,0.18);font-family:Manrope,Inter,sans-serif}',
            '.suite-wf-bar__left{display:flex;flex-wrap:wrap;align-items:center;gap:0.55rem;min-width:0}',
            '.suite-wf-bar__brand{font-weight:800;letter-spacing:-0.02em;font-size:0.82rem}',
            '.suite-wf-bar__chip{display:inline-flex;align-items:center;gap:0.3rem;padding:0.2rem 0.55rem;border-radius:999px;background:rgba(255,255,255,0.14);font-size:0.72rem;font-weight:700}',
            '.suite-wf-bar__hint{font-size:0.72rem;opacity:0.9;max-width:36rem}',
            '.suite-wf-bar__actions{display:flex;flex-wrap:wrap;gap:0.45rem}',
            '.suite-wf-bar__btn{display:inline-flex;align-items:center;gap:0.3rem;border-radius:999px;padding:0.42rem 0.85rem;font-size:0.72rem;font-weight:800;text-decoration:none;border:1px solid transparent;transition:transform .15s ease,background .15s ease}',
            '.suite-wf-bar__btn:hover{transform:translateY(-1px)}',
            '.suite-wf-bar__btn--ghost{color:#f4faf7;border-color:rgba(255,255,255,0.28);background:rgba(255,255,255,0.08)}',
            '.suite-wf-bar__btn--solid{color:#104036;background:#e7fff5}',
            '.suite-wf-next{margin:1rem 0 1.25rem;padding:1rem 1.1rem;border-radius:1.1rem;border:1px solid rgba(31,111,91,0.22);background:linear-gradient(180deg,#f7fcf9,#eef8f3);display:flex;flex-wrap:wrap;align-items:center;justify-content:space-between;gap:0.85rem}',
            '.suite-wf-next__copy h3{margin:0 0 0.25rem;font-size:0.95rem;font-weight:800;color:#10231f;font-family:Manrope,Inter,sans-serif}',
            '.suite-wf-next__copy p{margin:0;font-size:0.8rem;line-height:1.55;color:rgba(16,35,31,0.68)}',
            '.suite-wf-next__actions{display:flex;flex-wrap:wrap;gap:0.5rem}',
            '.suite-wf-next__btn{display:inline-flex;align-items:center;gap:0.35rem;border-radius:999px;padding:0.65rem 1rem;font-size:0.78rem;font-weight:800;text-decoration:none}',
            '.suite-wf-next__btn--primary{color:#fff;background:linear-gradient(135deg,#1f6f5b,#2f9d82)}',
            '.suite-wf-next__btn--ghost{color:#10231f;background:rgba(255,255,255,0.8);border:1px solid rgba(16,35,31,0.12)}',
            'body.solutions-page .suite-wf-bar,body:has(#solutions-workspace) .suite-wf-bar{top:0}',
        ].join('');
        document.head.appendChild(style);
    }

    function shouldShowBar(options) {
        if (options && options.force) return true;
        try {
            var params = new URLSearchParams(global.location.search);
            if (params.get('from') === 'suite' || params.get('workflow') === '1') return true;
            var state = load();
            return Boolean(state.updatedAt || Object.keys(state.completed).length);
        } catch (error) {
            return false;
        }
    }

    function mountBar(options) {
        options = options || {};
        var stepId = normalizeStepId(options.stepId) || 'diagnostic';
        if (!shouldShowBar(options) && !options.force) return null;
        ensureStyles();

        var existing = document.getElementById('suite-wf-bar');
        if (existing) existing.remove();

        var state = load();
        if (!state.completed[stepId]) {
            state.currentStep = stepId;
            save(state);
        }
        state = load();

        var step = getStep(stepId);
        var next = nextOf(stepId);
        var idx = stepIndex(stepId) + 1;
        var bar = document.createElement('div');
        bar.id = 'suite-wf-bar';
        bar.className = 'suite-wf-bar';
        bar.setAttribute('role', 'region');
        bar.setAttribute('aria-label', 'GEO Suite 工作流');

        var nextHref = options.nextHref || (next ? buildHref(next) : '/suite?step=review');
        var nextLabel = options.nextLabel || (next ? '下一步：' + next.label : '回 Suite 回看');
        var hint = options.hint || (state.completed[stepId]
            ? '本步已完成，可继续全套工作流。'
            : '你正在 GEO Suite 全套工作流 · 第 ' + idx + ' / ' + STEPS.length + ' 步');

        bar.innerHTML = [
            '<div class="suite-wf-bar__left">',
            '  <span class="suite-wf-bar__brand">GEO Suite</span>',
            '  <span class="suite-wf-bar__chip"><span class="material-symbols-outlined" style="font-size:14px">route</span>步骤 ' + idx + '/' + STEPS.length + ' · ' + step.label + '</span>',
            '  <span class="suite-wf-bar__hint">' + hint + '</span>',
            '</div>',
            '<div class="suite-wf-bar__actions">',
            '  <a class="suite-wf-bar__btn suite-wf-bar__btn--ghost" href="/suite?step=' + stepId + '">返回 Suite</a>',
            '  <a class="suite-wf-bar__btn suite-wf-bar__btn--solid" href="' + nextHref + '">' + nextLabel + '</a>',
            '</div>',
        ].join('');

        var header = document.getElementById('header-container');
        if (header && header.parentNode) {
            header.parentNode.insertBefore(bar, header.nextSibling);
        } else {
            document.body.insertBefore(bar, document.body.firstChild);
        }
        return bar;
    }

    function mountNextCard(container, options) {
        if (!container) return null;
        options = options || {};
        ensureStyles();
        var stepId = normalizeStepId(options.stepId) || 'diagnostic';
        var next = nextOf(stepId);
        var existing = container.querySelector('.suite-wf-next');
        if (existing) existing.remove();

        var card = document.createElement('div');
        card.className = 'suite-wf-next';
        card.id = options.id || 'suite-wf-next';

        var title = options.title || (next ? '本步完成 · 进入下一步' : '本步完成 · 回 Suite 查看状态');
        var copy = options.copy || (next
            ? '已记录到 GEO Suite 工作流。下一步：' + next.title + '。'
            : '已记录到 GEO Suite 工作流。可回 Suite 查看集成状态与最近移交。');
        var primaryHref = options.primaryHref || (next ? buildHref(next) : '/suite?step=review');
        var primaryLabel = options.primaryLabel || (next ? next.cta : '打开 GEO Suite');
        var secondaryHref = options.secondaryHref || '/suite?step=' + (next ? next.id : 'review');
        var secondaryLabel = options.secondaryLabel || '返回 Suite';

        card.innerHTML = [
            '<div class="suite-wf-next__copy">',
            '  <h3>' + title + '</h3>',
            '  <p>' + copy + '</p>',
            '</div>',
            '<div class="suite-wf-next__actions">',
            '  <a class="suite-wf-next__btn suite-wf-next__btn--ghost" href="' + secondaryHref + '">' + secondaryLabel + '</a>',
            '  <a class="suite-wf-next__btn suite-wf-next__btn--primary" href="' + primaryHref + '">' + primaryLabel + '</a>',
            '</div>',
        ].join('');

        if (options.prepend) {
            container.insertBefore(card, container.firstChild);
        } else {
            container.appendChild(card);
        }
        return card;
    }

    function syncFromQuery() {
        try {
            var params = new URLSearchParams(global.location.search);
            var step = normalizeStepId(params.get('step'));
            var done = normalizeStepId(params.get('done'));
            if (done) markComplete(done);
            if (step) setCurrent(step);
            return load();
        } catch (error) {
            return load();
        }
    }

    global.GEOrank = global.GEOrank || {};
    global.GEOrank.SuiteWorkflow = {
        STORAGE_KEY: STORAGE_KEY,
        STEPS: STEPS,
        load: load,
        save: save,
        clear: clear,
        getStep: getStep,
        stepIndex: stepIndex,
        normalizeStepId: normalizeStepId,
        setCurrent: setCurrent,
        markComplete: markComplete,
        saveHandoff: saveHandoff,
        buildHref: buildHref,
        nextOf: nextOf,
        progressPercent: progressPercent,
        mountBar: mountBar,
        mountNextCard: mountNextCard,
        syncFromQuery: syncFromQuery,
        shouldShowBar: shouldShowBar,
    };
})(window);
