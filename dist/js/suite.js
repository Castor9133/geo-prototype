document.addEventListener('DOMContentLoaded', async () => {
    const Workflow = window.GEOrank?.SuiteWorkflow;
    const statusEl = document.getElementById('suite-status');
    const statusText = document.getElementById('suite-status-text');
    const openGeoflow = document.getElementById('suite-open-geoflow');
    const integrationCopy = document.getElementById('suite-integration-copy');
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

    let integrationStatus = null;
    let activeStepId = 'diagnostic';

    if (!Workflow) {
        console.error('[suite] SuiteWorkflow missing');
        return;
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
        if (handoffMessage) {
            handoffMessage.textContent = record.message || '已完成移交。';
        }
        if (handoffMeta) {
            const bits = [];
            if (record.source) bits.push(`来源：${record.source}`);
            if (record.task_name) bits.push(`任务：${record.task_name}`);
            if (record.at) bits.push(`时间：${formatTime(record.at)}`);
            handoffMeta.textContent = bits.join(' · ');
        }
        if (handoffActions) {
            const buttons = [];
            const taskUrl = record.geoflow_task_url || record.geoflow_admin_url;
            if (taskUrl && record.mode === 'live') {
                buttons.push(
                    `<button type="button" class="suite-btn suite-btn--primary suite-btn--tiny" data-open-sso="${taskUrl}">SSO 打开任务</button>`
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
                            handoffMessage.textContent = `任务状态：${status.status || 'unknown'} · ${status.name || ''}`;
                        }
                    } catch (error) {
                        window.alert(error.message || '刷新任务状态失败');
                    }
                });
            });
        }
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
        const next = Workflow.nextOf(step.id);
        const percent = Workflow.progressPercent(state);

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
            if (step.id === 'handoff') {
                stepNote.textContent = integrationStatus?.configured
                    ? 'Live 已就绪：在拓词或问答页点「发送到 GEOFlow」将创建真实任务（勿用 force preview）。'
                    : '当前为 preview：可演示载荷，但验收要求配置 Token 后走 live。';
            } else if (step.id === 'review') {
                stepNote.textContent = integrationStatus?.configured
                    ? '验收点：mode=live、任务可刷新、发布回调可见；然后进入事实卡看板。'
                    : '未配置 Token 时只能演示 preview；请到系统设置补齐 GEO Suite Token。';
            } else if (step.id === 'knowledge') {
                stepNote.textContent = '只读看板来自演示资产；真实向量化率可在灌入 Flow KB 后改写 metrics.json。';
            } else if (step.id === 'trust_asset') {
                stepNote.textContent = 'L3-C1 样板：图文 + 文字稿元数据，不做真视频管线。';
            } else if (step.id === 'measure') {
                stepNote.textContent = '优先读取后台最新 completed 采样；若无则回落演示数据。徽章声明「非网页抓取」。';
            } else {
                stepNote.textContent = done
                    ? '本步已完成。可进入下一步，或点步骤条回看。'
                    : '进入模块完成操作后会自动记进度；也可在此手动标记完成。';
            }
        }

        if (stepActions) {
            const actions = [];
            const suitePanel = Boolean(step.suitePanel);
            if (step.id === 'review') {
                actions.push(
                    `<a class="suite-btn suite-btn--primary" href="/suite?step=knowledge"><span class="material-symbols-outlined text-sm">arrow_forward</span>进入事实卡</a>`
                );
                if (openGeoflow?.href) {
                    actions.push(
                        `<a class="suite-btn suite-btn--ghost" href="${openGeoflow.href}" target="_blank" rel="noreferrer"><span class="material-symbols-outlined text-sm">open_in_new</span>打开 GEOFlow</a>`
                    );
                }
                actions.push(
                    `<a class="suite-btn suite-btn--ghost" href="${Workflow.buildHref('diagnostic')}"><span class="material-symbols-outlined text-sm">replay</span>再跑诊断</a>`
                );
            } else if (step.id === 'handoff') {
                actions.push(
                    `<a class="suite-btn suite-btn--primary" href="${Workflow.buildHref('keywords')}"><span class="material-symbols-outlined text-sm">sync_alt</span>${step.cta}</a>`
                );
                if (step.altHref) {
                    actions.push(
                        `<a class="suite-btn suite-btn--ghost" href="${Workflow.buildHref('solutions')}"><span class="material-symbols-outlined text-sm">forum</span>${step.altCta}</a>`
                    );
                }
            } else if (suitePanel) {
                actions.push(
                    `<button type="button" class="suite-btn suite-btn--primary" data-mark-done="${step.id}"><span class="material-symbols-outlined text-sm">check</span>标记完成并继续</button>`
                );
            } else {
                actions.push(
                    `<a class="suite-btn suite-btn--primary" href="${Workflow.buildHref(step)}"><span class="material-symbols-outlined text-sm">${step.icon}</span>${step.cta}</a>`
                );
                if (step.altHref) {
                    actions.push(
                        `<a class="suite-btn suite-btn--ghost" href="${step.altHref}?from=suite&workflow=1"><span class="material-symbols-outlined text-sm">task_alt</span>${step.altCta}</a>`
                    );
                }
            }

            if (!done && !suitePanel && step.id !== 'review') {
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
            continueCta.href = continueStep.suitePanel || continueStep.id === 'review'
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
        document.getElementById('suite-workflow')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }

    function refresh() {
        const state = Workflow.load();
        renderStepper(state);
        renderPanel(state);
        renderHandoff(state);
    }

    // 初始：URL ?step= 优先，否则用会话 currentStep
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
        const mode = integrationStatus.mode || 'preview';
        if (statusEl) statusEl.dataset.mode = mode;
        if (statusText) {
            statusText.textContent = integrationStatus.configured
                ? 'GEOFlow 已连接（live）：验收要求走真实移交 + 回调回看'
                : '预览模式（preview）：演示可用，但 L1 验收未通过——请配置 Token';
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
                ? `已连接到 ${integrationStatus.public_base_url || 'GEOFlow'}。在问答或拓词页点击「${integrationStatus.public_cta_label || '发送到 GEOFlow'}」即可创建任务；可用 SSO 免二次登录。`
                : '当前为预览模式。先在后台「系统设置 → GEO Suite」填写 base_url 与 API Token；未配置也可走通 handoff 演示并在本页查看最近移交。';
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
        if (statusText) statusText.textContent = '暂未读取到集成状态，仍可使用 GEORank 工作流';
        console.warn('[suite] status failed', error);
    }
});
