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

    async function fetchJson(url) {
        const response = await fetch(url, { credentials: 'same-origin' });
        if (!response.ok) throw new Error(`加载失败 ${response.status}`);
        return response.json();
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
        const badge = native ? 'native-python' : 'legacy-flow';
        const sources = (metrics && metrics.sources_note)
            || '事实来自大疆官网产品页/技术参数/FAQ，非官方合作包';
        const cards = metrics && Array.isArray(metrics.cards) ? metrics.cards : [];
        const adminUrl = native
            ? (demo && demo.admin_path) || nativeAdminUrl()
            : geoflowUrl(`/geo_admin/knowledge-bases/${(metrics && metrics.kb_id) || DEMO_KB.kbId}/detail`);
        const listUrl = native ? nativeAdminUrl() : geoflowUrl('/geo_admin/knowledge-bases');
        const ready = demo && demo.demo_ready;
        const kbStats = demo && demo.knowledge_base;

        container.innerHTML = [
            `<div class="suite-extra__head">`,
            `<h3>${escapeHtml(entity)} · 事实卡看板</h3>`,
            `<span class="suite-badge suite-badge--accent">${escapeHtml(badge)}</span>`,
            `</div>`,
            `<p class="suite-extra__lead">`,
            `<strong>${escapeHtml(kbName)}</strong>`,
            native
                ? ` · Rank 内容引擎${ready ? '已导入' : '待导入'} · 切片/JSONB 向量`
                : ` · GEOFlow KB #${escapeHtml((metrics && metrics.kb_id) || DEMO_KB.kbId)}`,
            ` · 包路径 <code>${escapeHtml(DEMO_KB.docsPath)}</code>`,
            `</p>`,
            `<p class="suite-extra__meta">${escapeHtml(sources)}</p>`,
            `<div class="suite-metric-grid">`,
            kbStats
                ? [
                    `<div class="suite-metric"><strong>${kbStats.doc_count ?? 0}</strong><span>文档</span></div>`,
                    `<div class="suite-metric"><strong>${kbStats.chunk_count ?? 0}</strong><span>切片</span></div>`,
                    `<div class="suite-metric"><strong>${kbStats.vectorized_count ?? 0}</strong><span>已向量</span></div>`,
                    `<div class="suite-metric"><strong>${ready ? '就绪' : '待导入'}</strong><span>演示包</span></div>`,
                ].join('')
                : [
                    `<div class="suite-metric"><strong>${pct(metrics?.coverage?.rate)}</strong><span>事实卡覆盖率</span><small>${metrics?.coverage?.approved_cards || 0}/${metrics?.coverage?.checklist_total || 0}</small></div>`,
                    `<div class="suite-metric"><strong>${pct(metrics?.embedding?.rate)}</strong><span>切片向量化率</span><small>${metrics?.embedding?.chunk_embedded || 0}/${metrics?.embedding?.chunk_total || 0}</small></div>`,
                    `<div class="suite-metric"><strong>${pct(metrics?.evidence_production?.rate)}</strong><span>带证据生产比例</span></div>`,
                    `<div class="suite-metric"><strong>${metrics?.prompt_library_count ?? 5}</strong><span>产品提示词</span></div>`,
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
                : (ready
                    ? `<p class="suite-extra__meta">已从 Rank 导入演示知识库；打开内容引擎可检索切片。</p>`
                    : `<p class="suite-extra__meta">尚未导入：请管理员在内容引擎点击「导入 DJI 演示包」。</p>`),
            `<div class="suite-cta-row suite-cta-row--compact">`,
            `<a class="suite-btn suite-btn--primary" href="${escapeHtml(adminUrl)}" ${native ? '' : 'target="_blank" rel="noreferrer"'}>${native ? '打开内容引擎' : '打开 KB 详情'}</a>`,
            `<a class="suite-btn suite-btn--ghost" href="${escapeHtml(listUrl)}" ${native ? '' : 'target="_blank" rel="noreferrer"'}>${native ? '管理知识库' : '知识库列表'}</a>`,
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
            : `<p class="suite-extra__meta">暂无任务草稿。请在内容引擎新建任务（绑 KB + 提示词）生成。</p>`;

        if (native) {
            container.innerHTML = [
                `<div class="suite-extra__head">`,
                `<h3>分发（Rank 原生）</h3>`,
                `<span class="suite-badge suite-badge--accent">native-python</span>`,
                `</div>`,
                `<p class="suite-extra__lead">`,
                `在 <strong>内容引擎</strong> 新建任务：选中国生态提示词并绑定「${escapeHtml(DEMO_KB.kbName)}」，生成答案优先草稿，再登记渠道 / 模板 key。`,
                `</p>`,
                `<ol class="suite-demo-list suite-extra__steps">`,
                `<li>打开内容引擎 → 任务</li>`,
                `<li>提示词：中国生态 5 条之一</li>`,
                `<li>知识库：绑定 DJI 演示包</li>`,
                `<li>生成草稿（同步；无 LLM 时本地降级）</li>`,
                `<li>渠道页登记模板 key；标记已分发</li>`,
                `</ol>`,
                taskList,
                `<div class="suite-cta-row suite-cta-row--compact">`,
                `<a class="suite-btn suite-btn--primary" href="${escapeHtml(tasksUrl)}">打开内容引擎任务</a>`,
                `<a class="suite-btn suite-btn--ghost" href="${escapeHtml(detailUrl)}">核对知识库</a>`,
                `<a class="suite-btn suite-btn--ghost" href="${escapeHtml(distUrl)}">渠道 / 模板</a>`,
                `</div>`,
                `<p class="suite-extra__meta">验收路径不经 Laravel；包路径 <code>${escapeHtml(DEMO_KB.docsPath)}</code></p>`,
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
            `<li>提示词：中国生态 5 条之一</li>`,
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
        const native = isNative();
        const kbUrl = native ? nativeAdminUrl() : geoflowUrl(DEMO_KB.defaultDetailPath);
        container.innerHTML = [
            `<div class="suite-extra__head">`,
            `<h3>L3 信任素材（次要）</h3>`,
            `<span class="suite-badge">样板 · 不阻塞 L2</span>`,
            `</div>`,
            `<p class="suite-extra__lead">主演示走 DJI Mini 5 Pro 知识库与任务绑定。</p>`,
            `<div class="suite-cta-row suite-cta-row--compact">`,
            `<a class="suite-btn suite-btn--primary" href="${escapeHtml(kbUrl)}" ${native ? '' : 'target="_blank" rel="noreferrer"'}>打开推荐 KB</a>`,
            `<a class="suite-btn suite-btn--ghost" href="/pilot-demo/geo-demo-column/trust-asset.html" target="_blank" rel="noreferrer">打开 L3 样板全文</a>`,
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
            `<header class="measure-monitor__head">`,
            `<div>`,
            `<p class="measure-eyebrow">Suite · 步骤 5 观测</p>`,
            `<h2>AI 答案监测</h2>`,
            `<p class="measure-lead">监测 AI 回答中的品牌提及与引用来源，评估可见性与可信度表现。</p>`,
            `</div>`,
            `<div class="measure-monitor__tools">`,
            `<span class="suite-badge">${escapeHtml(meta.badge)}</span>`,
            `<select id="mf-range" aria-label="时间范围"><option>近 7 天</option><option selected>近 30 天</option></select>`,
            `<select id="mf-platform" aria-label="平台"><option selected>全部平台</option><option>豆包</option><option>文心一言</option><option>通义</option></select>`,
            `<button type="button" class="cockpit-btn cockpit-btn--primary" id="mf-apply">应用筛选</button>`,
            `</div>`,
            `</header>`,

            `<section class="measure-kpi-row" aria-label="观测 KPI">`,
            `<article class="measure-kpi">`,
            `<span class="measure-kpi__icon measure-kpi__icon--blue material-symbols-outlined">monitoring</span>`,
            `<div><strong id="mk-q">${questionCount}</strong><span>监测问题</span></div>`,
            `<small>个问题</small>`,
            `</article>`,
            `<article class="measure-kpi">`,
            `<span class="measure-kpi__icon measure-kpi__icon--green material-symbols-outlined">verified</span>`,
            `<div><strong id="mk-m">${mentionKpi}</strong><span>本期提及</span></div>`,
            `<small>次 · 样本 ${agg.total_samples ?? '--'}</small>`,
            `</article>`,
            `<article class="measure-kpi">`,
            `<span class="measure-kpi__icon measure-kpi__icon--orange material-symbols-outlined">track_changes</span>`,
            `<div><strong id="mk-t">${trustKpi}</strong><span>平均来源可信度</span></div>`,
            `<small>/100</small>`,
            `</article>`,
            `</section>`,

            `<div class="measure-body-grid">`,
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

            `<section class="measure-panel measure-answer">`,
            `<div class="measure-panel__head">`,
            `<h3>答案占位</h3>`,
            `<span class="measure-ai-badge">AI</span>`,
            `</div>`,
            `<p class="measure-answer__q" id="measure-answer-q"></p>`,
            `<p class="measure-answer__meta" id="measure-answer-meta"></p>`,
            `<div class="measure-answer__box" id="measure-answer-body"></div>`,
            `<div class="measure-answer__cites">`,
            `<span class="measure-answer__cites-label">引用证据</span>`,
            `<div id="measure-answer-cites"></div>`,
            `</div>`,
            `</section>`,

            `<aside class="measure-right-col">`,
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
            `<p class="cockpit-muted">按引用域名权威度与官网命中加权的演示评分。</p>`,
            `</section>`,
            `</aside>`,
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
            `<p class="suite-extra__meta">${escapeHtml(payload.method_note || payload.message || '')} `
            + `探针：<code>${escapeHtml(DEMO_KB.docsPath)}probe-questions.md</code></p>`,
            `<div class="suite-cta-row suite-cta-row--compact">`,
            `<button type="button" class="suite-btn suite-btn--primary" data-measure-done="1">标记观测完成</button>`,
            `<a class="suite-btn suite-btn--ghost" href="/admin/trust-obs">打开可信观测后台</a>`,
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
                    note.textContent = `已应用本地筛选壳：${plat}（演示 UI，不请求新采样）`;
                }
            });
        }

        const addBtn = container.querySelector('#measure-add-q');
        if (addBtn) {
            addBtn.addEventListener('click', () => {
                addBtn.textContent = '+ 演示模式：请在可信观测后台配置探针';
            });
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

    async function renderMeasure(container) {
        try {
            const latest = await fetchJson('/api/admin/trust-obs/runs/latest');
            if (latest && latest.run) {
                renderMeasurePayload(container, latest);
                return;
            }
        } catch (error) {
            console.warn('[suite-extra] latest run failed', error);
        }
        const demo = await fetchJson('/pilot-demo/geo-demo-column/measure-demo.json');
        renderMeasurePayload(container, demo);
    }

    async function renderExtraPanel(stepId, container) {
        if (!container) return;
        const suiteOnly = stepId === 'knowledge'
            || stepId === 'distribute'
            || stepId === 'trust_asset'
            || stepId === 'measure';
        if (!suiteOnly) {
            container.hidden = true;
            container.innerHTML = '';
            return;
        }
        container.hidden = false;
        container.innerHTML = '<p class="suite-extra__lead">加载中…</p>';
        try {
            if (stepId === 'knowledge') await renderKnowledge(container);
            else if (stepId === 'distribute') await renderDistribute(container);
            else if (stepId === 'trust_asset') await renderTrustAsset(container);
            else await renderMeasure(container);
        } catch (error) {
            container.innerHTML = `<p class="suite-extra__lead">面板加载失败：${error.message || error}</p>`;
        }
    }

    global.GEOrank = global.GEOrank || {};
    global.GEOrank.SuiteExtra = {
        renderExtraPanel: renderExtraPanel,
        DEMO_KB: DEMO_KB,
        geoflowBase: geoflowBase,
        geoflowUrl: geoflowUrl,
        isNative: isNative,
        contentBackend: contentBackend,
    };
})(window);
