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
            label: '检查',
            title: '基础 SEO 检查',
            desc: '输入网址，查看四类 SEO 就绪情况；GEO Tab 为初诊观测（与 Suite「观测」同一漏斗）。',
            href: '/diagnostic',
            cta: '开始检查',
            icon: 'monitoring',
            next: 'knowledge',
        },
        {
            id: 'knowledge',
            label: '知识',
            title: '知识库与事实材料',
            desc: '新建或导入示例库，沉淀事实材料后进入拓词与内容。',
            href: '/knowledge',
            cta: '打开知识库',
            icon: 'database',
            next: 'keywords',
            external: false,
            suitePanel: true,
        },
        {
            id: 'keywords',
            label: '拓词',
            title: '选题清单',
            desc: '生成选题，勾选后创建内容任务。',
            href: '/keywords',
            cta: '打开选题',
            icon: 'travel_explore',
            next: 'distribute',
        },
        {
            id: 'distribute',
            label: '内容/分发',
            title: '草稿与渠道预览',
            desc: '生成草稿并预览渠道壳，标记就绪（预览·不外发）。',
            href: '/distribute',
            cta: '打开内容/分发',
            icon: 'sync_alt',
            next: 'measure',
            external: false,
            suitePanel: true,
        },
        {
            id: 'measure',
            label: '观测',
            title: '三层用户追问',
            desc: '按认知 → 约束 → 推荐查看出现率与证据密度（演示数据）。',
            href: '/suite?step=measure',
            cta: '查看观测',
            icon: 'monitoring',
            next: null,
            suitePanel: true,
        },
    ];

    var DEFAULT_RUN = {
        entity: 'DJI Mini 5 Pro',
        competitor: 'Autel',
        platforms: ['豆包', '元宝', 'Kimi', 'DeepSeek'],
        observe_script_key: 'geo-observe-funnel-dji-vs-autel',
    };

    function defaultState() {
        return {
            currentStep: 'diagnostic',
            completed: {},
            meta: {},
            runId: null,
            run: null,
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
            qa: 'keywords',
            solution: 'keywords',
            solutions: 'keywords',
            plans: 'keywords',
            plan: 'keywords',
            keyword: 'keywords',
            flow: 'distribute',
            geoflow: 'distribute',
            send: 'distribute',
            handoff: 'distribute',
            review: 'distribute',
            status: 'distribute',
            next: 'distribute',
            facts: 'knowledge',
            factcard: 'knowledge',
            kb: 'knowledge',
            trust: 'measure',
            trust_asset: 'measure',
            l3: 'measure',
            obs: 'measure',
            trustobs: 'measure',
            measurement: 'measure',
            distribution: 'distribute',
            publish: 'distribute',
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
                if (parsed.runId) state.runId = String(parsed.runId);
                if (parsed.run && typeof parsed.run === 'object') state.run = parsed.run;
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
        state.completed.distribute = true;
        state.completed.handoff = true;
        state.currentStep = 'measure';
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
            suite_path: result && result.suite_path ? result.suite_path : '/suite?step=measure',
            preview: result && result.preview ? result.preview : null,
            at: new Date().toISOString(),
        };
        if (result && result.source === 'keywords') {
            state.completed.keywords = true;
        }
        if (result && (result.source === 'solutions' || result.source === 'plans')) {
            state.completed.keywords = true;
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

    function apiBase() {
        try {
            return (global.GEOrank && global.GEOrank.Auth && global.GEOrank.Auth.apiBase) || '';
        } catch (e) {
            return '';
        }
    }

    function authHeaders() {
        var headers = { 'Content-Type': 'application/json' };
        try {
            var token = global.GEOrank && global.GEOrank.Auth && global.GEOrank.Auth.getToken && global.GEOrank.Auth.getToken();
            if (token) headers.Authorization = 'Bearer ' + token;
        } catch (e) { /* ignore */ }
        return headers;
    }

    function getRunId() {
        try {
            var params = new URLSearchParams(global.location.search);
            var fromQuery = params.get('run_id') || params.get('runId');
            if (fromQuery) return String(fromQuery);
        } catch (e) { /* ignore */ }
        var state = load();
        return state.runId || null;
    }

    function setRun(run) {
        var state = load();
        if (run && run.id) {
            state.runId = String(run.id);
            state.run = run;
        }
        return save(state);
    }

    function ensureRun(options) {
        options = options || {};
        var existing = getRunId();
        if (existing && !options.forceNew) {
            return Promise.resolve(load().run || { id: existing }).then(function (cached) {
                if (cached && cached.id && !options.refresh) return cached;
                return fetch(apiBase() + '/api/geo-runs/' + existing, {
                    headers: authHeaders(),
                }).then(function (res) {
                    if (!res.ok) throw new Error('load run failed');
                    return res.json();
                }).then(function (run) {
                    setRun(run);
                    return run;
                }).catch(function () {
                    return createRun(options);
                });
            });
        }
        return createRun(options);
    }

    function createRun(options) {
        options = options || {};
        var body = {
            title: options.title || null,
            entity: options.entity || DEFAULT_RUN.entity,
            competitor: options.competitor || DEFAULT_RUN.competitor,
            url: options.url || null,
            platforms: options.platforms || DEFAULT_RUN.platforms,
            knowledge_base_id: options.knowledge_base_id || null,
            observe_script_key: options.observe_script_key || DEFAULT_RUN.observe_script_key,
        };
        return fetch(apiBase() + '/api/geo-runs/', {
            method: 'POST',
            headers: authHeaders(),
            body: JSON.stringify(body),
        }).then(function (res) {
            if (!res.ok) throw new Error('create run failed');
            return res.json();
        }).then(function (run) {
            setRun(run);
            return run;
        });
    }

    function handoff(step, payload) {
        var runId = getRunId();
        if (!runId) {
            return ensureRun({ url: payload && payload.url }).then(function (run) {
                return handoff(step, payload);
            });
        }
        var body = Object.assign({ step: step }, payload || {});
        return fetch(apiBase() + '/api/geo-runs/' + runId + '/handoff', {
            method: 'PATCH',
            headers: authHeaders(),
            body: JSON.stringify(body),
        }).then(function (res) {
            if (!res.ok) throw new Error('handoff failed');
            return res.json();
        }).then(function (run) {
            setRun(run);
            return run;
        });
    }

    function buildHref(stepOrId, extras) {
        var step = typeof stepOrId === 'string' ? getStep(stepOrId) : stepOrId;
        var url = new URL(step.href, global.location.origin);
        if (!step.external) {
            url.searchParams.set('from', 'suite');
            url.searchParams.set('workflow', '1');
            url.searchParams.set('step', step.id);
        }
        var runId = (extras && extras.run_id) || getRunId();
        if (runId) url.searchParams.set('run_id', String(runId));
        if (extras && typeof extras === 'object') {
            Object.keys(extras).forEach(function (key) {
                if (extras[key] == null || extras[key] === '') return;
                url.searchParams.set(key, String(extras[key]));
            });
        }
        if (step.external || url.origin !== global.location.origin) {
            return url.toString();
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
        var style = document.getElementById(STYLE_ID);
        if (!style) {
            style = document.createElement('style');
            style.id = STYLE_ID;
            document.head.appendChild(style);
        }
        style.textContent = [
            '.suite-wf-bar{position:sticky;top:4rem;z-index:45;margin:4rem 0 0;padding:0.65rem 1rem;display:flex;flex-wrap:wrap;align-items:center;justify-content:space-between;gap:0.65rem;background:linear-gradient(135deg,rgba(31,111,91,0.96),rgba(47,157,130,0.94));color:#f4faf7;box-shadow:0 10px 28px rgba(16,35,31,0.18);border-bottom:1px solid rgba(16,35,31,0.22);font-family:Manrope,Inter,sans-serif}',
            'body:has(#suite-wf-bar) main{padding-top:1.25rem !important}',
            '.suite-wf-bar__left{display:flex;flex-wrap:wrap;align-items:center;gap:0.55rem;min-width:0}',
            '.suite-wf-bar__brand{font-weight:800;letter-spacing:-0.02em;font-size:0.82rem}',
            '.suite-wf-bar__chip{display:inline-flex;align-items:center;gap:0.3rem;padding:0.2rem 0.55rem;border-radius:999px;background:rgba(255,255,255,0.14);font-size:0.72rem;font-weight:700}',
            '.suite-wf-bar__hint{font-size:0.72rem;opacity:0.9;max-width:36rem}',
            '.suite-wf-bar__actions{display:flex;flex-wrap:wrap;gap:0.45rem}',
            '.suite-wf-bar__btn{display:inline-flex;align-items:center;gap:0.3rem;border-radius:999px;padding:0.42rem 0.85rem;font-size:0.72rem;font-weight:800;text-decoration:none;border:1px solid transparent;transition:transform .15s ease,background .15s ease}',
            '.suite-wf-bar__btn:hover{transform:translateY(-1px)}',
            '.suite-wf-bar__btn--ghost{color:#f4faf7;border-color:rgba(255,255,255,0.28);background:rgba(255,255,255,0.08)}',
            '.suite-wf-bar__btn--solid{color:#104036;background:#e7fff5}',
            '.suite-wf-bar__steps{display:flex;flex-wrap:wrap;gap:0.28rem;width:100%}',
            '.suite-wf-bar__step{display:inline-flex;align-items:center;padding:0.18rem 0.48rem;border-radius:999px;font-size:0.66rem;font-weight:700;color:rgba(244,250,247,0.82);text-decoration:none;border:1px solid rgba(255,255,255,0.18);background:rgba(0,0,0,0.08)}',
            '.suite-wf-bar__step.is-active{background:#e7fff5;color:#104036;border-color:transparent}',
            '.suite-wf-bar__step.is-done{opacity:0.95;border-color:rgba(231,255,245,0.45)}',
            '.suite-wf-next{margin:1rem 0 1.25rem;padding:1rem 1.1rem;border-radius:1.1rem;border:1px solid rgba(31,111,91,0.22);background:linear-gradient(180deg,#f7fcf9,#eef8f3);display:flex;flex-wrap:wrap;align-items:center;justify-content:space-between;gap:0.85rem}',
            '.suite-wf-next__copy h3{margin:0 0 0.25rem;font-size:0.95rem;font-weight:800;color:#10231f;font-family:Manrope,Inter,sans-serif}',
            '.suite-wf-next__copy p{margin:0;font-size:0.8rem;line-height:1.55;color:rgba(16,35,31,0.68)}',
            '.suite-wf-next__actions{display:flex;flex-wrap:wrap;gap:0.5rem}',
            '.suite-wf-next__btn{display:inline-flex;align-items:center;gap:0.35rem;border-radius:999px;padding:0.65rem 1rem;font-size:0.78rem;font-weight:800;text-decoration:none}',
            '.suite-wf-next__btn--primary{color:#fff;background:linear-gradient(135deg,#1f6f5b,#2f9d82)}',
            '.suite-wf-next__btn--ghost{color:#10231f;background:rgba(255,255,255,0.8);border:1px solid rgba(16,35,31,0.12)}',
        ].join('');
    }

    function mountBar(options) {
        var existing = document.getElementById('suite-wf-bar');
        if (existing) existing.remove();
        // 顶栏五步条已下线：顶栏主导航已覆盖 Suite 路径；条在各页出现不一致，演示观感差。
        // handoff / ensureRun / markComplete 仍可用，不依赖此 UI。
        void options;
        return null;
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

        var title = options.title || (next ? '本步完成 · 进入下一步' : '本步完成 · 回 Suite 查看观测');
        var copy = options.copy || (next
            ? '已记录到 GEO Suite 工作流。下一步：' + next.title + '。'
            : '已记录到 GEO Suite 工作流。可回 Suite 查看观测结果与最近移交。');
        var primaryHref = options.primaryHref || (next ? buildHref(next) : '/suite?step=measure');
        var primaryLabel = options.primaryLabel || (next ? next.cta : '打开 GEO Suite');
        var secondaryHref = options.secondaryHref || '/suite?step=' + (next ? next.id : 'measure');
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
            var runId = params.get('run_id') || params.get('runId');
            if (runId) {
                var state = load();
                state.runId = String(runId);
                save(state);
            }
            if (done) markComplete(done);
            if (step) setCurrent(step);
            return load();
        } catch (error) {
            return load();
        }
    }

    function shouldShowBar(options) {
        void options;
        return false;
    }

    /** 按 CONTENT_BACKEND_MODE 切换知识库/分发步链接（不覆盖产品短文案） */
    function applyContentBackendMode(mode, options) {
        var native = String(mode || 'native-python').toLowerCase() !== 'legacy-flow';
        var publicPath = (options && options.public_path) || '/knowledge';
        var flowBase = ((options && options.flow_base) || 'http://localhost:18080').replace(/\/$/, '');
        var knowledge = getStep('knowledge');
        var distribute = getStep('distribute');
        if (native) {
            knowledge.href = publicPath;
            knowledge.cta = '打开知识库';
            knowledge.external = false;
            distribute.href = '/distribute';
            distribute.cta = '打开内容/分发';
            distribute.external = false;
        } else {
            knowledge.href = flowBase + '/geo_admin/knowledge-bases/9/detail';
            knowledge.cta = '打开知识库';
            knowledge.external = true;
            distribute.href = flowBase + '/geo_admin/tasks';
            distribute.cta = '打开内容任务';
            distribute.external = true;
        }
        return native;
    }

    global.GEOrank = global.GEOrank || {};
    global.GEOrank.SuiteWorkflow = {
        STORAGE_KEY: STORAGE_KEY,
        STEPS: STEPS,
        DEFAULT_RUN: DEFAULT_RUN,
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
        applyContentBackendMode: applyContentBackendMode,
        getRunId: getRunId,
        setRun: setRun,
        ensureRun: ensureRun,
        createRun: createRun,
        handoff: handoff,
    };
})(window);
