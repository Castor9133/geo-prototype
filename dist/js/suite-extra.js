/**
 * Suite 扩展步：事实卡 / 信任素材 / 分发指引 / 可信观测只读面板
 * 读取 content_backend：native-python | legacy-flow
 */
(function (global) {
    'use strict';

    var DEMO_KB = {
        pack: 'cn-product-demo-v2',
        metricsUrl: '/pilot-demo/cn-product-demo-v2/metrics.json',
        docsPath: 'docs/pilot-demo/cn-product-demo-v2/',
        kbId: 9,
        kbName: '中文产品演示包·DJI Mini 5 Pro',
        entity: 'DJI Mini 5 Pro',
        defaultDetailPath: '/geo_admin/knowledge-bases/9/detail',
        tasksPath: '/geo_admin/tasks',
        defaultBase: 'http://localhost:18080',
        nativeAdminPath: '/admin/content-engine',
    };

    function contentBackend() {
        return global.GEOrank && global.GEOrank._contentBackend
            ? global.GEOrank._contentBackend
            : { mode: 'native-python', native: true, admin_path: DEMO_KB.nativeAdminPath };
    }

    function isNative() {
        var cb = contentBackend();
        return cb.native === true || cb.mode === 'native-python';
    }

    function geoflowBase() {
        var status = global.GEOrank && global.GEOrank._suiteIntegrationStatus;
        var base = (status && status.public_base_url) || DEMO_KB.defaultBase;
        return String(base).replace(/\/$/, '');
    }

    function geoflowUrl(path) {
        return geoflowBase() + path;
    }

    function nativeAdminUrl(hash) {
        var path = (contentBackend().admin_path || DEMO_KB.nativeAdminPath);
        return hash ? path + hash : path;
    }

    async function fetchJson(url, timeoutMs) {
        const ms = Number(timeoutMs) > 0 ? Number(timeoutMs) : 8000;
        const controller = new AbortController();
        const timer = setTimeout(() => controller.abort(), ms);
        try {
            const response = await fetch(url, {
                credentials: 'same-origin',
                signal: controller.signal,
            });
            if (!response.ok) throw new Error(`加载失败 ${response.status}`);
            return await response.json();
        } catch (error) {
            if (error && error.name === 'AbortError') {
                throw new Error(`加载超时 ${url}`);
            }
            throw error;
        } finally {
            clearTimeout(timer);
        }
    }

    function pct(rate) {
        const n = Number(rate);
        if (!Number.isFinite(n)) return '--';
        return `${Math.round(n * 100)}%`;
    }

    function escapeHtml(value) {
        return String(value == null ? '' : value)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;');
    }

    async function renderKnowledge(container) {
        const native = isNative();
        let metrics = null;
        try {
            metrics = await fetchJson(DEMO_KB.metricsUrl);
        } catch (e) {
            console.warn('[suite-extra] metrics fallback', e);
        }
        let demo = null;
        try {
            demo = await fetchJson('/api/content-engine/public/demo-summary');
        } catch (e) {
            console.warn('[suite-extra] demo-summary failed', e);
        }

        const entity = (metrics && metrics.entity_name) || DEMO_KB.entity;
        const kbName = (demo && demo.knowledge_base && demo.knowledge_base.name)
            || (metrics && metrics.kb_name)
            || DEMO_KB.kbName;
        const readyFlag = demo && demo.demo_ready;
        const badge = readyFlag ? '已就绪' : '待导入';
        const sources = (metrics && metrics.sources_note)
            || '基于公开产品页与 FAQ 整理的事实材料';
        const cards = metrics && Array.isArray(metrics.cards) ? metrics.cards : [];
        const adminUrl = '/knowledge';
        const listUrl = '/knowledge';
        const kbStats = demo && demo.knowledge_base;

        container.innerHTML = [
            `<div class="suite-extra__head">`,
            `<h3>${escapeHtml(entity)} · 知识概览</h3>`,
            `<span class="suite-badge suite-badge--accent">${escapeHtml(badge)}</span>`,
            `</div>`,
            `<p class="suite-extra__lead">`,
            `<strong>${escapeHtml(kbName)}</strong>`,
            native
                ? ` · ${readyFlag ? '示例库已导入' : '可导入示例库或新建知识库'}`
                : ` · 知识库`,
            `</p>`,
            `<p class="suite-extra__meta">${escapeHtml(sources)}</p>`,
            `<div class="suite-metric-grid">`,
            kbStats
                ? [
                    `<div class="suite-metric"><strong>${kbStats.doc_count ?? 0}</strong><span>文档</span></div>`,
                    `<div class="suite-metric"><strong>${kbStats.chunk_count ?? 0}</strong><span>切片</span></div>`,
                    `<div class="suite-metric"><strong>${kbStats.vectorized_count ?? 0}</strong><span>已向量</span></div>`,
                    `<div class="suite-metric"><strong>${readyFlag ? '就绪' : '待导入'}</strong><span>示例库</span></div>`,
                ].join('')
                : [
                    `<div class="suite-metric"><strong>${pct(metrics?.coverage?.rate)}</strong><span>事实卡覆盖率</span><small>${metrics?.coverage?.approved_cards || 0}/${metrics?.coverage?.checklist_total || 0}</small></div>`,
                    `<div class="suite-metric"><strong>${pct(metrics?.embedding?.rate)}</strong><span>切片向量化率</span><small>${metrics?.embedding?.chunk_embedded || 0}/${metrics?.embedding?.chunk_total || 0}</small></div>`,
                    `<div class="suite-metric"><strong>${pct(metrics?.evidence_production?.rate)}</strong><span>带证据生产比例</span></div>`,
                    `<div class="suite-metric"><strong>${metrics?.prompt_library_count ?? 8}</strong><span>产品提示词</span></div>`,
                ].join(''),
            `</div>`,
            cards.length
                ? [
                    `<ul class="suite-fact-list">`,
                    ...cards.slice(0, 8).map((card) => (
                        `<li><code>${escapeHtml(card.fact_id || '')}</code> ${escapeHtml(card.claim || '')}</li>`
                    )),
                    `</ul>`,
                ].join('')
                : (readyFlag
                    ? `<p class="suite-extra__meta">示例知识库已就绪，可在知识库页检索与生成。</p>`
                    : `<p class="suite-extra__meta">尚未导入示例库：可在知识库页导入或新建。</p>`),
            `<div class="suite-cta-row suite-cta-row--compact">`,
            `<a class="suite-btn suite-btn--primary" href="${escapeHtml(adminUrl)}">打开知识库</a>`,
            `<a class="suite-btn suite-btn--ghost" href="${escapeHtml(listUrl)}">管理知识库</a>`,
            `</div>`,
        ].join('');
    }

    async function renderDistribute(container) {
        const native = isNative();
        let demo = null;
        try {
            demo = await fetchJson('/api/content-engine/public/demo-summary');
        } catch (e) {
            console.warn('[suite-extra] demo-summary failed', e);
        }
        const tasks = (demo && demo.recent_tasks) || [];
        const adminUrl = (demo && demo.admin_path) || nativeAdminUrl();
        const detailUrl = native ? adminUrl : geoflowUrl(DEMO_KB.defaultDetailPath);
        const tasksUrl = native ? adminUrl : geoflowUrl(DEMO_KB.tasksPath);
        const distUrl = native ? adminUrl : geoflowUrl('/geo_admin/distribution');

        const taskList = tasks.length
            ? [
                `<ul class="suite-fact-list">`,
                ...tasks.slice(0, 5).map((t) => (
                    `<li><strong>${escapeHtml(t.status)}</strong> ${escapeHtml(t.title)}`
                    + (t.has_draft ? ` — <span class="suite-extra__meta">${escapeHtml((t.draft_preview || '').slice(0, 80))}…</span>` : '')
                    + `</li>`
                )),
                `</ul>`,
            ].join('')
            : `<p class="suite-extra__meta">暂无任务草稿。请在知识库/分发页新建任务并生成草稿。</p>`;

        if (native) {
            container.innerHTML = [
                `<div class="suite-extra__head">`,
                `<h3>渠道预览</h3>`,
                `<span class="suite-badge suite-badge--accent">预览·不外发</span>`,
                `</div>`,
                `<p class="suite-extra__lead">`,
                `绑定知识库与提示词生成草稿，再预览渠道壳并标记就绪。`,
                `</p>`,
                `<ol class="suite-demo-list suite-extra__steps">`,
                `<li>打开内容/分发 → 任务</li>`,
                `<li>选择提示词并绑定知识库</li>`,
                `<li>生成草稿</li>`,
                `<li>预览渠道壳并标记就绪</li>`,
                `</ol>`,
                taskList,
                `<div class="suite-cta-row suite-cta-row--compact">`,
                `<a class="suite-btn suite-btn--primary" href="/distribute">打开内容/分发</a>`,
                `<a class="suite-btn suite-btn--ghost" href="/knowledge">打开知识库</a>`,
                `</div>`,
            ].join('');
            return;
        }

        container.innerHTML = [
            `<div class="suite-extra__head">`,
            `<h3>分发操作指引（legacy-flow）</h3>`,
            `<span class="suite-badge suite-badge--accent">绑定 KB #${DEMO_KB.kbId}</span>`,
            `</div>`,
            `<p class="suite-extra__lead">`,
            `在 Flow <strong>任务中心新建任务</strong>，选中国生态提示词并<strong>绑定「${escapeHtml(DEMO_KB.kbName)}」（KB #${DEMO_KB.kbId}）</strong>。`,
            `</p>`,
            `<ol class="suite-demo-list suite-extra__steps">`,
            `<li>打开任务中心 → <strong>新建任务</strong></li>`,
            `<li>提示词：中国生态 8 条之一</li>`,
            `<li>知识库：绑定 KB #${DEMO_KB.kbId}</li>`,
            `<li>生成正文后选分发渠道 / 模板</li>`,
            `</ol>`,
            `<div class="suite-cta-row suite-cta-row--compact">`,
            `<a class="suite-btn suite-btn--primary" href="${escapeHtml(tasksUrl)}" target="_blank" rel="noreferrer">打开任务中心新建</a>`,
            `<a class="suite-btn suite-btn--ghost" href="${escapeHtml(detailUrl)}" target="_blank" rel="noreferrer">核对 KB #${DEMO_KB.kbId}</a>`,
            `<a class="suite-btn suite-btn--ghost" href="${escapeHtml(distUrl)}" target="_blank" rel="noreferrer">分发渠道</a>`,
            `</div>`,
        ].join('');
    }

    async function renderTrustAsset(container) {
        container.innerHTML = [
            `<div class="suite-extra__head">`,
            `<h3>补充材料</h3>`,
            `</div>`,
            `<p class="suite-extra__lead">主路径请使用知识库与内容任务；需要时再补充公开材料。</p>`,
            `<div class="suite-cta-row suite-cta-row--compact">`,
            `<a class="suite-btn suite-btn--primary" href="/knowledge">打开知识库</a>`,
            `</div>`,
        ].join('');
    }

    /** 样板 B「AI 答案监测」演示问题库（无真实采样时回落） */
    var MEASURE_DEMO_QUESTIONS = [
        {
            id: 'q1',
            text: 'DJI Mini 5 Pro 和 Mini 4 Pro 有什么区别？',
            status: '监测中',
            statusKind: 'live',
            date: '07-22',
            answer: '综合公开参数与评测，DJI Mini 5 Pro 在影像规格与避障能力上相对 Mini 4 Pro 有升级；若你更关注轻量航拍与法规重量档，两者仍同属同类便携机型。GEORank 演示包中的事实卡会优先引用官网规格与 FAQ。',
            cites: [
                { domain: 'dji.com', tag: '官网', kind: 'official' },
                { domain: '36kr.com', tag: '媒体', kind: 'media' },
                { domain: 'zhihu.com', tag: '社区', kind: 'community' },
            ],
            trust: 78,
            platforms: [
                { name: '豆包', mention: 72, trust: 76 },
                { name: '文心一言', mention: 64, trust: 71 },
                { name: '通义千问', mention: 58, trust: 68 },
                { name: 'Kimi', mention: 61, trust: 70 },
            ],
            trend: [
                { d: '07-16', v: 62 }, { d: '07-18', v: 68 }, { d: '07-20', v: 71 },
                { d: '07-22', v: 74 }, { d: '07-24', v: 76 }, { d: '07-26', v: 78 },
            ],
        },
        {
            id: 'q2',
            text: 'Mini 5 Pro 续航和抗风能力怎么样？',
            status: '监测中',
            statusKind: 'live',
            date: '07-21',
            answer: '续航与抗风表现依赖具体飞行环境。演示答案会强调「以官网标称飞行时间为准」，并提示大风、低温会缩短有效续航；避障与传感器配置是选择理由之一。',
            cites: [
                { domain: 'dji.com', tag: '官网', kind: 'official' },
                { domain: 'bilibili.com', tag: '媒体', kind: 'media' },
            ],
            trust: 72,
            platforms: [
                { name: '豆包', mention: 55, trust: 70 },
                { name: '文心一言', mention: 48, trust: 66 },
                { name: '通义千问', mention: 52, trust: 69 },
                { name: 'Kimi', mention: 44, trust: 64 },
            ],
            trend: [
                { d: '07-16', v: 58 }, { d: '07-18', v: 60 }, { d: '07-20', v: 65 },
                { d: '07-22', v: 68 }, { d: '07-24', v: 70 }, { d: '07-26', v: 72 },
            ],
        },
        {
            id: 'q3',
            text: '适合旅行航拍的轻便无人机推荐？',
            status: '新增',
            statusKind: 'new',
            date: '07-20',
            answer: '旅行场景通常优先考虑重量档、折叠体积与一键跟拍。演示监测中，Mini 系列会作为高频提及候选；是否出现品牌名取决于知识库证据是否被模型采信。',
            cites: [
                { domain: 'xiaohongshu.com', tag: '社区', kind: 'community' },
                { domain: 'dji.com', tag: '官网', kind: 'official' },
            ],
            trust: 69,
            platforms: [
                { name: '豆包', mention: 41, trust: 65 },
                { name: '文心一言', mention: 38, trust: 62 },
                { name: '通义千问', mention: 46, trust: 67 },
                { name: 'Kimi', mention: 33, trust: 60 },
            ],
            trend: [
                { d: '07-16', v: 52 }, { d: '07-18', v: 55 }, { d: '07-20', v: 58 },
                { d: '07-22', v: 63 }, { d: '07-24', v: 66 }, { d: '07-26', v: 69 },
            ],
        },
        {
            id: 'q4',
            text: 'Mini 5 Pro 是否支持垂直拍摄？',
            status: '监测中',
            statusKind: 'live',
            date: '07-18',
            answer: '垂直拍摄能力以产品发布说明与说明书为准。演示观测会检查答案是否引用官网规格页，而非泛化「支持竖拍」的无来源表述。',
            cites: [
                { domain: 'dji.com', tag: '官网', kind: 'official' },
            ],
            trust: 81,
            platforms: [
                { name: '豆包', mention: 66, trust: 80 },
                { name: '文心一言', mention: 59, trust: 74 },
                { name: '通义千问', mention: 61, trust: 77 },
                { name: 'Kimi', mention: 57, trust: 73 },
            ],
            trend: [
                { d: '07-16', v: 70 }, { d: '07-18', v: 73 }, { d: '07-20', v: 75 },
                { d: '07-22', v: 78 }, { d: '07-24', v: 80 }, { d: '07-26', v: 81 },
            ],
        },
        {
            id: 'q5',
            text: '入门航拍选 Mini 5 Pro 还是竞品？',
            status: '待复核',
            statusKind: 'warn',
            date: '07-15',
            answer: '对比类问题最容易出现无证据推荐。演示监测关注：是否出现可核验参数对比，以及引用是否落到官网 / 权威测评，而非纯口碑复述。',
            cites: [
                { domain: 'ithome.com', tag: '媒体', kind: 'media' },
                { domain: 'dji.com', tag: '官网', kind: 'official' },
                { domain: 'sspai.com', tag: '媒体', kind: 'media' },
            ],
            trust: 64,
            platforms: [
                { name: '豆包', mention: 36, trust: 58 },
                { name: '文心一言', mention: 42, trust: 61 },
                { name: '通义千问', mention: 39, trust: 60 },
                { name: 'Kimi', mention: 31, trust: 55 },
            ],
            trend: [
                { d: '07-16', v: 48 }, { d: '07-18', v: 52 }, { d: '07-20', v: 55 },
                { d: '07-22', v: 58 }, { d: '07-24', v: 61 }, { d: '07-26', v: 64 },
            ],
        },
    ];

    function buildSparkPath(points) {
        if (!points || !points.length) return '';
        const vals = points.map((p) => Number(p.v) || 0);
        const min = Math.min.apply(null, vals);
        const max = Math.max.apply(null, vals);
        const span = Math.max(1, max - min);
        return points.map((p, i) => {
            const x = points.length === 1 ? 50 : (i / (points.length - 1)) * 100;
            const y = 88 - ((Number(p.v) - min) / span) * 70;
            return `${i === 0 ? 'M' : 'L'}${x.toFixed(1)},${y.toFixed(1)}`;
        }).join(' ');
    }

    function trustLabel(score) {
        const n = Number(score) || 0;
        if (n >= 75) return '可信度良好';
        if (n >= 60) return '可信度一般';
        return '可信度偏低';
    }

    function renderMeasureDetail(container, questions, activeId, meta) {
        const active = questions.find((q) => q.id === activeId) || questions[0];
        if (!active) return;
        const qList = container.querySelector('#measure-q-list');
        const answerEl = container.querySelector('#measure-answer-body');
        const citesEl = container.querySelector('#measure-answer-cites');
        const evidenceEl = container.querySelector('#measure-evidence-list');
        const trustScore = container.querySelector('#measure-trust-score');
        const trustNote = container.querySelector('#measure-trust-note');
        const trustGauge = container.querySelector('#measure-trust-gauge');
        const trendList = container.querySelector('#measure-trend-list');
        const trendPath = container.querySelector('#measure-trend-path');
        const platformEl = container.querySelector('#measure-platform-list');
        const answerTitle = container.querySelector('#measure-answer-q');
        const answerMeta = container.querySelector('#measure-answer-meta');

        if (qList) {
            qList.querySelectorAll('[data-qid]').forEach((el) => {
                el.classList.toggle('is-active', el.getAttribute('data-qid') === active.id);
            });
        }
        if (answerTitle) answerTitle.textContent = active.text;
        if (answerMeta) {
            answerMeta.textContent = `监测更新 ${active.date} · ${meta.demo ? '演示' : '采样'} · AI 回答`;
        }
        if (answerEl) {
            const highlighted = escapeHtml(active.answer).replace(
                /(DJI Mini 5 Pro|Mini 5 Pro|GEORank|大疆)/g,
                '<mark class="measure-hl">$1</mark>'
            );
            answerEl.innerHTML = highlighted;
        }
        if (citesEl) {
            citesEl.innerHTML = (active.cites || []).map((c) => (
                `<span class="measure-cite-tag measure-cite-tag--${escapeHtml(c.kind || 'media')}">${escapeHtml(c.domain)}</span>`
            )).join('');
        }
        if (evidenceEl) {
            evidenceEl.innerHTML = (active.cites || []).map((c, i) => (
                `<li>`
                + `<span class="measure-ev-num">${i + 1}</span>`
                + `<div><strong>${escapeHtml(c.domain)}</strong>`
                + `<span class="measure-ev-tag measure-ev-tag--${escapeHtml(c.kind || 'media')}">${escapeHtml(c.tag || '来源')}</span></div>`
                + `<span class="material-symbols-outlined measure-ev-link" aria-hidden="true">open_in_new</span>`
                + `</li>`
            )).join('');
        }
        if (trustScore) trustScore.textContent = String(active.trust);
        if (trustNote) trustNote.textContent = trustLabel(active.trust);
        if (trustGauge) trustGauge.style.setProperty('--p', String(active.trust));
        if (trendList) {
            trendList.innerHTML = (active.trend || []).map((t) => (
                `<li><span>${escapeHtml(t.d)}</span><b>${escapeHtml(t.v)}</b></li>`
            )).join('');
        }
        if (trendPath) trendPath.setAttribute('d', buildSparkPath(active.trend || []));
        if (platformEl) {
            platformEl.innerHTML = (active.platforms || []).map((p) => (
                `<li>`
                + `<span class="measure-plat-name">${escapeHtml(p.name)}</span>`
                + `<div class="measure-plat-bar"><i style="width:${Number(p.mention) || 0}%"></i></div>`
                + `<b class="measure-plat-pct">${Number(p.mention) || 0}%</b>`
                + `<span class="measure-plat-ring" style="--p:${Number(p.trust) || 0}"><em>${Number(p.trust) || 0}</em></span>`
                + `</li>`
            )).join('');
        }
    }

    function renderMeasurePayload(container, payload) {
        const run = payload.run || {};
        const agg = run.aggregate || {};
        const demo = Boolean(payload.demo_data);
        const mention = Number(agg.mention);
        const citation = Number(agg.citation);
        const total = Number(agg.total_samples) || 0;
        const questions = MEASURE_DEMO_QUESTIONS;
        const questionCount = questions.length * (demo ? 8 : 12);
        const mentionKpi = Number.isFinite(mention) && mention > 0
            ? (demo ? mention * 32 : mention)
            : 128;
        const trustAvg = Math.round(
            questions.reduce((s, q) => s + (Number(q.trust) || 0), 0) / Math.max(1, questions.length)
        );
        const citeBoost = total > 0 && Number.isFinite(citation)
            ? Math.min(12, Math.round((citation / total) * 20))
            : 0;
        const trustKpi = Math.min(99, trustAvg + citeBoost);
        const activeId = questions[0].id;
        const meta = { demo: demo, badge: demo ? '演示' : (payload.badge || 'API 采样') };

        container.innerHTML = [
            `<div class="measure-monitor" data-demo="${demo ? '1' : '0'}">`,
            `<div class="measure-toolbar">`,
            `<div class="measure-toolbar__meta">`,
            `<span class="suite-badge">${escapeHtml(meta.badge)}</span>`,
            `<span class="measure-toolbar__hint">问题库 · 答案抽样 · 来源可信度</span>`,
            `</div>`,
            `<div class="measure-toolbar__filters">`,
            `<select id="mf-range" aria-label="时间范围"><option>近 7 天</option><option selected>近 30 天</option></select>`,
            `<select id="mf-platform" aria-label="平台"><option selected>全部平台</option><option>豆包</option><option>文心一言</option><option>通义</option></select>`,
            `<button type="button" class="cockpit-btn cockpit-btn--primary" id="mf-apply">应用筛选</button>`,
            `</div>`,
            `</div>`,

            `<section class="measure-kpi-row" aria-label="观测 KPI">`,
            `<article class="measure-kpi">`,
            `<span class="measure-kpi__icon measure-kpi__icon--blue material-symbols-outlined">monitoring</span>`,
            `<div><strong id="mk-q">${questionCount}</strong><span>监测问题</span></div>`,
            `</article>`,
            `<article class="measure-kpi">`,
            `<span class="measure-kpi__icon measure-kpi__icon--green material-symbols-outlined">verified</span>`,
            `<div><strong id="mk-m">${mentionKpi}</strong><span>本期提及</span></div>`,
            `<small>样本 ${agg.total_samples ?? '--'}</small>`,
            `</article>`,
            `<article class="measure-kpi">`,
            `<span class="measure-kpi__icon measure-kpi__icon--orange material-symbols-outlined">track_changes</span>`,
            `<div><strong id="mk-t">${trustKpi}</strong><span>平均可信度</span></div>`,
            `<small>/100</small>`,
            `</article>`,
            `</section>`,

            `<div class="measure-workspace">`,
            `<section class="measure-panel measure-q-lib">`,
            `<div class="measure-panel__head"><h3>问题库</h3></div>`,
            `<label class="measure-search">`,
            `<span class="material-symbols-outlined" aria-hidden="true">search</span>`,
            `<input type="search" id="measure-q-search" placeholder="搜索监测问题…" autocomplete="off">`,
            `</label>`,
            `<ul class="measure-q-list" id="measure-q-list">`,
            ...questions.map((q, i) => (
                `<li>`
                + `<button type="button" class="measure-q-item${i === 0 ? ' is-active' : ''}" data-qid="${escapeHtml(q.id)}">`
                + `<span class="measure-q-item__text">${escapeHtml(q.text)}</span>`
                + `<span class="measure-q-item__meta">`
                + `<em class="measure-status measure-status--${escapeHtml(q.statusKind)}">${escapeHtml(q.status)}</em>`
                + `<time>${escapeHtml(q.date)}</time>`
                + `</span></button></li>`
            )),
            `</ul>`,
            `<button type="button" class="measure-add-q" id="measure-add-q">+ 新增监测问题</button>`,
            `</section>`,

            `<div class="measure-main">`,
            `<section class="measure-panel measure-answer">`,
            `<div class="measure-panel__head">`,
            `<h3>答案抽样</h3>`,
            `<span class="measure-ai-badge">AI</span>`,
            `</div>`,
            `<p class="measure-answer__q" id="measure-answer-q"></p>`,
            `<p class="measure-answer__meta" id="measure-answer-meta"></p>`,
            `<div class="measure-answer__box" id="measure-answer-body"></div>`,
            `</section>`,

            `<div class="measure-insight-row">`,
            `<section class="measure-panel">`,
            `<div class="measure-panel__head"><h3>引用证据</h3></div>`,
            `<ol class="measure-evidence" id="measure-evidence-list"></ol>`,
            `</section>`,
            `<section class="measure-panel measure-trust-card">`,
            `<div class="measure-panel__head"><h3>来源可信度</h3></div>`,
            `<div class="gauge gauge--lg" id="measure-trust-gauge" style="--p:76">`,
            `<span id="measure-trust-score">76</span>`,
            `<small>/100</small>`,
            `</div>`,
            `<p class="measure-trust-ok" id="measure-trust-note">可信度良好</p>`,
            `</section>`,
            `</div>`,
            `</div>`,
            `</div>`,

            `<div class="measure-lower-grid">`,
            `<section class="measure-panel">`,
            `<div class="measure-panel__head"><h3>监测详情</h3><span class="cockpit-muted">可信度趋势</span></div>`,
            `<div class="measure-trend">`,
            `<ul class="measure-trend__list" id="measure-trend-list"></ul>`,
            `<svg class="measure-trend__svg" viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true">`,
            `<path id="measure-trend-path" fill="none" stroke="currentColor" stroke-width="2.2"></path>`,
            `</svg>`,
            `</div>`,
            `</section>`,
            `<section class="measure-panel">`,
            `<div class="measure-panel__head"><h3>平台对比</h3><span class="cockpit-muted">提及率 · 可信度</span></div>`,
            `<ul class="measure-platform-list" id="measure-platform-list"></ul>`,
            `</section>`,
            `</div>`,

            `<footer class="measure-monitor__foot">`,
            `<p class="suite-extra__meta">${escapeHtml(payload.method_note || payload.message || '演示数据')}</p>`,
            `<div class="suite-cta-row suite-cta-row--compact">`,
            `<button type="button" class="suite-btn suite-btn--primary" data-measure-done="1">标记观测完成</button>`,
            `</div>`,
            `</footer>`,
            `</div>`,
        ].join('');

        renderMeasureDetail(container, questions, activeId, meta);

        container.querySelectorAll('[data-qid]').forEach((btn) => {
            btn.addEventListener('click', () => {
                renderMeasureDetail(container, questions, btn.getAttribute('data-qid'), meta);
            });
        });

        const search = container.querySelector('#measure-q-search');
        if (search) {
            search.addEventListener('input', () => {
                const q = String(search.value || '').trim().toLowerCase();
                container.querySelectorAll('.measure-q-item').forEach((item) => {
                    const hit = !q || item.textContent.toLowerCase().indexOf(q) >= 0;
                    item.parentElement.hidden = !hit;
                });
            });
        }

        const apply = container.querySelector('#mf-apply');
        if (apply) {
            apply.addEventListener('click', () => {
                const plat = container.querySelector('#mf-platform')?.value || '';
                const note = container.querySelector('.measure-monitor__foot .suite-extra__meta');
                if (note) {
                    note.textContent = plat ? `已筛选：${plat}` : '已应用筛选';
                }
            });
        }

        const addBtn = container.querySelector('#measure-add-q');
        if (addBtn) {
            addBtn.hidden = true;
        }

        const doneBtn = container.querySelector('[data-measure-done]');
        if (doneBtn && global.GEOrank?.SuiteWorkflow) {
            doneBtn.addEventListener('click', () => {
                global.GEOrank.SuiteWorkflow.markComplete('measure');
                doneBtn.textContent = '已标记完成';
                doneBtn.disabled = true;
            });
        }
    }

    function asPct(n) {
        return Math.round((Number(n) || 0) * 100);
    }

    function questionEntityStatus(q) {
        const rows = Object.values(q.platforms || {});
        const total = rows.length || 1;
        const hits = rows.filter((r) => r && r.entity_mentioned).length;
        if (hits >= total) return { kind: 'full', label: '本品全中' };
        if (hits <= 0) return { kind: 'miss', label: '本品缺席' };
        return { kind: 'partial', label: '部分出现' };
    }

    function layerEntityRate(questions, layerId) {
        let hit = 0;
        let total = 0;
        (questions || []).forEach((q) => {
            if (q.layer !== layerId) return;
            Object.values(q.platforms || {}).forEach((r) => {
                total += 1;
                if (r && r.entity_mentioned) hit += 1;
            });
        });
        return total ? hit / total : 0;
    }

    function platformAggRows(script) {
        const questions = script.questions || [];
        const summary = script.summary || {};
        const readiness = summary.platform_readiness || {};
        return (script.platforms || []).map((name) => {
            let e = 0;
            let c = 0;
            let d = 0;
            let n = 0;
            questions.forEach((q) => {
                const row = (q.platforms || {})[name];
                if (!row) return;
                n += 1;
                if (row.entity_mentioned) e += 1;
                if (row.competitor_mentioned) c += 1;
                d += Number(row.evidence_density) || 0;
            });
            return {
                name,
                entityRate: n ? e / n : 0,
                competitorRate: n ? c / n : 0,
                evidenceDensity: n ? d / n : 0,
                readiness: Number(readiness[name]) || 0,
                samples: n,
            };
        });
    }

    function renderFunnelObserve(container, script, aiFocus, options) {
        const opts = options || {};
        const doneStep = opts.doneStep || 'measure';
        const doneLabel = opts.doneLabel || '标记观测完成';
        const layers = script.layers || [];
        const questions = script.questions || [];
        const summary = script.summary || {};
        const platforms = script.platforms || [];
        const rubric = script.scoring_rubric || {};
        const meta = script.meta || {};
        const matrix = platformAggRows(script);
        const sampleCount = Number(meta.sample_count) || (questions.length * platforms.length) || 0;
        const readinessVals = Object.values(summary.platform_readiness || {});
        const readinessAvg = readinessVals.length
            ? readinessVals.reduce((s, v) => s + Number(v || 0), 0) / readinessVals.length
            : 0;
        const focusItems = (aiFocus && aiFocus.items) || [];

        let layerIdx = 0;
        let qIdx = 0;
        let platformFilter = 'all';
        let windowLabel = meta.window_label || '近 30 天';
        let focusPlat = platforms[0] || '';

        function layerQuestions() {
            const layer = layers[layerIdx];
            if (!layer) return [];
            return questions.filter((q) => q.layer === layer.id);
        }

        function sourcePrefsPanelHtml() {
            if (!focusItems.length) return '';
            const rows = focusItems.map((row) => {
                const chips = (row.source_prefs || [])
                    .map((sp) => {
                        const ex = (sp.examples || []).slice(0, 2).join('、');
                        return `<span class="obs-src-chip" title="${escapeHtml(ex)}">${escapeHtml(sp.type)}</span>`
                            + (ex ? `<span class="obs-src-ex">${escapeHtml(ex)}</span>` : '');
                    })
                    .join('');
                return `<tr><th>${escapeHtml(row.platform)}</th><td class="obs-src-cell">${chips}</td></tr>`;
            }).join('');
            return [
                '<section class="measure-panel obs-source-prefs-panel">',
                '<div class="measure-panel__head"><h3>平台信源偏好</h3>',
                '<span class="cockpit-muted">演示策略表 · 非平台实测</span></div>',
                `<p class="obs-source-prefs__note">${escapeHtml((aiFocus && aiFocus.disclaimer) || '同源策略表，供对照生成侧重；非实测引用率。')}</p>`,
                '<div class="obs-source-prefs-scroll"><table class="obs-source-prefs">',
                '<thead><tr><th>平台</th><th>偏好信源类型（示例域）</th></tr></thead>',
                `<tbody>${rows}</tbody></table></div>`,
                '</section>',
            ].join('');
        }

        function paint() {
            const layer = layers[layerIdx] || {};
            const qs = layerQuestions();
            if (qIdx >= qs.length) qIdx = 0;
            const q = qs[qIdx] || {};
            const allPlatRows = Object.entries(q.platforms || {});
            const platRows = platformFilter === 'all'
                ? allPlatRows
                : allPlatRows.filter(([name]) => name === platformFilter);
            if (focusPlat && !allPlatRows.some(([name]) => name === focusPlat)) {
                focusPlat = (allPlatRows[0] && allPlatRows[0][0]) || platforms[0] || '';
            }
            if (platformFilter !== 'all') focusPlat = platformFilter;
            const entityHits = allPlatRows.filter(([, r]) => r.entity_mentioned).length;
            const compHits = allPlatRows.filter(([, r]) => r.competitor_mentioned).length;
            const densAvg = allPlatRows.length
                ? allPlatRows.reduce((s, [, r]) => s + (Number(r.evidence_density) || 0), 0) / allPlatRows.length
                : 0;
            const focusRow = (q.platforms || {})[focusPlat] || {};
            const focusEvidence = focusRow.evidence || [];

            container.innerHTML = [
                '<div class="measure-monitor obs-monitor" data-demo="1">',
                '<div class="measure-toolbar obs-toolbar">',
                '<div class="measure-toolbar__meta">',
                '<span class="suite-badge">演示剧本 · 非平台实测</span>',
                `<span class="obs-entity-chip">${escapeHtml(script.entity || '本品')}</span>`,
                `<span class="obs-entity-chip obs-entity-chip--comp">vs ${escapeHtml(script.competitor || '竞品')}</span>`,
                '</div>',
                '<div class="measure-toolbar__filters">',
                `<label class="obs-filter"><span>时间窗</span><select id="obs-window" aria-label="时间范围">`,
                `<option value="近 7 天"${windowLabel === '近 7 天' ? ' selected' : ''}>近 7 天</option>`,
                `<option value="近 30 天"${windowLabel === '近 30 天' ? ' selected' : ''}>近 30 天</option>`,
                '</select></label>',
                `<label class="obs-filter"><span>平台</span><select id="obs-platform" aria-label="平台筛选">`,
                `<option value="all"${platformFilter === 'all' ? ' selected' : ''}>全部平台</option>`,
                platforms.map((p) => `<option value="${escapeHtml(p)}"${platformFilter === p ? ' selected' : ''}>${escapeHtml(p)}</option>`).join(''),
                '</select></label>',
                `<span class="measure-toolbar__hint">${escapeHtml(meta.probe_cycle || `${questions.length} 问 × ${platforms.length} 平台`)}</span>`,
                `<span class="measure-toolbar__hint">最近探针 ${escapeHtml(meta.last_probe_at || '—')}</span>`,
                '</div></div>',

                '<section class="measure-kpi-row obs-kpi-row" aria-label="观测 KPI">',
                `<article class="measure-kpi"><span class="measure-kpi__icon measure-kpi__icon--green material-symbols-outlined">verified</span><div><strong>${asPct(summary.entity_appearance_rate)}%</strong><span>本品出现率</span></div><small>${escapeHtml(script.entity || '')}</small></article>`,
                `<article class="measure-kpi"><span class="measure-kpi__icon measure-kpi__icon--blue material-symbols-outlined">compare</span><div><strong>${asPct(summary.competitor_appearance_rate)}%</strong><span>竞品出现率</span></div><small>${escapeHtml(script.competitor || '')}</small></article>`,
                `<article class="measure-kpi"><span class="measure-kpi__icon measure-kpi__icon--orange material-symbols-outlined">analytics</span><div><strong>${asPct(summary.avg_evidence_density)}%</strong><span>平均证据密度</span></div><small>演示指标</small></article>`,
                `<article class="measure-kpi"><span class="measure-kpi__icon measure-kpi__icon--blue material-symbols-outlined">hub</span><div><strong>${asPct(readinessAvg)}%</strong><span>平台就绪均值</span></div><small>四平台聚合</small></article>`,
                `<article class="measure-kpi"><span class="measure-kpi__icon measure-kpi__icon--green material-symbols-outlined">quiz</span><div><strong>${questions.length}/${sampleCount}</strong><span>问题 / 样本</span></div><small>${escapeHtml(windowLabel)}</small></article>`,
                '</section>',

                '<div class="obs-funnel" role="tablist" aria-label="观测漏斗层">',
                layers.map((l, i) => {
                    const rate = layerEntityRate(questions, l.id);
                    return `<button type="button" class="obs-funnel__btn${i === layerIdx ? ' is-active' : ''}" data-funnel-layer="${i}" role="tab" aria-selected="${i === layerIdx}">`
                        + `<em>${i + 1}. ${escapeHtml(l.label)}</em>`
                        + `<span>本品出现 ${asPct(rate)}%</span></button>`;
                }).join(''),
                '</div>',
                `<p class="obs-layer-desc"><strong>${escapeHtml(layer.label || '')}</strong> — ${escapeHtml(layer.desc || '')}</p>`,

                '<div class="obs-workspace">',
                '<section class="measure-panel obs-q-panel">',
                '<div class="measure-panel__head"><h3>本层追问</h3><span class="cockpit-muted">' + qs.length + ' 条</span></div>',
                '<ul class="measure-q-list">',
                qs.map((item, i) => {
                    const st = questionEntityStatus(item);
                    return `<li><button type="button" class="measure-q-item${i === qIdx ? ' is-active' : ''}" data-funnel-q="${i}">`
                        + `<span class="measure-q-item__text">${escapeHtml(item.text)}</span>`
                        + `<span class="obs-q-status obs-q-status--${st.kind}">${escapeHtml(st.label)}</span>`
                        + `</button></li>`;
                }).join(''),
                '</ul></section>',

                '<section class="measure-panel obs-cards-panel">',
                `<div class="measure-panel__head"><h3>平台答案回放</h3>`
                + `<span class="cockpit-muted">本品 ${entityHits}/${allPlatRows.length} · 竞品 ${compHits}/${allPlatRows.length} · 证据 ${asPct(densAvg)}%</span></div>`,
                `<p class="measure-answer__q">${escapeHtml(q.text || '')}</p>`,
                '<div class="obs-plat-cards">',
                (platRows.length ? platRows : [['—', {}]]).map(([name, row]) => {
                    const dens = asPct(row.evidence_density);
                    const body = row.answer_excerpt || row.snippet || '（无摘录）';
                    const evid = (row.evidence || []).map((e) => `<span class="obs-chip">${escapeHtml(e)}</span>`).join('');
                    return `<button type="button" class="obs-plat-card${name === focusPlat ? ' is-active' : ''}" data-focus-plat="${escapeHtml(name)}">`
                        + `<header><strong>${escapeHtml(name)}</strong>`
                        + `<span class="obs-dens">${dens}%</span></header>`
                        + `<div class="obs-dens-bar" aria-hidden="true"><i style="width:${dens}%"></i></div>`
                        + `<div class="obs-flags">`
                        + `<span class="obs-flag${row.entity_mentioned ? ' is-on' : ''}">本品${row.entity_mentioned ? '✓' : '×'}</span>`
                        + `<span class="obs-flag${row.competitor_mentioned ? ' is-on is-comp' : ''}">竞品${row.competitor_mentioned ? '✓' : '×'}</span>`
                        + `</div>`
                        + `<p class="obs-excerpt">${escapeHtml(body)}</p>`
                        + `<div class="obs-chips">${evid || '<span class="obs-chip obs-chip--muted">无引用示意</span>'}</div>`
                        + `</button>`;
                }).join(''),
                '</div></section>',

                '<aside class="measure-panel obs-side-panel">',
                '<div class="measure-panel__head"><h3>本问洞察</h3></div>',
                `<ul class="obs-stat-list">`
                + `<li><span>本品出现</span><b>${entityHits}/${allPlatRows.length}</b></li>`
                + `<li><span>竞品出现</span><b>${compHits}/${allPlatRows.length}</b></li>`
                + `<li><span>证据密度</span><b>${asPct(densAvg)}%</b></li>`
                + `<li><span>焦点平台</span><b>${escapeHtml(focusPlat || '—')}</b></li>`
                + `</ul>`,
                '<div class="measure-panel__head"><h3>评分规则</h3></div>',
                '<div class="obs-rubric">',
                '<p class="obs-rubric__label">加分</p>',
                '<ul>' + (rubric.plus || []).map((t) => `<li>${escapeHtml(t)}</li>`).join('') + '</ul>',
                '<p class="obs-rubric__label obs-rubric__label--minus">扣分</p>',
                '<ul>' + (rubric.minus || []).map((t) => `<li>${escapeHtml(t)}</li>`).join('') + '</ul>',
                '</div>',
                `<div class="measure-panel__head"><h3>引用 · ${escapeHtml(focusPlat || '')}</h3></div>`,
                '<ol class="measure-evidence">'
                + (focusEvidence.length
                    ? focusEvidence.map((e) => `<li>${escapeHtml(e)}</li>`).join('')
                    : '<li class="cockpit-muted">暂无引用示意</li>')
                + '</ol>',
                '</aside>',
                '</div>',

                '<section class="measure-panel obs-matrix-panel">',
                '<div class="measure-panel__head"><h3>平台 × 指标矩阵</h3><span class="cockpit-muted">全剧聚合 · 非实测</span></div>',
                '<div class="obs-matrix-scroll"><table class="obs-matrix">',
                '<thead><tr><th>平台</th><th>本品出现率</th><th>竞品出现率</th><th>证据密度</th><th>就绪度</th><th>样本</th></tr></thead>',
                '<tbody>',
                matrix.map((row) => `<tr>`
                    + `<td>${escapeHtml(row.name)}</td>`
                    + `<td><div class="obs-mini-bar"><i style="width:${asPct(row.entityRate)}%"></i></div>${asPct(row.entityRate)}%</td>`
                    + `<td><div class="obs-mini-bar obs-mini-bar--comp"><i style="width:${asPct(row.competitorRate)}%"></i></div>${asPct(row.competitorRate)}%</td>`
                    + `<td><div class="obs-mini-bar obs-mini-bar--dens"><i style="width:${asPct(row.evidenceDensity)}%"></i></div>${asPct(row.evidenceDensity)}%</td>`
                    + `<td>${asPct(row.readiness)}%</td>`
                    + `<td>${row.samples}</td></tr>`).join(''),
                '</tbody></table></div>',
                '</section>',

                sourcePrefsPanelHtml(),

                '<footer class="measure-monitor__foot">',
                `<p class="suite-extra__meta">${escapeHtml(
                    opts.disclaimer
                    || script.disclaimer
                    || (doneStep === 'diagnostic'
                        ? '初诊观测 · 演示剧本 · 与 Suite「观测」同一套漏斗（非平台实测）'
                        : '演示剧本 · 非平台实测'),
                )}</p>`,
                '<div class="suite-cta-row suite-cta-row--compact">',
                `<button type="button" class="suite-btn suite-btn--primary" data-measure-done="1">${escapeHtml(doneLabel)}</button>`,
                '</div></footer></div>',
            ].join('');

            container.querySelectorAll('[data-funnel-layer]').forEach((btn) => {
                btn.addEventListener('click', () => {
                    layerIdx = Number(btn.getAttribute('data-funnel-layer')) || 0;
                    qIdx = 0;
                    paint();
                });
            });
            container.querySelectorAll('[data-funnel-q]').forEach((btn) => {
                btn.addEventListener('click', () => {
                    qIdx = Number(btn.getAttribute('data-funnel-q')) || 0;
                    paint();
                });
            });
            container.querySelectorAll('[data-focus-plat]').forEach((btn) => {
                btn.addEventListener('click', () => {
                    focusPlat = btn.getAttribute('data-focus-plat') || focusPlat;
                    paint();
                });
            });
            const winSel = container.querySelector('#obs-window');
            if (winSel) {
                winSel.addEventListener('change', () => {
                    windowLabel = winSel.value || windowLabel;
                    paint();
                });
            }
            const platSel = container.querySelector('#obs-platform');
            if (platSel) {
                platSel.addEventListener('change', () => {
                    platformFilter = platSel.value || 'all';
                    paint();
                });
            }
            const doneBtn = container.querySelector('[data-measure-done]');
            if (doneBtn && global.GEOrank?.SuiteWorkflow) {
                doneBtn.addEventListener('click', () => {
                    const Workflow = global.GEOrank.SuiteWorkflow;
                    Workflow.markComplete(doneStep);
                    Workflow.handoff?.(doneStep, {
                        meta: {
                            script_key: script.key,
                            entity_appearance_rate: summary.entity_appearance_rate,
                            observation_kind: doneStep === 'diagnostic' ? 'initial_geo' : 'measure',
                        },
                    }).catch(() => null);
                    doneBtn.textContent = '已标记完成';
                    doneBtn.disabled = true;
                });
            }
        }

        paint();
    }

    let aiFocusCache = null;

    async function loadAiFocusScript() {
        if (aiFocusCache) return aiFocusCache;
        try {
            aiFocusCache = await fetchJson('/api/geo-runs/scripts/geo-ai-focus-dji');
            if (aiFocusCache && aiFocusCache.items) return aiFocusCache;
        } catch (_) {
            /* fallback */
        }
        try {
            aiFocusCache = await fetchJson('/pilot-demo/geo-ai-focus-dji.json');
        } catch (_) {
            aiFocusCache = null;
        }
        return aiFocusCache;
    }

    async function mountGeoObserve(container, options) {
        if (!container) return;
        const opts = options || {};
        container.innerHTML = '<div class="measure-monitor measure-monitor--loading"><div class="measure-toolbar"><span class="suite-badge">加载中</span><span class="measure-toolbar__hint">正在加载观测剧本…</span></div><div class="measure-kpi-row"><div class="measure-kpi skeleton"></div><div class="measure-kpi skeleton"></div><div class="measure-kpi skeleton"></div></div></div>';
        const Workflow = global.GEOrank?.SuiteWorkflow;
        const runId = opts.runId || Workflow?.getRunId?.();
        const aiFocus = await loadAiFocusScript().catch(() => null);
        try {
            if (runId) {
                const preview = await fetchJson(`/api/geo-runs/${runId}/geo-preview`);
                if (preview && preview.script) {
                    renderFunnelObserve(container, preview.script, aiFocus, opts);
                    return;
                }
            }
        } catch (error) {
            console.warn('[suite-extra] geo-preview failed', error);
        }
        try {
            const script = await fetchJson('/api/geo-runs/scripts/geo-observe-funnel-dji-vs-autel');
            if (script && script.questions) {
                renderFunnelObserve(container, script, aiFocus, opts);
                return;
            }
        } catch (error) {
            console.warn('[suite-extra] script api failed', error);
        }
        try {
            const script = await fetchJson('/pilot-demo/geo-observe-funnel-dji-vs-autel.json');
            if (script && script.questions) {
                renderFunnelObserve(container, script, aiFocus, opts);
                return;
            }
        } catch (error) {
            console.warn('[suite-extra] static funnel failed', error);
        }
        container.innerHTML = '<p class="suite-extra__lead">观测剧本加载失败。</p>';
    }

    function platformLabel(key) {
        const map = { doubao: '豆包', yuanbao: '元宝', deepseek: 'DeepSeek' };
        return map[key] || key;
    }

    function fmtPct(rate) {
        const n = Number(rate);
        if (!Number.isFinite(n)) return '—';
        return `${Math.round(n * 1000) / 10}%`;
    }

    async function postJson(url, body) {
        const response = await fetch(url, {
            method: 'POST',
            credentials: 'same-origin',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body || {}),
        });
        const data = await response.json().catch(() => ({}));
        if (!response.ok) {
            const detail = data.detail || data.message || response.statusText;
            throw new Error(typeof detail === 'string' ? detail : JSON.stringify(detail));
        }
        return data;
    }

    async function patchJson(url, body) {
        const response = await fetch(url, {
            method: 'PATCH',
            credentials: 'same-origin',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body || {}),
        });
        const data = await response.json().catch(() => ({}));
        if (!response.ok) {
            throw new Error(data.detail || response.statusText || '请求失败');
        }
        return data;
    }

    async function mountRealObs(container, options) {
        if (!container) return;
        const opts = options || {};
        const Workflow = global.GEOrank?.SuiteWorkflow;
        let runId = opts.runId || Workflow?.getRunId?.();
        if (!runId && Workflow?.ensureRun) {
            try {
                const run = await Workflow.ensureRun({});
                runId = run && (run.id || run.run_id);
            } catch (error) {
                console.warn('[suite-extra] ensureRun failed', error);
            }
        }
        if (!runId) {
            container.innerHTML = '<p class="suite-extra__lead">请先创建 GEO 回合，再开始真实点名。</p>';
            return;
        }

        const state = {
            runId,
            snapshots: [],
            activeSnapshotId: null,
            detail: null,
            compare: null,
        };

        async function reload() {
            const list = await fetchJson(`/api/geo-runs/${runId}/real-obs/snapshots`);
            state.snapshots = list.items || [];
            if (!state.activeSnapshotId && state.snapshots[0]) {
                state.activeSnapshotId = state.snapshots[0].id;
            }
            if (state.activeSnapshotId) {
                state.detail = await fetchJson(
                    `/api/geo-runs/${runId}/real-obs/snapshots/${state.activeSnapshotId}`
                );
            } else {
                state.detail = null;
            }
            try {
                state.compare = await fetchJson(`/api/geo-runs/${runId}/real-obs/compare`);
            } catch (_) {
                state.compare = null;
            }
            paint();
        }

        function paint() {
            const snap = state.detail && state.detail.snapshot;
            const samples = (state.detail && state.detail.samples) || [];
            const compare = state.compare || {};
            const afterStats = compare.after_stats || {};
            const delta = compare.delta;
            const cards = compare.action_cards || [];
            const hours = snap && snap.hours_since_publish;
            const hoursHint = (hours != null && hours >= 2)
                ? `距确认外发已约 ${hours} 小时（可点名；非自动爬虫）。`
                : (hours != null
                    ? `距确认外发约 ${hours} 小时（流程图建议满 2h 再采，仍可立即点名）。`
                    : '');

            const snapOptions = state.snapshots.map((s) => (
                `<option value="${escapeHtml(s.id)}"${s.id === state.activeSnapshotId ? ' selected' : ''}>`
                + `${escapeHtml(s.phase)} · ${escapeHtml(s.status)} · ${(s.created_at || '').slice(0, 19)}`
                + `</option>`
            )).join('');

            const sampleRows = samples.length
                ? samples.map((s) => (
                    `<tr data-sample-id="${escapeHtml(s.id)}">`
                    + `<td>${escapeHtml(platformLabel(s.platform))}</td>`
                    + `<td><code>${escapeHtml(s.question_id)}</code>`
                    + `<div class="real-obs-q">${escapeHtml((s.question_text || '').slice(0, 72))}</div></td>`
                    + `<td>${s.ok ? '是' : '否'}</td>`
                    + `<td>${s.mention ? '是' : '否'}</td>`
                    + `<td>${s.owned_citation ? '是' : '否'}</td>`
                    + `<td><strong class="${s.strong_adopted ? 'real-obs-yes' : 'real-obs-no'}">`
                    + `${s.strong_adopted ? '强采纳' : '未强采纳'}</strong></td>`
                    + `<td class="real-obs-actions">`
                    + `<button type="button" class="suite-btn suite-btn--ghost real-obs-toggle" data-field="mention" data-val="${s.mention ? '0' : '1'}">改提及</button>`
                    + `<button type="button" class="suite-btn suite-btn--ghost real-obs-toggle" data-field="owned_citation" data-val="${s.owned_citation ? '0' : '1'}">改自有源</button>`
                    + `</td></tr>`
                    + `<tr class="real-obs-detail-row"><td colspan="7">`
                    + `<details><summary>答案 / 引用</summary>`
                    + `<pre class="real-obs-pre">${escapeHtml((s.answer_text || s.error_message || '').slice(0, 2000))}</pre>`
                    + `<div class="real-obs-cites">${(s.citations || []).map((c) => (
                        `<span class="measure-cite-tag">${escapeHtml(c.domain || c.url || '')}</span>`
                    )).join(' ') || '<span class="suite-extra__meta">无引用</span>'}</div>`
                    + `</details></td></tr>`
                )).join('')
                : '<tr><td colspan="7">暂无样本。创建快照后用 scripts/browser-probe 半自动回传。</td></tr>';

            const cardHtml = cards.length
                ? cards.map((c) => (
                    `<article class="real-obs-card">`
                    + `<h4>${escapeHtml(c.title || '')}</h4>`
                    + `<p>${escapeHtml(c.synopsis || '')}</p>`
                    + `<div class="suite-cta-row">${(c.cta || []).map((a) => (
                        `<a class="suite-btn suite-btn--ghost" href="${escapeHtml(a.href || '#')}">${escapeHtml(a.label || '打开')}</a>`
                    )).join('')}</div></article>`
                )).join('')
                : '<p class="suite-extra__meta">暂无归因卡。</p>';

            container.innerHTML = [
                '<div class="real-obs">',
                '<div class="real-obs__banner">',
                '<span class="suite-badge">约定账号网页端点名抽样</span>',
                '<p>不等于全网引用率，也拿不到模型内部检索台账。强采纳 = 本品提及 + 自有域/事实源命中。</p>',
                hoursHint ? `<p class="suite-extra__meta">${escapeHtml(hoursHint)}</p>` : '',
                '</div>',
                '<div class="real-obs__controls">',
                '<label>阶段 <select id="real-obs-phase"><option value="after">改版后 after</option><option value="baseline">改版前 baseline</option></select></label>',
                '<label>已外发时间 <input type="datetime-local" id="real-obs-published"></label>',
                '<label>自有域（逗号分隔） <input type="text" id="real-obs-domains" placeholder="dji.com,example.com" value="dji.com"></label>',
                '<button type="button" class="suite-btn" id="real-obs-start">内容已外发，开始点名</button>',
                '</div>',
                '<div class="real-obs__meta-row">',
                `<label>快照 <select id="real-obs-snap">${snapOptions || '<option value="">（无）</option>'}</select></label>`,
                '<button type="button" class="suite-btn suite-btn--ghost" id="real-obs-refresh">刷新</button>',
                snap
                    ? `<span class="suite-extra__meta">状态 ${escapeHtml(snap.status)} · 平台 ${(snap.platforms || []).map(platformLabel).join(' / ')}</span>`
                    : '',
                '</div>',
                '<section class="measure-kpi-row" aria-label="真实点名 KPI">',
                `<article class="measure-kpi"><span>提及率</span><strong>${fmtPct(afterStats.mention_rate)}</strong>`
                + `<small>after · n=${afterStats.sample_count || 0}</small></article>`,
                `<article class="measure-kpi"><span>自有源命中率</span><strong>${fmtPct(afterStats.owned_citation_rate)}</strong></article>`,
                `<article class="measure-kpi"><span>强采纳率</span><strong>${fmtPct(afterStats.strong_adopted_rate)}</strong>`
                + (delta ? `<small>Δ提及 ${fmtPct(delta.mention_rate)}</small>` : '')
                + '</article>',
                '</section>',
                '<div class="real-obs__table-wrap"><table class="real-obs-table"><thead><tr>',
                '<th>平台</th><th>问法</th><th>成功</th><th>提及</th><th>自有源</th><th>强采纳</th><th>改标</th>',
                '</tr></thead><tbody>',
                sampleRows,
                '</tbody></table></div>',
                snap
                    ? `<p class="suite-extra__meta">CLI：<code>python scripts/browser-probe/run_probe.py --api http://127.0.0.1:8010 --run-id ${escapeHtml(runId)} --snapshot-id ${escapeHtml(snap.id)}</code></p>`
                    : '',
                '<section class="real-obs__cards"><h3>归因卡</h3>',
                cardHtml,
                '</section>',
                opts.doneStep && Workflow
                    ? `<div class="suite-cta-row"><button type="button" class="suite-btn" data-measure-done>${escapeHtml(opts.doneLabel || '标记观测完成')}</button></div>`
                    : '',
                '</div>',
            ].join('');

            container.querySelector('#real-obs-refresh')?.addEventListener('click', () => {
                reload().catch((e) => {
                    container.innerHTML = `<p class="suite-extra__lead">刷新失败：${escapeHtml(e.message || e)}</p>`;
                });
            });
            container.querySelector('#real-obs-snap')?.addEventListener('change', (ev) => {
                state.activeSnapshotId = ev.target.value || null;
                reload().catch(() => null);
            });
            container.querySelector('#real-obs-start')?.addEventListener('click', async () => {
                const phase = container.querySelector('#real-obs-phase')?.value || 'after';
                const domainsRaw = container.querySelector('#real-obs-domains')?.value || '';
                const domains = domainsRaw.split(/[,，\s]+/).map((s) => s.trim()).filter(Boolean);
                const pubInput = container.querySelector('#real-obs-published')?.value;
                let published_at = null;
                if (pubInput) {
                    const d = new Date(pubInput);
                    if (!Number.isNaN(d.getTime())) published_at = d.toISOString();
                }
                try {
                    const created = await postJson(`/api/geo-runs/${runId}/real-obs/snapshots`, {
                        phase,
                        platforms: ['doubao', 'yuanbao', 'deepseek'],
                        owned_domains: domains.length ? domains : undefined,
                        published_at,
                    });
                    state.activeSnapshotId = created.snapshot && created.snapshot.id;
                    await reload();
                } catch (err2) {
                    alert('创建快照失败：' + (err2.message || err2));
                }
            });

            container.querySelectorAll('.real-obs-toggle').forEach((btn) => {
                btn.addEventListener('click', async () => {
                    const tr = btn.closest('tr[data-sample-id]');
                    const sampleId = tr && tr.getAttribute('data-sample-id');
                    if (!sampleId) return;
                    const field = btn.getAttribute('data-field');
                    const val = btn.getAttribute('data-val') === '1';
                    const body = {};
                    body[field] = val;
                    try {
                        await patchJson(`/api/geo-runs/${runId}/real-obs/samples/${sampleId}`, body);
                        await reload();
                    } catch (error) {
                        alert(error.message || error);
                    }
                });
            });

            const doneBtn = container.querySelector('[data-measure-done]');
            if (doneBtn && Workflow) {
                doneBtn.addEventListener('click', () => {
                    Workflow.markComplete(opts.doneStep || 'measure');
                    Workflow.handoff?.(opts.doneStep || 'measure', {
                        meta: {
                            observation_kind: 'real_obs',
                            snapshot_id: state.activeSnapshotId,
                        },
                    }).catch(() => null);
                    doneBtn.textContent = '已标记完成';
                    doneBtn.disabled = true;
                });
            }
        }

        container.innerHTML = '<p class="suite-extra__lead">加载真实点名…</p>';
        try {
            await reload();
        } catch (error) {
            container.innerHTML = `<p class="suite-extra__lead">真实点名加载失败：${escapeHtml(error.message || error)}</p>`;
        }
    }

    async function renderMeasure(container) {
        const Workflow = global.GEOrank?.SuiteWorkflow;
        const runId = Workflow?.getRunId?.();
        container.innerHTML = [
            '<div class="measure-tabs" data-measure-tabs>',
            '<div class="measure-tabs__bar" role="tablist">',
            '<button type="button" class="measure-tabs__btn is-active" data-measure-tab="demo" role="tab">演示观测</button>',
            '<button type="button" class="measure-tabs__btn" data-measure-tab="real" role="tab">真实点名</button>',
            '</div>',
            '<p class="suite-extra__meta measure-tabs__hint">演示视图为方法剧本（非实测）；真实点名为约定账号网页端抽样。</p>',
            '<div class="measure-tabs__pane" data-measure-pane="demo"></div>',
            '<div class="measure-tabs__pane" data-measure-pane="real" hidden></div>',
            '</div>',
        ].join('');

        const demoPane = container.querySelector('[data-measure-pane="demo"]');
        const realPane = container.querySelector('[data-measure-pane="real"]');
        let realMounted = false;

        async function showTab(name) {
            container.querySelectorAll('.measure-tabs__btn').forEach((b) => {
                b.classList.toggle('is-active', b.getAttribute('data-measure-tab') === name);
            });
            if (demoPane) demoPane.hidden = name !== 'demo';
            if (realPane) realPane.hidden = name !== 'real';
            if (name === 'real' && realPane && !realMounted) {
                realMounted = true;
                await mountRealObs(realPane, {
                    runId,
                    doneStep: 'measure',
                    doneLabel: '标记观测完成',
                });
            }
        }

        container.querySelectorAll('.measure-tabs__btn').forEach((btn) => {
            btn.addEventListener('click', () => {
                showTab(btn.getAttribute('data-measure-tab') || 'demo').catch((e) => {
                    console.warn('[suite-extra] tab switch failed', e);
                });
            });
        });

        try {
            await mountGeoObserve(demoPane, {
                runId,
                doneStep: 'measure',
                doneLabel: '标记观测完成',
            });
            if (demoPane && !demoPane.querySelector('.obs-monitor, .measure-monitor')) {
                try {
                    const latest = await fetchJson('/api/admin/trust-obs/runs/latest');
                    if (latest && latest.run) {
                        renderMeasurePayload(demoPane, latest);
                    } else {
                        const demo = await fetchJson('/pilot-demo/geo-demo-column/measure-demo.json');
                        renderMeasurePayload(demoPane, demo);
                    }
                } catch (_) {
                    const demo = await fetchJson('/pilot-demo/geo-demo-column/measure-demo.json');
                    renderMeasurePayload(demoPane, demo);
                }
            }
        } catch (error) {
            console.warn('[suite-extra] mountGeoObserve failed', error);
            try {
                const demo = await fetchJson('/pilot-demo/geo-demo-column/measure-demo.json');
                renderMeasurePayload(demoPane, demo);
            } catch (err2) {
                if (demoPane) {
                    demoPane.innerHTML = `<p class="suite-extra__lead">演示观测加载失败：${escapeHtml(err2.message || err2)}</p>`;
                }
            }
        }
    }

    var _extraRenderGen = 0;

    async function renderExtraPanel(stepId, container) {
        if (!container) return;
        const suiteOnly = stepId === 'knowledge'
            || stepId === 'distribute'
            || stepId === 'trust_asset'
            || stepId === 'measure';
        if (!suiteOnly) {
            container.hidden = true;
            container.innerHTML = '';
            container.dataset.renderedStep = '';
            return;
        }
        const gen = ++_extraRenderGen;
        container.hidden = false;
        const sameStepReady = container.dataset.renderedStep === stepId
            && container.querySelector('.measure-tabs, .measure-monitor:not(.measure-monitor--loading), .suite-extra__lead, .suite-cta-row');
        // 同一步重复 refresh 时勿清空已渲染内容，避免「加载中」卡死
        if (!sameStepReady) {
            if (stepId === 'measure' || stepId === 'obs' || stepId === 'trustobs' || stepId === 'measurement') {
                container.innerHTML = '<div class="measure-monitor measure-monitor--loading"><div class="measure-toolbar"><span class="suite-badge">加载中</span><span class="measure-toolbar__hint">正在加载观测数据…</span></div><div class="measure-kpi-row"><div class="measure-kpi skeleton"></div><div class="measure-kpi skeleton"></div><div class="measure-kpi skeleton"></div></div></div>';
            } else {
                container.innerHTML = '<p class="suite-extra__lead">加载中…</p>';
            }
        }
        try {
            if (stepId === 'knowledge') await renderKnowledge(container);
            else if (stepId === 'distribute') await renderDistribute(container);
            else if (stepId === 'trust_asset') await renderTrustAsset(container);
            else await renderMeasure(container);
            if (gen !== _extraRenderGen) return;
            container.dataset.renderedStep = stepId;
        } catch (error) {
            if (gen !== _extraRenderGen) return;
            container.dataset.renderedStep = '';
            container.innerHTML = `<p class="suite-extra__lead">面板加载失败：${error.message || error}</p>`;
        }
    }

    global.GEOrank = global.GEOrank || {};
    global.GEOrank.SuiteExtra = {
        renderExtraPanel: renderExtraPanel,
        mountGeoObserve: mountGeoObserve,
        mountRealObs: mountRealObs,
        DEMO_KB: DEMO_KB,
        geoflowBase: geoflowBase,
        geoflowUrl: geoflowUrl,
        isNative: isNative,
        contentBackend: contentBackend,
    };
})(window);
