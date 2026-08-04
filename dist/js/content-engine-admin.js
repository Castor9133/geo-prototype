(function () {
  const TOKEN_KEYS = ["georank_admin_token", "georank_token", "token"];
  const isPublicShell =
    document.body.classList.contains("ce-page--public")
    || document.body.dataset.ceShell === "public";

  function getToken() {
    for (const key of TOKEN_KEYS) {
      const value = localStorage.getItem(key);
      if (value) return value;
    }
    return "";
  }

  function loginHref() {
    const returnUrl = window.location.pathname + window.location.search + window.location.hash;
    return `/admin/?returnUrl=${encodeURIComponent(returnUrl || "/knowledge")}`;
  }

  function isDemoOpenAccess() {
    if (window.GEORANK_OPEN_DEMO === true) return true;
    const host = String(window.location.hostname || "").toLowerCase();
    if (host === "localhost" || host === "127.0.0.1" || host === "::1") return true;
    if (/^(10\.|192\.168\.|172\.(1[6-9]|2\d|3[0-1])\.|169\.254\.)/.test(host)) return true;
    return Boolean(window.GEOrank?.APIKeyStore?.policy?.allow_anonymous_ai_usage);
  }

  function redirectToLogin() {
    window.location.href = loginHref();
  }

  function showAuthGate(visible) {
    const gate = document.getElementById("ce-auth-gate");
    if (!gate) return;
    // 本地演示永不展示登录门
    if (isDemoOpenAccess()) {
      gate.classList.add("hidden");
      return;
    }
    gate.classList.toggle("hidden", !visible);
    const link = document.getElementById("ce-auth-login");
    if (link) link.href = loginHref();
  }

  function headers(json = true) {
    const h = {};
    if (json) h["Content-Type"] = "application/json";
    const token = getToken();
    if (token) h.Authorization = `Bearer ${token}`;
    return h;
  }

  async function api(path, opts = {}) {
    const res = await fetch(`/api/content-engine${path}`, {
      ...opts,
      headers: { ...headers(!(opts.body instanceof FormData)), ...(opts.headers || {}) },
    });
    if (res.status === 401 || res.status === 403) {
      if (isDemoOpenAccess()) {
        showAuthGate(false);
        throw new Error("暂时无法免登录访问，请稍后重试或联系管理员");
      }
      if (isPublicShell) {
        showAuthGate(true);
      } else {
        redirectToLogin();
      }
      throw new Error("需要管理员登录");
    }
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      const detail = data.detail;
      const msg = typeof detail === "string" ? detail : data.message || res.statusText;
      throw new Error(msg);
    }
    return data;
  }

  function $(id) {
    return document.getElementById(id);
  }

  function escapeHtml(value) {
    return String(value ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function ensureToastHost() {
    let host = document.getElementById("ce-toast-host");
    if (host) return host;
    host = document.createElement("div");
    host.id = "ce-toast-host";
    host.className = "ce-toast-host";
    host.setAttribute("aria-live", "polite");
    document.body.appendChild(host);
    return host;
  }

  function toast(message, kind = "info") {
    const host = ensureToastHost();
    const el = document.createElement("div");
    el.className = `ce-toast ce-toast--${kind}`;
    el.textContent = String(message || "");
    host.appendChild(el);
    requestAnimationFrame(() => el.classList.add("is-in"));
    window.setTimeout(() => {
      el.classList.remove("is-in");
      window.setTimeout(() => el.remove(), 220);
    }, 2600);
  }

  async function withBusy(button, work, busyLabel) {
    if (!button) return work();
    if (button.dataset.busy === "1") return;
    const original = button.textContent;
    button.dataset.busy = "1";
    button.disabled = true;
    button.classList.add("is-busy");
    if (busyLabel) button.textContent = busyLabel;
    try {
      return await work();
    } finally {
      button.dataset.busy = "0";
      button.disabled = false;
      button.classList.remove("is-busy");
      button.textContent = original;
    }
  }

  let currentTaskId = null;
  let currentDraft = "";
  let currentTemplateKey = "";
  let templates = [];
  let suppressDocAutofill = false;
  let promptCache = [];
  let kbCache = [];
  let selectedKbIds = new Set();
  let docCache = [];
  let ceBootReady = false;

  function activateTab(name) {
    if (!name) return;
    const tabBtn = document.querySelector(`.tab[data-tab="${name}"]`);
    const panel = document.getElementById(`panel-${name}`);
    if (!tabBtn && !panel) return;
    document.querySelectorAll(".tab").forEach((b) => b.classList.toggle("active", b.dataset.tab === name));
    document.querySelectorAll(".panel").forEach((p) => p.classList.toggle("active", p.id === `panel-${name}`));
    if (panel) {
      panel.scrollIntoView({ behavior: "smooth", block: "start" });
    }
    try {
      const url = new URL(window.location.href);
      url.searchParams.set("tab", name);
      window.history.replaceState({}, "", url);
    } catch (_) {
      /* ignore */
    }
    // 切到提示词页时若下拉仍空，立刻补拉（避免 init 后半段失败导致永久空白）
    if (name === "prompts" && ceBootReady) {
      const pick = $("prompt-pick");
      const empty = !pick || !pick.options.length || (pick.options.length === 1 && !pick.options[0].value);
      if (empty || !promptCache.length) {
        refreshPrompts().catch((e) => {
          if ($("prompt-body")) $("prompt-body").textContent = String(e.message || e);
        });
      }
    }
  }

  function hrefForMissingTab(name) {
    if (name === "tasks" || name === "channels") {
      return name === "tasks" ? "/distribute?tab=tasks" : `/distribute?tab=${encodeURIComponent(name)}`;
    }
    if (name === "kb" || name === "hub") {
      return `/knowledge?tab=${encodeURIComponent(name)}`;
    }
    if (name === "prompts") {
      return pathNorm === "/distribute" ? "/distribute?tab=prompts" : `/knowledge?tab=prompts`;
    }
    return null;
  }

  document.querySelectorAll(".tab").forEach((btn) => {
    btn.addEventListener("click", () => activateTab(btn.dataset.tab));
  });

  const params = new URLSearchParams(window.location.search);
  const pathNorm = String(window.location.pathname || "").replace(/\.html$/, "").replace(/\/+$/, "") || "/";
  // 旧链 /knowledge?tab=tasks|channels → 独立分发页，避免与知识库导航双高亮
  if (pathNorm === "/knowledge") {
    const legacyTab = params.get("tab");
    if (legacyTab === "tasks" || legacyTab === "channels") {
      const next = legacyTab === "tasks" ? "/distribute?tab=tasks" : `/distribute?tab=${encodeURIComponent(legacyTab)}`;
      window.location.replace(next);
      return;
    }
  }
  if (pathNorm === "/distribute") {
    const legacyTab = params.get("tab");
    if (legacyTab === "kb" || legacyTab === "hub") {
      window.location.replace(`/knowledge?tab=${encodeURIComponent(legacyTab)}`);
      return;
    }
  }
  const deepTab = params.get("tab")
    || document.body.getAttribute("data-ce-default-tab")
    || (pathNorm === "/distribute" ? "tasks" : "");
  if (deepTab) activateTab(deepTab);

  async function loadStatus() {
    const el = $("backend-status");
    if (!el) return;
    // 前台编辑页不展示工程模式串（native-python 等）
    const isPublic = document.body.classList.contains("ce-page--public");
    if (isPublic) {
      el.textContent = "就绪";
      el.hidden = true;
      return;
    }
    try {
      const s = await fetch("/api/settings/content-backend").then((r) => r.json());
      el.textContent = `模式：${s.mode} — ${s.note}`;
      el.hidden = false;
    } catch (e) {
      el.textContent = String(e.message || e);
      el.hidden = false;
    }
  }

  async function loadTemplates() {
    try {
      const data = await api("/channel-templates");
      templates = data.items || [];
    } catch (_) {
      const local = await fetch("/data/channel-templates.json").then((r) => r.json()).catch(() => ({ items: [] }));
      templates = local.items || [];
    }
    const opts = templates
      .map((t) => `<option value="${escapeHtml(t.key)}">${escapeHtml(t.name)} (${escapeHtml(t.key)})</option>`)
      .join("");
    if ($("task-template")) {
      $("task-template").innerHTML = `<option value="">自动（跟渠道）</option>` + opts;
    }
    if ($("ch-template")) {
      $("ch-template").innerHTML = opts || `<option value="wechat-article">公众号文章</option>`;
    }
    if ($("template-manifest")) {
      $("template-manifest").textContent = JSON.stringify({ items: templates }, null, 2);
    }
  }

  function shellClass(templateKey) {
    const hit = templates.find((t) => t.key === templateKey);
    return hit?.shell || "wechat";
  }

  function renderShellPreview(title, body, templateKey) {
    const shell = shellClass(templateKey || "wechat-article");
    const names = {
      wechat: "微信公众号 · 文章",
      zhihu: "知乎 · 回答",
      xiaohongshu: "小红书 · 笔记",
      faq: "官网 · FAQ",
      douyin: "抖音 · 口播提纲",
    };
    const flowKeys = (templates.find((t) => t.key === templateKey) || {}).flow_theme_keys || [];
    const box = $("shell-preview");
    box.className = `shell-preview shell--${shell}`;
    box.innerHTML = `
      <div class="shell-preview__chrome">
        <span>${escapeHtml(names[shell] || shell)}</span>
        <span>${escapeHtml(templateKey || "—")}</span>
      </div>
      <div class="shell-preview__body">
        ${shell === "zhihu" ? `<div class="shell-preview__title">${escapeHtml(title || "未命名")}</div>` : ""}
        ${escapeHtml(body || "（无正文）")}
        <div class="shell-preview__meta">对照 GEOFlow themes: ${escapeHtml(flowKeys.join(", ") || "—")}（静态预览，无编译）</div>
      </div>`;
  }

  function fillKbMetaFromSelection() {
    const kbId = $("kb-select")?.value;
    const kb = kbCache.find((k) => k.id === kbId);
    if (!kb) return;
    if ($("kb-name")) $("kb-name").value = kb.name || "";
    if ($("kb-desc")) $("kb-desc").value = kb.description || "";
    if ($("kb-detail-sub")) {
      $("kb-detail-sub").textContent = kb.name
        ? `当前：${kb.name}`
        : "编辑名称、描述与 Markdown 证据正文，再提交语义切片";
    }
  }

  function syncTaskKbSelect() {
    const primary = [...selectedKbIds][0] || "";
    if ($("task-kb")) $("task-kb").value = primary;
    return primary;
  }

  function renderTaskKbCards(items, selectedId) {
    const host = $("task-kb-cards");
    if (!host) return;
    if (selectedId) {
      selectedKbIds = new Set(
        Array.isArray(selectedId) ? selectedId.filter(Boolean) : [selectedId].filter(Boolean)
      );
    } else if (!selectedKbIds.size && $("task-kb")?.value) {
      selectedKbIds.add($("task-kb").value);
    }
    const validIds = new Set((items || []).map((k) => k.id));
    selectedKbIds = new Set([...selectedKbIds].filter((id) => validIds.has(id)));
    syncTaskKbSelect();
    host.innerHTML =
      (items || [])
        .map((k) => {
          const on = selectedKbIds.has(k.id);
          return `<button type="button" class="ce-kb-card${on ? " is-selected" : ""}" data-kb-card="${k.id}" aria-pressed="${on}">
          <input class="ce-kb-card__check" type="checkbox" tabindex="-1" ${on ? "checked" : ""} aria-hidden="true">
          <span class="ce-kb-card__text">
            <strong>${escapeHtml(k.name)}</strong>
            <small>${escapeHtml(k.slug || "")} · ${k.doc_count || 0} 文档</small>
          </span>
        </button>`;
        })
        .join("") || `<p class="ce-hint">暂无知识库，请先在「知识库」页导入或新建。</p>`;
    host.querySelectorAll("[data-kb-card]").forEach((btn) => {
      btn.addEventListener("click", () => {
        const id = btn.dataset.kbCard;
        if (!id) return;
        if (selectedKbIds.has(id)) selectedKbIds.delete(id);
        else selectedKbIds.add(id);
        syncTaskKbSelect();
        renderTaskKbCards(kbCache);
      });
    });
  }

  async function refreshDocs(kbId) {
    if (!$("doc-table") && !$("kb-select")) return;
    if (!kbId) {
      $("doc-table").innerHTML = "<tr><td colspan=3>选择知识库</td></tr>";
      docCache = [];
      return;
    }
    const detail = await api(`/knowledge-bases/${kbId}`);
    docCache = detail.documents || [];
    if ($("kb-name") && detail.name) $("kb-name").value = detail.name;
    if ($("kb-desc") && detail.description != null) $("kb-desc").value = detail.description || "";
    if ($("kb-detail-sub") && detail.name) $("kb-detail-sub").textContent = `当前：${detail.name}`;

    $("doc-table").innerHTML =
      docCache
        .map(
          (d) => `<tr>
        <td>${escapeHtml(d.title)}<br><small>${escapeHtml(d.source_path || "")}</small></td>
        <td>${d.chunk_count}</td>
        <td>
          <button type="button" class="btn" data-edit-doc="${d.id}">编辑</button>
          <button type="button" class="btn" data-del-doc="${d.id}">删除</button>
        </td>
      </tr>`
        )
        .join("") || "<tr><td colspan=3>暂无文档</td></tr>";

    $("doc-table").querySelectorAll("[data-edit-doc]").forEach((btn) => {
      btn.addEventListener("click", () => {
        const doc = docCache.find((d) => d.id === btn.dataset.editDoc);
        if (!doc) return;
        $("doc-title").value = doc.title || "";
        $("doc-body").value = doc.body || "";
        activateTab("kb");
      });
    });
    $("doc-table").querySelectorAll("[data-del-doc]").forEach((btn) => {
      btn.addEventListener("click", async () => {
        if (!confirm("删除该文档及其切片？")) return;
        await api(`/documents/${btn.dataset.delDoc}`, { method: "DELETE" });
        await refreshKbs();
        await refreshDocs($("kb-select").value);
      });
    });

    if (docCache[0] && !suppressDocAutofill && !$("doc-body")?.value.trim()) {
      $("doc-title").value = docCache[0].title || "";
      $("doc-body").value = docCache[0].body || "";
    }
    suppressDocAutofill = false;
  }

  function syncImportExampleVisibility(kbCount) {
    const btn = $("btn-import-dji");
    if (!btn) return;
    const count = Number(kbCount);
    const hasKb = Number.isFinite(count) ? count > 0 : (kbCache && kbCache.length > 0);
    btn.hidden = hasKb;
    btn.textContent = "导入示例知识库";
  }

  async function refreshKbs() {
    const data = await api("/knowledge-bases");
    kbCache = data.items || [];
    syncImportExampleVisibility(kbCache.length);
    const tbody = $("kb-table");
    if (tbody) {
      tbody.innerHTML =
        kbCache
          .map(
            (k) => `<tr>
        <td>${escapeHtml(k.name)}<br><small>${escapeHtml(k.slug)}</small></td>
        <td>${k.doc_count}</td>
        <td>${k.chunk_count}</td>
        <td>${k.vectorized_count}</td>
        <td>
          <button type="button" class="btn" data-open-kb="${k.id}">打开</button>
          <button type="button" class="btn" data-del-kb="${k.id}">删除</button>
        </td>
      </tr>`
          )
          .join("") || "<tr><td colspan=5>暂无知识库 · 可新建或导入示例</td></tr>";
    }

    const opts = kbCache.map((k) => `<option value="${k.id}">${escapeHtml(k.name)}</option>`).join("");
    const prevKb = $("kb-select")?.value || "";
    const prevTaskKb = $("task-kb")?.value || "";
    if ($("kb-select")) {
      $("kb-select").innerHTML = opts || `<option value="">暂无知识库</option>`;
    }
    if ($("task-kb")) {
      $("task-kb").innerHTML = `<option value="">不绑定知识库</option>` + opts;
      if (prevTaskKb && kbCache.some((k) => k.id === prevTaskKb)) $("task-kb").value = prevTaskKb;
    }

    const prefer = params.get("kb");
    if ($("kb-select")) {
      if (prefer && kbCache.some((k) => k.id === prefer)) {
        $("kb-select").value = prefer;
      } else if (prevKb && kbCache.some((k) => k.id === prevKb)) {
        $("kb-select").value = prevKb;
      }
    }

    if (!selectedKbIds.size && prevTaskKb && kbCache.some((k) => k.id === prevTaskKb)) {
      selectedKbIds.add(prevTaskKb);
    }
    renderTaskKbCards(kbCache);

    if (tbody) {
      tbody.querySelectorAll("[data-open-kb]").forEach((btn) => {
        btn.addEventListener("click", async () => {
          if ($("kb-select")) $("kb-select").value = btn.dataset.openKb;
          const href = hrefForMissingTab("kb");
          if (href && !document.querySelector('.tab[data-tab="kb"]')) {
            window.location.href = href;
            return;
          }
          activateTab("kb");
          fillKbMetaFromSelection();
          await refreshDocs(btn.dataset.openKb);
        });
      });
      tbody.querySelectorAll("[data-del-kb]").forEach((btn) => {
        btn.addEventListener("click", async () => {
          if (!confirm("删除整个知识库？")) return;
          await api(`/knowledge-bases/${btn.dataset.delKb}`, { method: "DELETE" });
          await refreshKbs();
        });
      });
    }

    if ($("kb-select")?.value) {
      fillKbMetaFromSelection();
      await refreshDocs($("kb-select").value);
    }
  }

  async function loadPromptDetail(pid) {
    if (!pid) {
      if ($("prompt-body")) $("prompt-body").textContent = "从下拉列表选择提示词查看正文";
      return null;
    }
    const p = await api(`/prompts/${pid}`);
    if ($("prompt-body")) $("prompt-body").textContent = p.body || "（无正文）";
    return p;
  }

  async function refreshPrompts() {
    const pick = $("prompt-pick");
    const taskPrompt = $("task-prompt");
    if (pick && !pick.options.length) {
      pick.innerHTML = `<option value="">加载中…</option>`;
    }
    const data = await api("/prompts");
    promptCache = data.items || [];
    const opts = promptCache
      .map((p) => `<option value="${p.id}">${escapeHtml(p.title)}</option>`)
      .join("");
    const prevPick = pick?.value || "";
    const prevTask = taskPrompt?.value || "";
    if (pick) {
      pick.innerHTML = opts || `<option value="">暂无提示词 · 可点「恢复内置 10 套」</option>`;
      if (prevPick && promptCache.some((p) => p.id === prevPick)) pick.value = prevPick;
      else if (promptCache[0]) pick.value = promptCache[0].id;
    }
    if (taskPrompt) {
      taskPrompt.innerHTML =
        `<option value="">请选择内容提示词</option>` +
        (opts || `<option value="" disabled>暂无提示词</option>`);
      if (prevTask && promptCache.some((p) => p.id === prevTask)) taskPrompt.value = prevTask;
    }
    if (pick?.value) {
      try {
        await loadPromptDetail(pick.value);
      } catch (e) {
        if ($("prompt-body")) {
          $("prompt-body").textContent = `模板列表已加载，但正文读取失败：${e.message || e}`;
        }
      }
    }
  }

  function setTaskActions(enabled) {
    if ($("btn-preview-shell")) $("btn-preview-shell").disabled = !enabled;
    if ($("btn-mark-dist")) $("btn-mark-dist").disabled = !enabled;
    ["btn-save-template-draft", "btn-save-channel-draft", "btn-submit-review"].forEach((id) => {
      if ($(id)) $(id).disabled = !enabled;
    });
    if ($("btn-approve-ready")) $("btn-approve-ready").disabled = !enabled;
  }

  function setDraftText(text) {
    const el = $("task-draft");
    if (!el) return;
    if ("value" in el) el.value = text || "";
    else el.textContent = text || "";
  }

  function getDraftText() {
    const el = $("task-draft");
    if (!el) return "";
    return ("value" in el ? el.value : el.textContent) || "";
  }

  function setWorkflowHint(task) {
    const el = $("task-workflow-hint");
    if (!el) return;
    const wf = task?.workflow_status || "—";
    const sug = task?.promote_suggestion
      ? ` · 建议${task.promote_suggestion === "promote" ? "沉淀" : "剔除"}`
      : "";
    el.textContent = `状态：${wf}${sug} · 模板稿可改 → 平台适配稿可改 → 提交审核 → ready`;
  }

  const TASK_STATUS_LABEL = {
    pending: "待生成",
    running: "生成中",
    completed: "已完成",
    failed: "失败",
    open: "开启",
    paused: "暂停",
    done: "完成",
    claimed: "已领题",
    template_draft: "模板稿",
    channel_draft: "平台稿",
    in_review: "审核中",
    ready: "ready",
    archived: "已剔除",
    promoted: "已沉淀",
  };

  function formatTaskStatus(status, distributed, workflowStatus) {
    const wf = workflowStatus && TASK_STATUS_LABEL[workflowStatus]
      ? TASK_STATUS_LABEL[workflowStatus]
      : null;
    const label = wf || TASK_STATUS_LABEL[status] || status || "—";
    return distributed ? `${label} · 已就绪` : label;
  }

  let pendingKeywordsState = { keywords: [], entity: "", run_id: "", target_platforms: [] };
  const DEFAULT_AI_PLATFORMS = ["豆包", "元宝", "Kimi", "DeepSeek"];
  let aiFocusScript = null;
  let taskTargetPlatforms = new Set(DEFAULT_AI_PLATFORMS);

  async function loadAiFocusScript() {
    if (aiFocusScript) return aiFocusScript;
    try {
      const res = await fetch("/api/keywords/ai-focus", { credentials: "same-origin" });
      if (res.ok) {
        aiFocusScript = await res.json();
        return aiFocusScript;
      }
    } catch (_) {
      /* fall through */
    }
    aiFocusScript = {
      disclaimer: "目标 AI 侧重暂不可用",
      platforms: DEFAULT_AI_PLATFORMS,
      items: DEFAULT_AI_PLATFORMS.map((platform) => ({
        platform,
        generation_focus: "",
        avoid: [],
        source_prefs: [],
      })),
    };
    return aiFocusScript;
  }

  function selectedTaskPlatforms() {
    return Array.from(taskTargetPlatforms);
  }

  function renderTaskAiPlatforms() {
    const host = $("task-ai-platforms");
    if (!host) return;
    const platforms = (aiFocusScript && aiFocusScript.platforms) || DEFAULT_AI_PLATFORMS;
    host.innerHTML = platforms
      .map((p) => {
        const on = taskTargetPlatforms.has(p);
        return `<label class="ce-ai-plat"><input type="checkbox" data-task-ai-plat="${escapeHtml(p)}" ${on ? "checked" : ""}> ${escapeHtml(p)}</label>`;
      })
      .join("");
    host.querySelectorAll("[data-task-ai-plat]").forEach((input) => {
      input.addEventListener("change", () => {
        const name = input.getAttribute("data-task-ai-plat") || "";
        if (!name) return;
        if (input.checked) taskTargetPlatforms.add(name);
        else taskTargetPlatforms.delete(name);
        if (!taskTargetPlatforms.size) {
          taskTargetPlatforms = new Set(platforms);
          renderTaskAiPlatforms();
        }
        renderTaskAiFocusCard();
      });
    });
  }

  function renderTaskAiFocusCard() {
    const host = $("task-ai-focus-card");
    if (!host) return;
    const items = ((aiFocusScript && aiFocusScript.items) || []).filter((row) =>
      taskTargetPlatforms.has(row.platform)
    );
    if (!items.length) {
      host.innerHTML = '<p class="ce-hint">请选择至少一个目标 AI。</p>';
      return;
    }
    host.innerHTML = items
      .map((row) => {
        const prefs = (row.source_prefs || [])
          .map((sp) => `<span class="ce-ai-chip">${escapeHtml(sp.type)}</span>`)
          .join("");
        const avoids = (row.avoid || []).map((a) => escapeHtml(a)).join(" · ");
        return `<article class="ce-ai-focus-item">`
          + `<h4>${escapeHtml(row.platform)}</h4>`
          + `<p>${escapeHtml(row.generation_focus || "")}</p>`
          + `<div class="ce-ai-chips">${prefs}</div>`
          + (avoids ? `<p class="ce-hint">易踩坑：${avoids}</p>` : "")
          + `</article>`;
      })
      .join("");
  }

  function applyTargetPlatformsFromPending(platforms) {
    if (!Array.isArray(platforms) || !platforms.length) return;
    taskTargetPlatforms = new Set(platforms.filter(Boolean));
    if (!taskTargetPlatforms.size) taskTargetPlatforms = new Set(DEFAULT_AI_PLATFORMS);
    renderTaskAiPlatforms();
    renderTaskAiFocusCard();
  }

  function readPendingKeywords() {
    try {
      const raw = sessionStorage.getItem("georank_pending_keywords");
      if (!raw) return null;
      const parsed = JSON.parse(raw);
      if (!parsed || !Array.isArray(parsed.keywords) || !parsed.keywords.length) return null;
      return parsed;
    } catch (_) {
      return null;
    }
  }

  function applyPendingKeyword(keyword) {
    const entity = pendingKeywordsState.entity || "产品";
    if ($("task-keyword")) $("task-keyword").value = keyword;
    if ($("task-title")) $("task-title").value = `${entity} · ${keyword}`.slice(0, 300);
    document.querySelectorAll(".ce-keyword-chip").forEach((chip) => {
      chip.classList.toggle("is-active", chip.dataset.keyword === keyword);
    });
  }

  function renderPendingKeywords() {
    const bar = $("pending-keywords-bar");
    const host = $("pending-keywords-chips");
    if (!bar || !host) return;
    const data = readPendingKeywords();
    const Workflow = window.GEOrank?.SuiteWorkflow;
    const fromMeta = Workflow?.load?.()?.meta?.selected_keywords
      || Workflow?.load?.()?.lastHandoff?.selected_keywords
      || [];
    const keywords = (data && data.keywords) || (Array.isArray(fromMeta) ? fromMeta : []);
    if (!keywords.length) {
      bar.hidden = true;
      bar.classList.add("hidden");
      return;
    }
    const platforms =
      (data && data.target_platforms)
      || Workflow?.load?.()?.meta?.target_platforms
      || Workflow?.load?.()?.lastHandoff?.meta?.target_platforms
      || [];
    pendingKeywordsState = {
      keywords,
      entity: (data && data.entity) || (Workflow?.load?.()?.run?.entity) || "产品",
      run_id: (data && data.run_id) || Workflow?.getRunId?.() || "",
      target_platforms: Array.isArray(platforms) ? platforms : [],
    };
    applyTargetPlatformsFromPending(pendingKeywordsState.target_platforms);
    bar.hidden = false;
    bar.classList.remove("hidden");
    host.innerHTML = keywords
      .map(
        (kw) =>
          `<button type="button" class="ce-keyword-chip" data-keyword="${escapeHtml(kw)}">${escapeHtml(kw)}</button>`
      )
      .join("");
    host.querySelectorAll(".ce-keyword-chip").forEach((chip) => {
      chip.addEventListener("click", () => applyPendingKeyword(chip.dataset.keyword || ""));
    });
    if (!$("task-title")?.value?.trim()) {
      applyPendingKeyword(keywords[0]);
    }
  }

  async function refreshTasks() {
    if (!$("task-table")) return;
    const data = await api("/tasks");
    $("task-table").innerHTML =
      data.items
        .map(
          (t) => `<tr>
        <td>${escapeHtml(t.title)}</td>
        <td>${escapeHtml(formatTaskStatus(t.status, t.distributed, t.workflow_status))}</td>
        <td><button type="button" class="btn" data-tid="${t.id}">打开</button></td>
      </tr>`
        )
        .join("") || "<tr><td colspan=3>暂无任务</td></tr>";
    $("task-table").querySelectorAll("[data-tid]").forEach((b) => {
      b.addEventListener("click", async () => {
        const t = await api(`/tasks/${b.dataset.tid}`);
        currentTaskId = t.id;
        currentDraft = t.channel_draft_body || t.template_draft_body || t.draft_body || t.error_message || "";
        currentTemplateKey = t.template_key || $("task-template")?.value || "wechat-article";
        if ($("task-title") && t.title) $("task-title").value = t.title;
        if ($("task-keyword") && t.input_query) $("task-keyword").value = t.input_query;
        if ($("task-prompt") && t.prompt_id) {
          const opt = [...($("task-prompt").options || [])].find((o) => o.value === t.prompt_id);
          if (opt) $("task-prompt").value = t.prompt_id;
        }
        setDraftText(currentDraft || "（无正文）");
        setWorkflowHint(t);
        setTaskActions(Boolean(currentDraft));
        $("shell-preview")?.classList.add("hidden");
        activateTab("tasks");
        $("task-draft")?.scrollIntoView({ behavior: "smooth", block: "nearest" });
      });
    });
  }

  async function refreshChannels() {
    if (!$("ch-table")) return;
    const data = await api("/channels");
    $("ch-table").innerHTML =
      data.items
        .map(
          (c) => `<tr>
        <td>${escapeHtml(c.name)}</td>
        <td>${escapeHtml(c.channel_type)}</td>
        <td>${escapeHtml(c.template_key || "—")}</td>
      </tr>`
        )
        .join("") || "<tr><td colspan=3>暂无</td></tr>";
    $("task-channel").innerHTML =
      `<option value="">不分发渠道</option>` +
      data.items.map((c) => `<option value="${c.id}" data-tk="${escapeHtml(c.template_key || "")}">${escapeHtml(c.name)}</option>`).join("");
  }

  $("kb-select")?.addEventListener("change", () => {
    fillKbMetaFromSelection();
    $("doc-title").value = "";
    $("doc-body").value = "";
    void refreshDocs($("kb-select").value);
  });

  $("btn-save-kb")?.addEventListener("click", async () => {
    const kbId = $("kb-select")?.value;
    if (!kbId) {
      toast("请先选择或新建知识库", "warn");
      return;
    }
    const btn = $("btn-save-kb");
    try {
      await withBusy(btn, async () => {
        await api(`/knowledge-bases/${kbId}`, {
          method: "PATCH",
          body: JSON.stringify({
            name: $("kb-name").value.trim(),
            description: $("kb-desc").value,
          }),
        });
        await refreshKbs();
        $("kb-select").value = kbId;
        fillKbMetaFromSelection();
      }, "保存中…");
      toast("知识库信息已保存", "ok");
    } catch (e) {
      toast(String(e.message || e), "err");
    }
  });

  $("btn-import-dji")?.addEventListener("click", async () => {
    $("hub-out").textContent = "导入中…";
    try {
      const r = await api("/knowledge-bases/import-dji-demo", { method: "POST", body: "{}" });
      if ($("hub-out")) $("hub-out").textContent = JSON.stringify(r, null, 2);
      await Promise.all([refreshKbs(), refreshPrompts(), refreshChannels()]);
      await refreshHubDashboard();
      toast("示例知识库已导入", "ok");
    } catch (e) {
      if ($("hub-out")) $("hub-out").textContent = String(e.message || e);
      toast(String(e.message || e), "err");
    }
  });

  function setText(id, value) {
    const el = $(id);
    if (el) el.textContent = value;
  }

  async function refreshHubDashboard() {
    let summary = null;
    try {
      summary = await fetch("/api/content-engine/public/demo-summary").then((x) => x.json());
      if ($("hub-out")) $("hub-out").textContent = JSON.stringify(summary, null, 2);
    } catch (e) {
      if ($("hub-out")) $("hub-out").textContent = String(e.message || e);
    }

    let kbs = { items: [] };
    try {
      kbs = await api("/knowledge-bases");
    } catch (_) {
      /* 未登录时已跳转 */
    }

    const kb = (summary && summary.knowledge_base) || kbs.items[0];
    const tasks = (summary && summary.recent_tasks) || [];
    const drafts = tasks.filter((t) => t.has_draft).length;
    const docs = kb ? kb.doc_count || 0 : 0;
    const chunks = kb ? kb.chunk_count || 0 : 0;
    const vec = kb ? kb.vectorized_count || 0 : 0;
    const readyPct = chunks ? Math.round((vec / Math.max(chunks, 1)) * 100) : 0;

    setText("kpi-docs", String(docs || kbs.items.reduce((n, k) => n + (k.doc_count || 0), 0)));
    setText("kpi-chunks", String(chunks || kbs.items.reduce((n, k) => n + (k.chunk_count || 0), 0)));
    setText("kpi-vec", String(vec || kbs.items.reduce((n, k) => n + (k.vectorized_count || 0), 0)));
    setText("kpi-tasks", String(tasks.length));
    setText("kpi-docs-note", (summary && summary.demo_ready) || (kbs.items && kbs.items.length)
      ? "示例库 / 自建库"
      : "可导入示例或新建");
    setText("kpi-chunks-note", "可检索单元");
    setText("kpi-vec-note", `${readyPct}% 召回就绪`);
    setText("kpi-tasks-note", `草稿 ${drafts}`);
    setText("side-kb", String(kbs.items.length));
    setText("side-docs", String(docs));
    setText("side-chunks", String(chunks));
    setText("side-drafts", String(drafts));
    setText("pill-pending", (summary && summary.demo_ready) || (kbs.items && kbs.items.length) ? "已就绪" : "待导入");
    setText("pill-audit", drafts ? `有草稿 ${drafts}` : "待生成");
    setText("pill-ok", `已就绪 ${vec}`);
    const bar = $("embed-bar");
    if (bar) bar.style.width = `${readyPct}%`;
    setText("embed-label", `${readyPct}% · ${vec}/${chunks || 0}`);
    syncImportExampleVisibility((kbs.items || []).length);

    const tbody = $("evidence-table");
    if (tbody) {
      if (!kbs.items.length) {
        tbody.innerHTML = "<tr><td colspan=6>暂无知识库 · 可新建或导入示例知识库</td></tr>";
      } else {
        tbody.innerHTML = kbs.items
          .map(
            (k) => `<tr>
            <td>${escapeHtml(k.name)}<br><small>${escapeHtml(k.slug)}</small></td>
            <td>知识库</td>
            <td>${k.chunk_count}</td>
            <td>${k.vectorized_count}</td>
            <td>${k.vectorized_count > 0 ? '<span class="badge-ok">已验证</span>' : '<span class="badge-wait">待向量</span>'}</td>
            <td><button type="button" class="btn" data-open-kb="${k.id}">打开</button></td>
          </tr>`
          )
          .join("");
        tbody.querySelectorAll("[data-open-kb]").forEach((btn) => {
          btn.addEventListener("click", async () => {
            $("kb-select").value = btn.dataset.openKb;
            activateTab("kb");
            await refreshDocs(btn.dataset.openKb);
          });
        });
      }
    }
  }

  $("btn-refresh-hub")?.addEventListener("click", async () => {
    await refreshHubDashboard();
  });

  document.querySelectorAll("[data-goto-tab]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const name = btn.getAttribute("data-goto-tab");
      if (!name) return;
      if (document.querySelector(`.tab[data-tab="${name}"]`) || document.getElementById(`panel-${name}`)) {
        activateTab(name);
        return;
      }
      const href = hrefForMissingTab(name);
      if (href) window.location.href = href;
    });
  });

  $("btn-create-kb")?.addEventListener("click", async () => {
    const name = ($("kb-name").value || "").trim();
    if (!name) {
      toast("请填写知识库名称", "warn");
      $("kb-name")?.focus();
      return;
    }
    try {
      await withBusy($("btn-create-kb"), async () => {
        const created = await api("/knowledge-bases", {
          method: "POST",
          body: JSON.stringify({ name, description: $("kb-desc").value }),
        });
        await refreshKbs();
        if (created?.id) {
          $("kb-select").value = created.id;
          fillKbMetaFromSelection();
          await refreshDocs(created.id);
        }
      }, "创建中…");
      toast("知识库已创建", "ok");
    } catch (e) {
      toast(String(e.message || e), "err");
    }
  });

  $("btn-add-doc")?.addEventListener("click", async () => {
    const kbId = $("kb-select").value;
    if (!kbId) return toast("请先选择知识库", "warn");
    if (!($("doc-title").value || "").trim() || !($("doc-body").value || "").trim()) {
      toast("请填写文档标题和正文", "warn");
      return;
    }
    try {
      await withBusy($("btn-add-doc"), async () => {
        await api(`/knowledge-bases/${kbId}/documents`, {
          method: "POST",
          body: JSON.stringify({ title: $("doc-title").value, body: $("doc-body").value }),
        });
        suppressDocAutofill = true;
        $("doc-title").value = "";
        $("doc-body").value = "";
        await refreshKbs();
        await refreshDocs(kbId);
      }, "切片中…");
      toast("已提交语义切片", "ok");
    } catch (e) {
      toast(String(e.message || e), "err");
    }
  });

  $("btn-upload-doc")?.addEventListener("click", async () => {
    const kbId = $("kb-select").value;
    const file = $("doc-file").files?.[0];
    if (!kbId) return toast("请先选择知识库", "warn");
    if (!file) return toast("请选择 .md / .txt 文件", "warn");
    try {
      await withBusy($("btn-upload-doc"), async () => {
        const form = new FormData();
        form.append("file", file);
        if ($("doc-title").value) form.append("title", $("doc-title").value);
        const res = await fetch(`/api/content-engine/knowledge-bases/${kbId}/upload`, {
          method: "POST",
          headers: headers(false),
          body: form,
        });
        if (res.status === 401 || res.status === 403) {
          redirectToLogin();
          return;
        }
        const data = await res.json().catch(() => ({}));
        if (!res.ok) throw new Error(data.detail || data.message || res.statusText);
        $("doc-file").value = "";
        await refreshKbs();
        await refreshDocs(kbId);
        $("search-out").textContent = `已上传：${data.title}（${data.chunk_count} 切片）`;
      }, "上传中…");
      toast("文件已上传并切片", "ok");
    } catch (e) {
      toast(String(e.message || e), "err");
      $("search-out").textContent = String(e.message || e);
    }
  });

  $("btn-search")?.addEventListener("click", async () => {
    const kbId = $("kb-select").value;
    const query = $("search-q").value.trim();
    if (!kbId) return toast("请先选择知识库", "warn");
    if (!query) return toast("请输入检索问题", "warn");
    try {
      await withBusy($("btn-search"), async () => {
        const r = await api(`/knowledge-bases/${kbId}/search`, {
          method: "POST",
          body: JSON.stringify({ query, limit: 6 }),
        });
        $("search-out").textContent = (r.items || [])
          .map((h, i) => `#${i + 1} score=${h.score}\n${h.content}`)
          .join("\n\n---\n\n") || "无命中";
      }, "检索中…");
    } catch (e) {
      toast(String(e.message || e), "err");
    }
  });

  $("search-q")?.addEventListener("keydown", (ev) => {
    if (ev.key === "Enter") {
      ev.preventDefault();
      $("btn-search")?.click();
    }
  });

  $("btn-save-prompt")?.addEventListener("click", async () => {
    const id = $("prompt-id").value;
    const title = ($("prompt-title").value || "").trim();
    if (!title || !($("prompt-edit-body").value || "").trim()) {
      toast("请填写提示词标题和正文", "warn");
      return;
    }
    const body = { title, body: $("prompt-edit-body").value };
    try {
      await withBusy($("btn-save-prompt"), async () => {
        if (id) {
          await api(`/prompts/${id}`, { method: "PATCH", body: JSON.stringify(body) });
        } else {
          await api("/prompts", { method: "POST", body: JSON.stringify(body) });
        }
        $("prompt-id").value = "";
        $("prompt-title").value = "";
        $("prompt-edit-body").value = "";
        await refreshPrompts();
      }, "保存中…");
      toast(id ? "提示词已更新" : "提示词已创建", "ok");
    } catch (e) {
      toast(String(e.message || e), "err");
    }
  });

  $("btn-reset-prompt")?.addEventListener("click", () => {
    $("prompt-id").value = "";
    $("prompt-title").value = "";
    $("prompt-edit-body").value = "";
    toast("已清空编辑区", "info");
  });

  $("prompt-pick")?.addEventListener("change", async () => {
    await loadPromptDetail($("prompt-pick").value);
  });

  $("btn-load-prompt")?.addEventListener("click", async () => {
    const p = await loadPromptDetail($("prompt-pick")?.value);
    if (!p) {
      toast("请先选择提示词模板", "warn");
      return;
    }
    $("prompt-id").value = p.id;
    $("prompt-title").value = p.title;
    $("prompt-edit-body").value = p.body;
    activateTab("prompts");
    toast("已载入到编辑区", "ok");
  });

  $("btn-del-prompt")?.addEventListener("click", async () => {
    const pid = $("prompt-pick")?.value;
    if (!pid) return toast("请先选择提示词", "warn");
    if (!confirm("停用当前选中的提示词？")) return;
    try {
      await api(`/prompts/${pid}`, { method: "DELETE" });
      await refreshPrompts();
      toast("提示词已停用", "ok");
    } catch (e) {
      toast(String(e.message || e), "err");
    }
  });

  $("btn-restore-prompts")?.addEventListener("click", async () => {
    if (!confirm("恢复内置提示词模板，并停用被改乱的非内置项？")) return;
    try {
      const r = await withBusy($("btn-restore-prompts"), async () => {
        return api("/prompt-library/restore", { method: "POST", body: "{}" });
      }, "恢复中…");
      $("prompt-body").textContent = `已恢复 ${r.restored || 0} 套内置模板：\n${(r.titles || []).join("\n")}`;
      await refreshPrompts();
      toast(`已恢复 ${r.restored || 0} 套内置提示词`, "ok");
    } catch (e) {
      toast(String(e.message || e), "err");
    }
  });

  $("btn-create-task")?.addEventListener("click", async () => {
    const title = ($("task-title").value || "").trim();
    if (!title) {
      toast("请填写任务名称", "warn");
      $("task-title")?.focus();
      return;
    }
    if (!$("task-prompt")?.value) {
      toast("请先选择内容提示词模板", "warn");
      $("task-prompt")?.focus();
      return;
    }
    const channelSelect = $("task-channel");
    const selected = channelSelect?.options?.[channelSelect.selectedIndex];
    const channelTk = selected?.dataset?.tk || "";
    const templateKey = $("task-template")?.value || channelTk || null;
    const keyword = ($("task-keyword")?.value || "").trim() || title;
    const entity = pendingKeywordsState.entity
      || window.GEOrank?.SuiteWorkflow?.load?.()?.run?.entity
      || "";
    const body = {
      title,
      knowledge_base_id: syncTaskKbSelect() || null,
      prompt_id: $("task-prompt").value || null,
      channel_id: $("task-channel")?.value || null,
      template_key: templateKey,
      input_query: keyword,
      meta: {
        model: $("task-model")?.value || null,
        model_mode: $("task-model-mode")?.value || "fixed",
        status: $("task-status")?.value || "open",
        entity: entity || undefined,
        keyword,
        knowledge_base_ids: [...selectedKbIds],
        source: "distribute-template-first",
        target_platforms: selectedTaskPlatforms(),
        ai_focus_inject: Boolean($("task-ai-focus-inject")?.checked),
      },
    };
    setDraftText("生成中…");
    try {
      await withBusy($("btn-create-task"), async () => {
        const r = await api("/tasks", { method: "POST", body: JSON.stringify(body) });
        currentTaskId = r.id;
        const full = await api(`/tasks/${r.id}`);
        currentDraft = full.template_draft_body || full.draft_body || r.draft_preview || "";
        currentTemplateKey = full.template_key || templateKey || "wechat-article";
        setDraftText(currentDraft || "（无正文）");
        setWorkflowHint(full);
        setTaskActions(Boolean(currentDraft));
        $("shell-preview")?.classList.add("hidden");
        await refreshTasks();
      }, "生成中…");
      toast(currentDraft ? "模板稿已生成（可编辑）" : "任务已创建，但暂无正文", currentDraft ? "ok" : "warn");
    } catch (e) {
      setDraftText(String(e.message || e));
      toast(String(e.message || e), "err");
    }
  });

  $("btn-save-template-draft")?.addEventListener("click", async () => {
    if (!currentTaskId) return;
    const body = getDraftText();
    const t = await api(`/tasks/${currentTaskId}/template-draft`, {
      method: "PATCH",
      body: JSON.stringify({ body, template_key: currentTemplateKey || $("task-template")?.value }),
    });
    currentDraft = t.template_draft_body || body;
    setWorkflowHint(t);
    toast("模板稿已保存", "ok");
    await refreshTasks();
  });

  $("btn-save-channel-draft")?.addEventListener("click", async () => {
    if (!currentTaskId) return;
    const body = getDraftText();
    const t = await api(`/tasks/${currentTaskId}/channel-draft`, {
      method: "PATCH",
      body: JSON.stringify({
        body,
        channel_key: $("task-template")?.value || currentTemplateKey || "wechat-article",
      }),
    });
    currentDraft = t.channel_draft_body || body;
    setWorkflowHint(t);
    toast("平台适配稿已保存", "ok");
    await refreshTasks();
  });

  $("btn-submit-review")?.addEventListener("click", async () => {
    if (!currentTaskId) return;
    const t = await api(`/tasks/${currentTaskId}/submit-review`, { method: "POST", body: "{}" });
    setWorkflowHint(t);
    toast("已提交审核", "ok");
    await refreshTasks();
  });

  $("btn-approve-ready")?.addEventListener("click", async () => {
    if (!currentTaskId) return;
    try {
      const t = await api(`/tasks/${currentTaskId}/approve-ready`, { method: "POST", body: "{}" });
      setWorkflowHint(t);
      toast("已通过 → ready（可关联点名）", "ok");
      await refreshTasks();
    } catch (e) {
      toast(String(e.message || e), "err");
    }
  });

  $("btn-preview-shell")?.addEventListener("click", () => {
    currentDraft = getDraftText();
    if (!currentDraft) return;
    renderShellPreview($("task-title").value || "任务预览", currentDraft, currentTemplateKey);
    $("shell-preview").classList.remove("hidden");
  });

  $("btn-mark-dist")?.addEventListener("click", async () => {
    if (!currentTaskId) return;
    currentDraft = getDraftText();
    const r = await api(`/tasks/${currentTaskId}/mark-distributed`, { method: "POST", body: "{}" });
    setDraftText(`${currentDraft}\n\n——\n已标记就绪（未真实发布） · status=${r.status}`);
    const Workflow = window.GEOrank?.SuiteWorkflow;
    if (Workflow?.handoff) {
      const chLabel = ($("task-channel")?.selectedOptions?.[0]?.textContent || "channel").trim();
      Workflow.handoff("distribute", {
        task_ids: [currentTaskId],
        channel_ready: [chLabel],
        meta: { preview_only: true },
      }).catch(() => null);
      Workflow.markComplete("distribute", { task_id: currentTaskId, ready: true });
      Workflow.mountBar({
        stepId: "distribute",
        force: true,
        hint: "渠道壳已标记就绪（预览·不外发）",
        nextHref: Workflow.buildHref("measure"),
        nextLabel: "下一步：观测回放",
      });
    }
    await refreshTasks();
  });

  $("btn-create-ch")?.addEventListener("click", async () => {
    await api("/channels", {
      method: "POST",
      body: JSON.stringify({
        name: $("ch-name").value,
        channel_type: $("ch-type").value,
        template_key: $("ch-template").value,
      }),
    });
    $("ch-name").value = "";
    await refreshChannels();
  });

  (async function init() {
    const authed = Boolean(getToken());
    const demo = isDemoOpenAccess();
    if (!authed && !demo) {
      if (isPublicShell) {
        showAuthGate(true);
        await loadStatus();
        try {
          await refreshHubDashboard();
        } catch (e) {
          if ($("hub-out")) $("hub-out").textContent = String(e.message || e);
        }
        return;
      }
      redirectToLogin();
      return;
    }
    showAuthGate(false);
    await loadStatus();
    // 中枢 + 提示词优先，避免后半段失败时下拉永久空白
    await Promise.allSettled([refreshHubDashboard(), refreshPrompts()]);
    await loadTemplates();
    const settled = await Promise.allSettled([
      refreshKbs(),
      refreshPrompts(),
      refreshTasks(),
      refreshChannels(),
    ]);
    try {
      await refreshHubDashboard();
    } catch (_) {
      /* keep first paint */
    }
    const failed = settled.find((r) => r.status === "rejected");
    if (failed && $("hub-out") && $("hub-out").classList.contains("hidden")) {
      $("hub-out").textContent = String(failed.reason?.message || failed.reason || "部分面板加载失败");
      $("hub-out").classList.remove("hidden");
    }
    const tbody = $("evidence-table");
    if (tbody && /加载中/.test(tbody.textContent || "")) {
      tbody.innerHTML = "<tr><td colspan=6>加载失败 · 请点「刷新摘要」或新建/导入知识库</td></tr>";
    }
    const pick = $("prompt-pick");
    if (pick && (!pick.options.length || (pick.options.length === 1 && !pick.options[0].value))) {
      pick.innerHTML = `<option value="">暂无提示词 · 请点「恢复内置」</option>`;
    }
    await loadAiFocusScript();
    renderTaskAiPlatforms();
    renderTaskAiFocusCard();
    renderPendingKeywords();
    ceBootReady = true;
    const deep = params.get("tab");
    if (deep === "prompts") activateTab("prompts");
    if (params.get("from") === "keywords") activateTab("tasks");
  })();
})();
