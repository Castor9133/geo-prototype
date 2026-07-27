/**
 * Suite 扩展步：事实卡 / 信任素材 / 分发指引 / 可信观测只读面板
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
    };

    function geoflowBase() {
        var status = global.GEOrank && global.GEOrank._suiteIntegrationStatus;
        var base = (status && status.public_base_url) || DEMO_KB.defaultBase;
        return String(base).replace(/\/$/, '');
    }

    function geoflowUrl(path) {
        return geoflowBase() + path;
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
        const data = await fetchJson(DEMO_KB.metricsUrl);
        const cards = Array.isArray(data.cards) ? data.cards : [];
        const kbId = data.kb_id || DEMO_KB.kbId;
        const detailUrl = data.admin_detail_url
            || geoflowUrl(`/geo_admin/knowledge-bases/${kbId}/detail`);
        const entity = data.entity_name || DEMO_KB.entity;
        const kbName = data.kb_name || DEMO_KB.kbName;
        const badge = data.demo_data ? '演示数据' : '推荐演示包';
        const sources = data.sources_note
            || '事实来自大疆官网产品页/技术参数/FAQ，非官方合作包';

        container.innerHTML = [
            `<div class="suite-extra__head">`,
            `<h3>${escapeHtml(entity)} · 事实卡看板</h3>`,
            `<span class="suite-badge suite-badge--accent">${escapeHtml(badge)}</span>`,
            `</div>`,
            `<p class="suite-extra__lead">`,
            `<strong>${escapeHtml(kbName)}</strong>（GEOFlow KB #${escapeHtml(kbId)}）`,
            ` · ${escapeHtml(data.label || '已导入并向量化')}`,
            ` · 内容工程：事实卡覆盖 → 向量化 → 带证据生产`,
            `</p>`,
            `<p class="suite-extra__meta">${escapeHtml(sources)} · 包路径 <code>${escapeHtml(DEMO_KB.docsPath)}</code></p>`,
            `<div class="suite-metric-grid">`,
            `<div class="suite-metric"><strong>${pct(data.coverage?.rate)}</strong><span>事实卡覆盖率</span><small>${data.coverage?.approved_cards || 0}/${data.coverage?.checklist_total || 0}</small></div>`,
            `<div class="suite-metric"><strong>${pct(data.embedding?.rate)}</strong><span>切片向量化率</span><small>${data.embedding?.chunk_embedded || 0}/${data.embedding?.chunk_total || 0}</small></div>`,
            `<div class="suite-metric"><strong>${pct(data.evidence_production?.rate)}</strong><span>带证据生产比例</span><small>${data.evidence_production?.articles_with_citations || 0}/${data.evidence_production?.articles_total || 0}</small></div>`,
            `<div class="suite-metric"><strong>${data.prompt_library_count ?? 10}</strong><span>产品提示词</span><small>探针题 ${data.probe_question_count ?? 13}</small></div>`,
            `</div>`,
            `<ul class="suite-fact-list">`,
            ...cards.slice(0, 8).map((card) => (
                `<li><code>${escapeHtml(card.fact_id || '')}</code> ${escapeHtml(card.claim || '')}</li>`
            )),
            cards.length > 8
                ? `<li class="suite-extra__meta">…另有 ${cards.length - 8} 条，详见 Flow KB 详情</li>`
                : '',
            `</ul>`,
            `<div class="suite-cta-row suite-cta-row--compact">`,
            `<a class="suite-btn suite-btn--primary" href="${escapeHtml(detailUrl)}" target="_blank" rel="noreferrer">打开 KB #${escapeHtml(kbId)} 详情</a>`,
            `<a class="suite-btn suite-btn--ghost" href="${escapeHtml(geoflowUrl('/geo_admin/knowledge-bases'))}" target="_blank" rel="noreferrer">知识库列表</a>`,
            `</div>`,
            `<p class="suite-extra__meta suite-extra__meta--muted">旧包仅作对照：飞书多维表格（cn-product-demo）与合成栏目（geo-demo-column）已不推荐作主演示。</p>`,
        ].join('');
    }

    async function renderDistribute(container) {
        const detailUrl = geoflowUrl(DEMO_KB.defaultDetailPath);
        const tasksUrl = geoflowUrl(DEMO_KB.tasksPath);
        const distUrl = geoflowUrl('/geo_admin/distribution');

        container.innerHTML = [
            `<div class="suite-extra__head">`,
            `<h3>分发操作指引（按实际）</h3>`,
            `<span class="suite-badge suite-badge--accent">绑定 KB #${DEMO_KB.kbId}</span>`,
            `</div>`,
            `<p class="suite-extra__lead">`,
            `不要沿用旧拓词移交（如「哪家 GEO 优化公司好」）。演示请在 Flow <strong>任务中心新建任务</strong>，`,
            `选中国生态提示词并<strong>绑定「${escapeHtml(DEMO_KB.kbName)}」（KB #${DEMO_KB.kbId}）</strong>，`,
            `再生成答案优先正文、选渠道/模板。`,
            `</p>`,
            `<ol class="suite-demo-list suite-extra__steps">`,
            `<li>打开任务中心 → <strong>新建任务</strong></li>`,
            `<li>提示词：中国生态 5 条之一（DeepSeek 七段 / 微信专栏 / 豆包 FAQ+EEAT / 评测对比 / 白帽避坑）</li>`,
            `<li>知识库：绑定 <code>${escapeHtml(DEMO_KB.kbName)}</code>（id=${DEMO_KB.kbId}）</li>`,
            `<li>生成正文：首屏 80–150 字答案块 + 证据引用</li>`,
            `<li>再选分发渠道 / 模板；观测用 Mini 5 Pro 探针题</li>`,
            `</ol>`,
            `<div class="suite-cta-row suite-cta-row--compact">`,
            `<a class="suite-btn suite-btn--primary" href="${escapeHtml(tasksUrl)}" target="_blank" rel="noreferrer">打开任务中心新建</a>`,
            `<a class="suite-btn suite-btn--ghost" href="${escapeHtml(detailUrl)}" target="_blank" rel="noreferrer">核对 KB #${DEMO_KB.kbId}</a>`,
            `<a class="suite-btn suite-btn--ghost" href="${escapeHtml(distUrl)}" target="_blank" rel="noreferrer">分发渠道</a>`,
            `</div>`,
            `<p class="suite-extra__meta">包路径 <code>${escapeHtml(DEMO_KB.docsPath)}</code> · 拓词页「发送到 GEOFlow」若仍是旧词包，演示时请忽略，改走上方新建流程。</p>`,
        ].join('');
    }

    async function renderTrustAsset(container) {
        container.innerHTML = [
            `<div class="suite-extra__head">`,
            `<h3>L3 信任素材（次要）</h3>`,
            `<span class="suite-badge">样板 · 不阻塞 L2</span>`,
            `</div>`,
            `<p class="suite-extra__lead">主演示走 DJI Mini 5 Pro 知识库与任务绑定。L3 样板仍可用合成栏目图文骨架对照「人共鸣 + 模型可读」。</p>`,
            `<ul class="suite-fact-list">`,
            `<li>主路径实体：${escapeHtml(DEMO_KB.entity)}（KB #${DEMO_KB.kbId}）</li>`,
            `<li>对照样板：GEO 示范栏目（geo-demo-column）</li>`,
            `<li>边界：不承诺操控或保证进入全部模型答案</li>`,
            `</ul>`,
            `<div class="suite-cta-row suite-cta-row--compact">`,
            `<a class="suite-btn suite-btn--primary" href="${escapeHtml(geoflowUrl(DEMO_KB.defaultDetailPath))}" target="_blank" rel="noreferrer">打开推荐 KB</a>`,
            `<a class="suite-btn suite-btn--ghost" href="/pilot-demo/geo-demo-column/trust-asset.html" target="_blank" rel="noreferrer">打开 L3 样板全文</a>`,
            `</div>`,
        ].join('');
    }

    function renderMeasurePayload(container, payload) {
        const run = payload.run || {};
        const agg = run.aggregate || {};
        const demo = Boolean(payload.demo_data);
        container.innerHTML = [
            `<div class="suite-extra__head">`,
            `<h3>可信观测 · 最新一轮</h3>`,
            `<span class="suite-badge">${payload.badge || 'API 自动采样（非网页抓取）'}</span>`,
            `</div>`,
            `<p class="suite-extra__lead">${payload.method_note || payload.message || ''}${demo ? '（当前为演示回落数据）' : ''}</p>`,
            `<div class="suite-metric-grid">`,
            `<div class="suite-metric"><strong>${agg.mention ?? '--'}</strong><span>mention</span></div>`,
            `<div class="suite-metric"><strong>${agg.citation ?? '--'}</strong><span>citation</span></div>`,
            `<div class="suite-metric"><strong>${agg.absent ?? '--'}</strong><span>absent</span></div>`,
            `<div class="suite-metric"><strong>${agg.total_samples ?? '--'}</strong><span>样本数</span></div>`,
            `</div>`,
            `<p class="suite-extra__meta">口径：${run.locale || 'zh-CN'} · ${run.device || 'api'} · ${run.login_state || 'api-key'} · ${run.prompt_version || 'probe-v1'} · 模型 ${run.model_name || '--'}</p>`,
            `<p class="suite-extra__meta">演示探针请用 <code>${escapeHtml(DEMO_KB.docsPath)}probe-questions.md</code>（Mini 5 Pro），勿沿用旧 GEO 公司词包题。</p>`,
            `<div class="suite-cta-row suite-cta-row--compact">`,
            `<a class="suite-btn suite-btn--primary" href="/admin/trust-obs">打开可信观测后台</a>`,
            `</div>`,
        ].join('');
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
    };
})(window);
