(function () {
  'use strict';

  const doc = document;
  const root = doc.documentElement;
  const savedTheme = localStorage.getItem('jsj6-theme') || localStorage.getItem('ddc5i-theme') || 'dark';
  const savedFontSize = localStorage.getItem('jsj6-font-size') || 'standard';
  const savedDensity = localStorage.getItem('jsj6-density') || 'comfortable';
  root.dataset.theme = savedTheme;
  root.dataset.fontSize = ['standard', 'large', 'x-large'].includes(savedFontSize) ? savedFontSize : 'standard';
  root.dataset.density = ['comfortable', 'compact'].includes(savedDensity) ? savedDensity : 'comfortable';

  function toggleTheme() {
    const next = root.dataset.theme === 'dark' ? 'light' : 'dark';
    root.dataset.theme = next;
    localStorage.setItem('jsj6-theme', next);
  }

  function setFontSize(value) {
    const next = ['standard', 'large', 'x-large'].includes(value) ? value : 'standard';
    root.dataset.fontSize = next;
    localStorage.setItem('jsj6-font-size', next);
    doc.querySelectorAll('[data-font-size-choice]').forEach((control) => {
      control.checked = control.value === next;
    });
  }

  function setDensity(value) {
    const next = ['comfortable', 'compact'].includes(value) ? value : 'comfortable';
    root.dataset.density = next;
    localStorage.setItem('jsj6-density', next);
    doc.querySelectorAll('[data-density-choice]').forEach((control) => {
      control.checked = control.value === next;
    });
  }

  function toggleGuidance(button) {
    const guide = button?.closest('[data-page-guide]');
    if (!guide) return;
    const collapsed = guide.classList.toggle('is-collapsed');
    button.setAttribute('aria-expanded', String(!collapsed));
    button.textContent = collapsed ? 'Show guide' : 'Hide guide';
    localStorage.setItem('jsj6-guide-collapsed', collapsed ? 'true' : 'false');
  }

  function markInputZones() {
    const marked = new Set();
    doc.querySelectorAll('#main-content form').forEach((form) => {
      if (form.matches('.filters,.search-form,.signout-form,.inline-add,.comment-form,.wbs-actions form,.actions form,.report-actions form,.board-config-actions form')) return;
      const controls = [...form.querySelectorAll('input:not([type=hidden]):not([type=submit]), select, textarea')]
        .filter((control) => !control.disabled);
      if (controls.length < 2) return;

      controls.filter((control) => control.required).forEach((control) => {
        control.setAttribute('aria-required', 'true');
        const label = control.closest('label') || (control.id ? form.querySelector(`label[for="${CSS.escape(control.id)}"]`) : null);
        label?.classList.add('required-indicator');
      });

      let zone = form.classList.contains('card') ? form : form.closest('.card');
      if (!zone || marked.has(zone)) return;
      const zoneForms = [...zone.querySelectorAll('form')].filter((candidate) => candidate.querySelectorAll('input:not([type=hidden]), select, textarea').length >= 2);
      if (zone !== form && zoneForms.length > 1) zone = form;
      if (marked.has(zone)) return;
      zone.classList.add('input-zone');
      form.classList.add('guided-input-form');
      const banner = doc.createElement('div');
      banner.className = 'input-zone-banner';
      banner.innerHTML = '<strong>Input area</strong><span>Complete the fields, review the information, then use the action button below. Required fields are marked *.</span>';
      if (zone === form) form.prepend(banner);
      else form.before(banner);
      marked.add(zone);
    });
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

  function setupDivisionImages() {
    doc.querySelectorAll('.division-hero-image, .division-card-media img').forEach((image) => {
      const markLoaded = () => image.classList.add('is-loaded');
      if (image.complete && image.naturalWidth > 0) markLoaded();
      else image.addEventListener('load', markLoaded, { once: true });
      image.addEventListener('error', () => image.closest('[data-division-hero], .division-card-media')?.classList.add('image-unavailable'), { once: true });
    });

    doc.querySelectorAll('[data-division-card][data-banner-src]').forEach((card) => {
      let preloaded = false;
      const preload = () => {
        if (preloaded || !card.dataset.bannerSrc) return;
        preloaded = true;
        const image = new Image();
        image.decoding = 'async';
        image.src = card.dataset.bannerSrc;
      };
      card.addEventListener('pointerenter', preload, { once: true });
      card.addEventListener('focusin', preload, { once: true });
    });
  }

  function readJsonElement(id) {
    const element = doc.getElementById(id);
    if (!element) return null;
    try { return JSON.parse(element.textContent || 'null'); }
    catch (_error) { return null; }
  }

  function formatMoney(value) {
    return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(Number(value || 0));
  }


  /* ── v0.7.8 entrance animation engine ─────────────────────────────── */
  const ANIM_EASE = (t) => 1 - Math.pow(1 - t, 3);
  const animEnabled = !window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  function animateNumber(el, options = {}) {
    const raw = el.textContent;
    const match = raw.match(/-?[\d,]+(?:\.\d+)?/);
    if (!match) return;
    const numText = match[0];
    const target = Number(numText.replace(/,/g, ''));
    if (!Number.isFinite(target)) return;
    const decimals = (numText.split('.')[1] || '').length;
    const grouped = numText.includes(',') || Math.abs(target) >= 1000;
    const prefix = raw.slice(0, match.index);
    const suffix = raw.slice(match.index + numText.length);
    const duration = options.duration || 1100;
    const delay = options.delay || 0;
    const start = performance.now() + delay;
    el.textContent = prefix + (0).toLocaleString('en-US', { minimumFractionDigits: decimals, maximumFractionDigits: decimals, useGrouping: grouped }) + suffix;
    function frame(now) {
      const t = Math.min(1, Math.max(0, (now - start) / duration));
      const value = target * ANIM_EASE(t);
      el.textContent = prefix + value.toLocaleString('en-US', { minimumFractionDigits: decimals, maximumFractionDigits: decimals, useGrouping: grouped }) + suffix;
      if (t < 1) requestAnimationFrame(frame);
      else el.textContent = raw;
    }
    requestAnimationFrame(frame);
  }

  function animateDonut(donut, delay = 0) {
    const style = donut.getAttribute('style') || '';
    const onTrack = Number((style.match(/--on-track:\s*([\d.]+)/) || [])[1]);
    const atRisk = Number((style.match(/--at-risk:\s*([\d.]+)/) || [])[1]);
    if (!Number.isFinite(onTrack)) return;
    const duration = 1200;
    const start = performance.now() + delay;
    donut.style.setProperty('--on-track', '0%');
    donut.style.setProperty('--at-risk', '0%');
    function frame(now) {
      const t = Math.min(1, Math.max(0, (now - start) / duration));
      const eased = ANIM_EASE(t);
      donut.style.setProperty('--on-track', `${(onTrack * eased).toFixed(2)}%`);
      donut.style.setProperty('--at-risk', `${((Number.isFinite(atRisk) ? atRisk : 0) * eased).toFixed(2)}%`);
      if (t < 1) requestAnimationFrame(frame);
    }
    requestAnimationFrame(frame);
  }

  function setupEntranceAnimations() {
    if (!animEnabled) return;
    root.classList.add('anim-on');

    const cards = [...doc.querySelectorAll('.premium-kpi, .travel-kpis .kpi, .dashboard-panel, .travel-map-card, .travel-location-card, .travel-analytics-grid > .card, .engagement-impact-card')];
    cards.forEach((card) => card.classList.add('anim-rise'));

    const growX = [...doc.querySelectorAll('.stacked-track .segment, .compliance-meter i, .pipeline-fill, .bar-fill, .progress span')];
    growX.forEach((el) => el.classList.add('anim-bar-x'));
    const growY = [...doc.querySelectorAll('.travel-month-chart .cost-bar')];
    growY.forEach((el) => el.classList.add('anim-bar-y'));

    const seenNumbers = new WeakSet();
    const observer = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (!entry.isIntersecting) return;
        const el = entry.target;
        observer.unobserve(el);
        el.classList.add('anim-go');
        if (el.dataset.animGroup === 'card') {
          el.querySelectorAll('.kpi-value, .flow-summary strong, .map-coverage strong, .donut strong, .pipeline-count').forEach((num, index) => {
            if (seenNumbers.has(num)) return;
            seenNumbers.add(num);
            animateNumber(num, { delay: 120 + index * 90 });
          });
          el.querySelectorAll('.health-donut').forEach((donut) => animateDonut(donut, 150));
          window.setTimeout(() => {
            el.classList.remove('anim-rise', 'anim-go');
            el.style.transitionDelay = '';
          }, 1250);
        } else {
          window.setTimeout(() => {
            el.classList.remove('anim-bar-x', 'anim-bar-y', 'anim-go');
            el.style.transitionDelay = '';
          }, 1700);
        }
      });
    }, { threshold: 0.18 });

    cards.forEach((card, index) => {
      card.dataset.animGroup = 'card';
      card.style.transitionDelay = `${Math.min(index, 8) * 55}ms`;
      observer.observe(card);
    });
    [...growX, ...growY].forEach((el, index) => {
      el.style.transitionDelay = `${140 + (index % 12) * 45}ms`;
      observer.observe(el);
    });

    // Standalone number counters not inside an animated card
    doc.querySelectorAll('.kpi-value, .map-coverage strong').forEach((num) => {
      if (num.closest('[data-anim-group="card"]') || seenNumbers.has(num)) return;
      seenNumbers.add(num);
      animateNumber(num, { delay: 160 });
    });
  }

  function animateSankey(svg) {
    if (!animEnabled || !svg) return;
    const links = [...svg.querySelectorAll('.sankey-link')];
    links.forEach((path, index) => {
      let length = 0;
      try { length = path.getTotalLength(); } catch (error) { return; }
      if (!length) return;
      const targetOpacity = path.style.opacity || '';
      path.style.strokeDasharray = `${length}`;
      path.style.strokeDashoffset = `${length}`;
      path.style.transition = `stroke-dashoffset 1s cubic-bezier(.3,.7,.3,1) ${180 + index * 60}ms`;
      requestAnimationFrame(() => requestAnimationFrame(() => {
        path.style.strokeDashoffset = '0';
      }));
      path.addEventListener('transitionend', () => {
        path.style.strokeDasharray = '';
        path.style.strokeDashoffset = '';
        path.style.transition = '';
        path.style.opacity = targetOpacity;
      }, { once: true });
    });
    svg.querySelectorAll('.sankey-node').forEach((node, index) => {
      node.classList.add('anim-node');
      node.style.transitionDelay = `${120 + index * 45}ms`;
      requestAnimationFrame(() => requestAnimationFrame(() => node.classList.add('anim-go')));
    });
  }

  function setupInvestmentFlow() {
    const shell = doc.querySelector('[data-investment-flow]');
    const svg = shell?.querySelector('svg');
    const detail = shell?.querySelector('[data-flow-detail]');
    const data = readJsonElement('investment-flow-data');
    if (!shell || !svg || !detail || !data?.nodes?.length) return;
    const ns = 'http://www.w3.org/2000/svg';
    const width = 1120;
    const height = 430;
    const stageX = [20, 250, 480, 710, 950];
    const nodeWidth = 145;
    const stageGroups = new Map();
    data.nodes.forEach((node) => {
      if (!stageGroups.has(node.stage)) stageGroups.set(node.stage, []);
      stageGroups.get(node.stage).push(node);
    });
    const layout = new Map();
    stageGroups.forEach((nodes, stage) => {
      const gap = nodes.length > 9 ? 5 : 10;
      const top = 22;
      const available = height - 44 - gap * Math.max(0, nodes.length - 1);
      const total = nodes.reduce((sum, node) => sum + Math.max(Number(node.amount || 0), 0), 0) || 1;
      let sizes = nodes.map((node) => Math.max(16, Number(node.amount || 0) / total * available));
      const sizeTotal = sizes.reduce((sum, value) => sum + value, 0);
      if (sizeTotal > available) sizes = sizes.map((value) => Math.max(12, value * available / sizeTotal));
      let y = top;
      nodes.forEach((node, index) => {
        const nodeHeight = sizes[index];
        layout.set(node.id, { x: stageX[stage] || 20 + stage * 225, y, width: nodeWidth, height: nodeHeight });
        y += nodeHeight + gap;
      });
    });

    const maxLink = Math.max(...data.links.map((link) => Number(link.value || 0)), 1);
    const linkGroup = doc.createElementNS(ns, 'g');
    linkGroup.setAttribute('class', 'sankey-links');
    data.links.forEach((link) => {
      const source = layout.get(link.source);
      const target = layout.get(link.target);
      if (!source || !target) return;
      const path = doc.createElementNS(ns, 'path');
      const sx = source.x + source.width;
      const sy = source.y + source.height / 2;
      const tx = target.x;
      const ty = target.y + target.height / 2;
      const curve = Math.max(45, (tx - sx) * 0.47);
      path.setAttribute('d', `M ${sx} ${sy} C ${sx + curve} ${sy}, ${tx - curve} ${ty}, ${tx} ${ty}`);
      path.setAttribute('class', 'sankey-link');
      path.setAttribute('stroke-width', String(Math.max(2, Math.sqrt(Number(link.value || 0) / maxLink) * 32)));
      const title = doc.createElementNS(ns, 'title');
      title.textContent = `${formatMoney(link.value)} flow`;
      path.appendChild(title);
      linkGroup.appendChild(path);
    });
    svg.appendChild(linkGroup);

    function selectNode(node, group) {
      svg.querySelectorAll('.sankey-node.is-selected').forEach((item) => item.classList.remove('is-selected'));
      group?.classList.add('is-selected');
      detail.replaceChildren();
      const eyebrow = doc.createElement('span');
      eyebrow.className = 'eyebrow';
      eyebrow.textContent = node.kind === 'source' ? 'Flow origin' : `${node.kind} selection`;
      const heading = doc.createElement('h4');
      heading.textContent = node.label;
      const amount = doc.createElement('strong');
      amount.className = 'flow-detail-amount';
      amount.textContent = formatMoney(node.amount);
      const copy = doc.createElement('p');
      copy.textContent = 'Amount is derived from the currently accessible approved financial baseline. Open the records to inspect contributing projects and source evidence.';
      const link = doc.createElement('a');
      link.className = 'btn btn-small';
      link.href = node.url || '/financials';
      link.textContent = 'Open contributing records';
      detail.append(eyebrow, heading, amount, copy, link);
    }

    const nodeGroup = doc.createElementNS(ns, 'g');
    nodeGroup.setAttribute('class', 'sankey-nodes');
    data.nodes.forEach((node) => {
      const box = layout.get(node.id);
      if (!box) return;
      const group = doc.createElementNS(ns, 'g');
      group.setAttribute('class', `sankey-node sankey-${node.kind}`);
      group.setAttribute('tabindex', '0');
      group.setAttribute('role', 'link');
      group.setAttribute('aria-label', `${node.label}, ${formatMoney(node.amount)}. Open contributing records.`);
      const rect = doc.createElementNS(ns, 'rect');
      rect.setAttribute('x', String(box.x)); rect.setAttribute('y', String(box.y));
      rect.setAttribute('width', String(box.width)); rect.setAttribute('height', String(box.height));
      rect.setAttribute('rx', '8');
      const label = doc.createElementNS(ns, 'text');
      label.setAttribute('x', String(box.x + 10));
      label.setAttribute('y', String(box.y + Math.min(22, box.height / 2 + 4)));
      label.textContent = node.label.length > 21 ? `${node.label.slice(0, 20)}…` : node.label;
      const amount = doc.createElementNS(ns, 'text');
      amount.setAttribute('class', 'sankey-node-amount');
      amount.setAttribute('x', String(box.x + 10));
      amount.setAttribute('y', String(box.y + Math.min(41, box.height - 6)));
      amount.textContent = formatMoney(node.amount);
      group.append(rect, label);
      if (box.height >= 35) group.appendChild(amount);
      group.addEventListener('click', () => selectNode(node, group));
      group.addEventListener('dblclick', () => { window.location.href = node.url || '/financials'; });
      group.addEventListener('keydown', (event) => {
        if (event.key === 'Enter') { event.preventDefault(); selectNode(node, group); }
        if (event.key === ' ') { event.preventDefault(); window.location.href = node.url || '/financials'; }
      });
      nodeGroup.appendChild(group);
    });
    svg.appendChild(nodeGroup);
    const first = data.nodes.find((node) => node.kind === 'source') || data.nodes[0];
    const firstGroup = [...svg.querySelectorAll('.sankey-node')][data.nodes.indexOf(first)];
    selectNode(first, firstGroup);
    requestAnimationFrame(() => animateSankey(svg));
  }

  function setupTravelMap() {
    const shell = doc.querySelector('[data-travel-map]');
    const markers = shell?.querySelector('[data-map-markers]');
    const detail = shell?.querySelector('[data-map-detail]');
    const rows = readJsonElement('travel-map-data');
    if (!shell || !markers || !detail || !Array.isArray(rows)) return;
    const mapped = rows.filter((row) => row.mapped && Number.isFinite(Number(row.lat)) && Number.isFinite(Number(row.lon)));
    const maxCost = Math.max(...mapped.map((row) => Number(row.cost || 0)), 1);
    const markerByKey = new Map();

    function renderDetail(row) {
      detail.replaceChildren();
      const eyebrow = doc.createElement('span');
      eyebrow.className = 'eyebrow';
      eyebrow.textContent = row.region || 'Mapped location';
      const heading = doc.createElement('h4'); heading.textContent = row.location;
      const amount = doc.createElement('strong'); amount.textContent = formatMoney(row.cost);
      const copy = doc.createElement('p');
      copy.textContent = `${row.count} requests · ${row.engagement_count} engagements · ${row.division_count} divisions · ${row.report_count} reports`;
      const link = doc.createElement('a');
      link.className = 'btn btn-small'; link.href = row.url; link.textContent = 'Filter to this location';
      detail.append(eyebrow, heading, amount, copy, link);
      markerByKey.forEach((marker, key) => marker.classList.toggle('is-active', key === row.key));
      doc.querySelectorAll('[data-location-focus]').forEach((item) => item.classList.toggle('is-highlighted', item.dataset.locationFocus === row.key));
    }

    mapped.forEach((row) => {
      const marker = doc.createElement('button');
      marker.type = 'button';
      marker.className = 'travel-map-marker';
      marker.dataset.locationKey = row.key;
      marker.style.left = `${Math.max(1, Math.min(99, (Number(row.lon) + 180) / 360 * 100))}%`;
      marker.style.top = `${Math.max(3, Math.min(97, (90 - Number(row.lat)) / 180 * 100))}%`;
      const size = 12 + Math.sqrt(Number(row.cost || 0) / maxCost) * 24;
      marker.style.setProperty('--marker-size', `${size}px`);
      marker.setAttribute('aria-label', `${row.location}: ${formatMoney(row.cost)}, ${row.count} requests`);
      marker.title = `${row.location} · ${formatMoney(row.cost)} · ${row.count} requests`;
      marker.addEventListener('click', () => renderDetail(row));
      marker.addEventListener('focus', () => renderDetail(row));
      if (animEnabled) {
        marker.classList.add('anim-marker');
        marker.style.animationDelay = `${240 + markerByKey.size * 45}ms`;
        requestAnimationFrame(() => requestAnimationFrame(() => marker.classList.add('anim-go')));
      }
      markers.appendChild(marker);
      markerByKey.set(row.key, marker);
    });
    doc.querySelectorAll('[data-location-focus]').forEach((item) => {
      const row = rows.find((candidate) => candidate.key === item.dataset.locationFocus);
      if (!row) return;
      item.addEventListener('pointerenter', () => renderDetail(row));
      item.addEventListener('focus', () => renderDetail(row));
    });
    if (mapped[0]) renderDetail(mapped[0]);
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

  /* ===== v0.7.9 · adaptive shell, help drawer, onboarding, telemetry ===== */
  const telemetry = {
    record(event, detail) {
      // Privacy-conscious internal event queue. No record content, no identifiers,
      // no network calls. Ring buffer of the last 200 UX events, stored locally so
      // the organization can later connect approved analytics tooling.
      try {
        const queue = JSON.parse(localStorage.getItem('jsj6-telemetry') || '[]');
        queue.push({ e: event, d: detail || null, p: window.location.pathname, t: Date.now() });
        localStorage.setItem('jsj6-telemetry', JSON.stringify(queue.slice(-200)));
      } catch (error) { /* telemetry must never break the UI */ }
    },
    drain() {
      const queue = JSON.parse(localStorage.getItem('jsj6-telemetry') || '[]');
      localStorage.removeItem('jsj6-telemetry');
      return queue;
    },
  };
  window.jsj6Telemetry = telemetry;

  function toggleRoleFocus(forceCompact) {
    const strip = doc.querySelector('[data-role-focus]');
    const button = strip?.querySelector('[data-action="toggle-role-focus"]');
    if (!strip) return;
    const compact = typeof forceCompact === 'boolean' ? forceCompact : !strip.classList.contains('is-compact');
    strip.classList.toggle('is-compact', compact);
    if (button) {
      button.textContent = compact ? 'Expand' : 'Compact';
      button.setAttribute('aria-expanded', compact ? 'false' : 'true');
    }
    localStorage.setItem('jsj6-role-focus-compact', compact ? 'true' : 'false');
  }

  function openHelpDrawer() {
    const drawer = doc.querySelector('[data-help-drawer]');
    if (!drawer) return;
    drawer.hidden = false;
    doc.body.classList.add('drawer-open');
    drawer.querySelector('[data-glossary-search]')?.focus();
    telemetry.record('help-open');
  }

  function closeHelpDrawer() {
    const drawer = doc.querySelector('[data-help-drawer]');
    if (!drawer) return;
    drawer.hidden = true;
    doc.body.classList.remove('drawer-open');
  }

  function showPageGuide() {
    const guide = doc.querySelector('[data-page-guide]');
    const button = guide?.querySelector('[data-action="toggle-guidance"]');
    if (!guide) return;
    guide.classList.remove('is-collapsed');
    if (button) { button.setAttribute('aria-expanded', 'true'); button.textContent = 'Hide guide'; }
    localStorage.setItem('jsj6-guide-collapsed', 'false');
    guide.scrollIntoView({ block: 'nearest' });
  }

  function restartOnboarding() {
    localStorage.removeItem('jsj6-onboarded');
    localStorage.removeItem('jsj6-visited');
    localStorage.setItem('jsj6-guide-collapsed', 'false');
    localStorage.setItem('jsj6-role-focus-compact', 'false');
    if (window.location.pathname === '/dashboard') window.location.reload();
    else window.location.assign('/dashboard');
  }

  function dismissOnboarding() {
    localStorage.setItem('jsj6-onboarded', 'true');
    const card = doc.querySelector('[data-onboarding]');
    if (card) card.hidden = true;
    telemetry.record('onboarding-dismissed');
  }

  function initAdaptiveShell(returningUser) {
    const focusPref = localStorage.getItem('jsj6-role-focus-compact');
    if (focusPref === 'true' || (focusPref === null && returningUser)) toggleRoleFocus(true);

    doc.querySelectorAll('[data-nav-group]').forEach((group) => {
      const key = `jsj6-nav-${group.dataset.navGroup}`;
      if (!group.open && localStorage.getItem(key) === 'open') group.open = true;
      group.addEventListener('toggle', () => localStorage.setItem(key, group.open ? 'open' : 'closed'));
    });

    const onboarding = doc.querySelector('[data-onboarding]');
    if (onboarding && localStorage.getItem('jsj6-onboarded') !== 'true') onboarding.hidden = false;

    const glossarySearch = doc.querySelector('[data-glossary-search]');
    if (glossarySearch) {
      glossarySearch.addEventListener('input', () => {
        const query = glossarySearch.value.trim().toLowerCase();
        let visible = 0;
        doc.querySelectorAll('[data-glossary-term]').forEach((item) => {
          const match = !query || item.dataset.glossaryTerm.includes(query) || item.textContent.toLowerCase().includes(query);
          if (match) { item.removeAttribute('data-hidden'); visible += 1; }
          else item.setAttribute('data-hidden', '');
        });
        const empty = doc.querySelector('[data-glossary-empty]');
        if (empty) empty.hidden = visible > 0;
        if (query && visible === 0) telemetry.record('glossary-no-results');
      });
    }

    doc.addEventListener('keydown', (event) => {
      if (event.key === 'Escape') closeHelpDrawer();
    });

    doc.querySelectorAll('.quick-form').forEach((form) => form.addEventListener('submit', () => telemetry.record('quick-action', form.getAttribute('action')?.split('/')[2] || 'unknown')));
    doc.querySelector('.search-form')?.addEventListener('submit', () => telemetry.record('search'));
    telemetry.record('page-view');
  }

  function syncDashboardPreferenceFields() {
    const layout = doc.querySelector('[data-dashboard-layout]');
    const form = doc.querySelector('[data-dashboard-customizer]');
    if (!layout || !form) return;
    const panels = [...layout.querySelectorAll('[data-dashboard-panel]')];
    form.querySelector('[data-dashboard-order]').value = panels.map((panel) => panel.dataset.dashboardPanel).join(',');
    form.querySelector('[data-dashboard-hidden]').value = panels.filter((panel) => panel.dataset.userHidden === 'true').map((panel) => panel.dataset.dashboardPanel).join(',');
    const sizes = Object.fromEntries(panels.map((panel) => [panel.dataset.dashboardPanel, panel.dataset.panelSize || 'standard']));
    form.querySelector('[data-dashboard-sizes]').value = JSON.stringify(sizes);
  }

  function initDashboardLayout() {
    const layout = doc.querySelector('[data-dashboard-layout]');
    const data = doc.getElementById('dashboard-layout-data');
    if (!layout || !data) return;
    let config = { order: [], hidden: [], sizes: {} };
    try { config = JSON.parse(data.textContent || '{}'); } catch (_) { /* role defaults remain */ }
    const panels = [...doc.querySelectorAll('[data-dashboard-panel]')];
    const byId = new Map(panels.map((panel) => [panel.dataset.dashboardPanel, panel]));
    const ordered = [...(config.order || []).map((id) => byId.get(id)).filter(Boolean), ...panels.filter((panel) => !(config.order || []).includes(panel.dataset.dashboardPanel))];
    ordered.forEach((panel) => {
      const id = panel.dataset.dashboardPanel;
      panel.dataset.panelSize = (config.sizes || {})[id] || 'standard';
      panel.dataset.userHidden = (config.hidden || []).includes(id) ? 'true' : 'false';
      panel.hidden = panel.dataset.userHidden === 'true';
      panel.classList.add(`panel-size-${panel.dataset.panelSize}`);
      const controls = doc.createElement('div');
      controls.className = 'dashboard-panel-controls';
      controls.setAttribute('aria-label', `Arrange ${panel.dataset.panelTitle || id}`);
      controls.innerHTML = '<button type="button" data-action="panel-up" title="Move earlier">↑</button><button type="button" data-action="panel-down" title="Move later">↓</button><button type="button" data-action="panel-size" title="Change size">Size</button><button type="button" data-action="panel-hide" title="Show or hide">Hide</button>';
      panel.prepend(controls);
      layout.append(panel);
    });
    syncDashboardPreferenceFields();
  }

  function dashboardPanelAction(action, trigger) {
    const panel = trigger.closest('[data-dashboard-panel]');
    if (!panel) return;
    if (action === 'panel-up' && panel.previousElementSibling) panel.parentElement.insertBefore(panel, panel.previousElementSibling);
    if (action === 'panel-down' && panel.nextElementSibling) panel.parentElement.insertBefore(panel.nextElementSibling, panel);
    if (action === 'panel-hide') {
      panel.dataset.userHidden = panel.dataset.userHidden === 'true' ? 'false' : 'true';
      panel.classList.toggle('will-hide', panel.dataset.userHidden === 'true');
      trigger.textContent = panel.dataset.userHidden === 'true' ? 'Show' : 'Hide';
    }
    if (action === 'panel-size') {
      const values = ['compact', 'standard', 'wide'];
      const current = values.indexOf(panel.dataset.panelSize || 'standard');
      const next = values[(current + 1) % values.length];
      values.forEach((value) => panel.classList.remove(`panel-size-${value}`));
      panel.dataset.panelSize = next; panel.classList.add(`panel-size-${next}`); trigger.textContent = next[0].toUpperCase() + next.slice(1);
    }
    syncDashboardPreferenceFields();
  }

  doc.addEventListener('click', (event) => {
    const action = event.target.closest('[data-action]')?.dataset.action;
    if (action === 'toggle-sidebar') toggleSidebar();
    if (action === 'toggle-theme') toggleTheme();
    if (action === 'toggle-guidance') toggleGuidance(event.target.closest('[data-action]'));
    if (action === 'toggle-role-focus') toggleRoleFocus();
    if (action === 'open-help') openHelpDrawer();
    if (action === 'close-help') closeHelpDrawer();
    if (action === 'show-page-guide') { showPageGuide(); closeHelpDrawer(); }
    if (action === 'restart-onboarding') { restartOnboarding(); closeHelpDrawer(); }
    if (action === 'dismiss-onboarding') dismissOnboarding();
    if (action === 'customize-dashboard') {
      const form = doc.querySelector('[data-dashboard-customizer]');
      if (form) form.hidden = false;
      doc.body.classList.add('customizing-dashboard');
      doc.querySelectorAll('[data-dashboard-panel]').forEach((panel) => { panel.hidden = false; panel.classList.toggle('will-hide', panel.dataset.userHidden === 'true'); });
    }
    if (action === 'cancel-dashboard-customize') window.location.reload();
    if (['panel-up', 'panel-down', 'panel-size', 'panel-hide'].includes(action)) dashboardPanelAction(action, event.target.closest('[data-action]'));
    if (action === 'reset-display') {
      setFontSize('standard');
      setDensity('comfortable');
    }
    if (action === 'print') window.print();
    if (action === 'briefing-fullscreen') {
      const workspace = doc.querySelector('.briefing-workspace');
      if (!doc.fullscreenElement) workspace?.requestFullscreen?.();
      else doc.exitFullscreen?.();
    }
    if (action === 'division-fullscreen') {
      const experience = doc.querySelector('[data-division-experience]');
      if (!doc.fullscreenElement) experience?.requestFullscreen?.();
      else doc.exitFullscreen?.();
    }

    const taskButton = event.target.closest('[data-task-open]');
    if (taskButton && taskButton.dataset.quickPanel === 'true') {
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

  doc.addEventListener('change', (event) => {
    if (event.target.matches('[data-font-size-choice]')) setFontSize(event.target.value);
    if (event.target.matches('[data-density-choice]')) setDensity(event.target.value);
  });

  doc.addEventListener('submit', (event) => {
    const trigger = event.submitter;
    const message = trigger?.dataset.confirm || event.target.dataset.confirm;
    if (message && !window.confirm(message)) event.preventDefault();
  });

  doc.addEventListener('DOMContentLoaded', () => {
    const app = doc.getElementById('app-shell');
    if ((localStorage.getItem('jsj6-sidebar') || localStorage.getItem('ddc5i-sidebar')) === 'collapsed' && window.innerWidth > 820) app?.classList.add('collapsed');
    setFontSize(root.dataset.fontSize);
    setDensity(root.dataset.density);
    const guide = doc.querySelector('[data-page-guide]');
    const guideButton = guide?.querySelector('[data-action="toggle-guidance"]');
    const returningUser = localStorage.getItem('jsj6-visited') === 'true';
    const guidePref = localStorage.getItem('jsj6-guide-collapsed');
    if (guide && guideButton && (guidePref === 'true' || (guidePref === null && returningUser))) {
      guide.classList.add('is-collapsed');
      guideButton.setAttribute('aria-expanded', 'false');
      guideButton.textContent = 'Show guide';
    }
    initAdaptiveShell(returningUser);
    localStorage.setItem('jsj6-visited', 'true');
    markInputZones();

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
    setupDivisionImages();
    setupEntranceAnimations();
    setupInvestmentFlow();
    setupTravelMap();
    initDashboardLayout();

    const workspace = doc.querySelector('[data-project-task-workspace]');
    if (workspace?.dataset.openTask) {
      const projectId = workspace.dataset.projectId;
      const taskId = workspace.dataset.openTask;
      window.location.replace(`/projects/${encodeURIComponent(projectId)}/tasks/${encodeURIComponent(taskId)}`);
    }
  });
})();
