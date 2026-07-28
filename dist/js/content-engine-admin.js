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

  function redirectToLogin() {
    window.location.href = loginHref();
  }

  function showAuthGate(visible) {
    const gate = document.getElementById("ce-auth-gate");
    if (!gate) return;
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

  let currentTaskId = null;
  let currentDraft = "";
  let currentTemplateKey = "";
  let templates = [];

  function activateTab(name) {
    document.querySelectorAll(".tab").forEach((b) => b.classList.toggle("active", b.dataset.tab === name));
    document.querySelectorAll(".panel").forEach((p) => p.classList.toggle("active", p.id === `panel-${name}`));
  }

  document.querySelectorAll(".tab").forEach((btn) => {
    btn.addEventListener("click", () => activateTab(btn.dataset.tab));
  });

  const params = new URLSearchParams(window.location.search);
  const deepTab = params.get("tab");
  if (deepTab) activateTab(deepTab);

  async function loadStatus() {
    try {
      const s = await fetch("/api/settings/content-backend").then((r) => r.json());
      $("backend-status").textContent = `模式：${s.mode} — ${s.note}`;
    } catch (e) {
      $("backend-status").textContent = String(e.message || e);
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
    $("task-template").innerHTML = `<option value="">自动（跟渠道）</option>` + opts;
    $("ch-template").innerHTML = opts || `<option value="wechat-article">公众号文章</option>`;
    $("template-manifest").textContent = JSON.stringify({ items: templates }, null, 2);
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

  async function refreshDocs(kbId) {
    if (!kbId) {
      $("doc-table").innerHTML = "<tr><td colspan=3>选择知识库</td></tr>";
      return;
    }
    const detail = await api(`/knowledge-bases/${kbId}`);
    $("doc-table").innerHTML =
      (detail.documents || [])
        .map(
          (d) => `<tr>
        <td>${escapeHtml(d.title)}<br><small>${escapeHtml(d.source_path || "")}</small></td>
        <td>${d.chunk_count}</td>
        <td><button type="button" class="btn" data-del-doc="${d.id}">删除</button></td>
      </tr>`
        )
        .join("") || "<tr><td colspan=3>暂无文档</td></tr>";
    $("doc-table").querySelectorAll("[data-del-doc]").forEach((btn) => {
      btn.addEventListener("click", async () => {
        if (!confirm("删除该文档及其切片？")) return;
        await api(`/documents/${btn.dataset.delDoc}`, { method: "DELETE" });
        await refreshKbs();
        await refreshDocs($("kb-select").value);
      });
    });
  }

  async function refreshKbs() {
    const data = await api("/knowledge-bases");
    const tbody = $("kb-table");
    tbody.innerHTML =
      data.items
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
        .join("") || "<tr><td colspan=5>暂无</td></tr>";

    const opts = data.items.map((k) => `<option value="${k.id}">${escapeHtml(k.name)}</option>`).join("");
    $("kb-select").innerHTML = opts;
    $("task-kb").innerHTML = `<option value="">不绑定知识库</option>` + opts;

    const prefer = params.get("kb");
    if (prefer && data.items.some((k) => k.id === prefer)) {
      $("kb-select").value = prefer;
    }

    tbody.querySelectorAll("[data-open-kb]").forEach((btn) => {
      btn.addEventListener("click", async () => {
        $("kb-select").value = btn.dataset.openKb;
        activateTab("kb");
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

    if ($("kb-select").value) await refreshDocs($("kb-select").value);
  }

  async function refreshPrompts() {
    const data = await api("/prompts");
    $("prompt-table").innerHTML = data.items
      .map(
        (p) => `<tr>
        <td>${escapeHtml(p.title)}</td>
        <td>
          <button type="button" class="btn" data-view-pid="${p.id}">查看</button>
          <button type="button" class="btn" data-edit-pid="${p.id}">编辑</button>
          <button type="button" class="btn" data-del-pid="${p.id}">停用</button>
        </td>
      </tr>`
      )
      .join("");
    $("task-prompt").innerHTML = data.items
      .map((p) => `<option value="${p.id}">${escapeHtml(p.title)}</option>`)
      .join("");

    $("prompt-table").querySelectorAll("[data-view-pid]").forEach((b) => {
      b.addEventListener("click", async () => {
        const p = await api(`/prompts/${b.dataset.viewPid}`);
        $("prompt-body").textContent = p.body;
      });
    });
    $("prompt-table").querySelectorAll("[data-edit-pid]").forEach((b) => {
      b.addEventListener("click", async () => {
        const p = await api(`/prompts/${b.dataset.editPid}`);
        $("prompt-id").value = p.id;
        $("prompt-title").value = p.title;
        $("prompt-edit-body").value = p.body;
        $("prompt-body").textContent = p.body;
        activateTab("prompts");
      });
    });
    $("prompt-table").querySelectorAll("[data-del-pid]").forEach((b) => {
      b.addEventListener("click", async () => {
        if (!confirm("停用该提示词？")) return;
        await api(`/prompts/${b.dataset.delPid}`, { method: "DELETE" });
        await refreshPrompts();
      });
    });
  }

  function setTaskActions(enabled) {
    $("btn-preview-shell").disabled = !enabled;
    $("btn-mark-dist").disabled = !enabled;
  }

  async function refreshTasks() {
    const data = await api("/tasks");
    $("task-table").innerHTML =
      data.items
        .map(
          (t) => `<tr>
        <td>${escapeHtml(t.title)}</td>
        <td>${escapeHtml(t.status)}${t.distributed ? " · 已分发" : ""}</td>
        <td><button type="button" class="btn" data-tid="${t.id}">打开</button></td>
      </tr>`
        )
        .join("") || "<tr><td colspan=3>暂无</td></tr>";
    $("task-table").querySelectorAll("[data-tid]").forEach((b) => {
      b.addEventListener("click", async () => {
        const t = await api(`/tasks/${b.dataset.tid}`);
        currentTaskId = t.id;
        currentDraft = t.draft_body || t.error_message || "";
        currentTemplateKey = t.template_key || $("task-template").value || "wechat-article";
        $("task-draft").textContent = currentDraft || "（无正文）";
        setTaskActions(Boolean(currentDraft));
        $("shell-preview").classList.add("hidden");
      });
    });
  }

  async function refreshChannels() {
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
    void refreshDocs($("kb-select").value);
  });

  $("btn-import-dji").addEventListener("click", async () => {
    $("hub-out").textContent = "导入中…";
    try {
      const r = await api("/knowledge-bases/import-dji-demo", { method: "POST", body: "{}" });
      if ($("hub-out")) $("hub-out").textContent = JSON.stringify(r, null, 2);
      await Promise.all([refreshKbs(), refreshPrompts(), refreshChannels()]);
      await refreshHubDashboard();
    } catch (e) {
      if ($("hub-out")) $("hub-out").textContent = String(e.message || e);
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
    setText("kpi-docs-note", summary && summary.demo_ready ? "DJI 演示包已导入" : "待导入演示包");
    setText("kpi-chunks-note", "可检索单元");
    setText("kpi-vec-note", `${readyPct}% 召回就绪`);
    setText("kpi-tasks-note", `草稿 ${drafts}`);
    setText("side-kb", String(kbs.items.length));
    setText("side-docs", String(docs));
    setText("side-chunks", String(chunks));
    setText("side-drafts", String(drafts));
    setText("pill-pending", summary && summary.demo_ready ? "已导入" : "待导入");
    setText("pill-audit", drafts ? `有草稿 ${drafts}` : "待生成");
    setText("pill-ok", `已就绪 ${vec}`);
    const bar = $("embed-bar");
    if (bar) bar.style.width = `${readyPct}%`;
    setText("embed-label", `${readyPct}% · ${vec}/${chunks || 0}`);

    const tbody = $("evidence-table");
    if (tbody) {
      if (!kbs.items.length) {
        tbody.innerHTML = "<tr><td colspan=6>暂无知识库 · 请导入 DJI 演示包</td></tr>";
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

  $("btn-refresh-hub").addEventListener("click", async () => {
    await refreshHubDashboard();
  });

  document.querySelectorAll("[data-goto-tab]").forEach((btn) => {
    btn.addEventListener("click", () => activateTab(btn.getAttribute("data-goto-tab")));
  });

  $("btn-create-kb").addEventListener("click", async () => {
    await api("/knowledge-bases", {
      method: "POST",
      body: JSON.stringify({ name: $("kb-name").value, description: $("kb-desc").value }),
    });
    $("kb-name").value = "";
    $("kb-desc").value = "";
    await refreshKbs();
  });

  $("btn-add-doc").addEventListener("click", async () => {
    const kbId = $("kb-select").value;
    if (!kbId) return alert("请先选择知识库");
    await api(`/knowledge-bases/${kbId}/documents`, {
      method: "POST",
      body: JSON.stringify({ title: $("doc-title").value, body: $("doc-body").value }),
    });
    $("doc-title").value = "";
    $("doc-body").value = "";
    await refreshKbs();
    await refreshDocs(kbId);
  });

  $("btn-upload-doc").addEventListener("click", async () => {
    const kbId = $("kb-select").value;
    const file = $("doc-file").files?.[0];
    if (!kbId) return alert("请先选择知识库");
    if (!file) return alert("请选择 .md / .txt 文件");
    try {
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
    } catch (e) {
      $("search-out").textContent = String(e.message || e);
    }
  });

  $("btn-search").addEventListener("click", async () => {
    const kbId = $("kb-select").value;
    const query = $("search-q").value.trim();
    if (!kbId || !query) return;
    const r = await api(`/knowledge-bases/${kbId}/search`, {
      method: "POST",
      body: JSON.stringify({ query, limit: 6 }),
    });
    $("search-out").textContent = (r.items || [])
      .map((h, i) => `#${i + 1} score=${h.score}\n${h.content}`)
      .join("\n\n---\n\n") || "无命中";
  });

  $("btn-save-prompt").addEventListener("click", async () => {
    const id = $("prompt-id").value;
    const body = { title: $("prompt-title").value, body: $("prompt-edit-body").value };
    if (id) {
      await api(`/prompts/${id}`, { method: "PATCH", body: JSON.stringify(body) });
    } else {
      await api("/prompts", { method: "POST", body: JSON.stringify(body) });
    }
    $("prompt-id").value = "";
    $("prompt-title").value = "";
    $("prompt-edit-body").value = "";
    await refreshPrompts();
  });

  $("btn-reset-prompt").addEventListener("click", () => {
    $("prompt-id").value = "";
    $("prompt-title").value = "";
    $("prompt-edit-body").value = "";
  });

  $("btn-create-task").addEventListener("click", async () => {
    const channelSelect = $("task-channel");
    const selected = channelSelect.options[channelSelect.selectedIndex];
    const channelTk = selected?.dataset?.tk || "";
    const templateKey = $("task-template").value || channelTk || null;
    const body = {
      title: $("task-title").value || "未命名任务",
      knowledge_base_id: $("task-kb").value || null,
      prompt_id: $("task-prompt").value || null,
      channel_id: $("task-channel").value || null,
      template_key: templateKey,
      input_query: $("task-title").value,
    };
    $("task-draft").textContent = "生成中…";
    const r = await api("/tasks", { method: "POST", body: JSON.stringify(body) });
    currentTaskId = r.id;
    const full = await api(`/tasks/${r.id}`);
    currentDraft = full.draft_body || r.draft_preview || "";
    currentTemplateKey = full.template_key || templateKey || "wechat-article";
    $("task-draft").textContent = currentDraft || "（无正文）";
    setTaskActions(Boolean(currentDraft));
    $("shell-preview").classList.add("hidden");
    await refreshTasks();
  });

  $("btn-preview-shell").addEventListener("click", () => {
    if (!currentDraft) return;
    renderShellPreview($("task-title").value || "任务预览", currentDraft, currentTemplateKey);
    $("shell-preview").classList.remove("hidden");
  });

  $("btn-mark-dist").addEventListener("click", async () => {
    if (!currentTaskId) return;
    const r = await api(`/tasks/${currentTaskId}/mark-distributed`, { method: "POST", body: "{}" });
    $("task-draft").textContent = `${currentDraft}\n\n——\n已标记分发 · status=${r.status}`;
    await refreshTasks();
  });

  $("btn-create-ch").addEventListener("click", async () => {
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
    if (!authed) {
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
    await loadTemplates();
    try {
      await Promise.all([refreshKbs(), refreshPrompts(), refreshTasks(), refreshChannels()]);
      await refreshHubDashboard();
    } catch (e) {
      if ($("hub-out")) $("hub-out").textContent = String(e.message || e);
    }
  })();
})();
