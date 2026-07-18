(function () {
  'use strict';

  const doc = document;
  const root = doc.documentElement;
  const savedTheme = localStorage.getItem('jsj6-theme') || localStorage.getItem('ddc5i-theme') || 'dark';
  root.dataset.theme = savedTheme;

  function toggleTheme() {
    const next = root.dataset.theme === 'dark' ? 'light' : 'dark';
    root.dataset.theme = next;
    localStorage.setItem('jsj6-theme', next);
  }

  function toggleSidebar() {
    const app = doc.getElementById('app-shell');
    if (!app) return;
    if (window.innerWidth < 821) {
      app.classList.toggle('mobile-open');
    } else {
      app.classList.toggle('collapsed');
      localStorage.setItem('jsj6-sidebar', app.classList.contains('collapsed') ? 'collapsed' : 'open');
    }
  }

  function closeTaskDrawer() {
    const drawer = doc.getElementById('task-drawer');
    if (!drawer) return;
    drawer.hidden = true;
    drawer.setAttribute('aria-hidden', 'true');
    doc.body.classList.remove('drawer-open');
  }

  async function openTaskDrawer(taskId, panelUrl = "", fullUrl = "") {
    const workspace = doc.querySelector('[data-project-task-workspace]');
    const drawer = doc.getElementById('task-drawer');
    const content = doc.getElementById('task-drawer-content');
    if (!workspace || !drawer || !content || !taskId) return;
    const projectId = workspace.dataset.projectId;
    drawer.hidden = false;
    drawer.setAttribute('aria-hidden', 'false');
    doc.body.classList.add('drawer-open');
    content.innerHTML = '<div class="drawer-loading"><div class="spinner"></div><p>Loading task workspace…</p></div>';
    try {
      const resolvedPanelUrl = panelUrl || `/projects/${encodeURIComponent(projectId)}/tasks/${encodeURIComponent(taskId)}/panel`;
      const response = await fetch(resolvedPanelUrl, {
        headers: { 'X-Requested-With': 'XMLHttpRequest', 'Accept': 'text/html' },
        credentials: 'same-origin',
        cache: 'no-store'
      });
      if (!response.ok) throw new Error(response.status === 404 ? 'Task not found or not accessible.' : 'Unable to load task details.');
      const html = await response.text();
      if (!html.includes('task-drawer-panel')) throw new Error('The task workspace returned an unexpected response.');
      content.innerHTML = html;
      content.querySelector('[data-task-drawer-close]')?.focus();
    } catch (error) {
      content.innerHTML = '';
      const panel = doc.createElement('div');
      panel.className = 'task-drawer-panel drawer-error';
      const heading = doc.createElement('h2');
      heading.textContent = 'Task details unavailable';
      const message = doc.createElement('p');
      message.textContent = error.message || 'Unable to load task details.';
      const button = doc.createElement('button');
      button.type = 'button';
      button.className = 'btn';
      button.dataset.taskDrawerClose = '';
      button.textContent = 'Close';
      panel.append(heading, message);
      if (fullUrl) {
        const fallback = doc.createElement('a');
        fallback.className = 'btn btn-primary';
        fallback.href = fullUrl;
        fallback.textContent = 'Open Full Task Page';
        panel.appendChild(fallback);
      }
      panel.appendChild(button);
      content.appendChild(panel);
    }
  }

  function setupSearch() {
    const input = doc.getElementById('global-q');
    const box = doc.getElementById('search-suggestions');
    if (!input || !box) return;
    let timer = null;
    let controller = null;
    let activeIndex = -1;

    function clearSuggestions() {
      box.hidden = true;
      box.replaceChildren();
      activeIndex = -1;
      input.setAttribute('aria-expanded', 'false');
    }

    function activate(index) {
      const items = [...box.querySelectorAll('a')];
      if (!items.length) return;
      activeIndex = Math.max(0, Math.min(index, items.length - 1));
      items.forEach((item, i) => item.classList.toggle('active', i === activeIndex));
      items[activeIndex].scrollIntoView({ block: 'nearest' });
    }

    function renderSuggestions(results, query) {
      box.replaceChildren();
      if (!results.length) {
        const empty = doc.createElement('div');
        empty.className = 'search-empty';
        empty.textContent = `No accessible matches for “${query}”`;
        box.appendChild(empty);
      } else {
        results.forEach((result) => {
          const link = doc.createElement('a');
          link.href = result.url;
          link.setAttribute('role', 'option');
          link.className = 'search-suggestion-item';
          const kind = doc.createElement('span');
          kind.className = 'search-kind';
          kind.textContent = result.kind;
          const copy = doc.createElement('span');
          copy.className = 'search-suggestion-copy';
          const title = doc.createElement('strong');
          title.textContent = `${result.identifier} · ${result.title}`;
          const subtitle = doc.createElement('small');
          subtitle.textContent = result.subtitle || result.snippet || '';
          copy.append(title, subtitle);
          link.append(kind, copy);
          box.appendChild(link);
        });
        const footer = doc.createElement('a');
        footer.className = 'search-all-results';
        footer.href = `/search?q=${encodeURIComponent(query)}`;
        footer.textContent = 'View all search results →';
        box.appendChild(footer);
      }
      box.hidden = false;
      input.setAttribute('aria-expanded', 'true');
    }

    async function loadSuggestions(query) {
      if (controller) controller.abort();
      controller = new AbortController();
      try {
        const response = await fetch(`/api/search/suggest?q=${encodeURIComponent(query)}`, { signal: controller.signal });
        if (!response.ok) throw new Error('Search unavailable');
        const payload = await response.json();
        renderSuggestions(payload.results || [], query);
      } catch (error) {
        if (error.name !== 'AbortError') clearSuggestions();
      }
    }

    input.addEventListener('input', () => {
      const query = input.value.trim();
      window.clearTimeout(timer);
      if (query.length < 2) {
        clearSuggestions();
        return;
      }
      timer = window.setTimeout(() => loadSuggestions(query), 180);
    });

    input.addEventListener('keydown', (event) => {
      const items = [...box.querySelectorAll('a')];
      if (event.key === 'ArrowDown' && !box.hidden) {
        event.preventDefault();
        activate(activeIndex + 1);
      } else if (event.key === 'ArrowUp' && !box.hidden) {
        event.preventDefault();
        activate(activeIndex - 1);
      } else if (event.key === 'Enter' && activeIndex >= 0 && items[activeIndex]) {
        event.preventDefault();
        items[activeIndex].click();
      } else if (event.key === 'Escape') {
        clearSuggestions();
      }
    });

    doc.addEventListener('click', (event) => {
      if (!event.target.closest('.search-shell')) clearSuggestions();
    });
  }

  doc.addEventListener('keydown', (event) => {
    if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'k') {
      event.preventDefault();
      const input = doc.getElementById('global-q');
      input?.focus();
      input?.select();
    }
    if (event.key === 'Escape') closeTaskDrawer();
  });

  doc.addEventListener('click', (event) => {
    const action = event.target.closest('[data-action]')?.dataset.action;
    if (action === 'toggle-sidebar') toggleSidebar();
    if (action === 'toggle-theme') toggleTheme();
    if (action === 'print') window.print();

    const taskButton = event.target.closest('[data-task-open]');
    if (taskButton) {
      const drawer = doc.getElementById('task-drawer');
      const content = doc.getElementById('task-drawer-content');
      if (drawer && content) {
        event.preventDefault();
        openTaskDrawer(taskButton.dataset.taskOpen, taskButton.dataset.taskPanelUrl || '', taskButton.href || '');
      }
    }
    if (event.target.closest('[data-task-drawer-close]')) {
      event.preventDefault();
      closeTaskDrawer();
    }
  });

  doc.addEventListener('submit', (event) => {
    const trigger = event.submitter;
    const message = trigger?.dataset.confirm || event.target.dataset.confirm;
    if (message && !window.confirm(message)) event.preventDefault();
  });

  doc.addEventListener('DOMContentLoaded', () => {
    const app = doc.getElementById('app-shell');
    if ((localStorage.getItem('jsj6-sidebar') || localStorage.getItem('ddc5i-sidebar')) === 'collapsed' && window.innerWidth > 820) app?.classList.add('collapsed');

    doc.querySelectorAll('[data-auto-submit]').forEach((element) => element.addEventListener('change', () => element.form?.submit()));

    doc.querySelectorAll('[data-kanban-task]').forEach((card) => {
      card.addEventListener('dragstart', (event) => {
        event.dataTransfer.setData('text/plain', card.dataset.taskId);
        card.classList.add('dragging');
      });
      card.addEventListener('dragend', () => card.classList.remove('dragging'));
    });

    doc.querySelectorAll('[data-kanban-column]').forEach((column) => {
      column.addEventListener('dragover', (event) => {
        event.preventDefault();
        column.classList.add('drag-over');
      });
      column.addEventListener('dragleave', () => column.classList.remove('drag-over'));
      column.addEventListener('drop', async (event) => {
        event.preventDefault();
        column.classList.remove('drag-over');
        const taskId = event.dataTransfer.getData('text/plain');
        const targetColumn = column.dataset.kanbanColumn;
        const csrf = doc.querySelector('meta[name=csrf-token]')?.content || '';
        const response = await fetch(`/api/tasks/${encodeURIComponent(taskId)}/move`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': csrf },
          body: JSON.stringify({ column: targetColumn })
        });
        if (response.ok) window.location.reload();
        else {
          const data = await response.json().catch(() => ({}));
          window.alert(data.detail || 'Unable to move task');
        }
      });
    });

    doc.querySelectorAll('[data-score]').forEach((input) => input.addEventListener('input', () => {
      let total = 0;
      doc.querySelectorAll('[data-score]').forEach((item) => { total += Number(item.value || 0) * Number(item.dataset.weight || 0) / 5; });
      const output = doc.getElementById('score-total');
      if (output) output.textContent = total.toFixed(1);
    }));

    setupSearch();

    const workspace = doc.querySelector('[data-project-task-workspace]');
    if (workspace?.dataset.openTask) {
      const projectId = workspace.dataset.projectId;
      const taskId = workspace.dataset.openTask;
      openTaskDrawer(taskId, `/projects/${encodeURIComponent(projectId)}/tasks/${encodeURIComponent(taskId)}/panel`, `/projects/${encodeURIComponent(projectId)}/tasks/${encodeURIComponent(taskId)}`);
    }
  });
})();
