/*
 * charts-common.js — shared helpers for the two benchmark dashboards
 * (benchmark-charts.html · quality-benchmarks-charts.html).
 *
 * IMPORTANT: this is a plain classic script (NOT an ES module). It is loaded
 * with a bare <script src="charts-common.js"></script> so both pages keep
 * working when opened directly over file:// (ES modules would hit CORS). It
 * exposes a single global: window.ChartsCommon. Chart.js + the datalabels
 * plugin must already be loaded (their CDN <script> tags come first).
 *
 * The two pages drive every chart and scoreboard from a canonical, tidy data
 * model — MODELS (one record per model) + RESULTS (one record per measured
 * value) — defined inline in each page. This file only holds the machinery:
 * theme, the global filter state + filter bar, chart builders that derive
 * their data from RESULTS, and the sortable/filterable scoreboard.
 */
(function () {
  'use strict';

  // ---- theme / datalabels -------------------------------------------------

  var labelsOn = true;                 // shared "show data labels" state
  var charts = [];                     // every chart, for the label toggle

  // Shared datalabels config. `display` closes over THIS labelsOn, so every
  // chart built through the helpers (or spreading DATALABELS) honours the
  // single header checkbox. Individual charts spread this and override bits.
  var DATALABELS = {
    color: '#e6e6e6',
    anchor: 'end',
    align: 'end',
    offset: 2,
    clamp: true,
    font: { size: 10, weight: '600' },
    formatter: function (v) {
      return (v === null || v === undefined) ? '' : (Number.isInteger(v) ? v : v.toFixed(1));
    },
    display: function () { return labelsOn; }
  };

  // Tier fallback colors (local models carry their own `color`).
  var TIER_COLOR = { local: null, frontier: '#b86bff', open: '#888c94' };

  function initTheme() {
    Chart.defaults.color = '#9aa0a6';
    Chart.defaults.borderColor = '#262a33';
    Chart.defaults.font.family = '-apple-system, BlinkMacSystemFont, "SF Pro Text", Arial, sans-serif';
    Chart.register(ChartDataLabels);
    injectStyles();
  }

  function setLabelsOn(on) {
    labelsOn = on;
    charts.forEach(function (c) { c.update(); });
  }

  function bindLabelToggle(input) {
    if (!input) return;
    input.addEventListener('change', function (e) { setLabelsOn(e.target.checked); });
  }

  function gridOpts(yLabel, suggestedMax) {
    return {
      responsive: true,
      maintainAspectRatio: false,
      layout: { padding: { top: 20 } },
      plugins: {
        legend: { labels: { color: '#e6e6e6', boxWidth: 14 } },
        tooltip: { mode: 'index', intersect: false },
        datalabels: DATALABELS
      },
      scales: {
        x: { grid: { color: '#262a33' }, ticks: { color: '#9aa0a6' } },
        y: {
          grid: { color: '#262a33' },
          ticks: { color: '#9aa0a6' },
          title: { display: !!yLabel, text: yLabel, color: '#9aa0a6' },
          suggestedMax: suggestedMax
        }
      }
    };
  }

  function registerChart(c) { charts.push(c); return c; }

  // ---- data model helpers -------------------------------------------------

  function indexModels(models) {
    var m = new Map();
    models.forEach(function (x) { m.set(x.id, x); });
    return m;
  }

  // Find a single record in the tidy RESULTS array. `query` is an object whose
  // keys must all match (e.g. {metric:'accuracy', bench:'MMLU'} or
  // {metric:'genTps', scenario:'creative-writing'}). Returns the record or null.
  function findRecord(results, modelId, query) {
    for (var i = 0; i < results.length; i++) {
      var r = results[i];
      if (r.model !== modelId) continue;
      var ok = true;
      for (var k in query) { if (query[k] !== undefined && r[k] !== query[k]) { ok = false; break; } }
      if (ok) return r;
    }
    return null;
  }

  // The value for a query (explicit null = "not run"; null when no record).
  function metricValue(results, modelId, query) {
    var r = findRecord(results, modelId, query);
    return r ? (r.value === undefined ? null : r.value) : null;
  }

  // Ordered array of values for a grouped bar / line dataset: one value per
  // key (e.g. one per benchmark or per scenario). Nulls are preserved in
  // position so Chart.js renders a gap rather than shifting bars.
  function seriesFor(results, modelId, baseQuery, keys, keyField) {
    return keys.map(function (k) {
      var q = Object.assign({}, baseQuery);
      q[keyField] = k;
      return metricValue(results, modelId, q);
    });
  }

  // Rows for a ranked horizontal-bar chart: every model that has a value for
  // `query`, is not flagged refExclude, and passes the active filter — sorted
  // high→low. Row label = labelFn(model) + the matched record's per-row `note`
  // (footnotes such as "'26" or "(measured; comm ~80)" live on the record so a
  // model can carry a different note per benchmark).
  function deriveRanked(models, results, query, state, labelFn) {
    return models
      .filter(function (m) { return !m.refExclude; })
      .map(function (m) {
        var rec = findRecord(results, m.id, query);
        return { m: m, value: rec ? (rec.value === undefined ? null : rec.value) : null, note: rec ? rec.note : null };
      })
      .filter(function (x) { return x.value != null && state.isVisible(x.m); })
      .sort(function (a, b) { return b.value - a.value; })
      .map(function (x) {
        return {
          label: labelFn(x.m) + (x.note ? ' ' + x.note : ''),
          value: x.value,
          color: x.m.color || TIER_COLOR[x.m.tier],
          modelId: x.m.id
        };
      });
  }

  // ---- filter state -------------------------------------------------------

  // The global filter. A model is visible when its per-model checkbox is on
  // AND its tier/arch/quant are enabled. arch/quant only constrain models that
  // actually carry those fields — frontier/open models (no arch/quant) always
  // pass those two, so the tier toggle is what hides them.
  function createFilterState(models) {
    var byId = indexModels(models);
    var archs = new Set();
    var quants = new Set();
    var providers = new Set();
    var families = new Set();
    models.forEach(function (m) {
      if (m.arch) archs.add(m.arch);
      if (m.quant) quants.add(m.quant);
      if (m.provider) providers.add(m.provider);
      if (m.family) families.add(m.family);
    });

    var state = {
      models: models,
      byId: byId,
      checked: new Set(models.map(function (m) { return m.id; })),
      tiers: new Set(models.map(function (m) { return m.tier; })),
      archs: new Set(archs),
      quants: new Set(quants),
      providers: new Set(providers),
      families: new Set(families),
      _listeners: [],

      isVisible: function (m) {
        if (!m) return false;
        if (!this.checked.has(m.id)) return false;
        if (!this.tiers.has(m.tier)) return false;
        if (m.provider && !this.providers.has(m.provider)) return false;
        if (m.family && !this.families.has(m.family)) return false;
        if (m.arch && !this.archs.has(m.arch)) return false;
        if (m.quant && !this.quants.has(m.quant)) return false;
        return true;
      },
      isVisibleById: function (id) { return this.isVisible(this.byId.get(id)); },

      onChange: function (fn) { this._listeners.push(fn); return fn; },
      notify: function () {
        var self = this;
        this._listeners.forEach(function (fn) { fn(self); });
      },

      toggleModel: function (id) {
        if (this.checked.has(id)) this.checked.delete(id); else this.checked.add(id);
        this.notify();
      },
      setModelsChecked: function (ids, on) {
        var self = this;
        ids.forEach(function (id) { if (on) self.checked.add(id); else self.checked.delete(id); });
        this.notify();
      },
      toggleSet: function (setName, value) {
        var s = this[setName];
        if (s.has(value)) s.delete(value); else s.add(value);
        this.notify();
      }
    };
    return state;
  }

  // ---- filter bar UI ------------------------------------------------------

  // Renders the sticky filter bar into `container`. opts:
  //   checkboxModels : models to show individual checkboxes for (default: tier==='local')
  //   tiers          : tier values to expose as pills (default: distinct tiers, only if >1)
  //   sections       : [{id,label}] anchor-nav links (optional)
  function createFilterBar(container, state, opts) {
    opts = opts || {};
    var checkboxModels = opts.checkboxModels ||
      state.models.filter(function (m) { return m.tier === 'local'; });
    var checkIds = checkboxModels.map(function (m) { return m.id; });

    var tierVals = opts.tiers || distinct(state.models.map(function (m) { return m.tier; }));
    var archVals = distinct(state.models.map(function (m) { return m.arch; }).filter(Boolean));
    var quantVals = distinct(state.models.map(function (m) { return m.quant; }).filter(Boolean));
    var providerVals = distinct(state.models.map(function (m) { return m.provider; }).filter(Boolean));
    var familyVals = distinct(state.models.map(function (m) { return m.family; }).filter(Boolean));

    // --- models group ---
    var modelsGroup = el('div', 'filter-group');
    modelsGroup.appendChild(labelSpan('Models'));
    var checkboxes = [];
    checkboxModels.forEach(function (m) {
      var lab = el('label', 'model-check');
      var cb = document.createElement('input');
      cb.type = 'checkbox';
      cb.checked = true;
      cb.dataset.modelId = m.id;
      cb.addEventListener('change', function () { state.toggleModel(m.id); });
      lab.appendChild(cb);
      lab.appendChild(swatch(m.color || TIER_COLOR[m.tier]));
      lab.appendChild(document.createTextNode(m.label));
      modelsGroup.appendChild(lab);
      checkboxes.push(cb);
    });
    var allBtn = button('All', function () { state.setModelsChecked(checkIds, true); });
    var noneBtn = button('None', function () { state.setModelsChecked(checkIds, false); });
    modelsGroup.appendChild(allBtn);
    modelsGroup.appendChild(noneBtn);
    container.appendChild(modelsGroup);

    // --- pill groups ---
    var pillRefs = [];
    function pillGroup(title, values, setName) {
      if (values.length < 2) return;             // nothing to filter
      container.appendChild(divider());
      var g = el('div', 'filter-group');
      g.appendChild(labelSpan(title));
      values.forEach(function (v) {
        var p = el('button', 'pill-toggle active');
        p.type = 'button';
        p.textContent = v;
        p.addEventListener('click', function () { state.toggleSet(setName, v); });
        g.appendChild(p);
        pillRefs.push({ el: p, setName: setName, value: v });
      });
      container.appendChild(g);
    }
    pillGroup('Tier', tierVals, 'tiers');
    pillGroup('Provider', providerVals, 'providers');
    pillGroup('Family', familyVals, 'families');
    pillGroup('Arch', archVals, 'archs');
    pillGroup('Quant', quantVals, 'quants');

    // --- section nav ---
    if (opts.sections && opts.sections.length) {
      container.appendChild(divider());
      var nav = el('nav', 'section-nav');
      opts.sections.forEach(function (s) {
        var a = document.createElement('a');
        a.href = '#' + s.id;
        a.textContent = s.label;
        a.dataset.section = s.id;
        nav.appendChild(a);
      });
      container.appendChild(nav);
      setupSectionNav(nav, opts.sections);
    }

    // Keep the bar's controls in sync with state (e.g. legend clicks, All/None).
    state.onChange(function (st) {
      checkboxes.forEach(function (cb) { cb.checked = st.checked.has(cb.dataset.modelId); });
      pillRefs.forEach(function (p) { p.el.classList.toggle('active', st[p.setName].has(p.value)); });
    });
  }

  // Highlights the active section link while scrolling.
  function setupSectionNav(nav, sections) {
    if (!('IntersectionObserver' in window)) return;
    var links = {};
    sections.forEach(function (s) { links[s.id] = nav.querySelector('[data-section="' + s.id + '"]'); });
    var visible = {};
    var obs = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) { visible[e.target.id] = e.isIntersecting; });
      var current = null;
      for (var i = 0; i < sections.length; i++) { if (visible[sections[i].id]) { current = sections[i].id; break; } }
      Object.keys(links).forEach(function (id) { if (links[id]) links[id].classList.toggle('active', id === current); });
    }, { rootMargin: '-125px 0px -70% 0px' });
    sections.forEach(function (s) {
      var target = document.getElementById(s.id);
      if (target) obs.observe(target);
    });
  }

  // ---- chart builders -----------------------------------------------------

  // Grouped bar / line chart: one dataset per model. Datasets MUST carry a
  // `modelId`. Filtering hides datasets in place (setDatasetVisibility) so the
  // legend keeps every model (struck-through when hidden); clicking a local
  // model's legend entry toggles it globally across all charts + the bar.
  function buildGroupedChart(canvasId, cfg) {
    var opts = cfg.options || {};
    // Set the legend onClick on the plain options object BEFORE construction —
    // mutating the resolved chart.options proxy afterwards can send Chart.js
    // into an infinite option-resolution loop.
    opts.plugins = opts.plugins || {};
    opts.plugins.legend = opts.plugins.legend || {};
    opts.plugins.legend.onClick = groupedLegendOnClick(cfg.state);
    var chart = registerChart(new Chart(document.getElementById(canvasId), {
      type: cfg.type || 'bar',
      data: { labels: cfg.labels, datasets: cfg.datasets },
      options: opts
    }));
    registerGroupedVisibility(chart, cfg.state);
    return chart;
  }

  // Global legend behaviour: local models toggle everywhere; non-local
  // reference datasets (rare) fall back to a chart-local show/hide so they
  // can't get stuck off with no checkbox to restore them.
  function groupedLegendOnClick(state) {
    return function (e, item, legend) {
      var ds = legend.chart.data.datasets[item.datasetIndex];
      if (!ds) return;
      var m = state.byId.get(ds.modelId);
      if (m && m.tier === 'local') {
        state.toggleModel(ds.modelId);
      } else {
        legend.chart.setDatasetVisibility(item.datasetIndex, !legend.chart.isDatasetVisible(item.datasetIndex));
        legend.chart.update();
      }
    };
  }

  // Registers a filter listener that shows/hides each model's dataset in place.
  function registerGroupedVisibility(chart, state) {
    state.onChange(function (st) {
      chart.data.datasets.forEach(function (ds, i) {
        var m = st.byId.get(ds.modelId);
        if (m) chart.setDatasetVisibility(i, st.isVisible(m));
      });
      chart.update('none');
    });
  }

  // Ranked horizontal-bar chart driven by RESULTS. Rows drop & re-rank as the
  // filter changes. Legend is disabled (colors are per-row, not per-series).
  function buildRankedChart(canvasId, cfg) {
    var state = cfg.state;
    var labelFn = cfg.labelFn || function (m) { return m.label; };
    function rows() { return deriveRanked(cfg.models, cfg.results, cfg.query, state, labelFn); }
    var initial = rows();

    var chart = registerChart(new Chart(document.getElementById(canvasId), {
      type: 'bar',
      data: {
        labels: initial.map(function (r) { return r.label; }),
        datasets: [{
          label: cfg.axisLabel,
          data: initial.map(function (r) { return r.value; }),
          backgroundColor: initial.map(function (r) { return r.color; }),
          borderWidth: 0,
          maxBarThickness: 26
        }]
      },
      options: {
        indexAxis: 'y',
        responsive: true,
        maintainAspectRatio: false,
        layout: { padding: { right: 34 } },
        plugins: {
          legend: { display: false },
          tooltip: { mode: 'nearest', intersect: false },
          datalabels: Object.assign({}, DATALABELS, { anchor: 'end', align: 'end', offset: 4, color: '#e6e6e6' })
        },
        scales: {
          x: {
            grid: { color: '#262a33' }, ticks: { color: '#9aa0a6' }, suggestedMax: 100,
            title: { display: true, text: cfg.axisLabel + ' (%)', color: '#9aa0a6' }
          },
          y: { grid: { display: false }, ticks: { color: '#e6e6e6', font: { size: 11 } } }
        }
      }
    }));

    state.onChange(function () {
      var r = rows();
      chart.data.labels = r.map(function (x) { return x.label; });
      chart.data.datasets[0].data = r.map(function (x) { return x.value; });
      chart.data.datasets[0].backgroundColor = r.map(function (x) { return x.color; });
      chart.update('none');
    });
    return chart;
  }

  // Quality-vs-speed bubble scatter: one dataset per (local) model, single
  // point each. x from xQuery, y from a selectable benchmark, radius from disk
  // size. `benchOptions` populates the <select>; a `composite` option averages
  // the accuracy benches. Models missing an x value are omitted.
  function buildScatterChart(canvasId, cfg) {
    var state = cfg.state;
    var selectEl = cfg.selectEl;
    var models = cfg.models.filter(function (m) {
      return metricValue(cfg.results, m.id, cfg.xQuery) != null;
    });

    function yValue(m, key) {
      if (key === 'composite') {
        var vals = cfg.compositeBenches
          .map(function (b) { return metricValue(cfg.results, m.id, { metric: cfg.accuracyMetric, bench: b }); })
          .filter(function (v) { return v != null; });
        if (!vals.length) return { v: null, n: 0 };
        var sum = vals.reduce(function (a, b) { return a + b; }, 0);
        return { v: sum / vals.length, n: vals.length };
      }
      return { v: metricValue(cfg.results, m.id, { metric: cfg.accuracyMetric, bench: key }), n: 1 };
    }

    function pointFor(m, key) {
      var x = metricValue(cfg.results, m.id, cfg.xQuery);
      var y = yValue(m, key);
      if (y.v == null) return null;
      return { x: x, y: y.v, r: cfg.radiusFn(m.diskGB || 0), _n: y.n, _diskGB: m.diskGB };
    }

    function currentKey() { return selectEl ? selectEl.value : 'composite'; }

    var datasets = models.map(function (m) {
      var p = pointFor(m, currentKey());
      return {
        label: m.label,
        modelId: m.id,
        backgroundColor: (m.color || TIER_COLOR[m.tier]) + 'cc',
        borderColor: m.color || TIER_COLOR[m.tier],
        borderWidth: 1,
        data: p ? [p] : [],
        datalabels: Object.assign({}, DATALABELS, {
          anchor: 'end', align: 'top', offset: 4, font: { size: 9, weight: '600' },
          formatter: function () { return m.label; }
        })
      };
    });

    var chart = registerChart(new Chart(document.getElementById(canvasId), {
      type: 'bubble',
      data: { datasets: datasets },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        layout: { padding: { top: 20, right: 20 } },
        plugins: {
          legend: { labels: { color: '#e6e6e6', boxWidth: 12, font: { size: 11 } }, onClick: groupedLegendOnClick(state) },
          tooltip: {
            callbacks: {
              label: function (ctx) {
                var d = ctx.raw;
                var suffix = (currentKey() === 'composite' && d._n < cfg.compositeBenches.length)
                  ? ' (' + d._n + '/' + cfg.compositeBenches.length + ' benches)' : '';
                return ctx.dataset.label + ': ' + round1(d.y) + ' pts' + suffix +
                  ' @ ' + round1(d.x) + ' tok/s · ' + d._diskGB + ' GB';
              }
            }
          },
          datalabels: { display: function () { return labelsOn; } }
        },
        scales: {
          x: {
            grid: { color: '#262a33' }, ticks: { color: '#9aa0a6' }, beginAtZero: true,
            title: { display: true, text: cfg.xLabel, color: '#9aa0a6' }
          },
          y: {
            grid: { color: '#262a33' }, ticks: { color: '#9aa0a6' }, beginAtZero: true, suggestedMax: 100,
            title: { display: true, text: 'Benchmark score', color: '#9aa0a6' }
          }
        }
      }
    }));

    function refreshPoints() {
      var key = currentKey();
      chart.data.datasets.forEach(function (ds) {
        var m = state.byId.get(ds.modelId);
        var p = pointFor(m, key);
        ds.data = p ? [p] : [];
      });
      chart.update();
    }
    if (selectEl) selectEl.addEventListener('change', refreshPoints);
    registerGroupedVisibility(chart, state);
    return chart;
  }

  // Model radar with its own 2–3 model picker (independent of the global
  // filter, which only constrains which models the picker offers). Axes are
  // fixed 0–100 — every axis is already a percentage, and fixed bounds keep
  // polygon shapes comparable regardless of which models are selected.
  function buildRadarChart(canvasId, cfg) {
    var state = cfg.state;
    var maxSel = cfg.maxSelected || 3;
    var selectable = cfg.models.filter(function (m) {
      return cfg.axes.some(function (a) { return metricValue(cfg.results, m.id, a.query) != null; });
    });
    var selected = (cfg.defaultSelection || []).slice(0, maxSel);

    var chart = registerChart(new Chart(document.getElementById(canvasId), {
      type: 'radar',
      data: { labels: cfg.axes.map(function (a) { return a.label; }), datasets: [] },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { labels: { color: '#e6e6e6', boxWidth: 12, font: { size: 11 } } },
          tooltip: { mode: 'nearest', intersect: true },
          datalabels: { display: false }
        },
        scales: {
          r: {
            min: 0, max: 100,
            angleLines: { color: '#262a33' },
            grid: { color: '#262a33' },
            pointLabels: { color: '#cdd1d6', font: { size: 11 } },
            ticks: { color: '#9aa0a6', backdropColor: 'transparent', stepSize: 25, showLabelBackdrop: false }
          }
        }
      }
    }));

    function datasetFor(m) {
      return {
        label: m.label,
        data: cfg.axes.map(function (a) { return metricValue(cfg.results, m.id, a.query); }),
        backgroundColor: (m.color || TIER_COLOR[m.tier]) + '33',
        borderColor: m.color || TIER_COLOR[m.tier],
        pointBackgroundColor: m.color || TIER_COLOR[m.tier],
        pointRadius: 3,
        borderWidth: 2,
        fill: true
      };
    }
    function rebuild() {
      chart.data.datasets = selected.map(function (id) { return datasetFor(state.byId.get(id)); });
      chart.update();
    }

    // picker
    var boxes = [];
    selectable.forEach(function (m) {
      var lab = el('label', 'radar-opt');
      var cb = document.createElement('input');
      cb.type = 'checkbox';
      cb.dataset.modelId = m.id;
      cb.checked = selected.indexOf(m.id) !== -1;
      cb.addEventListener('change', function () {
        if (cb.checked) {
          if (selected.length >= maxSel) { cb.checked = false; return; }
          selected.push(m.id);
        } else {
          selected = selected.filter(function (x) { return x !== m.id; });
        }
        rebuild();
        syncPicker();
      });
      lab.appendChild(cb);
      var sw = swatch(m.color || TIER_COLOR[m.tier]);
      lab.appendChild(sw);
      var txt = document.createElement('span');
      txt.textContent = m.label;
      lab.appendChild(txt);
      cfg.pickerContainer.appendChild(lab);
      boxes.push({ cb: cb, model: m, label: lab });
    });

    function syncPicker() {
      var full = selected.length >= maxSel;
      boxes.forEach(function (b) {
        var offered = state.isVisible(b.model);
        b.label.style.display = offered ? '' : 'none';
        b.cb.disabled = (!b.cb.checked && full) || !offered;
      });
    }

    // Drop globally-filtered models from the selection.
    state.onChange(function (st) {
      var before = selected.length;
      selected = selected.filter(function (id) { return st.isVisible(st.byId.get(id)); });
      if (selected.length !== before) rebuild();
      syncPicker();
    });

    rebuild();
    syncPicker();
    return chart;
  }

  // ---- scoreboard ---------------------------------------------------------

  // Generates a scoreboard <tbody> from the data model. `columns` describes
  // each column after the model cell:
  //   { kind:'str', get:fn }                        — text column (e.g. Tier)
  //   { kind:'num', query:{...}, fmt?:fn }          — numeric metric column
  // Rows are emitted in MODELS order and tagged with data-model-id + tier class
  // so the filter can hide them and best-per-column can recompute.
  function buildScoreboard(tableEl, models, results, columns) {
    var tbody = tableEl.querySelector('tbody') || tableEl.appendChild(document.createElement('tbody'));
    tbody.innerHTML = '';
    models.forEach(function (m) {
      var tr = document.createElement('tr');
      tr.dataset.modelId = m.id;
      tr.classList.add('tier-' + m.tier);

      var td0 = document.createElement('td');
      td0.className = 'model-cell';
      td0.appendChild(swatch(m.color || TIER_COLOR[m.tier]));
      td0.appendChild(document.createTextNode(m.label));
      tr.appendChild(td0);

      columns.forEach(function (col) {
        var td = document.createElement('td');
        if (col.kind === 'str') {
          td.textContent = col.get(m);
        } else {
          var v = metricValue(results, m.id, col.query);
          td.className = 'num';
          if (v == null) { td.classList.add('dash'); td.textContent = '—'; }
          else { td.dataset.value = v; td.textContent = (col.fmt || fmt1)(v); }
        }
        tr.appendChild(td);
      });
      tbody.appendChild(tr);
    });
  }

  function setupSortableTable(tableId, defaultSortCol, defaultDir) {
    if (defaultSortCol === undefined) defaultSortCol = null;
    if (defaultDir === undefined) defaultDir = -1;
    var table = document.getElementById(tableId);
    if (!table) return;
    var headers = Array.prototype.slice.call(table.querySelectorAll('thead th'));
    var tbody = table.querySelector('tbody');
    var originalOrder = Array.prototype.slice.call(tbody.querySelectorAll('tr'));
    var state = { col: null, dir: 1 };

    function sortBy(idx, dir) {
      var th = headers[idx];
      var sortType = th.dataset.sort;
      var rows = Array.prototype.slice.call(tbody.querySelectorAll('tr'));
      rows.sort(function (a, b) {
        var av = (a.children[idx].dataset.value != null ? a.children[idx].dataset.value : a.children[idx].textContent).trim();
        var bv = (b.children[idx].dataset.value != null ? b.children[idx].dataset.value : b.children[idx].textContent).trim();
        if (sortType === 'num') {
          var an = parseFloat(av), bn = parseFloat(bv);
          var aNaN = isNaN(an), bNaN = isNaN(bn);
          if (aNaN && bNaN) return 0;
          if (aNaN) return 1;
          if (bNaN) return -1;
          return (an - bn) * dir;
        }
        return av.localeCompare(bv) * dir;
      });
      rows.forEach(function (r) { tbody.appendChild(r); });
      headers.forEach(function (h) { h.removeAttribute('data-sorted'); });
      th.setAttribute('data-sorted', dir === 1 ? 'asc' : 'desc');
      state = { col: idx, dir: dir };
    }

    headers.forEach(function (th, idx) {
      if (!th.dataset.sort) return;
      th.addEventListener('click', function () {
        var dir;
        if (state.col === idx) dir = -state.dir;
        else dir = th.dataset.sort === 'num' ? -1 : 1;
        sortBy(idx, dir);
      });
    });
    headers.forEach(function (th) {
      th.addEventListener('dblclick', function () {
        originalOrder.forEach(function (r) { tbody.appendChild(r); });
        headers.forEach(function (h) { h.removeAttribute('data-sorted'); });
        state = { col: null, dir: 1 };
      });
    });
    if (defaultSortCol !== null) sortBy(defaultSortCol, defaultDir);
  }

  // Highlights the max cell in each numeric column. Clears any prior
  // highlight first and ignores filtered-out (hidden) rows, so it can re-run
  // on every filter change.
  function highlightBestPerColumn(tableId) {
    var table = document.getElementById(tableId);
    if (!table) return;
    var headers = Array.prototype.slice.call(table.querySelectorAll('thead th'));
    var rows = Array.prototype.slice.call(table.querySelectorAll('tbody tr'));
    table.querySelectorAll('td.best').forEach(function (c) { c.classList.remove('best'); });
    headers.forEach(function (th, idx) {
      if (th.dataset.sort !== 'num') return;
      var best = -Infinity, bestCells = [];
      rows.forEach(function (r) {
        if (r.classList.contains('filtered-out')) return;
        var cell = r.children[idx];
        var v = parseFloat(cell.textContent.trim());
        if (isNaN(v)) return;
        if (v > best) { best = v; bestCells = [cell]; }
        else if (v === best) bestCells.push(cell);
      });
      bestCells.forEach(function (c) { c.classList.add('best'); });
    });
  }

  // Hides/shows scoreboard (or editorial) rows by data-model-id, then re-runs
  // best-per-column. Call once to wire it to the filter.
  function applyTableFilter(tableId, state, opts) {
    opts = opts || {};
    var table = document.getElementById(tableId);
    if (!table) return;
    var rows = Array.prototype.slice.call(table.querySelectorAll('tbody tr'));
    rows.forEach(function (r) {
      var id = r.dataset.modelId;
      if (!id) return;                    // rows without an id stay visible
      r.classList.toggle('filtered-out', !state.isVisibleById(id));
    });
    if (opts.highlight) highlightBestPerColumn(tableId);
  }

  // ---- small DOM/format utils --------------------------------------------

  function el(tag, cls) { var e = document.createElement(tag); if (cls) e.className = cls; return e; }
  function labelSpan(text) { var s = el('span', 'filter-label'); s.textContent = text; return s; }
  function swatch(color) { var s = el('span', 'swatch'); s.style.background = color; return s; }
  function button(text, onClick) {
    var b = el('button', 'filter-btn'); b.type = 'button'; b.textContent = text;
    b.addEventListener('click', onClick); return b;
  }
  function divider() { return el('span', 'filter-divider'); }
  function distinct(arr) { var out = []; arr.forEach(function (x) { if (out.indexOf(x) === -1) out.push(x); }); return out; }
  function round1(v) { return Math.round(v * 10) / 10; }

  // Show one decimal by default, but keep extra precision when the source
  // value has it (e.g. 89.75 stays 89.75, 56.0 stays "56.0").
  function fmt1(v) {
    var r = v.toFixed(1);
    return (+r === v) ? r : String(v);
  }
  function fmtInt(v) { return String(v); }

  function injectStyles() {
    if (document.getElementById('charts-common-styles')) return;
    var css = [
      '.filter-bar{position:sticky;top:0;z-index:20;background:var(--bg);border-bottom:1px solid var(--border);',
      'padding:10px 32px;display:flex;flex-wrap:wrap;align-items:center;gap:8px 16px;}',
      '.filter-group{display:inline-flex;align-items:center;flex-wrap:wrap;gap:6px;}',
      '.filter-label{font-size:11px;text-transform:uppercase;letter-spacing:.04em;color:var(--muted);margin-right:2px;}',
      '.model-check{display:inline-flex;align-items:center;gap:4px;font-size:12px;color:var(--text);cursor:pointer;',
      'font-family:ui-monospace,SFMono-Regular,Menlo,monospace;}',
      '.model-check input,.radar-opt input{cursor:pointer;width:14px;height:14px;}',
      '.model-check .swatch,.radar-opt .swatch{margin-right:0;}',
      '.filter-btn{font-size:11px;color:var(--muted);background:#1b1f27;border:1px solid var(--border);border-radius:5px;',
      'padding:2px 8px;cursor:pointer;}',
      '.filter-btn:hover{color:var(--text);border-color:#3a414e;}',
      '.pill-toggle{font-size:12px;color:var(--muted);background:#1b1f27;border:1px solid var(--border);border-radius:12px;',
      'padding:2px 10px;cursor:pointer;user-select:none;}',
      '.pill-toggle.active{color:#0f1115;background:var(--accent);border-color:var(--accent);font-weight:600;}',
      '.filter-divider{width:1px;align-self:stretch;background:var(--border);margin:0 2px;min-height:20px;}',
      '.section-nav{display:inline-flex;flex-wrap:wrap;gap:12px;}',
      '.section-nav a{font-size:12px;color:var(--muted);text-decoration:none;padding:2px 2px;border-bottom:2px solid transparent;}',
      '.section-nav a:hover{color:var(--text);}',
      '.section-nav a.active{color:var(--accent);border-bottom-color:var(--accent);}',
      'html{scroll-behavior:smooth;}',
      '.category-heading{grid-column:1/-1;margin:16px 0 0;font-size:15px;font-weight:600;letter-spacing:.02em;',
      'color:var(--text);scroll-margin-top:120px;border-bottom:1px solid var(--border);padding-bottom:8px;}',
      '.category-heading .hint{font-size:12px;font-weight:400;color:var(--muted);margin-left:10px;text-transform:none;letter-spacing:0;}',
      '.radar-picker,.scatter-controls{display:flex;flex-wrap:wrap;gap:8px 14px;margin-bottom:12px;align-items:center;}',
      '.radar-opt{display:inline-flex;align-items:center;gap:4px;font-size:12px;color:var(--text);cursor:pointer;',
      'font-family:ui-monospace,SFMono-Regular,Menlo,monospace;}',
      '.radar-opt input:disabled{cursor:not-allowed;}',
      '.scatter-controls select{background:#1b1f27;color:var(--text);border:1px solid var(--border);border-radius:5px;',
      'padding:3px 8px;font-size:12px;}',
      '.control-label{font-size:11px;text-transform:uppercase;letter-spacing:.04em;color:var(--muted);}',
      'tr.filtered-out{display:none;}'
    ].join('');
    var style = document.createElement('style');
    style.id = 'charts-common-styles';
    style.textContent = css;
    document.head.appendChild(style);
  }

  // ---- public API ---------------------------------------------------------

  window.ChartsCommon = {
    initTheme: initTheme,
    DATALABELS: DATALABELS,
    TIER_COLOR: TIER_COLOR,
    setLabelsOn: setLabelsOn,
    bindLabelToggle: bindLabelToggle,
    gridOpts: gridOpts,
    registerChart: registerChart,

    indexModels: indexModels,
    metricValue: metricValue,
    seriesFor: seriesFor,
    deriveRanked: deriveRanked,

    createFilterState: createFilterState,
    createFilterBar: createFilterBar,

    buildGroupedChart: buildGroupedChart,
    buildRankedChart: buildRankedChart,
    buildScatterChart: buildScatterChart,
    buildRadarChart: buildRadarChart,

    buildScoreboard: buildScoreboard,
    setupSortableTable: setupSortableTable,
    highlightBestPerColumn: highlightBestPerColumn,
    applyTableFilter: applyTableFilter,

    fmt1: fmt1,
    fmtInt: fmtInt
  };
})();
