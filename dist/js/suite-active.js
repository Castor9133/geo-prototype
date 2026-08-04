/**
 * 工作台：进行中选题（最多 3 条）+ 下一步跳转
 */
(function () {
  'use strict';

  var ACTIVE = {
    draft: 1,
    pending_review: 1,
    executable: 1,
    deployed: 1,
    observing: 1,
  };
  var PLATFORM = { doubao: '豆包', yuanbao: '元宝', deepseek: 'DeepSeek' };
  var STATUS = {
    draft: '草稿',
    pending_review: '待审',
    executable: '可开工',
    deployed: '已发布',
    observing: '复测中',
  };

  function token() {
    try { return localStorage.getItem('georank_token') || ''; } catch (_) { return ''; }
  }

  function escapeHtml(s) {
    return String(s == null ? '' : s)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  function progressLine(s) {
    var na = s.next_action || {};
    if (na.label) return '下一步：' + na.label;
    return STATUS[s.status] || s.status || '';
  }

  async function loadActive() {
    var host = document.getElementById('suite-active-list');
    var empty = document.getElementById('suite-active-empty');
    var cta = document.getElementById('suite-start-cta');
    if (!host) return;
    host.innerHTML = '<p class="cockpit-muted">正在加载进行中选题…</p>';
    try {
      var res = await fetch('/api/geo-strategies?limit=50', {
        headers: token() ? { Authorization: 'Bearer ' + token() } : {},
        credentials: 'same-origin',
      });
      if (!res.ok) throw new Error('加载失败');
      var data = await res.json();
      var items = (data.items || []).filter(function (s) { return ACTIVE[s.status]; });
      items.sort(function (a, b) {
        return String(b.updated_at || '').localeCompare(String(a.updated_at || ''));
      });
      var top = items.slice(0, 3);
      if (!top.length) {
        host.innerHTML = '';
        if (empty) empty.hidden = false;
        if (cta) {
          cta.textContent = '去查页面';
          cta.href = '/diagnostic';
        }
        return;
      }
      if (empty) empty.hidden = true;
      host.innerHTML = '';
      top.forEach(function (s) {
        var na = s.next_action || {};
        var href = na.href || ('/strategies?strategy=' + encodeURIComponent(s.id) + '&tab=overview');
        var card = document.createElement('article');
        card.className = 'suite-active-card';
        card.innerHTML =
          '<div class="suite-active-card__body">' +
            '<h3>' + escapeHtml(s.title || s.question_class || '未命名选题') + '</h3>' +
            '<p class="suite-active-card__meta">' +
              escapeHtml(PLATFORM[s.platform] || s.platform || '') +
              ' · ' + escapeHtml(STATUS[s.status] || s.status || '') +
            '</p>' +
            '<p class="suite-active-card__progress">' + escapeHtml(progressLine(s)) + '</p>' +
          '</div>' +
          '<a class="cockpit-btn cockpit-btn--primary" href="' + escapeHtml(href) + '">' +
            escapeHtml(na.label || '打开选题') +
          '</a>';
        host.appendChild(card);
      });
      if (cta && top[0] && top[0].next_action) {
        cta.textContent = top[0].next_action.label || '继续选题';
        cta.href = top[0].next_action.href || '/strategies';
      }
    } catch (e) {
      host.innerHTML = '<p class="cockpit-muted">暂时无法加载选题。请先登录后重试，或直接打开选题策略。</p>';
      if (empty) empty.hidden = true;
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', loadActive);
  } else {
    loadActive();
  }
})();
