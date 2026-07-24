/**
 * Suite 扩展步：事实卡 / 信任素材 / 可信观测只读面板
 */
(function (global) {
    'use strict';

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

    async function renderKnowledge(container) {
        const data = await fetchJson('/pilot-demo/geo-demo-column/metrics.json');
        const cards = Array.isArray(data.cards) ? data.cards : [];
        container.innerHTML = [
            `<div class="suite-extra__head">`,
            `<h3>GEO 示范栏目 · 事实卡看板</h3>`,
            `<span class="suite-badge">${data.demo_data ? '演示数据' : '实测数据'}</span>`,
            `</div>`,
            `<p class="suite-extra__lead">${data.label || '知识工程资产只读视图'}</p>`,
            `<div class="suite-metric-grid">`,
            `<div class="suite-metric"><strong>${pct(data.coverage?.rate)}</strong><span>事实卡覆盖率</span><small>${data.coverage?.approved_cards || 0}/${data.coverage?.checklist_total || 0}</small></div>`,
            `<div class="suite-metric"><strong>${pct(data.embedding?.rate)}</strong><span>切片向量化率</span><small>${data.embedding?.chunk_embedded || 0}/${data.embedding?.chunk_total || 0}</small></div>`,
            `<div class="suite-metric"><strong>${pct(data.evidence_production?.rate)}</strong><span>带证据生产比例</span><small>${data.evidence_production?.articles_with_citations || 0}/${data.evidence_production?.articles_total || 0}</small></div>`,
            `</div>`,
            `<ul class="suite-fact-list">`,
            ...cards.map((card) => `<li><code>${card.fact_id || ''}</code> ${card.claim || ''}</li>`),
            `</ul>`,
            `<div class="suite-cta-row suite-cta-row--compact">`,
            `<a class="suite-btn suite-btn--ghost" href="/docs-not-served" onclick="return false;" hidden></a>`,
            `<a class="suite-btn suite-btn--ghost" href="http://localhost:18080/geo_admin" target="_blank" rel="noreferrer">打开 GEOFlow 知识库</a>`,
            `</div>`,
        ].join('');
    }

    async function renderTrustAsset(container) {
        container.innerHTML = [
            `<div class="suite-extra__head">`,
            `<h3>L3 信任素材样板</h3>`,
            `<span class="suite-badge">图文 · 非视频管线</span>`,
            `</div>`,
            `<p class="suite-extra__lead">人共鸣 + 模型可读：章节、实体对齐、口述要点、事实卡锚点。骨架来自 L2 事实卡。</p>`,
            `<ul class="suite-fact-list">`,
            `<li>实体：GEO 示范栏目</li>`,
            `<li>证据锚点：col-demo-f-001 ~ f-004</li>`,
            `<li>边界：不承诺操控或保证进入全部模型答案</li>`,
            `</ul>`,
            `<div class="suite-cta-row suite-cta-row--compact">`,
            `<a class="suite-btn suite-btn--primary" href="/pilot-demo/geo-demo-column/trust-asset.html" target="_blank" rel="noreferrer">打开样板全文</a>`,
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
        const suiteOnly = stepId === 'knowledge' || stepId === 'trust_asset' || stepId === 'measure';
        if (!suiteOnly) {
            container.hidden = true;
            container.innerHTML = '';
            return;
        }
        container.hidden = false;
        container.innerHTML = '<p class="suite-extra__lead">加载中…</p>';
        try {
            if (stepId === 'knowledge') await renderKnowledge(container);
            else if (stepId === 'trust_asset') await renderTrustAsset(container);
            else await renderMeasure(container);
        } catch (error) {
            container.innerHTML = `<p class="suite-extra__lead">面板加载失败：${error.message || error}</p>`;
        }
    }

    global.GEOrank = global.GEOrank || {};
    global.GEOrank.SuiteExtra = { renderExtraPanel };
})(window);
