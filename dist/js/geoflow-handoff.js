(function (global) {
    'use strict';

    async function fetchGeoflowStatus() {
        const response = await fetch('/api/integrations/geoflow/status', {
            headers: { Accept: 'application/json' },
            credentials: 'same-origin',
        });
        if (!response.ok) {
            throw new Error('无法读取 GEOFlow 集成状态');
        }
        return response.json();
    }

    async function sendHandoff(payload) {
        const response = await fetch('/api/integrations/geoflow/handoff', {
            method: 'POST',
            headers: {
                Accept: 'application/json',
                'Content-Type': 'application/json',
            },
            credentials: 'same-origin',
            body: JSON.stringify(payload || {}),
        });
        const data = await response.json().catch(() => ({}));
        if (!response.ok) {
            const detail = data.detail || data.message || `移交失败 (${response.status})`;
            throw new Error(typeof detail === 'string' ? detail : JSON.stringify(detail));
        }
        const result = Object.assign({}, data, {
            source: data.source || payload?.source || null,
            task_name: data.task_name || payload?.task_name || null,
            suite_path: data.suite_path || '/suite?step=review',
        });
        try {
            const Workflow = global.GEOrank?.SuiteWorkflow;
            if (Workflow?.saveHandoff) {
                Workflow.saveHandoff(result);
            } else {
                // suite-workflow.js 尚未加载时，仍写入同一 key 供 Suite 页读取
                const key = 'georank_suite_workflow_v1';
                let state = {};
                try {
                    state = JSON.parse(global.localStorage.getItem(key) || '{}') || {};
                } catch (error) {
                    state = {};
                }
                state.completed = Object.assign({}, state.completed || {}, {
                    handoff: true,
                });
                if (result.source === 'keywords') state.completed.keywords = true;
                if (result.source === 'solutions') state.completed.solutions = true;
                state.currentStep = 'review';
                state.lastHandoff = {
                    mode: result.mode || 'preview',
                    message: result.message || '已完成移交',
                    source: result.source,
                    task_name: result.task_name,
                    task_id: result.task_id || null,
                    company_id: result.company_id || null,
                    geoflow_admin_url: result.geoflow_task_url || result.geoflow_admin_url || null,
                    geoflow_task_url: result.geoflow_task_url || result.geoflow_admin_url || null,
                    suite_path: result.suite_path,
                    preview: result.preview || null,
                    at: new Date().toISOString(),
                };
                state.updatedAt = new Date().toISOString();
                global.localStorage.setItem(key, JSON.stringify(state));
            }
        } catch (error) {
            console.warn('[geoflow-handoff] persist workflow failed', error);
        }
        return result;
    }

    function formatResultMessage(result) {
        if (!result) return '已完成移交。';
        if (result.mode === 'preview') {
            return result.message || '预览载荷已生成（非 live）。验收要求配置 Token 后走真实移交。';
        }
        return result.message || '已 live 发送到 GEOFlow，请在 Suite 回看确认任务与回调。';
    }

    function openResult(result) {
        const url = result && (result.geoflow_task_url || result.geoflow_admin_url);
        if (url && result.mode === 'live') {
            window.open(url, '_blank', 'noopener');
        }
        const suitePath = (result && result.suite_path) || '/suite?step=review';
        window.setTimeout(() => {
            window.location.href = suitePath;
        }, result && result.mode === 'live' ? 400 : 700);
    }

    async function openGeoflowViaSso(nextPath) {
        const response = await fetch('/api/integrations/geoflow/sso-ticket', {
            method: 'POST',
            headers: {
                Accept: 'application/json',
                'Content-Type': 'application/json',
            },
            credentials: 'same-origin',
            body: JSON.stringify({
                next_path: nextPath || '/geo_admin/dashboard',
            }),
        });
        const data = await response.json().catch(() => ({}));
        if (!response.ok) {
            const detail = data.detail || data.message || `SSO 失败 (${response.status})`;
            throw new Error(typeof detail === 'string' ? detail : JSON.stringify(detail));
        }
        if (!data.consume_url) {
            throw new Error('未返回 SSO 跳转地址');
        }
        window.open(data.consume_url, '_blank', 'noopener');
        return data;
    }

    async function fetchReview() {
        const response = await fetch('/api/integrations/geoflow/review', {
            headers: { Accept: 'application/json' },
            credentials: 'same-origin',
        });
        if (!response.ok) {
            throw new Error('无法读取 Suite 回看数据');
        }
        return response.json();
    }

    async function fetchTaskStatus(taskId) {
        const response = await fetch(`/api/integrations/geoflow/tasks/${encodeURIComponent(taskId)}`, {
            headers: { Accept: 'application/json' },
            credentials: 'same-origin',
        });
        const data = await response.json().catch(() => ({}));
        if (!response.ok) {
            const detail = data.detail || data.message || `任务状态失败 (${response.status})`;
            throw new Error(typeof detail === 'string' ? detail : JSON.stringify(detail));
        }
        return data;
    }

    global.GEOrank = global.GEOrank || {};
    global.GEOrank.GeoflowHandoff = {
        fetchStatus: fetchGeoflowStatus,
        send: sendHandoff,
        formatResultMessage,
        openResult,
        openViaSso: openGeoflowViaSso,
        fetchReview,
        fetchTaskStatus,
    };
})(window);
