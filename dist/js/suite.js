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
    let activeStepId = 'diagnostic';

    if (!Workflow) {
        console.error('[suite] SuiteWorkflow missing');
        return;
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

    function renderStepper(state) {
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
        const kbUrl = geoflowUrl(DEMO_KB.defaultDetailPath);
        const tasksUrl = geoflowUrl(DEMO_KB.tasksPath);

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
                    ? '诊断完成：把 P0（FAQPage / 问句 H2 / 实体一致）记入 Backlog，再进知识库。'
                    : '按内容工程：先确认「可被抓取与理解」，再谈引用；详见 docs/content-engineering-sop.md。';
            } else if (step.id === 'knowledge') {
                stepNote.textContent = `推荐演示包：${DEMO_KB.kbName}（KB #${DEMO_KB.kbId}）。下方看板读自 ${DEMO_KB.docsPath}metrics.json；旧飞书/示范栏目已降为次要。`;
            } else if (step.id === 'keywords') {
                stepNote.textContent = done
                    ? '拓词完成：确认 P0 提示簇与 Mini 5 Pro 探针题已对齐事实卡 ID，再进分发。'
                    : '按内容工程：扩展真实用户问题（非堆砌词）；主演示用 Mini 5 Pro 探针，勿沿用旧 GEO 公司词包。';
            } else if (step.id === 'distribute') {
                stepNote.textContent = integrationStatus?.configured
                    ? `实际操作：任务中心新建 → 中国生态提示词 + 绑定 KB #${DEMO_KB.kbId} → 答案优先正文 → 渠道/模板。下方有分步指引。`
                    : `可先打开任务中心；配置 Token 后可 live 移交。演示仍须手动绑定 KB #${DEMO_KB.kbId}，勿假装旧移交已是 DJI 文。`;
            } else if (step.id === 'measure') {
                stepNote.textContent = '按内容工程：用 Mini 5 Pro 固定探针看 mention/citation/absent；缺口回写事实卡。非网页抓取。';
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
                    `<a class="suite-btn suite-btn--primary" href="${tasksUrl}" target="_blank" rel="noreferrer"><span class="material-symbols-outlined text-sm">sync_alt</span>打开任务中心新建</a>`
                );
                actions.push(
                    `<a class="suite-btn suite-btn--ghost" href="${kbUrl}" target="_blank" rel="noreferrer"><span class="material-symbols-outlined text-sm">database</span>核对 KB #${DEMO_KB.kbId}</a>`
                );
                actions.push(
                    `<a class="suite-btn suite-btn--ghost" href="${geoflowUrl('/geo_admin/distribution')}" target="_blank" rel="noreferrer"><span class="material-symbols-outlined text-sm">share</span>分发渠道</a>`
                );
                actions.push(
                    `<button type="button" class="suite-btn suite-btn--ghost" data-mark-done="${step.id}"><span class="material-symbols-outlined text-sm">check</span>标记完成并继续</button>`
                );
            } else if (step.id === 'knowledge') {
                actions.push(
                    `<a class="suite-btn suite-btn--primary" href="${kbUrl}" target="_blank" rel="noreferrer"><span class="material-symbols-outlined text-sm">database</span>打开 DJI Mini 5 Pro KB</a>`
                );
                actions.push(
                    `<a class="suite-btn suite-btn--ghost" href="${geoflowUrl('/geo_admin/knowledge-bases')}" target="_blank" rel="noreferrer"><span class="material-symbols-outlined text-sm">list</span>知识库列表</a>`
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
                    `<a class="suite-btn suite-btn--ghost" href="/admin/trust-obs"><span class="material-symbols-outlined text-sm">monitoring</span>打开观测后台</a>`
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
        if (window.GEOrank?.SuiteExtra?.renderExtraPanel) {
            window.GEOrank.SuiteExtra.renderExtraPanel(step.id, extra);
        } else if (extra) {
            extra.hidden = true;
        }
    }

    function selectStep(stepId, options = {}) {
        const id = Workflow.normalizeStepId(stepId) || 'diagnostic';
        activeStepId = id;
        Workflow.setCurrent(id);
        if (options.push) writeStepToUrl(id, false);
        else writeStepToUrl(id, true);
        const state = Workflow.load();
        renderStepper(state);
        renderPanel(state);
        renderHandoff(state);
        document.getElementById('suite-workflow')?.scrollIntoView({ behavior: 'auto', block: 'nearest' });
    }

    function refresh() {
        const state = Workflow.load();
        renderStepper(state);
        renderPanel(state);
        renderHandoff(state);
    }

    Workflow.syncFromQuery();
    const fromUrl = readStepFromUrl();
    const state = Workflow.load();
    activeStepId = fromUrl || state.currentStep || 'diagnostic';
    writeStepToUrl(activeStepId, true);
    refresh();

    resetBtn?.addEventListener('click', () => {
        if (!window.confirm('确定重置本机工作流进度？最近移交记录也会清空。')) return;
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
        integrationStatus = await window.GEOrank.GeoflowHandoff.fetchStatus();
        window.GEOrank._suiteIntegrationStatus = integrationStatus;
        const mode = integrationStatus.mode || 'preview';
        if (statusEl) statusEl.dataset.mode = mode;
        if (statusText) {
            statusText.textContent = integrationStatus.configured
                ? `GEOFlow 已连接（live）：演示请绑定 KB #${DEMO_KB.kbId}（${DEMO_KB.entity}）`
                : '预览模式（preview）：演示可用；真实任务须配置 Token，并手动绑定 KB #9';
        }
        if (openGeoflow && integrationStatus.public_base_url) {
            openGeoflow.href = `${String(integrationStatus.public_base_url).replace(/\/$/, '')}/geo_admin`;
            openGeoflow.addEventListener('click', async (event) => {
                if (!integrationStatus?.sso_available) return;
                event.preventDefault();
                try {
                    await window.GEOrank.GeoflowHandoff.openViaSso('/geo_admin/dashboard');
                } catch (error) {
                    window.open(openGeoflow.href, '_blank', 'noopener');
                }
            });
        }
        if (integrationCopy) {
            integrationCopy.textContent = integrationStatus.configured
                ? `已连接到 ${integrationStatus.public_base_url || 'GEOFlow'}。推荐演示 KB #${DEMO_KB.kbId}（${DEMO_KB.kbName}）。拓词「发送到 GEOFlow」若仍是旧词包，演示请改在任务中心新建并绑定该 KB。`
                : `当前为预览模式。配置 Token 后可 live 移交。主演示入口：KB #${DEMO_KB.kbId} 详情 + 任务中心绑定；包路径 ${DEMO_KB.docsPath}。`;
        }
        if (nextStepsEl) {
            nextStepsEl.textContent = `本地可用 scripts/start-geo-suite.ps1；导入/刷新 DJI 包：scripts/import-cn-product-demo-v2-kb.ps1。`;
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
        refresh();
    } catch (error) {
        if (statusEl) statusEl.dataset.mode = 'preview';
        if (statusText) statusText.textContent = '暂未读取到集成状态，仍可使用 GEORank 工作流（演示绑定 KB #9）';
        console.warn('[suite] status failed', error);
    }
});
