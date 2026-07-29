document.addEventListener('DOMContentLoaded', async () => {
    const Workflow = window.GEOrank?.SuiteWorkflow;
    const statusEl = document.getElementById('suite-status');
    const statusText = document.getElementById('suite-status-text');
    const openGeoflow = document.getElementById('suite-open-geoflow');
    const integrationCopy = document.getElementById('suite-integration-copy');
    const nextStepsEl = document.getElementById('suite-next-steps');
    const stepperEl = document.getElementById('suite-stepper');
    const progressBar = document.getElementById('suite-progress-bar');
    const progressLabel = document.getElementById('suite-progress-label');
    const startCta = document.getElementById('suite-start-cta');
    const continueCta = document.getElementById('suite-continue-cta');
    const resetBtn = document.getElementById('suite-reset-workflow');
    const stepIcon = document.getElementById('suite-step-icon');
    const stepEyebrow = document.getElementById('suite-step-eyebrow');
    const stepTitle = document.getElementById('suite-step-title');
    const stepDesc = document.getElementById('suite-step-desc');
    const stepActions = document.getElementById('suite-step-actions');
    const stepState = document.getElementById('suite-step-state');
    const stepNote = document.getElementById('suite-step-note');
    const lastHandoffCard = document.getElementById('suite-last-handoff');
    const handoffMode = document.getElementById('suite-handoff-mode');
    const handoffMessage = document.getElementById('suite-handoff-message');
    const handoffMeta = document.getElementById('suite-handoff-meta');
    const handoffActions = document.getElementById('suite-handoff-actions');

    const DEMO_KB = window.GEOrank?.SuiteExtra?.DEMO_KB || {
        kbId: 9,
        kbName: '中文产品演示包·DJI Mini 5 Pro',
        entity: 'DJI Mini 5 Pro',
        docsPath: 'docs/pilot-demo/cn-product-demo-v2/',
        defaultDetailPath: '/geo_admin/knowledge-bases/9/detail',
        tasksPath: '/geo_admin/tasks',
        defaultBase: 'http://localhost:18080',
    };

    let integrationStatus = null;
    let contentBackend = { mode: 'native-python', native: true, admin_path: '/admin/content-engine', public_path: '/knowledge' };
    let activeStepId = 'diagnostic';

    if (!Workflow) {
        console.error('[suite] SuiteWorkflow missing');
        return;
    }

    function isNative() {
        return contentBackend.native === true || contentBackend.mode === 'native-python';
    }

    function nativeAdminPath() {
        return contentBackend.admin_path || '/admin/content-engine';
    }

    function nativePublicPath() {
        return contentBackend.public_path || contentBackend.materials_path || '/knowledge';
    }

    function geoflowBase() {
        if (window.GEOrank?.SuiteExtra?.geoflowBase) {
            return window.GEOrank.SuiteExtra.geoflowBase();
        }
        const base = (integrationStatus && integrationStatus.public_base_url) || DEMO_KB.defaultBase;
        return String(base).replace(/\/$/, '');
    }

    function geoflowUrl(path) {
        return geoflowBase() + path;
    }

    function knowledgeHref() {
        return isNative() ? nativePublicPath() : geoflowUrl(DEMO_KB.defaultDetailPath);
    }

    function distributeHref() {
        if (!isNative()) return geoflowUrl(DEMO_KB.tasksPath);
        return '/distribute';
    }

    function readStepFromUrl() {
        const params = new URLSearchParams(window.location.search);
        return Workflow.normalizeStepId(params.get('step'));
    }

    function writeStepToUrl(stepId, replace) {
        const url = new URL(window.location.href);
        url.searchParams.set('step', stepId);
        const method = replace ? 'replaceState' : 'pushState';
        window.history[method]({ suiteStep: stepId }, '', url.pathname + url.search);
    }

    function formatTime(iso) {
        if (!iso) return '';
        try {
            return new Date(iso).toLocaleString('zh-CN', { hour12: false });
        } catch (error) {
            return iso;
        }
    }

    function isDemoAlignedHandoff(record) {
        const blob = [
            record?.task_name,
            record?.message,
            record?.preview?.task_name,
            JSON.stringify(record?.preview || {}),
        ].join(' ').toLowerCase();
        if (!blob.trim()) return false;
        if (/mini\s*5|dji|大疆|航拍|mini5/.test(blob)) return true;
        if (/geo\s*优化|哪家.*公司|哪家 geo|seo 公司|优化公司好/.test(blob)) return false;
        if (/飞书|多维表格|feishu/.test(blob) && !/mini|dji|大疆/.test(blob)) return false;
        return null;
    }

    function renderHandoff(state) {
        const record = state.lastHandoff;
        if (!record) {
            if (lastHandoffCard) lastHandoffCard.hidden = true;
            return;
        }
        if (lastHandoffCard) lastHandoffCard.hidden = false;
        if (handoffMode) {
            handoffMode.textContent = record.mode || 'preview';
            handoffMode.dataset.mode = record.mode || 'preview';
        }

        const aligned = isDemoAlignedHandoff(record);
        const tasksUrl = geoflowUrl(DEMO_KB.tasksPath);
        const kbUrl = geoflowUrl(DEMO_KB.defaultDetailPath);

        if (handoffMessage) {
            if (aligned === false) {
                handoffMessage.innerHTML = [
                    escapeHtml(record.message || '已完成移交。'),
                    `<br><span class="suite-handoff-warn">此记录像是旧拓词任务（非 ${escapeHtml(DEMO_KB.entity)}）。`,
                    `演示请<strong>新建任务并绑定 KB #${DEMO_KB.kbId}</strong>，勿把本条当成已生成 DJI 正文。</span>`,
                ].join('');
            } else {
                handoffMessage.textContent = record.message || '已完成移交。';
            }
        }
        if (handoffMeta) {
            const bits = [];
            if (record.source) bits.push(`来源：${record.source}`);
            if (record.task_name) bits.push(`任务：${record.task_name}`);
            if (record.at) bits.push(`时间：${formatTime(record.at)}`);
            if (aligned === false) bits.push('演示对齐：未绑定 Mini 5 Pro');
            else if (aligned === true) bits.push('演示对齐：疑似 Mini 5 Pro');
            handoffMeta.textContent = bits.join(' · ');
        }
        if (handoffActions) {
            const buttons = [];
            const taskUrl = record.geoflow_task_url || record.geoflow_admin_url;
            if (aligned === false) {
                buttons.push(
                    `<a class="suite-btn suite-btn--primary suite-btn--tiny" href="${tasksUrl}" target="_blank" rel="noreferrer">一键打开任务中心新建</a>`
                );
                buttons.push(
                    `<a class="suite-btn suite-btn--ghost suite-btn--tiny" href="${kbUrl}" target="_blank" rel="noreferrer">绑定前核对 KB #${DEMO_KB.kbId}</a>`
                );
            }
            if (taskUrl && record.mode === 'live') {
                buttons.push(
                    `<button type="button" class="suite-btn suite-btn--${aligned === false ? 'ghost' : 'primary'} suite-btn--tiny" data-open-sso="${taskUrl}">SSO 打开旧任务</button>`
                );
                buttons.push(
                    `<a class="suite-btn suite-btn--ghost suite-btn--tiny" href="${taskUrl}" target="_blank" rel="noreferrer">直接打开</a>`
                );
            }
            if (record.task_id && record.mode === 'live') {
                buttons.push(
                    `<button type="button" class="suite-btn suite-btn--ghost suite-btn--tiny" data-refresh-task="${record.task_id}">刷新任务状态</button>`
                );
            }
            if (aligned !== false) {
                buttons.push(
                    `<a class="suite-btn suite-btn--ghost suite-btn--tiny" href="${tasksUrl}" target="_blank" rel="noreferrer">任务中心新建（绑 KB #${DEMO_KB.kbId}）</a>`
                );
            }
            buttons.push(
                `<a class="suite-btn suite-btn--ghost suite-btn--tiny" href="${Workflow.buildHref('keywords')}">再发一批词包</a>`
            );
            buttons.push(
                `<a class="suite-btn suite-btn--ghost suite-btn--tiny" href="${Workflow.buildHref('diagnostic')}">重新跑诊断</a>`
            );
            handoffActions.innerHTML = buttons.join('');
            handoffActions.querySelectorAll('[data-open-sso]').forEach((button) => {
                button.addEventListener('click', async () => {
                    try {
                        const path = new URL(button.getAttribute('data-open-sso'), window.location.origin).pathname;
                        await window.GEOrank.GeoflowHandoff.openViaSso(path);
                    } catch (error) {
                        window.alert(error.message || 'SSO 打开失败，请先登录 GEORank');
                    }
                });
            });
            handoffActions.querySelectorAll('[data-refresh-task]').forEach((button) => {
                button.addEventListener('click', async () => {
                    try {
                        const status = await window.GEOrank.GeoflowHandoff.fetchTaskStatus(button.getAttribute('data-refresh-task'));
                        if (handoffMessage) {
                            const base = `任务状态：${status.status || 'unknown'} · ${status.name || ''}`;
                            if (aligned === false) {
                                handoffMessage.innerHTML = `${escapeHtml(base)}<br><span class="suite-handoff-warn">仍建议新建任务并绑定 KB #${DEMO_KB.kbId}。</span>`;
                            } else {
                                handoffMessage.textContent = base;
                            }
                        }
                    } catch (error) {
                        window.alert(error.message || '刷新任务状态失败');
                    }
                });
            });
        }
    }

    function escapeHtml(value) {
        return String(value == null ? '' : value)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;');
    }

    let demoSummary = null;

    function pipelineMetrics(step, state) {
        const done = Boolean(state.completed[step.id]);
        const active = step.id === activeStepId || state.currentStep === step.id;
        const kb = demoSummary && demoSummary.knowledge_base;
        const tasks = (demoSummary && demoSummary.recent_tasks) || [];
        const drafts = tasks.filter((t) => t.has_draft).length;
        const map = {
            diagnostic: {
                lines: done ? ['检查记录 1', '可继续知识库'] : ['待开始检查', '四类 SEO 就绪'],
                delta: done ? '已完成' : '待启动',
            },
            knowledge: {
                lines: kb
                    ? [`文档 ${kb.doc_count ?? 0}`, `切片 ${kb.chunk_count ?? 0}`]
                    : ['可新建或导入', '示例库'],
                delta: kb ? `向量 ${kb.vectorized_count ?? 0}` : '待就绪',
            },
            keywords: {
                lines: done ? ['词包已生成', '可进分发'] : ['选题待生成', '勾选后建任务'],
                delta: done ? '+就绪' : '待执行',
            },
            distribute: {
                lines: [`任务 ${tasks.length}`, `草稿 ${drafts}`],
                delta: drafts ? '+有产出' : '待生成',
            },
            measure: {
                lines: done ? ['观测已标记', '可回看对比'] : ['出现率对比', '证据密度'],
                delta: done ? '完成' : '待观测',
            },
        };
        return map[step.id] || { lines: [active ? '进行中' : '未开始'], delta: '—' };
    }

    function renderPipeline(state) {
        const pipe = document.getElementById('suite-pipeline');
        if (!pipe) return;
        pipe.innerHTML = Workflow.STEPS.map((step, index) => {
            const done = Boolean(state.completed[step.id]);
            const active = step.id === activeStepId;
            const m = pipelineMetrics(step, state);
            return [
                `<button type="button" class="pipe-card" data-step="${step.id}" data-active="${active}" data-done="${done}">`,
                `  <span class="pipe-card__num">${done ? '✓' : index + 1}</span>`,
                `  <p class="pipe-card__title">${escapeHtml(step.label)}</p>`,
                `  <ul class="pipe-card__metrics"><li>${escapeHtml(m.lines[0] || '')}</li><li>${escapeHtml(m.lines[1] || '')}</li></ul>`,
                `  <span class="pipe-card__delta">${escapeHtml(m.delta)}</span>`,
                `</button>`,
            ].join('');
        }).join('');
        pipe.querySelectorAll('[data-step]').forEach((button) => {
            button.addEventListener('click', () => selectStep(button.getAttribute('data-step'), { push: true }));
        });
    }

    function renderTaskBoard(state) {
        const runningEl = document.getElementById('col-running');
        const reviewEl = document.getElementById('col-review');
        const doneEl = document.getElementById('col-done');
        if (!runningEl || !reviewEl || !doneEl) return;

        const tasks = (demoSummary && demoSummary.recent_tasks) || [];
        const running = [];
        const review = [];
        const done = [];

        Workflow.STEPS.forEach((step) => {
            const card = {
                title: step.title,
                meta: step.label,
                href: `/suite?step=${step.id}`,
                pct: state.completed[step.id] ? 100 : (step.id === activeStepId || state.currentStep === step.id ? 55 : 15),
                kind: state.completed[step.id] ? 'done' : (step.id === activeStepId || state.currentStep === step.id ? 'running' : 'review'),
            };
            if (card.kind === 'done') done.push(card);
            else if (card.kind === 'running') running.push(card);
            else review.push(card);
        });

        tasks.slice(0, 6).forEach((t) => {
            const status = String(t.status || '');
            const card = {
                title: t.title || '内容任务',
                meta: `${status}${t.has_draft ? ' · 有草稿' : ''}`,
                href: distributeHref(),
                pct: status === 'distributed' || status === 'completed' ? 100 : (t.has_draft ? 80 : 40),
                kind: status === 'distributed' || status === 'completed' ? 'done' : (status === 'running' || status === 'pending' ? 'running' : 'review'),
            };
            if (card.kind === 'done') done.push(card);
            else if (card.kind === 'running') running.push(card);
            else review.push(card);
        });

        function paint(el, items, cls) {
            if (!items.length) {
                el.innerHTML = '<p class="task-empty">暂无卡片</p>';
                return;
            }
            el.innerHTML = items.map((item) => [
                `<a class="task-card task-card--${cls}" href="${escapeHtml(item.href)}">`,
                `  <p class="task-card__title">${escapeHtml(item.title)}</p>`,
                `  <p class="task-card__meta">${escapeHtml(item.meta)}</p>`,
                `  <div class="task-card__bar"><i style="width:${item.pct}%"></i></div>`,
                `</a>`,
            ].join('')).join('');
        }

        paint(runningEl, running, 'running');
        paint(reviewEl, review, 'review');
        paint(doneEl, done, 'done');
        const rc = document.getElementById('col-running-count');
        const vc = document.getElementById('col-review-count');
        const dc = document.getElementById('col-done-count');
        if (rc) rc.textContent = String(running.length);
        if (vc) vc.textContent = String(review.length);
        if (dc) dc.textContent = String(done.length);
    }

    function renderSideGauges(state) {
        const kb = demoSummary && demoSummary.knowledge_base;
        const tasks = (demoSummary && demoSummary.recent_tasks) || [];
        const drafts = tasks.filter((t) => t.has_draft).length;
        const wf = Workflow.progressPercent(state);
        const kbScore = kb ? Math.min(100, 40 + (kb.vectorized_count || 0) * 2) : 20;
        const quality = Math.round((kbScore * 0.35) + (drafts ? 25 : 8) + (wf * 0.4));
        const channel = Math.min(100, 40 + drafts * 8 + (kb ? 20 : 0));

        const qGauge = document.getElementById('quality-gauge');
        const cGauge = document.getElementById('channel-gauge');
        if (qGauge) qGauge.style.setProperty('--p', String(quality));
        if (cGauge) cGauge.style.setProperty('--p', String(channel));
        const qs = document.getElementById('quality-score');
        const cs = document.getElementById('channel-score');
        if (qs) qs.textContent = String(quality);
        if (cs) cs.textContent = String(channel);
        const set = (id, val) => { const el = document.getElementById(id); if (el) el.textContent = val; };
        set('q-kb', kb ? '就绪' : '待导入');
        set('q-vec', kb ? `${kb.vectorized_count ?? 0}` : '—');
        set('q-draft', String(drafts));
        set('q-wf', `${wf}%`);
    }

    function renderStepper(state) {
        renderPipeline(state);
        renderTaskBoard(state);
        renderSideGauges(state);
        if (!stepperEl) return;
        stepperEl.innerHTML = Workflow.STEPS.map((step, index) => {
            const done = Boolean(state.completed[step.id]);
            const active = step.id === activeStepId;
            return [
                `<li>`,
                `<button type="button" class="suite-stepper__item" data-step="${step.id}" data-active="${active}" data-done="${done}" aria-current="${active ? 'step' : 'false'}">`,
                `  <span class="suite-stepper__index">${done ? '✓' : index + 1}</span>`,
                `  <span class="suite-stepper__label">${step.label}</span>`,
                `  <span class="suite-stepper__sub">${step.title}</span>`,
                `</button>`,
                `</li>`,
            ].join('');
        }).join('');

        stepperEl.querySelectorAll('[data-step]').forEach((button) => {
            button.addEventListener('click', () => {
                selectStep(button.getAttribute('data-step'), { push: true });
            });
        });
    }

    function renderPanel(state) {
        const step = Workflow.getStep(activeStepId);
        const idx = Workflow.stepIndex(activeStepId) + 1;
        const done = Boolean(state.completed[step.id]);
        const panelEl = document.getElementById('suite-step-panel');
        if (panelEl) {
            panelEl.classList.remove('suite-step-panel--enter');
            void panelEl.offsetWidth;
            panelEl.classList.add('suite-step-panel--enter');
        }
        const next = Workflow.nextOf(step.id);
        const percent = Workflow.progressPercent(state);
        const kbUrl = knowledgeHref();
        const tasksUrl = distributeHref();
        const channelUrl = isNative() ? nativeAdminPath() : geoflowUrl('/geo_admin/distribution');
        const linkTarget = isNative() ? '' : ' target="_blank" rel="noreferrer"';

        if (progressBar) progressBar.style.width = `${Math.max(8, percent)}%`;
        if (progressLabel) progressLabel.textContent = `进度 ${percent}% · 完成 ${Object.keys(state.completed).filter((key) => state.completed[key]).length}/${Workflow.STEPS.length}`;

        if (stepIcon) {
            stepIcon.innerHTML = `<span class="material-symbols-outlined">${step.icon || 'hub'}</span>`;
        }
        if (stepEyebrow) stepEyebrow.textContent = `步骤 ${idx} / ${Workflow.STEPS.length}`;
        if (stepTitle) stepTitle.textContent = step.title;
        if (stepDesc) stepDesc.textContent = step.desc;
        if (stepState) stepState.textContent = done ? '已完成' : (state.currentStep === step.id ? '进行中' : '未开始');
        if (stepNote) {
            if (step.id === 'diagnostic') {
                stepNote.textContent = done
                    ? '检查完成，可继续沉淀知识材料。'
                    : '先确认页面可被抓取与理解，再进入知识库。';
            } else if (step.id === 'knowledge') {
                stepNote.textContent = done
                    ? '知识库已就绪，可继续拓词。'
                    : '新建或导入示例库，沉淀事实材料后进入拓词。';
            } else if (step.id === 'keywords') {
                stepNote.textContent = done
                    ? '选题已就绪，可生成内容任务。'
                    : '生成选题并勾选后创建内容任务。';
            } else if (step.id === 'distribute') {
                stepNote.textContent = done
                    ? '渠道预览已标记，可查看观测。'
                    : '生成草稿并预览渠道壳（预览·不外发）。';
            } else if (step.id === 'measure') {
                stepNote.textContent = done
                    ? '观测已记录。'
                    : '查看三层追问中的出现率与证据密度（演示数据）。';
            } else {
                stepNote.textContent = done
                    ? '本步已完成。可进入下一步，或点步骤条回看。'
                    : '进入模块完成操作后会自动记进度；也可在此手动标记完成。';
            }
        }

        if (stepActions) {
            const actions = [];
            const suitePanel = Boolean(step.suitePanel);
            if (step.id === 'distribute') {
                actions.push(
                    `<a class="suite-btn suite-btn--primary" href="${tasksUrl}"${linkTarget}><span class="material-symbols-outlined text-sm">sync_alt</span>打开内容任务</a>`
                );
                actions.push(
                    `<a class="suite-btn suite-btn--ghost" href="${kbUrl}"${linkTarget}><span class="material-symbols-outlined text-sm">database</span>打开知识库</a>`
                );
                actions.push(
                    `<button type="button" class="suite-btn suite-btn--ghost" data-mark-done="${step.id}"><span class="material-symbols-outlined text-sm">check</span>标记完成并继续</button>`
                );
            } else if (step.id === 'knowledge') {
                actions.push(
                    `<a class="suite-btn suite-btn--primary" href="${kbUrl}"${linkTarget}><span class="material-symbols-outlined text-sm">database</span>打开知识库</a>`
                );
                actions.push(
                    `<button type="button" class="suite-btn suite-btn--ghost" data-mark-done="${step.id}"><span class="material-symbols-outlined text-sm">check</span>标记完成并继续</button>`
                );
            } else if (suitePanel) {
                actions.push(
                    `<button type="button" class="suite-btn suite-btn--primary" data-mark-done="${step.id}"><span class="material-symbols-outlined text-sm">check</span>标记完成并继续</button>`
                );
            } else {
                const primaryHref = Workflow.buildHref(step);
                const externalAttrs = step.external ? ' target="_blank" rel="noreferrer"' : '';
                actions.push(
                    `<a class="suite-btn suite-btn--primary" href="${primaryHref}"${externalAttrs}><span class="material-symbols-outlined text-sm">${step.icon}</span>${step.cta}</a>`
                );
                if (step.altHref) {
                    actions.push(
                        `<a class="suite-btn suite-btn--ghost" href="${step.altHref}?from=suite&workflow=1"><span class="material-symbols-outlined text-sm">task_alt</span>${step.altCta}</a>`
                    );
                }
            }

            if (!done && !suitePanel && step.id !== 'distribute') {
                actions.push(
                    `<button type="button" class="suite-btn suite-btn--ghost" data-mark-done="${step.id}"><span class="material-symbols-outlined text-sm">check</span>标记完成</button>`
                );
            }
            if (done && next) {
                actions.push(
                    `<button type="button" class="suite-btn suite-btn--primary" data-goto-next="${next.id}"><span class="material-symbols-outlined text-sm">arrow_forward</span>进入下一步</button>`
                );
            } else if (done && !next) {
                actions.push(
                    `<a class="suite-btn suite-btn--ghost" href="/suite?step=measure"><span class="material-symbols-outlined text-sm">monitoring</span>查看观测</a>`
                );
            }

            stepActions.innerHTML = actions.join('');

            stepActions.querySelectorAll('[data-mark-done]').forEach((button) => {
                button.addEventListener('click', () => {
                    const id = button.getAttribute('data-mark-done');
                    Workflow.markComplete(id);
                    const nextStep = Workflow.nextOf(id);
                    selectStep(nextStep ? nextStep.id : id, { push: true });
                });
            });
            stepActions.querySelectorAll('[data-goto-next]').forEach((button) => {
                button.addEventListener('click', () => {
                    const id = button.getAttribute('data-goto-next');
                    Workflow.setCurrent(id);
                    selectStep(id, { push: true });
                });
            });
        }

        if (startCta) {
            startCta.href = Workflow.buildHref('diagnostic');
        }
        if (continueCta) {
            const continueStep = Workflow.getStep(state.currentStep || activeStepId);
            continueCta.href = continueStep.suitePanel || continueStep.external
                ? `/suite?step=${continueStep.id}`
                : Workflow.buildHref(continueStep);
            continueCta.textContent = '';
            continueCta.innerHTML = `<span class="material-symbols-outlined text-sm">route</span>继续：${continueStep.label}`;
        }

        const extra = document.getElementById('suite-extra-panel');
        // 等 content-backend 就绪后再拉观测面板，避免 init 阶段二次 refresh 把「加载中」盖住结果
        if (window.GEOrank?.SuiteExtra?.renderExtraPanel && window.GEOrank._suiteExtraReady) {
            window.GEOrank.SuiteExtra.renderExtraPanel(step.id, extra);
        } else if (extra) {
            const pendingExtra = step.id === 'measure'
                || step.id === 'knowledge'
                || step.id === 'distribute'
                || step.id === 'trust_asset';
            if (pendingExtra) {
                extra.hidden = false;
                if (!extra.dataset.bootLoading) {
                    extra.dataset.bootLoading = '1';
                    extra.innerHTML = step.id === 'measure'
                        ? '<div class="measure-monitor measure-monitor--loading"><div class="measure-toolbar"><span class="suite-badge">加载中</span><span class="measure-toolbar__hint">正在加载观测数据…</span></div><div class="measure-kpi-row"><div class="measure-kpi skeleton"></div><div class="measure-kpi skeleton"></div><div class="measure-kpi skeleton"></div></div></div>'
                        : '<p class="suite-extra__lead">加载中…</p>';
                }
            } else {
                extra.hidden = true;
                delete extra.dataset.bootLoading;
            }
        }
    }

    function applyMeasureViewMode(stepId) {
        const isMeasure = stepId === 'measure';
        document.body.classList.toggle('suite-view--measure', isMeasure);
        const title = document.getElementById('suite-cockpit-title');
        const sub = document.getElementById('suite-cockpit-sub');
        if (title) title.textContent = isMeasure ? 'AI 答案监测' : 'GEO Suite';
        if (sub) {
            sub.textContent = isMeasure
                ? '监测 AI 回答中的品牌提及与引用来源'
                : '检查 → 知识 → 拓词 → 内容/分发预览 → 观测';
        }
        document.querySelectorAll('[data-suite-tab]').forEach((el) => {
            const tab = el.getAttribute('data-suite-tab');
            const active = isMeasure ? tab === 'measure' : tab === 'factory';
            el.classList.toggle('is-active', active);
        });
        // 观测页只保留监测主区，避免步骤卡 / 看板 / 侧栏叠层
        [
            'suite-pipeline',
            'suite-step-panel',
            'suite-board-section',
            'suite-last-handoff',
        ].forEach((id) => {
            const el = document.getElementById(id);
            if (el) el.hidden = isMeasure;
        });
        document.querySelectorAll('.cockpit-side').forEach((el) => {
            el.hidden = isMeasure;
        });
        document.querySelectorAll('.suite-wf-bar, [data-suite-workflow-bar]').forEach((el) => {
            el.hidden = isMeasure;
        });
        const shortcuts = document.getElementById('suite-side-shortcuts');
        if (shortcuts) shortcuts.hidden = isMeasure;
        const startCtaEl = document.getElementById('suite-start-cta');
        if (startCtaEl && isMeasure) {
            startCtaEl.textContent = '标记观测完成';
            startCtaEl.href = '/suite?step=measure';
            startCtaEl.onclick = (event) => {
                event.preventDefault();
                Workflow.markComplete('measure');
                startCtaEl.textContent = '已标记完成';
            };
        } else if (startCtaEl && !isMeasure) {
            startCtaEl.onclick = async (event) => {
                event.preventDefault();
                try {
                    const run = await Workflow.ensureRun({
                        forceNew: true,
                        entity: 'DJI Mini 5 Pro',
                        url: 'https://www.dji.com/mini-5-pro',
                    });
                    window.location.href = Workflow.buildHref('diagnostic', { run_id: run.id });
                } catch (error) {
                    window.location.href = Workflow.buildHref('diagnostic');
                }
            };
            startCtaEl.textContent = '开始工作流';
            startCtaEl.href = Workflow.buildHref('diagnostic');
        }
    }

    function selectStep(stepId, options = {}) {
        const id = Workflow.normalizeStepId(stepId) || 'diagnostic';
        activeStepId = id;
        Workflow.setCurrent(id);
        if (options.push) writeStepToUrl(id, false);
        else writeStepToUrl(id, true);
        const state = Workflow.load();
        applyMeasureViewMode(id);
        renderStepper(state);
        renderPanel(state);
        renderHandoff(state);
        document.getElementById('suite-workflow')?.scrollIntoView({ behavior: 'auto', block: 'nearest' });
    }

    function refresh() {
        const state = Workflow.load();
        applyMeasureViewMode(activeStepId);
        renderStepper(state);
        renderPanel(state);
        renderHandoff(state);
    }

    Workflow.syncFromQuery();
    const fromUrl = readStepFromUrl();
    const state = Workflow.load();
    activeStepId = fromUrl || state.currentStep || 'diagnostic';
    writeStepToUrl(activeStepId, true);
    Workflow.mountBar({
        stepId: activeStepId,
        force: true,
        hint: '按步骤完成检查、知识、拓词、分发与观测。',
    });
    refresh();

    resetBtn?.addEventListener('click', () => {
        if (!window.confirm('确定重置本机工作流进度？')) return;
        Workflow.clear();
        selectStep('diagnostic', { push: true });
    });

    window.addEventListener('popstate', () => {
        const step = readStepFromUrl() || 'diagnostic';
        activeStepId = step;
        Workflow.setCurrent(step);
        refresh();
    });

    try {
        contentBackend = await fetch('/api/settings/content-backend', { credentials: 'same-origin' })
            .then((r) => r.json())
            .catch(() => contentBackend);
        window.GEOrank._contentBackend = contentBackend;
        Workflow.applyContentBackendMode(contentBackend.mode, {
            public_path: contentBackend.public_path || '/knowledge',
            admin_path: contentBackend.admin_path,
            flow_base: (integrationStatus && integrationStatus.public_base_url) || DEMO_KB.defaultBase,
        });

        const openCe = document.getElementById('suite-open-content-engine');
        if (openCe) {
            openCe.href = knowledgeHref();
            openCe.textContent = isNative() ? '打开知识库' : '打开 GEOFlow';
            if (isNative()) {
                openCe.removeAttribute('target');
                openCe.removeAttribute('rel');
            }
        }

        const kb9Link = document.getElementById('suite-kb9-link');
        if (kb9Link) {
            kb9Link.href = knowledgeHref();
            kb9Link.innerHTML = isNative()
                ? `<span>打开知识库</span><span class="material-symbols-outlined text-sm">database</span>`
                : `<span>打开推荐 KB #9</span><span class="material-symbols-outlined text-sm">database</span>`;
            if (isNative()) {
                kb9Link.removeAttribute('target');
                kb9Link.removeAttribute('rel');
            }
        }

        if (openGeoflow) {
            if (isNative()) {
                openGeoflow.hidden = true;
            } else {
                openGeoflow.hidden = false;
            }
        }

        try {
            demoSummary = await fetch('/api/content-engine/public/demo-summary', { credentials: 'same-origin' }).then((r) => r.json());
        } catch (_) {
            demoSummary = null;
        }

        if (isNative()) {
            if (statusEl) statusEl.dataset.mode = 'native-python';
            if (statusText) {
                statusText.textContent = '就绪';
            }
            if (integrationCopy) {
                integrationCopy.textContent = '';
                integrationCopy.hidden = true;
            }
            if (nextStepsEl) {
                nextStepsEl.textContent = '';
                nextStepsEl.hidden = true;
            }
            const handoffCard = document.getElementById('suite-last-handoff');
            if (handoffCard && !Workflow.load().lastHandoff) handoffCard.hidden = true;
            window.GEOrank._suiteExtraReady = true;
            refresh();
        } else {
            integrationStatus = await window.GEOrank.GeoflowHandoff.fetchStatus();
            window.GEOrank._suiteIntegrationStatus = integrationStatus;
            Workflow.applyContentBackendMode('legacy-flow', {
                public_path: contentBackend.public_path || '/knowledge',
                admin_path: contentBackend.admin_path,
                flow_base: integrationStatus.public_base_url || DEMO_KB.defaultBase,
            });
            const mode = integrationStatus.mode || 'preview';
            if (statusEl) statusEl.dataset.mode = mode;
            if (statusText) {
                statusText.textContent = integrationStatus.configured ? '已连接' : '就绪';
            }
            if (openGeoflow) {
                openGeoflow.hidden = true;
            }
            if (integrationCopy) {
                integrationCopy.textContent = '';
                integrationCopy.hidden = true;
            }
            if (nextStepsEl) {
                nextStepsEl.textContent = '';
                nextStepsEl.hidden = true;
            }
            try {
                const review = await window.GEOrank.GeoflowHandoff.fetchReview();
                if (Array.isArray(review?.events) && review.events.length && handoffMeta) {
                    const latest = review.events[0];
                    const extra = document.getElementById('suite-callback-events');
                    if (extra) {
                        extra.hidden = false;
                        extra.textContent = `最近发布回调：${latest.event || ''} ${latest.public_url || ''}`.trim();
                    }
                }
            } catch (error) {
                console.warn('[suite] review failed', error);
            }
            window.GEOrank._suiteExtraReady = true;
            refresh();
        }
    } catch (error) {
        if (statusEl) statusEl.dataset.mode = 'native-python';
        if (statusText) statusText.textContent = '就绪';
        console.warn('[suite] content-backend / status failed', error);
        window.GEOrank._suiteExtraReady = true;
        refresh();
    }
});
