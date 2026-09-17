// Dashboard · Violencia de pareja contra la mujer en el Perú
// Datos: INEI · ENDES 2021-2025. Generados por scripts/generar_sitio.py.
// Servicios de atención: MIMP · Consolidado Directorio Nacional.
'use strict';
// ╔══════════════════════════════════════════════════════════════╗
// ║  JavaScript.html v6 · Dashboard Violencia contra la Mujer   ║
// ╚══════════════════════════════════════════════════════════════╝

// ── Estado global ────────────────────────────────────────────────
let DATOS = null, DIRECTORIO = null, PANEL = 1, charts = {};
const RUTA_INDICADORES = 'data/indicadores.json';
const RUTA_DIRECTORIO  = 'data/directorio.json';
const RUTA_GEOMETRIA   = 'data/departamentos.geojson';
const RUTA_UBIGEOS     = 'data/ubigeos.json';
const RUTA_GEO_DEP     = 'data/geo/';   // + <ubigeo de departamento>.json

// Filtro de KPI activo en P1 (null = todos)
let kpiActivo = null;

// Panel 2: tipos activos (multi) — se sincroniza con msState.tipo
let p2Tipos = ['violencia_total','violencia_psicologica','violencia_fisica','violencia_sexual'];

// Multi-select state
// Los años disponibles salen de los datos, no del código: al incorporar un año
// nuevo al pipeline el tablero lo ofrece solo, sin tocar el HTML.
let ANIOS = [];            // p. ej. ['2021','2022','2023','2024','2025']
let ANIO_ACTUAL = '';      // el más reciente publicado

const msState = {
  p1:     [],
  p2:     [],
  p3:     [],
  p4:     [],
  dep:    ['Todos'],
  tipoP1: ['violencia_total','violencia_psicologica','violencia_fisica','violencia_sexual'],
  tipo:   ['violencia_total','violencia_psicologica','violencia_fisica','violencia_sexual']
};

// Paleta principal — colores opacos/modernos para tipos de violencia
const C = {
  total: '#C0534A', fisica: '#5B8EC4', psic: '#7B6BBF', sexual: '#4BAD8A',
  green: '#16A34A', amber: '#D97706', red: '#DC2626',
  text: '#1A1D2E', muted: '#8B8FA8', border: '#DDE1EC', bg: '#F0F2F8',
  azul:    ['#1E3A8A','#1D4ED8','#2563EB','#3B82F6','#60A5FA','#93C5FD','#BFDBFE','#DBEAFE','#EFF6FF','#F0F9FF'],
  verde:   ['#14532D','#166534','#15803D','#16A34A','#22C55E','#4ADE80','#86EFAC','#BBF7D0','#DCFCE7','#F0FDF4'],
  morado:  ['#4C1D95','#5B21B6','#6D28D9','#7C3AED','#8B5CF6','#A78BFA','#C4B5FD','#DDD6FE','#EDE9FE','#F5F3FF'],
  naranja: ['#7C2D12','#9A3412','#C2410C','#EA580C','#F97316','#FB923C','#FDBA74','#FED7AA','#FFEDD5','#FFF7ED'],
};

const TIPOS = {
  violencia_total:       { label:'Total',       color:C.total,  mono:C.naranja },
  violencia_psicologica: { label:'Psicológica', color:C.psic,   mono:C.verde },
  violencia_fisica:      { label:'Física',      color:C.fisica, mono:C.azul },
  violencia_sexual:      { label:'Sexual',      color:C.sexual, mono:C.morado }
};

// Corrección de tildes en nombres de departamentos (fuente: GeoJSON / Excel sin tilde)
const DEPT_NAMES = {
  'Ancash':'Áncash','Apurimac':'Apurímac','Huanuco':'Huánuco','Junin':'Junín',
  'San Martin':'San Martín'
};
function deptLabel(dep) { return DEPT_NAMES[dep] || dep; }

// Situaciones de control del cuadro 12.2 del INEI: [etiqueta corta, columna del JSON].
// Las seis entran en el indicador de violencia psicológica.
const CTRL_ITEMS = [
  ['Es celoso o molesto',       'Es celoso o molesto si conversa con otro hombre'],
  ['La acusa de ser infiel',    'La acusa frecuentemente de ser infiel'],
  ['Insiste en saber dónde va', 'Insiste siempre en saber a dónde va'],
  ['Impide visitar amistades',  'Le impide que visite o la visiten sus amistades'],
  ['Desconfía con el dinero',   'Desconfía con el dinero'],
  ['Limita contacto familiar',  'Trata de limitar las visitas o el contacto con su familia']
];

// ── Chart.js defaults ────────────────────────────────────────────
Chart.register(ChartDataLabels);
Chart.defaults.color = C.muted;
Chart.defaults.font.family = "'Inter', system-ui, sans-serif";
Chart.defaults.font.size = 12;

// ════════════════════════════════════════════════════════════════
//  BOOTSTRAP
// ════════════════════════════════════════════════════════════════
window.addEventListener('DOMContentLoaded', () => {
  initToggleStates();
  fetch(RUTA_INDICADORES)
    .then(r => { if (!r.ok) throw new Error(`No se pudo leer ${RUTA_INDICADORES} (${r.status})`); return r.json(); })
    .then(d => {
      DATOS = d;
      inicializarAnios(d.meta);
      mostrarPie(d.meta);
      hideLoading();
      renderPanel(1);
    })
    .catch(e => { document.getElementById('loadingMsg').innerHTML =
      `❌ ${e.message}<br><span style="font-size:12px">Si abriste el archivo con doble clic, ` +
      `sírvelo por HTTP: <code>python -m http.server</code> dentro de <code>site/</code>.</span>`; });
  document.addEventListener('click', e => {
    if (!e.target.closest('.multi-select-wrap')) {
      document.querySelectorAll('.multi-select-dropdown.open').forEach(d => d.classList.remove('open'));
      document.querySelectorAll('.multi-select-btn.open').forEach(b => b.classList.remove('open'));
    }
  });
});

function hideLoading() { document.getElementById('loadingOverlay').style.display = 'none'; }

function enterDashboard(panelNum) {
  const overlay = document.getElementById('introOverlay');
  overlay.style.opacity = '0';
  overlay.style.transition = 'opacity .3s ease';
  setTimeout(() => { overlay.style.display = 'none'; }, 300);
  if (panelNum && panelNum !== 1) { showPanel(panelNum); }
}

function showToast(m) {
  const t = document.getElementById('updateToast');
  t.querySelector('.toast-msg').textContent = m;
  t.classList.add('show');
  setTimeout(() => t.classList.remove('show'), 3500);
}

// ════════════════════════════════════════════════════════════════
//  TOGGLE TEMPORAL (Alguna vez / 12 meses)
//  Estado guardado en JS — sobrevive rebuilds del DOM en P2
// ════════════════════════════════════════════════════════════════
const toggleState = {};  // { wrapperId: 'av'|'dm' }

function setToggle(wrapperId, val) {
  toggleState[wrapperId] = val;
  // Actualizar DOM si el elemento existe (puede no existir si P2 lo reconstruyó)
  const el = document.getElementById(wrapperId);
  if (el) {
    el.querySelectorAll('.temp-btn').forEach(b => {
      b.classList.toggle('active', b.dataset.val === val);
    });
  }
}

function getToggle(wrapperId) {
  // Primero mirar el estado JS (persistente entre rebuilds)
  if (toggleState[wrapperId]) return toggleState[wrapperId];
  // Fallback: leer del DOM
  const el = document.getElementById(wrapperId);
  if (el) {
    const active = el.querySelector('.temp-btn.active');
    return active ? active.dataset.val : 'av';
  }
  return 'av';
}

// Inicializar el estado de los toggles fijos del DOM al arrancar
function initToggleStates() {
  ['mapaToggle','g2Toggle','vennToggle'].forEach(id => {
    if (!toggleState[id]) toggleState[id] = 'av';
  });
}

// ════════════════════════════════════════════════════════════════
//  MULTI-SELECT (años, departamento, tipo)
// ════════════════════════════════════════════════════════════════
// Rellena los cuatro desplegables de año con los años que traen los datos y deja
// seleccionado el más reciente.
function inicializarAnios(meta) {
  ANIOS = (meta && meta.anios ? meta.anios : []).map(String);
  if (!ANIOS.length) return;
  ANIO_ACTUAL = ANIOS[ANIOS.length - 1];

  ['p1', 'p2', 'p3', 'p4'].forEach(panel => {
    msState[panel] = [ANIO_ACTUAL];
    const drop = document.getElementById('msDrop-' + panel);
    if (!drop) return;
    drop.innerHTML = [...ANIOS].reverse().map(anio => {
      const sel = anio === ANIO_ACTUAL;
      return `<div class="ms-option${sel ? ' selected' : ''}" data-val="${anio}"
        onclick="toggleMsOpt('${panel}','${anio}',this)"><div class="ms-check">${
        sel ? '✓' : ''}</div>${anio}</div>`;
    }).join('');
    const etiqueta = document.getElementById('msLabel-' + panel);
    if (etiqueta) etiqueta.textContent = ANIO_ACTUAL;
  });
}

function toggleMs(panel) {
  const drop = document.getElementById('msDrop-' + panel);
  const btn  = drop.previousElementSibling;
  const isOpen = drop.classList.contains('open');
  document.querySelectorAll('.multi-select-dropdown.open').forEach(d => d.classList.remove('open'));
  document.querySelectorAll('.multi-select-btn.open').forEach(b => b.classList.remove('open'));
  if (!isOpen) { drop.classList.add('open'); btn.classList.add('open'); }
}

function toggleMsOpt(panel, val, el) {
  const arr = msState[panel];
  const idx = arr.indexOf(val);
  if (idx >= 0) { if (arr.length > 1) arr.splice(idx, 1); }
  else arr.push(val);
  el.classList.toggle('selected', arr.includes(val));
  el.querySelector('.ms-check').textContent = arr.includes(val) ? '✓' : '';
  const sorted = [...arr].sort();
  document.getElementById('msLabel-' + panel).textContent =
    sorted.length === ANIOS.length ? 'Todos' : sorted.join(', ');
  renderPanel(PANEL);
}

// Departamento — selección única + opción "Todos"
function toggleDepOpt(val, el) {
  document.querySelectorAll('#msDrop-dep .ms-option').forEach(o => {
    o.classList.remove('selected');
    o.querySelector('.ms-check').textContent = '';
  });
  el.classList.add('selected');
  el.querySelector('.ms-check').textContent = '✓';
  msState.dep = [val];
  document.getElementById('msLabel-dep').textContent = val;
  renderPanel(PANEL);
}

// Tipo violencia P2 — multi
function toggleTipoOpt(val, el) {
  const arr = msState.tipo;
  const idx = arr.indexOf(val);
  if (idx >= 0) { if (arr.length > 1) arr.splice(idx, 1); }
  else arr.push(val);
  el.classList.toggle('selected', arr.includes(val));
  el.querySelector('.ms-check').textContent = arr.includes(val) ? '✓' : '';
  p2Tipos = [...msState.tipo];
  const n = msState.tipo.length;
  document.getElementById('msLabel-tipo').textContent =
    n === 4 ? 'Todos los tipos' : msState.tipo.map(t => TIPOS[t].label).join(', ');
  renderPanel(PANEL);
}

// Tipo violencia P1 — multiselect igual que año/depto
function toggleTipoP1Opt(val, el) {
  const arr = msState.tipoP1;
  const idx = arr.indexOf(val);
  if (idx >= 0) { if (arr.length > 1) arr.splice(idx, 1); }
  else arr.push(val);
  el.classList.toggle('selected', arr.includes(val));
  el.querySelector('.ms-check').textContent = arr.includes(val) ? '✓' : '';
  const n = msState.tipoP1.length;
  document.getElementById('msLabel-tipoP1').textContent =
    n === 4 ? 'Todos los tipos' : msState.tipoP1.map(t => TIPOS[t].label).join(', ');
  // Si hay exactamente un tipo seleccionado, sincronizar kpiActivo
  kpiActivo = n === 1 ? msState.tipoP1[0] : null;
  renderPanel(PANEL);
}

// Tipo violencia P2 — multi
function toggleTipoOpt(val, el) {
  const arr = msState.tipo;
  const idx = arr.indexOf(val);
  if (idx >= 0) { if (arr.length > 1) arr.splice(idx, 1); }
  else arr.push(val);
  el.classList.toggle('selected', arr.includes(val));
  el.querySelector('.ms-check').textContent = arr.includes(val) ? '✓' : '';
  p2Tipos = [...msState.tipo];
  const n = msState.tipo.length;
  document.getElementById('msLabel-tipo').textContent =
    n === 4 ? 'Todos los tipos' : msState.tipo.map(t => TIPOS[t].label).join(', ');
  renderPanel(PANEL);
}

function clearFiltersP2() {
  msState.p2 = [ANIO_ACTUAL];
  document.querySelectorAll('#msDrop-p2 .ms-option').forEach(o => {
    const isDefault = o.dataset.val === ANIO_ACTUAL;
    o.classList.toggle('selected', isDefault);
    o.querySelector('.ms-check').textContent = isDefault ? '✓' : '';
  });
  document.getElementById('msLabel-p2').textContent = ANIO_ACTUAL;
  msState.tipo = ['violencia_total','violencia_psicologica','violencia_fisica','violencia_sexual'];
  p2Tipos = [...msState.tipo];
  document.querySelectorAll('#msDrop-tipo .ms-option').forEach(o => {
    o.classList.add('selected');
    o.querySelector('.ms-check').textContent = '✓';
  });
  document.getElementById('msLabel-tipo').textContent = 'Todos los tipos';
  // Reset all P2 card toggles to 'av'
  const p2CardIds = ['p2Edad','p2Res','p2Trab','p2Edu','p2EC','p2Ric','p2Inf','p2Etn'];
  p2CardIds.forEach(id => setToggle(id + 'Toggle', 'av'));
  renderPanel(2);
}

function clearFiltersP3() {
  msState.p3 = [ANIO_ACTUAL];
  document.querySelectorAll('#msDrop-p3 .ms-option').forEach(o => {
    const isDefault = o.dataset.val === ANIO_ACTUAL;
    o.classList.toggle('selected', isDefault);
    o.querySelector('.ms-check').textContent = isDefault ? '✓' : '';
  });
  document.getElementById('msLabel-p3').textContent = ANIO_ACTUAL;
  renderPanel(3);
}

function clearFiltersP4() {
  msState.p4 = [ANIO_ACTUAL];
  document.querySelectorAll('#msDrop-p4 .ms-option').forEach(o => {
    const isDefault = o.dataset.val === ANIO_ACTUAL;
    o.classList.toggle('selected', isDefault);
    o.querySelector('.ms-check').textContent = isDefault ? '✓' : '';
  });
  document.getElementById('msLabel-p4').textContent = ANIO_ACTUAL;
  renderPanel(4);
}
// ════════════════════════════════════════════════════════════════
//  HELPERS DE ESTADO
// ════════════════════════════════════════════════════════════════
function getAnios(panel) { return [...msState[panel]].sort(); }
function isSerie(panel)  { return msState[panel].length > 1; }
function getDepto()      { return msState.dep[0] || 'Todos'; }
function getTiposP1()    { return msState.tipoP1.length > 0 ? msState.tipoP1 : Object.keys(TIPOS); }

function clearFiltersP1() {
  msState.p1 = [ANIO_ACTUAL];
  document.querySelectorAll('#msDrop-p1 .ms-option').forEach(o => {
    const isDefault = o.dataset.val === ANIO_ACTUAL;
    o.classList.toggle('selected', isDefault);
    o.querySelector('.ms-check').textContent = isDefault ? '✓' : '';
  });
  document.getElementById('msLabel-p1').textContent = ANIO_ACTUAL;
  msState.dep = ['Todos'];
  document.querySelectorAll('#msDrop-dep .ms-option').forEach(o => {
    const isDefault = o.dataset.val === 'Todos';
    o.classList.toggle('selected', isDefault);
    o.querySelector('.ms-check').textContent = isDefault ? '✓' : '';
  });
  document.getElementById('msLabel-dep').textContent = 'Todos';
  msState.tipoP1 = ['violencia_total','violencia_psicologica','violencia_fisica','violencia_sexual'];
  document.querySelectorAll('#msDrop-tipoP1 .ms-option').forEach(o => {
    o.classList.add('selected');
    o.querySelector('.ms-check').textContent = '✓';
  });
  document.getElementById('msLabel-tipoP1').textContent = 'Todos los tipos';
  kpiActivo = null;
  // Reset toggles to default 'av'
  ['mapaToggle','g2Toggle','vennToggle'].forEach(id => {
    setToggle(id, 'av');
  });
  renderPanel(1);
}

// ════════════════════════════════════════════════════════════════
//  NAVEGACIÓN
// ════════════════════════════════════════════════════════════════
function showPanel(n) {
  document.querySelectorAll('.tab').forEach((t,i) => t.classList.toggle('active', i===n-1));
  document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
  document.getElementById('panel-' + n).classList.add('active');
  PANEL = n;
  if (n === 5) renderCanales(); else renderPanel(n);
}

function renderPanel(n) {
  if (!DATOS) return;
  switch(n) {
    case 1: renderP1(); break;
    case 2: renderP2(); break;
    case 3: renderP3(); break;
    case 4: renderP4(); break;
  }
}

// ════════════════════════════════════════════════════════════════
//  SISTEMA NARRATIVO — Banners intro, insights de gráficos, CTAs
// ════════════════════════════════════════════════════════════════

// ── Helper: insertar o actualizar un elemento en el DOM ──────────
function setEl(id, html) {
  let el = document.getElementById(id);
  if (el) el.outerHTML = html;
}
function insertBefore(refId, html) {
  const ref = document.getElementById(refId);
  if (!ref) return;
  const existing = document.getElementById(refId + '_before');
  if (existing) existing.remove();
  const div = document.createElement('div');
  div.id = refId + '_before';
  div.innerHTML = html;
  ref.parentNode.insertBefore(div, ref);
}
function insertAfter(refId, html) {
  const ref = document.getElementById(refId);
  if (!ref) return;
  const existingId = refId + '_after';
  const existing = document.getElementById(existingId);
  if (existing) { existing.innerHTML = html; return; }
  const div = document.createElement('div');
  div.id = existingId;
  div.innerHTML = html;
  ref.parentNode.insertBefore(div, ref.nextSibling);
}

// Insertar insight dentro del card padre de un canvas/elemento
function insertInsightInCard(refId, html) {
  const ref = document.getElementById(refId);
  if (!ref) return;
  const slotId = refId + '_insight';
  const existing = document.getElementById(slotId);
  if (existing) { existing.innerHTML = html; return; }
  const div = document.createElement('div');
  div.id = slotId;
  div.innerHTML = html;
  // Buscar el card contenedor más cercano
  const card = ref.closest ? ref.closest('.card') : null;
  if (card) card.appendChild(div);
  else ref.parentNode.insertBefore(div, ref.nextSibling);
}
function insertIntoPanel(panelId, position, id, html) {
  const panel = document.getElementById(panelId);
  if (!panel) return;
  const existing = document.getElementById(id);
  if (existing) { existing.outerHTML = `<div id="${id}">${html}</div>`; return; }
  const div = document.createElement('div');
  div.id = id;
  div.innerHTML = html;
  if (position === 'first') panel.insertBefore(div, panel.firstChild);
  else panel.appendChild(div);
}

// ── Descripción dinámica bajo un gráfico ────────────────────────
function insightBox(icon, html) {
  // Strip HTML tags for TTS, then store as data attribute to avoid escaping issues
  const plainText = html.replace(/<[^>]+>/g, '').replace(/"/g, '&quot;');
  const speakerBtn = `<button class="ci-speak-btn" title="Escuchar descripción"
    data-tts="${plainText}"
    onclick="speakInsight(this)" aria-label="Leer descripción en voz alta">🔊</button>`;
  return `<div class="chart-insight"><span class="ci-icon">${icon}</span><span class="ci-text">${html}</span>${speakerBtn}</div>`;
}

// TTS helper — reads text from data-tts attribute to avoid inline string escaping issues
function speakInsight(btn) {
  if (!window.speechSynthesis) return;
  // If already speaking this btn, stop it
  if (btn.dataset.speaking === 'true') {
    window.speechSynthesis.cancel();
    btn.dataset.speaking = 'false';
    btn.textContent = '🔊';
    return;
  }
  // Cancel any ongoing speech
  window.speechSynthesis.cancel();
  document.querySelectorAll('.ci-speak-btn[data-speaking="true"]').forEach(b => {
    b.dataset.speaking = 'false'; b.textContent = '🔊';
  });
  // Read text from data attribute (safe from escaping issues)
  const raw = btn.dataset.tts || '';
  // Expand abbreviations for natural speech
  const spoken = raw
    .replace(/(\d+(?:[.,]\d+)?)\s*pp\b/gi, '$1 puntos porcentuales')
    .replace(/\bpp\b/gi, 'puntos porcentuales')
    .replace(/▲/g, 'subió ')
    .replace(/▼/g, 'bajó ')
    .replace(/→/g, 'a ')
    .replace(/&quot;/g, '"');
  const utt = new SpeechSynthesisUtterance(spoken);
  utt.lang = 'es-PE';
  utt.rate = 1.605;   // +30% sobre 1.235
  // Prefer female voice
  const voices = window.speechSynthesis.getVoices();
  const femaleVoice = voices.find(v => v.lang.startsWith('es') && /female|mujer|f\b/i.test(v.name))
    || voices.find(v => v.lang.startsWith('es') && !/male|hombre/i.test(v.name) && v.name)
    || voices.find(v => v.lang.startsWith('es'))
    || null;
  if (femaleVoice) utt.voice = femaleVoice;
  btn.dataset.speaking = 'true';
  btn.textContent = '⏹';
  utt.onend = () => { btn.dataset.speaking = 'false'; btn.textContent = '🔊'; };
  utt.onerror = () => { btn.dataset.speaking = 'false'; btn.textContent = '🔊'; };
  window.speechSynthesis.speak(utt);
}

// ── Banner intro de panel ────────────────────────────────────────
function introBanner(icon, text) {
  return `<div class="panel-narrative-intro"><span class="narrative-icon">${icon}</span><span>${text}</span></div>`;
}

// ── Banner CTA cierre de panel ───────────────────────────────────
function ctaBanner(text, btnLabel, panelNum) {
  return `<div class="panel-narrative-cta">
    <div class="cta-text">${text}</div>
    <button class="cta-btn" onclick="showPanel(${panelNum})">${btnLabel} →</button>
  </div>`;
}

// ── Formatear número con un decimal ─────────────────────────────
function fmt(v) { return Number(v).toFixed(1); }

// ════════════════════════════════════════════════════════════════
//  NARRATIVAS PANEL 1
// ════════════════════════════════════════════════════════════════
function renderNarrativesP1() {
  const anios = getAnios('p1'), depto = getDepto();
  const anio  = anios[anios.length - 1];
  const oldest = anios[0];
  const isSer  = isSerie('p1');
  const sheet = depto === 'Todos' ? 'General_Anual' : 'Departamento';
  const av = oneRow('alguna_vez', sheet, anio, depto);
  const dm = oneRow('doce_meses', sheet, anio, depto);
  const ctx = depto === 'Todos' ? `en el Perú (${anio})` : `en ${depto} (${anio})`;
  const ctxCorto = depto === 'Todos' ? 'a nivel nacional' : `en ${depto}`;

  // Intro banner
  insertIntoPanel('panel-1', 'first', 'p1-intro-banner',
    introBanner('📌',
      `Estos datos evidencian que la violencia no es un hecho aislado, sino un <strong>problema estructural</strong> que requiere respuestas integrales y sostenidas.`
    )
  );

  // ── Datos base ──────────────────────────────────────────────
  const totAV = Math.round(pct(av['violencia_total']));
  const totDM = Math.round(pct(dm['violencia_total']));
  const fisAV = Math.round(pct(av['violencia_fisica']));
  const psicAV= Math.round(pct(av['violencia_psicologica']));
  const sexAV = Math.round(pct(av['violencia_sexual']));

  // Tipos sin 'total', ordenados de mayor a menor
  const tiposSinTotal = ['violencia_psicologica','violencia_fisica','violencia_sexual']
    .map(k => ({ k, v: pct(av[k]), l: TIPOS[k].label }))
    .sort((a,b) => b.v - a.v);
  const mayorTipo = tiposSinTotal[0];

  // ── Insight debajo de g2Chart ──
  const temp = getToggle('g2Toggle');
  const fuente = temp === 'av' ? 'alguna_vez' : 'doce_meses';
  const rowG2 = oneRow(fuente, sheet, anio, depto);
  const tiposSinTotalG2 = ['violencia_psicologica','violencia_fisica','violencia_sexual']
    .map(k => ({ k, v: pct(rowG2[k]), l: TIPOS[k].label }))
    .sort((a,b) => b.v - a.v);
  const mayorG2 = tiposSinTotalG2[0];
  const tiempoLabel = temp === 'av' ? 'alguna vez en su vida' : 'en los últimos 12 meses';
  const totG2 = Math.round(pct(rowG2['violencia_total']));

  let insightG2;
  if (isSer) {
    const rowG2Old = oneRow(fuente, sheet, oldest, depto);
    const totOld = Math.round(pct(rowG2Old['violencia_total']));
    const delta = totG2 - totOld;
    const dir = delta > 0 ? `aumentó ${Math.abs(delta).toFixed(1)} pp` : delta < 0 ? `disminuyó ${Math.abs(delta).toFixed(1)} pp` : 'se mantuvo estable';
    insightG2 = `Entre <strong>${oldest}</strong> y <strong>${anio}</strong>, la violencia total ${tiempoLabel} <strong>${dir}</strong> (${totOld}% → ${totG2}%). La violencia <strong>${mayorG2.l}</strong> sigue siendo la más prevalente en ${anio} (${fmt(mayorG2.v)}%).`;
  } else {
    insightG2 = `La violencia <strong>${mayorG2.l}</strong> es la más prevalente ${ctxCorto} (${fmt(mayorG2.v)}%) entre las mujeres que la sufrieron ${tiempoLabel}. En total, <strong>${totG2} de cada 100 mujeres</strong> experimentaron algún tipo de violencia de pareja.`;
  }
  insertInsightInCard('g2Chart', insightBox('💡', insightG2));

  // ── Insight debajo de mapaWrap ──
  let insightMapa;
  if (isSer) {
    const avOld = oneRow('alguna_vez', sheet, oldest, depto);
    const dmOld = oneRow('doce_meses', sheet, oldest, depto);
    const totAVOld = Math.round(pct(avOld['violencia_total']));
    const totDMOld = Math.round(pct(dmOld['violencia_total']));
    const deltaAV = totAV - totAVOld, deltaDM = totDM - totDMOld;
    const dirAV = deltaAV > 0 ? `▲${Math.abs(deltaAV).toFixed(1)}pp` : deltaAV < 0 ? `▼${Math.abs(deltaAV).toFixed(1)}pp` : '—';
    const dirDM = deltaDM > 0 ? `▲${Math.abs(deltaDM).toFixed(1)}pp` : deltaDM < 0 ? `▼${Math.abs(deltaDM).toFixed(1)}pp` : '—';
    insightMapa = `De <strong>${oldest}</strong> a <strong>${anio}</strong>: violencia total alguna vez <strong>${totAVOld}% → ${totAV}% (${dirAV})</strong> y en los últimos 12 meses <strong>${totDMOld}% → ${totDM}% (${dirDM})</strong> ${ctxCorto}.`;
  } else {
    insightMapa = `La violencia <strong>${mayorTipo.l}</strong> es la más frecuente ${ctx} (${fmt(mayorTipo.v)}%). En total, el <strong>${totAV}%</strong> de las mujeres han sufrido algún tipo de violencia de pareja alguna vez en su vida, y el <strong>${totDM}%</strong> la vivió en los últimos 12 meses.`;
  }
  insertInsightInCard('mapaWrap', insightBox('📊', insightMapa));

  // ── Insight Polivictimización ──
  const fpAV  = pct(av['violencia_fis_psic']);
  const spAV  = pct(av['violencia_sex_psic']);
  const fsAV  = pct(av['violencia_fis_sex']);
  const triAV = pct(av['violencia_triple']);
  const combos = [
    { l: 'Física + Psicológica', v: fpAV },
    { l: 'Sexual + Psicológica', v: spAV },
    { l: 'Física + Sexual',      v: fsAV }
  ].sort((a,b) => b.v - a.v);
  const mayorCombo = combos[0];

  let insightVenn;
  if (isSer) {
    const avOld = oneRow('alguna_vez', sheet, oldest, depto);
    const triOld = pct(avOld['violencia_triple']);
    const deltaT = +(triAV - triOld).toFixed(1);
    const dirT = deltaT > 0 ? `▲${Math.abs(deltaT)}pp` : deltaT < 0 ? `▼${Math.abs(deltaT)}pp` : '—';
    insightVenn = `La polivictimización triple pasó de <strong>${fmt(triOld)}%</strong> (${oldest}) a <strong>${fmt(triAV)}%</strong> (${anio}) — <strong>${dirT}</strong>. La combinación más frecuente sigue siendo <strong>${mayorCombo.l}</strong> (${fmt(mayorCombo.v)}% en ${anio}).`;
  } else {
    insightVenn = `La combinación más frecuente de violencias es <strong>${mayorCombo.l}</strong> (${fmt(mayorCombo.v)}%). Además, el <strong>${fmt(triAV)}%</strong> de las mujeres sufrieron los tres tipos de violencia simultáneamente (polivictimización triple) ${ctxCorto}.`;
  }
  insertInsightInCard('vennContainer', insightBox('🔗', insightVenn));

  // CTA cierre P1
  insertIntoPanel('panel-1', 'last', 'p1-cta',
    ctaBanner(
      `Pero esta realidad <em>no afecta a todas las mujeres por igual.</em> Existen diferencias importantes según edad, nivel educativo y lugar de residencia. Esto nos lleva a analizar quiénes están más expuestas a la violencia.`,
      'Ver perfiles · Panel 2', 2
    )
  );
}

// ════════════════════════════════════════════════════════════════
//  NARRATIVAS PANEL 2
// ════════════════════════════════════════════════════════════════
function renderNarrativesP2() {
  const anios = getAnios('p2');
  const anio  = anios[anios.length - 1];

  insertIntoPanel('panel-2', 'first', 'p2-intro-banner',
    introBanner('🔍',
      `La violencia de pareja <strong>no se distribuye de manera uniforme</strong>: existen grupos de mujeres con mayor exposición según sus características sociodemográficas y experiencias de vida.`
    )
  );

  insertIntoPanel('panel-2', 'last', 'p2-cta',
    ctaBanner(
      `Pero estas diferencias <em>no ocurren por casualidad.</em> Existen factores y dinámicas que reproducen y sostienen la violencia en el tiempo. Esto nos lleva a analizar cómo funciona y se perpetúa la violencia en las relaciones de pareja.`,
      'Ver dinámicas · Panel 3', 3
    )
  );
}

// ── Insight dinámico bajo cada gráfico de P2 ────────────────────
function renderP2ChartInsight(cfg, anios, catData) {
  const insightId = cfg.id + 'C_insight';
  const existing = document.getElementById(insightId);
  if (existing) existing.remove();

  const cats = Object.keys(catData);
  if (!cats.length) return;

  const tipo = p2Tipos[0] || 'violencia_total';
  const tipoLabel = TIPOS[tipo]?.label || 'violencia total';
  const sorted = cats.map(c => ({ c, v: catData[c][tipo] || 0 })).sort((a,b) => b.v - a.v);
  const mayor = sorted[0], menor = sorted[sorted.length - 1];
  const anio = anios[anios.length - 1];
  const isSer = anios.length > 1;
  const oldest = anios[0];

  let txt;
  if (isSer) {
    // Compare mayor category between oldest and newest
    const temp = getToggle(cfg.id + 'Toggle');
    const oldData = getP2CatData(cfg, temp, oldest);
    const vOld = (oldData[mayor.c] && oldData[mayor.c][tipo]) ? oldData[mayor.c][tipo] : null;
    const delta = vOld !== null ? +(mayor.v - vOld).toFixed(1) : null;
    const dirStr = delta !== null ? (delta > 0 ? `▲${Math.abs(delta)}pp` : delta < 0 ? `▼${Math.abs(delta)}pp` : 'sin cambio') : '';
    txt = `Entre <strong>${oldest}</strong> y <strong>${anio}</strong>, el grupo <strong>"${mayor.c}"</strong> sigue con la mayor prevalencia de violencia ${tipoLabel.toLowerCase()} (${vOld !== null ? fmt(vOld)+'% → ' : ''}${fmt(mayor.v)}% ${dirStr}). El grupo con menor prevalencia en ${anio} es <strong>"${menor.c}"</strong> (${fmt(menor.v)}%).`;
  } else {
    txt = `En <strong>${anio}</strong>, las mujeres del grupo <strong>"${mayor.c}"</strong> presentan la mayor prevalencia de violencia ${tipoLabel.toLowerCase()} (${fmt(mayor.v)}%), mientras que las del grupo <strong>"${menor.c}"</strong> presentan la menor (${fmt(menor.v)}%).`;
  }

  const canvas = document.getElementById(cfg.id + 'C');
  if (!canvas) return;
  const box = document.createElement('div');
  box.id = insightId;
  box.innerHTML = insightBox('💡', txt);
  canvas.parentNode.parentNode.appendChild(box);
}

// ════════════════════════════════════════════════════════════════
//  NARRATIVAS PANEL 3
// ════════════════════════════════════════════════════════════════
function renderNarrativesP3() {
  const anios = getAnios('p3');
  const anio  = anios[anios.length - 1];
  const oldest = anios[0];
  const isSer = isSerie('p3');

  insertIntoPanel('panel-3', 'first', 'p3-intro-banner',
    introBanner('🔄',
      `La violencia de pareja <strong>no ocurre de forma aislada</strong>: se sostiene a través de conductas de control, desigualdades en la toma de decisiones y normas que la toleran o justifican.`
    )
  );

  const gF = h => (DATOS.factores[h]||[]).find(r=>String(r['Año']).trim()===anio)||{};
  const gFOld = h => (DATOS.factores[h]||[]).find(r=>String(r['Año']).trim()===oldest)||{};

  if (!isSer) {
    // Control de pareja
    const ctrl = gF('Control_Pareja');
    const ctrlItems = CTRL_ITEMS.map(([l, k]) => ({ l, v: pct(ctrl[k]) })).sort((a,b)=>b.v-a.v);
    const ctrlMax = ctrlItems[0];
    insertInsightInCard('p3Ctrl', insightBox('💡',
      `La conducta de control más frecuente en ${anio} es <strong>"${ctrlMax.l}"</strong>, reportada por el ${fmt(ctrlMax.v)}% de las mujeres. Las seis conductas son indicadores de relaciones de poder y dominación que anteceden la violencia física.`
    ));

    const alc = gF('Alcohol');
    const fMucha = pct(alc['Mucha frecuencia']);
    insertInsightInCard('p3Alc', insightBox('💡',
      `En ${anio}, el ${fmt(fMucha)}% de las parejas reportadas tienen episodios frecuentes de embriaguez. El consumo de alcohol <strong>amplifica la frecuencia y severidad</strong> de la violencia aunque no es su causa.`
    ));

    const dec = gF('Toma_Decisiones');
    const decItems = [
      { l:'Gasto propio dinero', v: pct(dec['Gasto del propio dinero']) },
      { l:'Cuidado de su salud', v: pct(dec['Cuidado de su propia salud']) },
      { l:'Grandes compras',     v: pct(dec['Grandes compras del hogar']) },
      { l:'Compras diarias',     v: pct(dec['Compras para necesidades diarias']) },
      { l:'Visitas a familiares',v: pct(dec['Visitas a familiares o amigos']) },
      { l:'Comida del hogar',    v: pct(dec['Qué alimentos cocinar cada día']) }
    ].sort((a,b)=>b.v-a.v);
    const decMax = decItems[0];
    insertInsightInCard('p3Dec', insightBox('💡',
      `La decisión en la que las mujeres tienen mayor participación (${anio}) es <strong>"${decMax.l}"</strong> (${fmt(decMax.v)}%). La autonomía en la toma de decisiones es un factor protector frente a la violencia de pareja.`
    ));

    const just = gF('Justificacion');
    const justItems = [
      { l:'Descuida a los niños', v: pct(just['Si descuida a los niños']) },
      { l:'Sale sin avisar',      v: pct(just['Si sale sin decirle']) },
      { l:'Discute con él',       v: pct(just['Si ella discute con él']) },
      { l:'Niega relaciones',     v: pct(just['Si se niega a tener relaciones sexuales']) },
      { l:'Quema la comida',      v: pct(just['Si ella quema la comida']) }
    ].sort((a,b)=>b.v-a.v);
    const justMax = justItems[0];
    insertInsightInCard('p3Just', insightBox('💡',
      `La situación que más mujeres usan para justificar la violencia es <strong>"${justMax.l}"</strong> (${fmt(justMax.v)}%). Aunque las cifras son bajas, la normalización de la violencia refleja normas culturales que requieren intervención.`
    ));
  } else {
    // Multi-year: compare oldest vs newest
    const ctrlNew = gF('Control_Pareja'), ctrlOld = gFOld('Control_Pareja');
    const [ctrlLabel, ctrlKey] = CTRL_ITEMS[0];
    const vNew = pct(ctrlNew[ctrlKey]), vOld = pct(ctrlOld[ctrlKey]);
    const dCtrl = +(vNew-vOld).toFixed(1);
    insertInsightInCard('p3Ctrl', insightBox('💡',
      `Entre <strong>${oldest}</strong> y <strong>${anio}</strong>, la conducta "${ctrlLabel}" pasó de <strong>${fmt(vOld)}% → ${fmt(vNew)}%</strong> (${dCtrl>0?'▲':'▼'}${Math.abs(dCtrl)}pp). Las conductas de control son precursoras documentadas de la violencia física.`
    ));

    const alcNew = gF('Alcohol'), alcOld = gFOld('Alcohol');
    const fNNew = pct(alcNew['Mucha frecuencia']), fNOld = pct(alcOld['Mucha frecuencia']);
    const dAlc = +(fNNew-fNOld).toFixed(1);
    insertInsightInCard('p3Alc', insightBox('💡',
      `La embriaguez frecuente de la pareja pasó de <strong>${fmt(fNOld)}%</strong> (${oldest}) a <strong>${fmt(fNNew)}%</strong> (${anio}) — ${dAlc>0?'▲':'▼'}${Math.abs(dAlc)}pp. El alcohol amplifica la violencia aunque no es su causa.`
    ));

    const decNew = gF('Toma_Decisiones'), decOld = gFOld('Toma_Decisiones');
    const decKey = 'Gasto del propio dinero';
    const dNNew = pct(decNew[decKey]), dNOld = pct(decOld[decKey]);
    const dDec = +(dNNew-dNOld).toFixed(1);
    insertInsightInCard('p3Dec', insightBox('💡',
      `La participación de la mujer en el gasto de su propio dinero pasó de <strong>${fmt(dNOld)}%</strong> (${oldest}) a <strong>${fmt(dNNew)}%</strong> (${anio}) — ${dDec>0?'▲':'▼'}${Math.abs(dDec)}pp. Mayor autonomía económica se asocia a menor violencia.`
    ));

    const justNew = gF('Justificacion'), justOld = gFOld('Justificacion');
    const justKey = 'Si descuida a los niños';
    const jNNew = pct(justNew[justKey]), jNOld = pct(justOld[justKey]);
    const dJust = +(jNNew-jNOld).toFixed(1);
    insertInsightInCard('p3Just', insightBox('💡',
      `La justificación de la violencia por "descuidar a los niños" pasó de <strong>${fmt(jNOld)}%</strong> (${oldest}) a <strong>${fmt(jNNew)}%</strong> (${anio}) — ${dJust>0?'▲':'▼'}${Math.abs(dJust)}pp. La tendencia refleja cambios culturales lentos pero relevantes.`
    ));
  }

  insertIntoPanel('panel-3', 'last', 'p3-cta',
    ctaBanner(
      `Frente a estas dinámicas, <strong>la intervención del Estado es clave.</strong> Se requieren servicios accesibles y efectivos que protejan a las víctimas y rompan el ciclo de violencia. Esto nos lleva a analizar cómo responde el sistema frente a esta problemática.`,
      'Ver respuesta institucional · Panel 4', 4
    )
  );
}

// ════════════════════════════════════════════════════════════════
//  NARRATIVAS PANEL 4
// ════════════════════════════════════════════════════════════════
function renderNarrativesP4() {
  const anios = getAnios('p4');
  const anio  = anios[anios.length - 1];
  const oldest = anios[0];
  const isSer = isSerie('p4');

  insertIntoPanel('panel-4', 'first', 'p4-intro-banner',
    introBanner('🆘',
      `Aunque muchas mujeres buscan ayuda frente a la violencia, <strong>la respuesta se concentra en pocos canales</strong> y persisten barreras importantes que limitan el acceso a protección.`
    )
  );

  const gF = h => (DATOS.factores[h]||[]).find(r=>String(r['Año']).trim()===anio)||{};
  const gFOld = h => (DATOS.factores[h]||[]).find(r=>String(r['Año']).trim()===oldest)||{};

  if (!isSer) {
    const inf = gF('Ayuda_Informal');
    const madre = pct(inf['Madre']), amiga = pct(inf['Amiga(o) / Vecina(o)']);
    insertInsightInCard('p4Inf', insightBox('💡',
      `En ${anio}, la red de apoyo informal más frecuente son <strong>la madre</strong> (${fmt(madre)}%) y <strong>amigas/vecinas</strong> (${fmt(amiga)}%). Esto indica que la primera respuesta sigue siendo familiar y comunitaria antes que institucional.`
    ));

    const inst = gF('Ayuda_Institucional');
    const comisaria = pct(inst['Comisaría']);
    const cem = pct(inst['Ministerio de la Mujer y Poblaciones Vulnerables']);
    insertInsightInCard('p4Inst', insightBox('💡',
      `La <strong>Comisaría</strong> concentra el ${fmt(comisaria)}% de las búsquedas de ayuda institucional en ${anio}, siendo la puerta de entrada principal al sistema. El MIMP/CEM recibe el ${fmt(cem)}%. Esta concentración evidencia la necesidad de fortalecer otros servicios especializados.`
    ));

    const barr = gF('Barreras');
    const noNec = pct(barr['No era necesario']);
    const verg  = pct(barr['Vergüenza']);
    const noDonde = pct(barr['No sabe donde ir/no conoce servicios']);
    insertInsightInCard('p4Barr', insightBox('💡',
      `La principal barrera para no buscar ayuda en ${anio} es creer que <strong>"No era necesario"</strong> (${fmt(noNec)}%), seguida de la <strong>vergüenza</strong> (${fmt(verg)}%) y el <strong>desconocimiento de servicios</strong> (${fmt(noDonde)}%). Estas barreras señalan la urgencia de estrategias de comunicación y cambio cultural.`
    ));
  } else {
    // Multi-year comparison
    const infNew = gF('Ayuda_Informal'), infOld = gFOld('Ayuda_Informal');
    const madreNew = pct(infNew['Madre']), madreOld = pct(infOld['Madre']);
    const dMadre = +(madreNew-madreOld).toFixed(1);
    insertInsightInCard('p4Inf', insightBox('💡',
      `El apoyo de la <strong>madre</strong> como primera red informal pasó de <strong>${fmt(madreOld)}%</strong> (${oldest}) a <strong>${fmt(madreNew)}%</strong> (${anio}) — ${dMadre>0?'▲':'▼'}${Math.abs(dMadre)}pp. La familia sigue siendo el primer recurso antes que las instituciones.`
    ));

    const instNew = gF('Ayuda_Institucional'), instOld = gFOld('Ayuda_Institucional');
    const comNew = pct(instNew['Comisaría']), comOld = pct(instOld['Comisaría']);
    const dCom = +(comNew-comOld).toFixed(1);
    insertInsightInCard('p4Inst', insightBox('💡',
      `El acceso a la <strong>Comisaría</strong> pasó de <strong>${fmt(comOld)}%</strong> (${oldest}) a <strong>${fmt(comNew)}%</strong> (${anio}) — ${dCom>0?'▲':'▼'}${Math.abs(dCom)}pp. La tendencia indica si el sistema institucional está ganando o perdiendo alcance.`
    ));

    const barrNew = gF('Barreras'), barrOld = gFOld('Barreras');
    const noNecNew = pct(barrNew['No era necesario']), noNecOld = pct(barrOld['No era necesario']);
    const dBarr = +(noNecNew-noNecOld).toFixed(1);
    insertInsightInCard('p4Barr', insightBox('💡',
      `La barrera "No era necesario" pasó de <strong>${fmt(noNecOld)}%</strong> (${oldest}) a <strong>${fmt(noNecNew)}%</strong> (${anio}) — ${dBarr>0?'▲':'▼'}${Math.abs(dBarr)}pp. Cambios en esta percepción reflejan el impacto de políticas de concientización.`
    ));
  }

  insertIntoPanel('panel-4', 'last', 'p4-cta',
    ctaBanner(
      `Pero el acceso a la ayuda <em>tampoco es igual en todo el país.</em> Existen diferencias importantes según el lugar donde viven las mujeres. Esto nos lleva a analizar cómo se distribuye la violencia y la respuesta en el territorio.`,
      'Ver territorio · Panel 5', 5
    )
  );
}

// ════════════════════════════════════════════════════════════════
//  NARRATIVAS PANEL 6
// ════════════════════════════════════════════════════════════════

function renderCanales() {
  insertIntoPanel('panel-5', 'first', 'p6-intro-banner',
    introBanner('📞',
      `Conoce los canales de atención disponibles en el Perú ante hechos de violencia. Cada servicio está diseñado para acompañar a las mujeres en distintas etapas y contextos.`
    )
  );

  // El buscador (filtros, mapa y resultados) es HTML estático del panel; aquí solo
  // se cargan los datos que lo alimentan, una vez por sesión.
  if (DIRECTORIO) {
    p6InicializarDirectorio();
  } else {
    fetch(RUTA_DIRECTORIO)
      .then(r => { if (!r.ok) throw new Error(`estado ${r.status}`); return r.json(); })
      .then(d => { DIRECTORIO = d; p6InicializarDirectorio(); })
      .catch(e => {
        const carga = document.getElementById('p6-dir-loading');
        if (carga) carga.innerHTML =
          `<p style="color:var(--c-red);font-size:13px">No se pudo cargar el directorio (${e.message}).</p>`;
      });
  }

  insertIntoPanel('panel-5', 'last', 'p6-cta',
    `<div class="panel-narrative-cta" style="justify-content:center;text-align:center;background:#FDF5EA;">
      <div style="width:100%">
        <p style="font-size:16px;font-weight:700;color:#7A4A10;margin-bottom:4px">🤝 La atención oportuna salva vidas.</p>
        <p style="font-size:14px;color:#B8721A;">Informar también es prevenir.</p>
      </div>
    </div>`
  );
}

// ── Lógica del directorio ──────────────────────────────────────
// Esquema de data/directorio.json: { meta, tipos, servicios:[{tipo, departamento,
// provincia, distrito, nombre, direccion, telefono, lat, lon}] }
const P6_TIPOS = {
  CEM: { label:'Centro Emergencia Mujer (CEM)',        icon:'🏛️', color:'#2563EB' },
  SAR: { label:'Servicio de Atención Rural (SAR)',     icon:'🌿', color:'#16A34A' },
  SAU: { label:'Servicio de Atención Urgente (SAU)',   icon:'🚨', color:'#DC2626' },
  HRT: { label:'Hogar de Refugio Temporal (HRT)',      icon:'🏠', color:'#D97706' },
  CAI: { label:'Centro de Atención Institucional (CAI)', icon:'🏢', color:'#7B6BBF' }
};

function p6Servicios() { return (DIRECTORIO && DIRECTORIO.servicios) || []; }

// Estado del buscador. Se guarda por **ubigeo**, no por nombre: es la llave con la
// que el directorio del MIMP y la geometría de Perú-maps se cruzan sin ambigüedad
// (hay distritos homónimos en departamentos distintos).
const p6Sel = { dep: '', prov: '', dist: '', ubicacion: null };

let UBIGEOS = null;               // jerarquía dep → prov → dist (solo nombres)
const GEO_DEP = new Map();        // ubigeo de departamento → {provincias, distritos}
const geoDepPendiente = new Map();

function cargarUbigeos() {
  if (UBIGEOS) return Promise.resolve(UBIGEOS);
  return fetch(RUTA_UBIGEOS)
    .then(r => { if (!r.ok) throw new Error(`estado ${r.status}`); return r.json(); })
    .then(j => { UBIGEOS = j; return j; });
}

// Provincias y distritos se descargan por departamento, no de una vez: los 1 892
// distritos del país pesan varios megabytes y casi nadie mira más de uno.
function cargarGeoDep(uDep) {
  if (!uDep) return Promise.resolve(null);
  if (GEO_DEP.has(uDep)) return Promise.resolve(GEO_DEP.get(uDep));
  if (geoDepPendiente.has(uDep)) return geoDepPendiente.get(uDep);
  const p = fetch(`${RUTA_GEO_DEP}${uDep}.json`)
    .then(r => { if (!r.ok) throw new Error(`estado ${r.status}`); return r.json(); })
    .then(g => { GEO_DEP.set(uDep, g); geoDepPendiente.delete(uDep); return g; })
    .catch(e => { geoDepPendiente.delete(uDep); throw e; });
  geoDepPendiente.set(uDep, p);
  return p;
}

// ── Conteo de servicios por unidad ───────────────────────────────
function p6Conteos() {
  const dep = {}, prov = {}, dist = {};
  p6Servicios().forEach(s => {
    dep[s.ubigeo_dep] = (dep[s.ubigeo_dep] || 0) + 1;
    prov[s.ubigeo_prov] = (prov[s.ubigeo_prov] || 0) + 1;
    dist[s.ubigeo] = (dist[s.ubigeo] || 0) + 1;
  });
  return { dep, prov, dist };
}

function p6Opciones(select, entradas, placeholder) {
  select.innerHTML = `<option value="">${placeholder}</option>`;
  entradas.forEach(([valor, nombre, n]) => {
    const o = document.createElement('option');
    o.value = valor;
    // El conteo importa: un distrito con cero sedes es información, no un error.
    o.textContent = n === undefined ? nombre : `${nombre} (${n})`;
    if (n === 0) o.className = 'sin-servicios';
    select.appendChild(o);
  });
}

function p6OrdenarPorNombre(entradas) {
  return entradas.sort((a, b) => a[1].localeCompare(b[1], 'es'));
}

// ── Poblado de los desplegables ──────────────────────────────────
function p6LlenarDepartamentos() {
  const c = p6Conteos();
  const entradas = p6OrdenarPorNombre(
    Object.entries(UBIGEOS).map(([u, d]) => [u, d.n, c.dep[u] || 0]));
  p6Opciones(document.getElementById('p6SelDep'), entradas, '— Selecciona —');
  document.getElementById('p6SelDep').value = p6Sel.dep;
}

function p6LlenarProvincias() {
  const sel = document.getElementById('p6SelProv');
  const departamento = UBIGEOS[p6Sel.dep];
  if (!departamento) {
    p6Opciones(sel, [], '— Primero el departamento —');
    sel.disabled = true;
    return;
  }
  const c = p6Conteos();
  const entradas = p6OrdenarPorNombre(
    Object.entries(departamento.p).map(([u, p]) => [u, p.n, c.prov[u] || 0]));
  p6Opciones(sel, entradas, '— Todas las provincias —');
  sel.disabled = false;
  sel.value = p6Sel.prov;
}

function p6LlenarDistritos() {
  const sel = document.getElementById('p6SelDist');
  const provincia = UBIGEOS[p6Sel.dep] && UBIGEOS[p6Sel.dep].p[p6Sel.prov];
  if (!provincia) {
    p6Opciones(sel, [], '— Primero la provincia —');
    sel.disabled = true;
    return;
  }
  const c = p6Conteos();
  const entradas = p6OrdenarPorNombre(
    Object.entries(provincia.d).map(([u, n]) => [u, n, c.dist[u] || 0]));
  p6Opciones(sel, entradas, '— Todos los distritos —');
  sel.disabled = false;
  sel.value = p6Sel.dist;
}

// ── Reacciones a cada desplegable ────────────────────────────────
function p6CambiaDepartamento() {
  p6Sel.dep = document.getElementById('p6SelDep').value;
  p6Sel.prov = ''; p6Sel.dist = ''; p6Sel.ubicacion = null;
  p6LlenarProvincias(); p6LlenarDistritos();
  cargarGeoDep(p6Sel.dep).then(p6Actualizar).catch(p6Actualizar);
  p6Actualizar();
}

function p6CambiaProvincia() {
  p6Sel.prov = document.getElementById('p6SelProv').value;
  p6Sel.dist = ''; p6Sel.ubicacion = null;
  p6LlenarDistritos();
  p6Actualizar();
}

function p6CambiaDistrito() {
  p6Sel.dist = document.getElementById('p6SelDist').value;
  p6Sel.ubicacion = null;
  p6Actualizar();
}

function p6Limpiar() {
  p6Sel.dep = ''; p6Sel.prov = ''; p6Sel.dist = ''; p6Sel.ubicacion = null;
  window._p6TipoActivo = null;
  p6Estado('');
  p6LlenarDepartamentos(); p6LlenarProvincias(); p6LlenarDistritos();
  p6Actualizar();
}

function p6InicializarDirectorio() {
  document.getElementById('p6-dir-loading').style.display = 'none';
  document.getElementById('p6-dir-content').style.display = 'block';

  const total = (DIRECTORIO.meta && DIRECTORIO.meta.total) || p6Servicios().length;
  const nota = document.getElementById('p6-dir-total');
  if (nota) nota.textContent = `${total} servicios de atención frente a la violencia`;

  cargarUbigeos().then(() => {
    p6LlenarDepartamentos();
    p6Actualizar();
  }).catch(e => {
    p6Estado(`No se pudo cargar la división administrativa (${e.message}).`, 'error');
    p6Actualizar();
  });
}

// ── Punto en polígono (para la autoubicación) ────────────────────
// Algoritmo de cruce de rayos. Recorre los anillos de cada polígono: el primero es
// el contorno y los siguientes son huecos, así que un punto dentro de un hueco
// cambia de paridad dos veces y queda fuera, como debe ser.
function anilloContiene(anillo, lon, lat) {
  let dentro = false;
  for (let i = 0, j = anillo.length - 1; i < anillo.length; j = i++) {
    const [xi, yi] = anillo[i], [xj, yj] = anillo[j];
    if ((yi > lat) !== (yj > lat) &&
        lon < (xj - xi) * (lat - yi) / (yj - yi) + xi) dentro = !dentro;
  }
  return dentro;
}

function poligonoContiene(anillos, lon, lat) {
  if (!anilloContiene(anillos[0], lon, lat)) return false;      // fuera del contorno
  for (let i = 1; i < anillos.length; i++) {                     // dentro de un hueco
    if (anilloContiene(anillos[i], lon, lat)) return false;
  }
  return true;
}

function geometriaContiene(geometria, lon, lat) {
  const poligonos = geometria.type === 'Polygon' ? [geometria.coordinates]
                                                 : geometria.coordinates;
  return poligonos.some(anillos => poligonoContiene(anillos, lon, lat));
}

function buscarFeature(features, lon, lat) {
  return features.find(f => geometriaContiene(f.geometry, lon, lat)) || null;
}

// ── Autoubicación ────────────────────────────────────────────────
function p6Estado(mensaje, clase) {
  const el = document.getElementById('p6-ubicar-estado');
  if (!el) return;
  el.textContent = mensaje || '';
  el.className = 'p6-ubicar-estado' + (clase ? ' ' + clase : '');
}

function p6Ubicar() {
  const boton = document.getElementById('p6BtnUbicar');
  if (!navigator.geolocation) {
    p6Estado('Tu navegador no permite compartir la ubicación. Elige tu distrito en las listas.', 'error');
    return;
  }
  if (boton) { boton.disabled = true; boton.classList.add('cargando'); }
  p6Estado('Buscando tu ubicación…');

  navigator.geolocation.getCurrentPosition(
    pos => {
      const lon = pos.coords.longitude, lat = pos.coords.latitude;
      p6Localizar(lon, lat).finally(() => {
        if (boton) { boton.disabled = false; boton.classList.remove('cargando'); }
      });
    },
    err => {
      if (boton) { boton.disabled = false; boton.classList.remove('cargando'); }
      const motivos = {
        1: 'No diste permiso de ubicación. Puedes elegir tu distrito en las listas.',
        2: 'No se pudo determinar tu ubicación. Elige tu distrito en las listas.',
        3: 'La ubicación tardó demasiado. Elige tu distrito en las listas.'
      };
      p6Estado(motivos[err.code] || 'No se pudo obtener tu ubicación.', 'error');
    },
    // Sin caché: quien pulsa el botón espera que lo sitúe donde está ahora.
    { enableHighAccuracy: true, timeout: 12000, maximumAge: 0 }
  );
}

// Localiza en dos pasos —primero el departamento, luego el distrito dentro de él—
// para no descargar los 1 892 polígonos del país solo para situar un punto.
function p6Localizar(lon, lat) {
  return cargarGeo()
    .then(geo => {
      const departamento = buscarFeature(geo.features, lon, lat);
      if (!departamento) {
        p6Estado('Tu ubicación parece estar fuera del Perú. Elige tu distrito en las listas.', 'error');
        return null;
      }
      p6Sel.dep = departamento.properties.u;
      p6Sel.prov = ''; p6Sel.dist = '';
      p6Sel.ubicacion = { lon, lat };
      return cargarGeoDep(p6Sel.dep);
    })
    .then(paquete => {
      if (!paquete) return;
      const distrito = buscarFeature(paquete.distritos, lon, lat);
      if (distrito) {
        p6Sel.dist = distrito.properties.u;
        p6Sel.prov = distrito.properties.p;
      }
      p6LlenarDepartamentos(); p6LlenarProvincias(); p6LlenarDistritos();
      p6Actualizar();

      const nombre = p6NombreSeleccion();
      const cerca = p6MasCercanos(lon, lat, 1)[0];
      p6Estado(
        `Estás en ${nombre}.` +
        (cerca ? ` El servicio más cercano está a ${p6FormatoDistancia(cerca.d)}.` : ''),
        'ok');
    })
    .catch(e => p6Estado(`No se pudo situar tu ubicación (${e.message}).`, 'error'));
}

function p6NombreSeleccion() {
  if (!UBIGEOS || !p6Sel.dep) return 'el Perú';
  const d = UBIGEOS[p6Sel.dep];
  if (!d) return 'el Perú';
  const pr = d.p[p6Sel.prov];
  const di = pr && pr.d[p6Sel.dist];
  return [di, pr && pr.n, d.n].filter(Boolean).join(' · ');
}

// Distancia en línea recta (haversine). Sirve para ordenar, no para indicar ruta.
function p6Distancia(lon1, lat1, lon2, lat2) {
  const R = 6371, rad = Math.PI / 180;
  const dLat = (lat2 - lat1) * rad, dLon = (lon2 - lon1) * rad;
  const a = Math.sin(dLat / 2) ** 2 +
            Math.cos(lat1 * rad) * Math.cos(lat2 * rad) * Math.sin(dLon / 2) ** 2;
  return 2 * R * Math.asin(Math.sqrt(a));
}

function p6FormatoDistancia(km) {
  if (km < 0.05) return 'unos pasos';            // la precisión del GPS no da para más
  if (km < 1) return `${Math.round(km * 1000)} m`;
  return `${km.toFixed(km < 10 ? 1 : 0)} km`;
}

// Centro aproximado de la unidad elegida. Sirve para ordenar por cercanía cuando la
// persona eligió su distrito a mano en vez de compartir su ubicación.
function p6CentroSeleccion() {
  if (p6Sel.ubicacion) return p6Sel.ubicacion;
  const paquete = GEO_DEP.get(p6Sel.dep);
  if (!paquete) return null;
  const unidad = p6Sel.dist
    ? paquete.distritos.find(f => f.properties.u === p6Sel.dist)
    : p6Sel.prov ? paquete.provincias.find(f => f.properties.u === p6Sel.prov) : null;
  if (!unidad) return null;
  const puntos = anillosDe(unidad.geometry).reduce((a, r) => a.concat(r), []);
  return {
    lon: puntos.reduce((s, p) => s + p[0], 0) / puntos.length,
    lat: puntos.reduce((s, p) => s + p[1], 0) / puntos.length,
  };
}

function p6MasCercanos(lon, lat, n) {
  return p6Servicios()
    .filter(s => s.lat != null && s.lon != null)
    .map(s => ({ s, d: p6Distancia(lon, lat, s.lon, s.lat) }))
    .sort((a, b) => a.d - b.d)
    .slice(0, n);
}

// ── Selección vigente y repintado ────────────────────────────────
function p6Visibles() {
  const tipo = window._p6TipoActivo || null;
  return p6Servicios().filter(s =>
    (!p6Sel.dep || s.ubigeo_dep === p6Sel.dep) &&
    (!p6Sel.prov || s.ubigeo_prov === p6Sel.prov) &&
    (!p6Sel.dist || s.ubigeo === p6Sel.dist) &&
    (!tipo || s.tipo === tipo));
}

function p6Actualizar() {
  p6RenderMapa();
  p6MostrarResultados();
}

function p6RenderMapa() {
  renderMapaServicios('p6MapaWrap', p6Visibles(), p6Sel);
}

function p6MostrarResultados() {
  const container = document.getElementById('p6-dir-results');
  if (!container) return;

  const tipoActivo = window._p6TipoActivo || null;
  let encontrados = p6Visibles();
  const ubic = p6Sel.ubicacion;
  if (ubic) {
    encontrados = encontrados
      .map(s => ({ s, d: (s.lat != null && s.lon != null)
                        ? p6Distancia(ubic.lon, ubic.lat, s.lon, s.lat) : Infinity }))
      .sort((a, b) => a.d - b.d)
      .map(x => Object.assign({}, x.s, { _d: x.d }));
  }

  const filtroLabel = tipoActivo
    ? `<div class="p6-chip">🔍 ${(P6_TIPOS[tipoActivo] || {}).label || tipoActivo}
        <button onclick="window._p6TipoActivo=null;p6Actualizar()" title="Quitar filtro">✕</button>
      </div>` : '';

  if (!p6Sel.dep) {
    container.innerHTML = filtroLabel + `<p class="p6-vacio">
      Elige tu departamento o pulsa <strong>Usar mi ubicación</strong> para ver los servicios de tu zona.
    </p>`;
    return;
  }

  if (!encontrados.length) {
    // Que no haya sede en tu distrito es lo normal fuera de las capitales: lo útil
    // no es decir "sin resultados", sino indicar a dónde ir.
    const centro = p6CentroSeleccion();
    const cercanos = centro
      ? p6MasCercanos(centro.lon, centro.lat, 3).filter(c => !tipoActivo || c.s.tipo === tipoActivo)
      : [];
    container.innerHTML = filtroLabel + `<p class="p6-vacio">
      No hay servicios registrados en <strong>${p6NombreSeleccion()}</strong>.
      ${cercanos.length ? 'Estos son los más cercanos:' : 'Prueba con otra provincia o quita el filtro por tipo.'}<br>
      La <strong>Línea 100</strong> atiende gratis en todo el país, las 24 horas.
    </p>` + (cercanos.length ? p6ListaServicios(
      cercanos.map(c => Object.assign({}, c.s, { _d: c.d }))) : '');
    return;
  }

  container.innerHTML = filtroLabel + `<div class="p6-resumen">
    ${encontrados.length} servicio${encontrados.length !== 1 ? 's' : ''} en ${p6NombreSeleccion()}
    ${ubic ? ' · ordenados por cercanía' : ''}
  </div>` + p6ListaServicios(encontrados);
}

function p6ListaServicios(servicios) {
  let html = '';
  Object.entries(P6_TIPOS).forEach(([tipo, cfg]) => {
    const grupo = servicios.filter(s => s.tipo === tipo);
    if (!grupo.length) return;
    html += `<div class="p6-grupo">
      <div class="p6-grupo-titulo" style="color:${cfg.color}">
        ${cfg.icon} ${cfg.label} (${grupo.length})</div>
      <div class="p6-fichas">`;
    grupo.forEach(s => {
      const mapa = (s.lat != null && s.lon != null)
        ? `<a href="https://www.google.com/maps/search/?api=1&query=${s.lat},${s.lon}"
             target="_blank" rel="noopener" class="p6-ficha-mapa">🗺️ Ver en el mapa</a>` : '';
      const tel = s.telefono
        ? `<a href="tel:${s.telefono}" class="p6-ficha-tel">📞 ${s.telefono}</a>` : '';
      const dist = Number.isFinite(s._d)
        ? `<span class="p6-ficha-dist">a ${p6FormatoDistancia(s._d)}</span>` : '';
      html += `<div class="p6-ficha">
        <div class="p6-ficha-nombre">${s.nombre} ${dist}</div>
        ${s.direccion ? `<div class="p6-ficha-dir">📍 ${s.direccion}</div>` : ''}
        <div class="p6-ficha-ubic">${[s.distrito, s.provincia].filter(Boolean).join(' · ')}</div>
        <div class="p6-ficha-acciones">${tel}${mapa}</div>
      </div>`;
    });
    html += '</div></div>';
  });
  return html;
}

// ── helpers ──────────────────────────────────────────────────────

// Click-to-call helper for Línea 100
// El campo de número es decorativo — el botón siempre abre tel:100 en el dispositivo del usuario
function p6UpdateCtcLink() {
  // Always call 100 — opens the phone dialer ready to call
  return true; // allow href="tel:100" default navigation
}

// Scroll to directory widget and pre-filter by service type
// Stores the active tipo so p6MostrarResultados can filter results
window._p6TipoActivo = null;

function p6ScrollToDirectorio(tipo) {
  window._p6TipoActivo = tipo || null;

  const slot = document.getElementById('p6-mapa-card');
  if (slot) {
    slot.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }

  // Update the widget title to show which service was selected
  const titleEl = document.querySelector('#p6-mapa-card [style*="font-size:14px"]');
  if (titleEl && tipo && P6_TIPOS[tipo]) {
    titleEl.textContent = `${P6_TIPOS[tipo].icon} Buscar ${P6_TIPOS[tipo].label} — Encuentra el más cercano`;
  }

  // Si ya hay un departamento elegido, vuelve a pintar con el nuevo filtro
  p6Actualizar();
}

function pct(v) {
  if (typeof v === 'number') return v;
  if (typeof v === 'string') return parseFloat(v.replace('%','').replace(',','.')) || 0;
  return 0;
}
function rowsByAnio(fuente, hoja, anio) {
  return (DATOS[fuente][hoja] || []).filter(r => String(r['Año']).trim() === String(anio));
}
function oneRow(fuente, hoja, anio, depto) {
  const rows = rowsByAnio(fuente, hoja, anio);
  if (!depto || depto === 'Todos') return rows[0] || {};
  return rows.find(r => String(r['V024']||'').trim() === depto) || rows[0] || {};
}
function dk(id) { if (charts[id]) { charts[id].destroy(); delete charts[id]; } }
function ctxEl(id) { return document.getElementById(id); }

// Procedencia de los datos (pie de página)
function mostrarPie(meta) {
  const el = document.getElementById('tsDisplay');
  if (!el || !meta) return;
  const anios = meta.anios || [];
  const rango = anios.length ? `${anios[0]}-${anios[anios.length-1]}` : '';
  const fecha = meta.generado ? new Date(meta.generado).toLocaleDateString('es-PE') : '';
  el.textContent = `ENDES ${rango} · datos generados el ${fecha}`;
  el.title = meta.nota || '';
}

// ════════════════════════════════════════════════════════════════
//  PANEL 1 · Magnitud
// ════════════════════════════════════════════════════════════════
function renderP1() {
  renderKpis();
  renderP1Charts();
  renderMapa();
  renderCoropletaP1();
  renderVennPanel();
  renderNarrativesP1();
}

// ── KPIs ─────────────────────────────────────────────────────────
function renderKpis() {
  const anios = getAnios('p1'), depto = getDepto();
  const anio  = anios[anios.length - 1];
  const serie = isSerie('p1');
  const sheet = depto === 'Todos' ? 'General_Anual' : 'Departamento';
  const av = oneRow('alguna_vez', sheet, anio, depto);
  const dm = oneRow('doce_meses', sheet, anio, depto);
  const tiposActivos = getTiposP1();

  const orden = ['violencia_total','violencia_psicologica','violencia_fisica','violencia_sexual'];
  document.getElementById('kpiRow').innerHTML = orden.map(campo => {
    const avV = Math.round(pct(av[campo]));
    const dmV = Math.round(pct(dm[campo]));
    const c   = TIPOS[campo].color;
    const isActive = tiposActivos.includes(campo);
    const hint = serie
      ? `<div class="kpi-hint">Mostrando valores del año ${anio}</div>`
      : '';
    return `<div class="kpi-card"
      style="--kpi-color:${c};opacity:${isActive?1:.3};pointer-events:${isActive?'auto':'none'}" onclick="clickKpi('${campo}')">
      <div class="kpi-tipo">${TIPOS[campo].label}</div>
      <div class="kpi-main">
        <strong>${avV}</strong> de cada 100 mujeres la sufrieron alguna vez en su vida
      </div>
      <div class="kpi-sec">
        <strong>${dmV}</strong> de cada 100 mujeres la sufrieron en los últimos 12 meses
      </div>
      ${hint}
    </div>`;
  }).join('');
}

function clickKpi(campo) {
  // Toggle en tipoP1: si ya es el único, deseleccionar (volver a todos)
  if (msState.tipoP1.length === 1 && msState.tipoP1[0] === campo) {
    msState.tipoP1 = ['violencia_fisica','violencia_sexual','violencia_psicologica','violencia_total'];
    document.querySelectorAll('#msDrop-tipoP1 .ms-option').forEach(o => { o.classList.add('selected'); o.querySelector('.ms-check').textContent = '✓'; });
    document.getElementById('msLabel-tipoP1').textContent = 'Todos los tipos';
    kpiActivo = null;
  } else {
    msState.tipoP1 = [campo];
    document.querySelectorAll('#msDrop-tipoP1 .ms-option').forEach(o => {
      const sel = o.dataset.val === campo;
      o.classList.toggle('selected', sel);
      o.querySelector('.ms-check').textContent = sel ? '✓' : '';
    });
    document.getElementById('msLabel-tipoP1').textContent = TIPOS[campo].label;
    kpiActivo = campo;
  }
  renderP1();
}

// ── G2 Prevalencia ───────────────────────────────────────────────
function renderP1Charts() {
  const anios  = getAnios('p1'), serie = isSerie('p1');
  const temp   = getToggle('g2Toggle');
  const depto  = getDepto();
  const fuente = temp === 'av' ? 'alguna_vez' : 'doce_meses';
  const sheet  = depto === 'Todos' ? 'General_Anual' : 'Departamento';
  const camposBase = getTiposP1();
  const colores = camposBase.map(c => TIPOS[c].color);

  dk('g2Chart');
  const el = ctxEl('g2Chart');
  if (!el) return;

  if (serie) {
    document.getElementById('g2Subtitle').textContent = 'Evolución ' + anios.join(' – ');
    charts['g2Chart'] = new Chart(el.getContext('2d'), {
      type: 'line',
      data: {
        labels: anios,
        datasets: camposBase.map((campo, i) => ({
          label: TIPOS[campo].label,
          data: anios.map(a => pct(oneRow(fuente, sheet, a, depto)[campo])),
          borderColor: colores[i], backgroundColor: 'transparent',
          tension: 0.3, pointRadius: 5, pointBackgroundColor: colores[i], borderWidth: 2.5
        }))
      },
      options: lineOpts()
    });
  } else {
    const anio = anios[0];
    const row  = oneRow(fuente, sheet, anio, depto);
    document.getElementById('g2Subtitle').textContent = 'Porcentaje de mujeres afectadas — ' + anio;
    const data = camposBase.map(c => ({
      label: TIPOS[c].label, val: pct(row[c]), color: TIPOS[c].color
    })).sort((a,b) => b.val - a.val);

    charts['g2Chart'] = new Chart(el.getContext('2d'), {
      type: 'bar',
      data: {
        labels: data.map(d => d.label),
        datasets: [{ data: data.map(d => d.val),
          backgroundColor: data.map(d => d.color), borderRadius: 5 }]
      },
      options: hBarOpts(100, false, true)
    });
  }
}

// ── Mapa departamental ────────────────────────────────────────────
// Coropleta de prevalencia: magnitud de una sola serie, escala secuencial.
function renderCoropletaP1() {
  const anios  = getAnios('p1');
  const anio   = anios[anios.length - 1];
  const fuente = getToggle('coropletaToggle') === 'dm' ? 'doce_meses' : 'alguna_vez';
  const tipos  = getTiposP1();
  const campo  = tipos.length === 1 ? tipos[0] : 'violencia_total';

  const valores = {};
  rowsByAnio(fuente, 'Departamento', anio).forEach(r => {
    valores[String(r['V024']).trim()] = pct(r[campo]);
  });

  const etiqueta = TIPOS[campo].label;
  const ventana  = fuente === 'alguna_vez' ? 'alguna vez' : 'en los últimos 12 meses';
  setEl('coropletaSubtitulo', `Violencia ${etiqueta.toLowerCase()} ${ventana} — ${anio}`);
  renderCoropleta('coropletaWrap', valores, `violencia ${etiqueta.toLowerCase()}`);
}

function renderMapa() {
  if (!DATOS) return;
  const anios  = getAnios('p1'), serie = isSerie('p1');
  const temp   = getToggle('mapaToggle');
  const fuente = temp === 'av' ? 'alguna_vez' : 'doce_meses';
  const tiposActivos = getTiposP1();

  const camposInfo = tiposActivos.map(k => ({ key:k, label:TIPOS[k].label, color:TIPOS[k].color }));
  const anio = anios[anios.length - 1];
  const wrap = document.getElementById('mapaWrap');

  // MULTI-AÑO → tabla comparativa HTML
  if (serie) {
    const deptos = (DATOS[fuente]['Departamento'] || [])
      .filter(r => String(r['Año']).trim() === anio)
      .sort((a,b) => pct(b['violencia_total']) - pct(a['violencia_total']))
      .map(r => r['V024']).filter(Boolean);

    const campo = tiposActivos.length === 1 ? tiposActivos[0] : 'violencia_total';
    const labelCampo = TIPOS[campo].label;
    const colorCampo = TIPOS[campo].color;

    // Calcular variación entre el año más antiguo y el más reciente
    const oldest = anios[0], newest = anios[anios.length - 1];

    const headerCols = anios.map(a =>
      `<th style="text-align:right;padding:7px 10px;font-size:11px;color:var(--c-muted);font-weight:700;letter-spacing:.3px">${a}</th>`
    ).join('') + `<th style="text-align:right;padding:7px 10px;font-size:11px;color:var(--c-muted);font-weight:700;white-space:nowrap">Δ ${oldest}→${newest}</th>`;

    const bodyRows = deptos.map((dep, idx) => {
      const vals = anios.map(a => {
        const r = (DATOS[fuente]['Departamento']||[])
          .find(x => String(x['Año']).trim() === a && x['V024'] === dep) || {};
        return pct(r[campo]);
      });
      const v0 = vals[0], vN = vals[vals.length - 1];
      const delta = +(vN - v0).toFixed(1);
      const deltaColor = delta > 0 ? '#DC2626' : delta < 0 ? '#16A34A' : '#8B8FA8';
      const deltaStr = delta > 0 ? `▲${delta}` : delta < 0 ? `▼${Math.abs(delta)}` : '—';
      const bg = idx % 2 === 0 ? '#fff' : '#F7F8FC';
      const valCells = vals.map((v,i) => {
        const isMax = v === Math.max(...vals);
        return `<td style="text-align:right;padding:6px 10px;font-size:12px;font-weight:${isMax?'700':'400'};color:${isMax?colorCampo:'var(--c-text)'}">${v.toFixed(1)}%</td>`;
      }).join('');
      return `<tr style="background:${bg}">
        <td style="padding:6px 10px;font-size:12px;font-weight:500;color:var(--c-text)">${dep}</td>
        ${valCells}
        <td style="text-align:right;padding:6px 10px;font-size:11px;font-weight:700;color:${deltaColor}">${deltaStr}pp</td>
      </tr>`;
    }).join('');

    wrap.innerHTML = `
      <div style="padding:0 0 8px;font-size:11px;color:var(--c-muted)">
        Comparando <strong style="color:${colorCampo}">${labelCampo}</strong> entre ${anios.join(' y ')} — ordenado por ${newest}
      </div>
      <div style="overflow-x:auto">
        <table style="width:100%;border-collapse:collapse;font-family:var(--font)">
          <thead style="background:#F0F2F8;border-bottom:2px solid var(--c-border)">
            <tr>
              <th style="text-align:left;padding:7px 10px;font-size:11px;color:var(--c-muted);font-weight:700;letter-spacing:.3px">Departamento</th>
              ${headerCols}
            </tr>
          </thead>
          <tbody>${bodyRows}</tbody>
        </table>
      </div>`;
    return;
  }

  // UN AÑO → barras horizontales ordenadas por total
  const rows = (DATOS[fuente]['Departamento'] || [])
    .filter(r => String(r['Año']).trim() === anio)
    .sort((a,b) => pct(b['violencia_total']) - pct(a['violencia_total']));

  const maxVal = Math.max(...rows.map(r => pct(r['violencia_total'])), 1);
  wrap.innerHTML = '<div class="dept-list">' + rows.map(r => {
    const depName = r['V024'];
    if (!depName) return '';
    return `<div class="dept-row">
      <div class="dept-name">${depName}</div>
      <div class="dept-bars">
        ${camposInfo.map(c => {
          const val = pct(r[c.key]);
          const w   = Math.round((val / maxVal) * 100);
          return `<div class="dept-bar-row">
            <div class="dept-bar-label">${c.label}</div>
            <div class="dept-bar-track">
              <div class="dept-bar-fill" style="width:${w}%;background:${c.color}"></div>
            </div>
            <div class="dept-bar-val" style="color:${c.color}">${val.toFixed(1)}%</div>
          </div>`;
        }).join('')}
      </div>
    </div>`;
  }).join('') + '</div>';
}

// ── Venn / Polivictimización ──────────────────────────────────────
function renderVennPanel() {
  const anios  = getAnios('p1');
  const temp   = getToggle('vennToggle');
  const fuente = temp === 'av' ? 'alguna_vez' : 'doce_meses';
  const depto  = getDepto();
  const sheet  = depto === 'Todos' ? 'General_Anual' : 'Departamento';
  const container = document.getElementById('vennContainer');

  const combos = [
    { key:'violencia_fis_psic',    label:'Física + Psicológica',   color:'#7C3AED' },
    { key:'violencia_sex_psic',    label:'Sexual + Psicológica',   color:'#2563EB' },
    { key:'violencia_fis_sex',     label:'Física + Sexual',        color:'#EA580C' },
    { key:'violencia_triple',      label:'Los tres tipos (triple)', color:C.total  }
  ];

  if (anios.length === 1) {
    const row = oneRow(fuente, sheet, anios[0], depto);
    container.innerHTML = `
      <div style="text-align:center;margin-bottom:8px">
        <span class="venn-year-title">${anios[0]}</span>
      </div>
      <div class="venn-wrap">
        <svg viewBox="0 0 220 200" width="280" id="vennSvg0"></svg>
        <table class="venn-table" style="width:100%">
          <thead><tr><th>Combinación</th><th style="text-align:right">%</th></tr></thead>
          <tbody id="vennTbody0"></tbody>
        </table>
      </div>`;
    renderOneVennSvg('vennSvg0', row);
    renderOneVennTabla('vennTbody0', combos, row, null, null, null);
    return;
  }

  const oldest = anios[0];
  const newest = anios[anios.length - 1];
  const rowA = oneRow(fuente, sheet, oldest, depto);
  const rowB = oneRow(fuente, sheet, newest, depto);

  container.innerHTML = `
    <div class="venn-panels">
      <div class="venn-single">
        <div style="text-align:center;margin-bottom:8px">
          <span class="venn-year-title">${oldest}</span>
        </div>
        <div class="venn-wrap">
          <svg viewBox="0 0 220 200" width="240" id="vennSvgA"></svg>
          <table class="venn-table" style="width:100%">
            <thead><tr><th>Combinación</th><th style="text-align:right">%</th></tr></thead>
            <tbody id="vennTbodyA"></tbody>
          </table>
        </div>
      </div>
      <div class="venn-single">
        <div style="text-align:center;margin-bottom:8px">
          <span class="venn-year-title">${newest}</span>
        </div>
        <div class="venn-wrap">
          <svg viewBox="0 0 220 200" width="240" id="vennSvgB"></svg>
          <table class="venn-table" style="width:100%">
            <thead><tr><th>Combinación</th><th style="text-align:right">%</th><th style="text-align:right">Δ vs ${oldest}</th></tr></thead>
            <tbody id="vennTbodyB"></tbody>
          </table>
        </div>
      </div>
    </div>`;

  renderOneVennSvg('vennSvgA', rowA);
  renderOneVennSvg('vennSvgB', rowB);
  renderOneVennTabla('vennTbodyA', combos, rowA, null, null, null);
  renderOneVennTabla('vennTbodyB', combos, rowB, rowA, oldest, newest);
}

function renderOneVennSvg(svgId, row) {
  const fp  = pct(row['violencia_fis_psic']);
  const sp  = pct(row['violencia_sex_psic']);
  const fs  = pct(row['violencia_fis_sex']);
  const tri = pct(row['violencia_triple']);

  // Posiciones de los textos de intersección en el SVG
  const svg = `
    <circle cx="83" cy="72" r="57" fill="${C.fisica}" fill-opacity=".28" stroke="${C.fisica}" stroke-width="1.5"/>
    <circle cx="137" cy="72" r="57" fill="${C.psic}" fill-opacity=".28" stroke="${C.psic}" stroke-width="1.5"/>
    <circle cx="110" cy="126" r="57" fill="${C.sexual}" fill-opacity=".28" stroke="${C.sexual}" stroke-width="1.5"/>

    <!-- Labels externos -->
    <text x="55"  y="42" fill="${C.fisica}" font-size="10" text-anchor="middle" font-weight="700">Física</text>
    <text x="165" y="42" fill="${C.psic}"   font-size="10" text-anchor="middle" font-weight="700">Psic.</text>
    <text x="110" y="196" fill="${C.sexual}" font-size="10" text-anchor="middle" font-weight="700">Sexual</text>

    <!-- Intersección Física+Psic (centro superior) -->
    <text x="110" y="62" fill="#1A1D2E" font-size="9" text-anchor="middle" font-weight="700">${fp.toFixed(1)}%</text>
    <text x="110" y="72" fill="#8B8FA8" font-size="8" text-anchor="middle">F+P</text>

    <!-- Intersección Sexual+Psic (derecha) -->
    <text x="143" y="118" fill="#1A1D2E" font-size="9" text-anchor="middle" font-weight="700">${sp.toFixed(1)}%</text>
    <text x="143" y="128" fill="#8B8FA8" font-size="8" text-anchor="middle">S+P</text>

    <!-- Intersección Física+Sexual (izquierda) -->
    <text x="77"  y="118" fill="#1A1D2E" font-size="9" text-anchor="middle" font-weight="700">${fs.toFixed(1)}%</text>
    <text x="77"  y="128" fill="#8B8FA8" font-size="8" text-anchor="middle">F+S</text>

    <!-- Triple (centro) -->
    <text x="110" y="101" fill="#1A1D2E" font-size="11" text-anchor="middle" font-weight="800">${tri.toFixed(1)}%</text>
    <text x="110" y="113" fill="#8B8FA8" font-size="8"  text-anchor="middle">Triple</text>
  `;
  document.getElementById(svgId).innerHTML = svg;
}

function renderOneVennTabla(tbodyId, combos, row, rowPrev, yearPrev, yearCur) {
  document.getElementById(tbodyId).innerHTML = combos.map(c => {
    const v = pct(row[c.key]);
    const vp = rowPrev ? pct(rowPrev[c.key]) : null;
    const diff = vp !== null ? +(v - vp).toFixed(1) : null;
    return `<tr>
      <td><span class="venn-dot" style="background:${c.color}"></span>${c.label}</td>
      <td class="venn-num" style="color:${c.color}">${v.toFixed(1)}%</td>
      ${diff !== null ? `<td class="venn-num" style="font-size:11px;color:${diff>0?C.red:C.green}">
        ${diff > 0 ? '▲' : '▼'}${Math.abs(diff).toFixed(1)}pp</td>` : ''}
    </tr>`;
  }).join('');
}

// ════════════════════════════════════════════════════════════════
//  PANEL 2 · Perfiles
// ════════════════════════════════════════════════════════════════
function renderP2() {
  const anios = getAnios('p2'), serie = isSerie('p2');
  const container = document.getElementById('p2Container');

  /*
    Alturas:
    - Gráficos pequeños (vbar der): 168px (+20% de 140)
    - Gráficos grandes (hbar izq): deben igualar 168*2 + gap = 168+168+16 = 352px → usamos 352px
    Fila 3: Infancia hbar grande + Etnia hbar derecha → misma altura: 384px (+20% de 320)
  */
  const H_SMALL = 168;   // vbar pequeños +20%
  const H_BIG   = H_SMALL * 2 + 16;  // = 352px — exactamente igual a 2 small + 1 gap
  const H_INF   = 384;   // infancia +20% de 320
  const H_ETN   = 384;   // etnia = misma altura que infancia

  const layout = [
    {
      left:  { id:'p2Edad', title:'Grupo de edad',              hoja:'Edad',               key:'V013',  tipo:'hbar', hPx:H_BIG },
      right: [
        { id:'p2Res',  title:'Área de residencia',   hoja:'Lugar de Residencia', key:'V025', tipo:'vbar', hPx:H_SMALL },
        { id:'p2Trab', title:'Condición laboral',     special:'trab',             tipo:'vbar', hPx:H_SMALL }
      ]
    },
    {
      left:  { id:'p2Edu',  title:'Nivel educativo',            hoja:'Logro Académico',    key:'V149',  tipo:'hbar', hPx:H_BIG },
      right: [
        { id:'p2EC',   title:'Estado civil',          special:'ec',               tipo:'vbar', hPx:H_SMALL },
        { id:'p2Ric',  title:'Índice de riqueza',      hoja:'Indice de Riqueza',   key:'V190', tipo:'vbar', hPx:H_SMALL }
      ]
    },
    {
      left:  { id:'p2Inf',  title:'Exposición a violencia en la infancia', special:'inf', tipo:'hbar', hPx:H_INF },
      right: [
        { id:'p2Etn',  title:'Autoidentificación étnica', special:'etnia', tipo:'hbar', hPx:H_ETN }
      ]
    }
  ];

  container.innerHTML = '';

  layout.forEach(row => {
    const rowEl = document.createElement('div');
    rowEl.className = 'p2-row';
    rowEl.style.alignItems = 'stretch';

    // Columna izquierda
    const leftCard = buildCard(row.left);
    rowEl.appendChild(leftCard);

    // Columna derecha: sub-columna con flex:1 en cada tarjeta hija
    const rightCol = document.createElement('div');
    rightCol.className = 'p2-sub-col';
    rightCol.style.height = '100%';
    row.right.forEach(cfg => {
      const card = buildCard(cfg);
      card.style.flex = '1';  // divide el espacio equitativamente
      rightCol.appendChild(card);
    });
    rowEl.appendChild(rightCol);

    container.appendChild(rowEl);
  });

  // Render todos los charts
  const allCfgs = layout.flatMap(r => [r.left, ...r.right]);
  window._p2Layout = allCfgs; // store for single-chart re-renders
  allCfgs.forEach(cfg => renderP2Chart(cfg, anios, serie));
  renderNarrativesP2();
}

function buildCard(cfg) {
  const toggleId = cfg.id + 'Toggle';
  // Init state for new cards that haven't been seen yet
  if (!toggleState[toggleId]) toggleState[toggleId] = 'av';
  const curVal = toggleState[toggleId];

  const card = document.createElement('div');
  card.className = 'card';
  card.style.cssText = 'display:flex;flex-direction:column;';
  card.innerHTML = `
    <div class="card-header" style="flex-shrink:0">
      <div><div class="card-title">${cfg.title}</div></div>
      <div class="card-actions">
        <div class="temp-toggle" id="${toggleId}">
          <button class="temp-btn ${curVal==='av'?'active':''}" data-val="av"
            onclick="setToggle('${toggleId}','av'); renderSingleP2Chart('${cfg.id}')">Alguna vez</button>
          <button class="temp-btn ${curVal==='dm'?'active':''}" data-val="dm"
            onclick="setToggle('${toggleId}','dm'); renderSingleP2Chart('${cfg.id}')">Últimos 12m</button>
        </div>
      </div>
    </div>
    <div class="chart-wrap" style="flex:1;min-height:${cfg.hPx}px"><canvas id="${cfg.id}C"></canvas></div>`;
  return card;
}

// Renders only one P2 chart when its toggle is clicked (avoids full panel rebuild)
function renderSingleP2Chart(cfgId) {
  if (!window._p2Layout) { renderP2(); return; }
  const anios = getAnios('p2'), serie = isSerie('p2');
  const cfg = window._p2Layout.find(c => c.id === cfgId);
  if (!cfg) { renderP2(); return; }
  renderP2Chart(cfg, anios, serie);
  // Insight is now emitted inside renderP2Chart / renderP2SerieSmart
}

// Extract catData helper used by both renderP2Chart and renderSingleP2Chart
function getP2CatData(cfg, fuente_key, anio) {
  const fuente = fuente_key === 'av' ? 'alguna_vez' : (fuente_key === 'dm' ? 'doce_meses' : fuente_key);
  let catData = {};
  if (cfg.special === 'trab')   catData = getTrabajoData(fuente, anio);
  else if (cfg.special === 'ec')    catData = getECData(fuente, anio);
  else if (cfg.special === 'etnia') catData = getEtniaData(fuente, anio);
  else if (cfg.special === 'inf')   catData = getInfanciaData(anio);
  else {
    const rows = rowsByAnio(fuente, cfg.hoja, anio).filter(r => r[cfg.key] && String(r[cfg.key]) !== 'No respondio');
    rows.forEach(r => {
      const cat = String(r[cfg.key]).trim();
      catData[cat] = {};
      p2Tipos.forEach(t => { catData[cat][t] = pct(r[t] || r['violencia_total']); });
    });
  }
  return catData;
}

function renderP2Chart(cfg, anios, serie) {
  const temp   = getToggle(cfg.id + 'Toggle');
  const fuente = temp === 'av' ? 'alguna_vez' : 'doce_meses';

  if (serie) {
    renderP2SerieSmart(cfg, anios, fuente);
    return;
  }

  const anio = anios[0];
  let catData = {};
  if (cfg.special === 'trab')   catData = getTrabajoData(fuente, anio);
  else if (cfg.special === 'ec')    catData = getECData(fuente, anio);
  else if (cfg.special === 'etnia') catData = getEtniaData(fuente, anio);
  else if (cfg.special === 'inf')   catData = getInfanciaData(anio);
  else {
    const rows = rowsByAnio(fuente, cfg.hoja, anio)
      .filter(r => r[cfg.key] && String(r[cfg.key]) !== 'No respondio');
    rows.forEach(r => {
      const cat = String(r[cfg.key]).trim();
      catData[cat] = {};
      p2Tipos.forEach(t => { catData[cat][t] = pct(r[t] || r['violencia_total']); });
    });
  }

  const cats = Object.keys(catData).sort((a,b) => {
    const ta = catData[a]['violencia_total'] || catData[a][p2Tipos[0]] || 0;
    const tb = catData[b]['violencia_total'] || catData[b][p2Tipos[0]] || 0;
    return tb - ta;
  });
  const short = cats.map(c => c.length > 24 ? c.slice(0,22)+'…' : c);

  dk(cfg.id + 'C');
  const el = ctxEl(cfg.id + 'C');
  if (!el) return;

  const datasets = p2Tipos.map(t => ({
    label: TIPOS[t].label,
    data:  cats.map(c => catData[c][t] || 0),
    backgroundColor: TIPOS[t].color,
    borderRadius: 4
  }));

  charts[cfg.id + 'C'] = new Chart(el.getContext('2d'), {
    type: 'bar',
    data: { labels: short, datasets },
    options: cfg.tipo === 'vbar' ? vBarOptsLegend(100) : hBarOpts(100, true, true)
  });

  // Insight dinámico bajo el gráfico — siempre, incluso en modo serie viene de renderP2Chart
  if (Object.keys(catData).length) {
    renderP2ChartInsight(cfg, anios, catData);
  }
}

// Serie P2: para cada categoría, mostrar evolución temporal
function renderP2SerieSmart(cfg, anios, fuente) {
  dk(cfg.id + 'C');
  const el = ctxEl(cfg.id + 'C');
  if (!el) return;

  // Obtener categorías del último año
  const lastAnio = anios[anios.length - 1];
  let catData = {};
  if (cfg.special === 'trab')  catData = getTrabajoData(fuente, lastAnio);
  else if (cfg.special === 'ec') catData = getECData(fuente, lastAnio);
  else if (cfg.special === 'etnia') catData = getEtniaData(fuente, lastAnio);
  else if (cfg.special === 'inf')   catData = getInfanciaData(lastAnio);
  else {
    const rows = rowsByAnio(fuente, cfg.hoja, lastAnio)
      .filter(r => r[cfg.key] && String(r[cfg.key]) !== 'No respondio');
    rows.forEach(r => {
      const cat = String(r[cfg.key]).trim();
      catData[cat] = {};
      p2Tipos.forEach(t => { catData[cat][t] = pct(r[t] || r['violencia_total']); });
    });
  }

  const cats = Object.keys(catData).slice(0, 6); // máx 6 categorías
  const tipo = p2Tipos[0] || 'violencia_total';
  const colorPalette = [C.azul[0], C.azul[2], C.azul[4], C.azul[6], C.verde[1], C.naranja[2]];

  // Por cada categoría, serie temporal
  const datasets = cats.map((cat, i) => ({
    label: cat.length > 18 ? cat.slice(0,16) + '…' : cat,
    data: anios.map(a => {
      let d = {};
      if (cfg.special === 'trab')  d = getTrabajoData(fuente, a);
      else if (cfg.special === 'ec') d = getECData(fuente, a);
      else if (cfg.special === 'etnia') d = getEtniaData(fuente, a);
      else if (cfg.special === 'inf')   d = getInfanciaData(a);
      else {
        const rows = rowsByAnio(fuente, cfg.hoja, a).filter(r => r[cfg.key]);
        rows.forEach(r => { const c = String(r[cfg.key]).trim(); d[c] = {}; p2Tipos.forEach(t => { d[c][t] = pct(r[t]||r['violencia_total']); }); });
      }
      return d[cat] ? (d[cat][tipo] || 0) : 0;
    }),
    borderColor: colorPalette[i % colorPalette.length],
    backgroundColor: 'transparent',
    tension: 0.3, pointRadius: 4, borderWidth: 2.5
  }));

  charts[cfg.id + 'C'] = new Chart(el.getContext('2d'), {
    type: 'line',
    data: { labels: anios, datasets },
    options: lineOpts()
  });

  // Insight dinámico — también en modo serie, comparando oldest vs newest
  if (Object.keys(catData).length) {
    // Build catData for oldest year too (needed by renderP2ChartInsight comparison)
    renderP2ChartInsight(cfg, anios, catData);
  }
}

// ── Helpers de datos Panel 2 ─────────────────────────────────────
// Los grupos agregados (situación de pareja, condición laboral, grupo étnico) llegan
// como una hoja más: el pipeline los calcula sobre el microdato con el ponderador de
// la encuesta, que es la única forma de que el agregado corresponda a una población.
function porCategoria(fuente, hoja, clave, anio) {
  const res = {};
  rowsByAnio(fuente, hoja, anio).forEach(r => {
    const cat = String(r[clave] || '').trim();
    if (!cat) return;
    res[cat] = {};
    p2Tipos.forEach(t => { res[cat][t] = pct(r[t] ?? r['violencia_total']); });
  });
  return res;
}

function getTrabajoData(fuente, anio) {
  return porCategoria(fuente, 'Condición laboral', 'trabajo_12m', anio);
}

function getECData(fuente, anio) {
  return porCategoria(fuente, 'Situación de pareja', 'pareja_actual', anio);
}

function getEtniaData(fuente, anio) {
  return porCategoria(fuente, 'Grupo étnico', 'etnia', anio);
}

function getInfanciaData(anio) {
  const res = {};
  // Promediar entre fuentes
  ['alguna_vez','doce_meses'].forEach(fuente => {
    const madre = rowsByAnio(fuente, 'Violencia por Madre', anio)
      .filter(r => r['D115B'] === 'Sí' || r['D115B'] === 'No');
    madre.forEach(r => {
      const cat = 'Maltrato directo por parte de la madre — ' + r['D115B'];
      if (!res[cat]) { res[cat] = {}; p2Tipos.forEach(t => { res[cat][t] = pct(r[t]||r['violencia_total']); }); }
    });
    const padre = rowsByAnio(fuente, 'Violencia por Padre', anio)
      .filter(r => r['D115C'] === 'Sí' || r['D115C'] === 'No');
    padre.forEach(r => {
      const cat = 'Maltrato directo por parte del padre — ' + r['D115C'];
      if (!res[cat]) { res[cat] = {}; p2Tipos.forEach(t => { res[cat][t] = pct(r[t]||r['violencia_total']); }); }
    });
    const inter = rowsByAnio(fuente, 'Violencia Interparental', anio)
      .filter(r => r['D121'] === 'Sí' || r['D121'] === 'No');
    inter.forEach(r => {
      const cat = 'Violencia entre padres presenciada — ' + r['D121'];
      if (!res[cat]) { res[cat] = {}; p2Tipos.forEach(t => { res[cat][t] = pct(r[t]||r['violencia_total']); }); }
    });
  });
  return res;
}

// ════════════════════════════════════════════════════════════════
//  PANEL 3 · Dinámicas
// ════════════════════════════════════════════════════════════════
function renderP3() {
  const anios = getAnios('p3'), serie = isSerie('p3');

  function gF(h) {
    if (serie) return anios.map(a => ({ anio:a, row:(DATOS.factores[h]||[]).find(r=>String(r['Año']).trim()===a)||{} }));
    return (DATOS.factores[h]||[]).find(r=>String(r['Año']).trim()===anios[0])||{};
  }

  const ctrlKeys = CTRL_ITEMS;
  dk('p3Ctrl');
  if (serie) {
    const rows = gF('Control_Pareja');
    charts['p3Ctrl'] = new Chart(ctxEl('p3Ctrl').getContext('2d'), {
      type:'line',
      data:{ labels:anios, datasets: ctrlKeys.map((c,i)=>({
        label:c[0], data:rows.map(r=>pct(r.row[c[1]])),
        borderColor:C.azul[i*2], backgroundColor:'transparent', tension:.3, pointRadius:4, borderWidth:2.5
      }))},
      options:lineOpts()
    });
  } else {
    const row = gF('Control_Pareja');
    const items = ctrlKeys.map(c=>({l:c[0], v:pct(row[c[1]])})).sort((a,b)=>b.v-a.v);
    charts['p3Ctrl'] = new Chart(ctxEl('p3Ctrl').getContext('2d'), monoHBar(items.map(i=>i.l), items.map(i=>i.v), C.azul, 40));
  }

  const alcKeys = [['Nunca se embriaga','Nunca'],['Algunas veces','Algunas veces'],['Con mucha frecuencia','Mucha frecuencia']];
  dk('p3Alc');
  if (serie) {
    const rows = gF('Alcohol');
    charts['p3Alc'] = new Chart(ctxEl('p3Alc').getContext('2d'), {
      type:'line',
      data:{ labels:anios, datasets: alcKeys.map((c,i)=>({
        label:c[0], data:rows.map(r=>pct(r.row[c[1]])),
        borderColor:C.naranja[i*2], backgroundColor:'transparent', tension:.3, pointRadius:4, borderWidth:2.5
      }))},
      options:lineOpts()
    });
  } else {
    const row = gF('Alcohol');
    // La frecuencia de embriaguez es ordinal: se muestra en su orden natural
    // (nunca → algunas veces → mucha frecuencia) y el color recorre la rampa en
    // ese mismo orden. Ordenar por valor rompería la escala que representa.
    const items = alcKeys.map(c => ({ l: c[0], v: pct(row[c[1]]) }));
    const cfgAlc = monoVBar(items.map(i => i.l), items.map(i => i.v), C.naranja, 80);
    cfgAlc.data.datasets[0].backgroundColor = rampaOrdinal(items.length, C.naranja).reverse();
    charts['p3Alc'] = new Chart(ctxEl('p3Alc').getContext('2d'), cfgAlc);
  }

  const decKeys = [
    ['Gasto del dinero propio','Gasto del propio dinero'],
    ['Cuidado de su salud','Cuidado de su propia salud'],
    ['Grandes compras del hogar','Grandes compras del hogar'],
    ['Compras necesidades diarias','Compras para necesidades diarias'],
    ['Visitas a familiares','Visitas a familiares o amigos'],
    ['Comida del hogar','Qué alimentos cocinar cada día']
  ];
  dk('p3Dec');
  if (serie) {
    const rows = gF('Toma_Decisiones');
    charts['p3Dec'] = new Chart(ctxEl('p3Dec').getContext('2d'), {
      type:'line',
      data:{ labels:anios, datasets: decKeys.map((c,i)=>({
        label:c[0], data:rows.map(r=>pct(r.row[c[1]])),
        borderColor:C.verde[i], backgroundColor:'transparent', tension:.3, pointRadius:4, borderWidth:2.5
      }))},
      options:lineOpts()
    });
  } else {
    const row = gF('Toma_Decisiones');
    const items = decKeys.map(c=>({l:c[0],v:pct(row[c[1]])})).sort((a,b)=>b.v-a.v);
    charts['p3Dec'] = new Chart(ctxEl('p3Dec').getContext('2d'), monoHBar(items.map(i=>i.l), items.map(i=>i.v), C.verde, 105));
  }

  const justKeys = [
    ['Descuida a los niños','Si descuida a los niños'],
    ['Sale sin avisar','Si sale sin decirle'],
    ['Discute con él','Si ella discute con él'],
    ['Niega relaciones','Si se niega a tener relaciones sexuales'],
    ['Quema la comida','Si ella quema la comida']
  ];
  dk('p3Just');
  if (serie) {
    const rows = gF('Justificacion');
    charts['p3Just'] = new Chart(ctxEl('p3Just').getContext('2d'), {
      type:'line',
      data:{ labels:anios, datasets: justKeys.map((c,i)=>({
        label:c[0], data:rows.map(r=>pct(r.row[c[1]])),
        borderColor:C.morado[i*2], backgroundColor:'transparent', tension:.3, pointRadius:4, borderWidth:2.5
      }))},
      options:lineOpts()
    });
  } else {
    const row = gF('Justificacion');
    const items = justKeys.map(c=>({l:c[0],v:pct(row[c[1]])})).sort((a,b)=>b.v-a.v);
    charts['p3Just'] = new Chart(ctxEl('p3Just').getContext('2d'), monoVBar(items.map(i=>i.l), items.map(i=>i.v), C.morado, 2.5));
  }
  renderNarrativesP3();
}

// ════════════════════════════════════════════════════════════════
//  PANEL 4 · Respuesta
// ════════════════════════════════════════════════════════════════
function renderP4() {
  const anios = getAnios('p4'), serie = isSerie('p4');

  function gF(h) {
    if (serie) return anios.map(a=>({anio:a, row:(DATOS.factores[h]||[]).find(r=>String(r['Año']).trim()===a)||{}}));
    return (DATOS.factores[h]||[]).find(r=>String(r['Año']).trim()===anios[0])||{};
  }

  // ── Informal ──
  const infKeys = [
    ['Madre','Madre'],['Amiga / Vecina','Amiga(o) / Vecina(o)'],
    ['Hermana','Hermana'],['Padre','Padre'],['Hermano','Hermano'],
    ['Pariente esposo','Otro pariente del esposo'],['Pariente mujer','Otro pariente de la mujer'],
    ['Suegros','Suegros'],['Otra persona','Otra persona'],
    ['Esposo actual','Actual/último esposo o compañero']
  ];
  dk('p4Inf');
  if (serie) {
    // Barras verticales agrupadas por año
    const rows = gF('Ayuda_Informal');
    const labels = infKeys.slice(0,8).map(c=>c[0]);
    const barColors = ['#1E3A8A','#2563EB','#60A5FA','#BFDBFE'];
    charts['p4Inf'] = new Chart(ctxEl('p4Inf').getContext('2d'), {
      type:'bar',
      data:{
        labels,
        datasets: rows.map((r,i) => ({
          label: r.anio,
          data: infKeys.slice(0,8).map(c => pct(r.row[c[1]])),
          backgroundColor: barColors[i % barColors.length],
          borderRadius: 4
        }))
      },
      options: {
        responsive:true, maintainAspectRatio:false,
        plugins:{
          legend:{display:true, position:'top', labels:{boxWidth:12, font:{size:11}}},
          datalabels:{anchor:'end', align:'top', color:C.text, font:{size:9,weight:'600'}, formatter:v=>v.toFixed(1)+'%'}
        },
        scales:{
          x:{grid:{display:false}, ticks:{font:{size:10}}},
          y:{grid:{color:'rgba(0,0,0,.05)'}, ticks:{callback:v=>v+'%', font:{size:10}}}
        }
      }
    });
  } else {
    const row = gF('Ayuda_Informal');
    const items = infKeys.map(c=>({l:c[0],v:pct(row[c[1]])})).sort((a,b)=>b.v-a.v);
    charts['p4Inf'] = new Chart(ctxEl('p4Inf').getContext('2d'), monoHBar(items.map(i=>i.l), items.map(i=>i.v), C.azul, 50));
  }

  // ── Institucional ──
  const instKeys = [
    ['Comisaría',        'Comisaría'],
    ['MIMP / CEM',       'Ministerio de la Mujer y Poblaciones Vulnerables'],
    ['DEMUNA',           'Defensoría Municipal (DEMUNA)'],
    ['Fiscalía',         'Fiscalía'],
    ['Estab. de salud',  'Establecimiento de salud'],
    ['Juzgado',          'Juzgado'],
    ['Def. del Pueblo',  'Defensoría del Pueblo'],
    ['Otra institución', 'Otra institución']
  ];
  dk('p4Inst');
  if (serie) {
    // Barras verticales agrupadas por año
    const rows = gF('Ayuda_Institucional');
    const labels = instKeys.map(c=>c[0]);
    const barColors = ['#14532D','#16A34A','#4ADE80','#BBF7D0'];
    charts['p4Inst'] = new Chart(ctxEl('p4Inst').getContext('2d'), {
      type:'bar',
      data:{
        labels,
        datasets: rows.map((r,i) => ({
          label: r.anio,
          data: instKeys.map(c => pct(r.row[c[1]])),
          backgroundColor: barColors[i % barColors.length],
          borderRadius: 4
        }))
      },
      options: {
        responsive:true, maintainAspectRatio:false,
        plugins:{
          legend:{display:true, position:'top', labels:{boxWidth:12, font:{size:11}}},
          datalabels:{anchor:'end', align:'top', color:C.text, font:{size:9,weight:'600'}, formatter:v=>v.toFixed(1)+'%'}
        },
        scales:{
          x:{grid:{display:false}, ticks:{font:{size:10}}},
          y:{grid:{color:'rgba(0,0,0,.05)'}, ticks:{callback:v=>v+'%', font:{size:10}}}
        }
      }
    });
  } else {
    const row = gF('Ayuda_Institucional');
    const items = instKeys.map(c=>({l:c[0],v:pct(row[c[1]])})).sort((a,b)=>b.v-a.v);
    charts['p4Inst'] = new Chart(ctxEl('p4Inst').getContext('2d'), monoHBar(items.map(i=>i.l), items.map(i=>i.v), C.verde, 90));
  }

  // ── Barreras ──
  const barrKeys = [
    ['No era necesario',              'No era necesario'],
    ['Vergüenza',                     'Vergüenza'],
    ['No sabe dónde ir',              'No sabe donde ir/no conoce servicios'],
    ['Miedo a más violencia',         'Miedo a que le pegara de neuvo a ella o a sus hijas e hijos'],
    ['Miedo al agresor',              'Miedo de causarle un problema a la persona que le pego'],
    ['Miedo al divorcio',             'Miedo al divorcio/separación'],
    ['No sirve de nada',              'No sirve de nada'],
    ['Ella tenía la culpa',           'Ella tenía la culpa'],
    ['Es parte de la vida',           'Es parte de la vida'],
    ['Presión familiar',              'Presión familiar'],
    ['Miedo a quedarse sin sustento', 'Miedo a que no le de dinero para el sustento de su familia'],
    ['Otro',                          'Otro']
  ];
  dk('p4Barr');
  if (serie) {
    charts['p4Barr'] = new Chart(ctxEl('p4Barr').getContext('2d'), {
      type:'line',
      data:{ labels:anios, datasets: barrKeys.slice(0,6).map((c,i)=>({
        label:c[0], data:gF('Barreras').map(r=>pct(r.row[c[1]])),
        borderColor:C.naranja[i], backgroundColor:'transparent', tension:.3, pointRadius:4, borderWidth:2.5
      }))},
      options:lineOpts()
    });
  } else {
    const row = gF('Barreras');
    const items = barrKeys.map(c=>({l:c[0],v:pct(row[c[1]])})).sort((a,b)=>b.v-a.v);
    charts['p4Barr'] = new Chart(ctxEl('p4Barr').getContext('2d'), monoVBar(items.map(i=>i.l), items.map(i=>i.v), C.naranja, 50));
  }
  renderNarrativesP4();
}

// ════════════════════════════════════════════════════════════════
//  MAPAS · SVG puro, sin librería de mapas ni servidor de teselas
//  Geometría: Perú-maps (github.com/Rodasluis/Peru-maps), simplificada
//  para web y recortada a una sola propiedad, `dep`, igual a V024.
// ════════════════════════════════════════════════════════════════

let GEO = null;                 // FeatureCollection departamental
let geoPendiente = null;        // promesa en curso, para no pedirla dos veces

function cargarGeo() {
  if (GEO) return Promise.resolve(GEO);
  if (geoPendiente) return geoPendiente;
  geoPendiente = fetch(RUTA_GEOMETRIA)
    .then(r => { if (!r.ok) throw new Error(`estado ${r.status}`); return r.json(); })
    .then(g => { GEO = g; return g; });
  return geoPendiente;
}

// Rampa secuencial para magnitud: un solo tono, claro → oscuro.
// Validada con scripts/validate_palette.js --ordinal (L monótona, ΔL ≥ 0.06,
// extremo claro ≥ 2:1 sobre blanco, tono único).
const RAMPA_SECUENCIAL = ['#FB923C', '#EA580C', '#C2410C', '#9A3412', '#7C2D12'];
const SIN_DATO = '#E8EAF0';

// Alto del lienzo del mapa de servicios, en píxeles. Debe coincidir con la altura
// de .p6-mapa-lienzo en styles.css.
const ALTO_MAPA = 380;

// Proyección equirrectangular ajustada al contenedor. A la escala del Perú la
// distorsión es irrelevante y evita arrastrar una librería de proyecciones.
function proyeccion(features, ancho, alto, margen) {
  let minLon = 180, maxLon = -180, minLat = 90, maxLat = -90;
  const recorrer = c => {
    if (typeof c[0] === 'number') {
      if (c[0] < minLon) minLon = c[0];
      if (c[0] > maxLon) maxLon = c[0];
      if (c[1] < minLat) minLat = c[1];
      if (c[1] > maxLat) maxLat = c[1];
    } else c.forEach(recorrer);
  };
  features.forEach(f => recorrer(f.geometry.coordinates));

  const escala = Math.min((ancho - margen * 2) / (maxLon - minLon),
                          (alto - margen * 2) / (maxLat - minLat));
  const dx = margen + ((ancho - margen * 2) - (maxLon - minLon) * escala) / 2;
  const dy = margen + ((alto - margen * 2) - (maxLat - minLat) * escala) / 2;
  return ([lon, lat]) => [dx + (lon - minLon) * escala, dy + (maxLat - lat) * escala];
}

function anillosDe(geometria) {
  return geometria.type === 'Polygon' ? geometria.coordinates
                                      : geometria.coordinates.flat();
}

function trazo(geometria, proyectar) {
  return anillosDe(geometria).map(anillo =>
    anillo.map((punto, i) => {
      const [x, y] = proyectar(punto);
      return (i === 0 ? 'M' : 'L') + x.toFixed(1) + ',' + y.toFixed(1);
    }).join(' ') + ' Z'
  ).join(' ');
}

function centroide(geometria, proyectar) {
  const puntos = anillosDe(geometria).reduce((a, r) => a.concat(r), []);
  const lon = puntos.reduce((s, p) => s + p[0], 0) / puntos.length;
  const lat = puntos.reduce((s, p) => s + p[1], 0) / puntos.length;
  return proyectar([lon, lat]);
}

// Corta el rango en cinco clases de igual amplitud y devuelve el color de cada valor.
function escalaSecuencial(valores) {
  const finitos = valores.filter(v => Number.isFinite(v) && v > 0);
  if (!finitos.length) return { color: () => SIN_DATO, cortes: [] };
  const min = Math.min(...finitos), max = Math.max(...finitos);
  const paso = (max - min) / RAMPA_SECUENCIAL.length || 1;
  const cortes = RAMPA_SECUENCIAL.map((_, i) => min + paso * i);
  return {
    min, max, cortes,
    color: v => {
      if (!Number.isFinite(v) || v <= 0) return SIN_DATO;
      const i = Math.min(RAMPA_SECUENCIAL.length - 1, Math.floor((v - min) / paso));
      return RAMPA_SECUENCIAL[i];
    }
  };
}

function leyendaSecuencial(escala, sufijo) {
  if (!escala.cortes.length) return '';
  const cajas = RAMPA_SECUENCIAL.map((c, i) => {
    const desde = escala.cortes[i];
    const hasta = i === RAMPA_SECUENCIAL.length - 1 ? escala.max : escala.cortes[i + 1];
    return `<div class="mapa-leyenda-item">
      <span class="mapa-leyenda-caja" style="background:${c}"></span>
      <span>${desde.toFixed(0)}–${hasta.toFixed(0)}${sufijo}</span>
    </div>`;
  }).join('');
  return `<div class="mapa-leyenda">${cajas}</div>`;
}

// ── Coropleta de prevalencia ─────────────────────────────────────
function renderCoropleta(wrapId, valores, etiquetaSerie) {
  const wrap = document.getElementById(wrapId);
  if (!wrap) return;
  cargarGeo().then(geo => {
    const ancho = wrap.clientWidth || 420;
    const alto = wrap.clientHeight || 520;
    const proyectar = proyeccion(geo.features, ancho, alto, 12);
    const escala = escalaSecuencial(Object.values(valores));

    const caminos = geo.features.map(f => {
      const dep = f.properties.dep;
      const v = valores[dep];
      const texto = Number.isFinite(v) ? `${deptLabel(dep)}: ${v.toFixed(1)}%`
                                       : `${deptLabel(dep)}: sin dato`;
      return `<path d="${trazo(f.geometry, proyectar)}" fill="${escala.color(v)}"
        stroke="#fff" stroke-width="0.7" class="mapa-dep"><title>${texto}</title></path>`;
    }).join('');

    wrap.innerHTML = `
      <svg viewBox="0 0 ${ancho} ${alto}" width="100%" height="100%"
           preserveAspectRatio="xMidYMid meet" role="img"
           aria-label="Mapa del Perú: ${etiquetaSerie} por departamento">
        ${caminos}
      </svg>
      ${leyendaSecuencial(escala, '%')}`;
  }).catch(e => {
    wrap.innerHTML = `<p class="mapa-error">No se pudo cargar la geometría (${e.message}).</p>`;
  });
}

// ── Mapa de servicios ────────────────────────────────────────────
// El tipo de servicio se codifica por FORMA, no por color: cinco colores no
// superan la prueba de separación para daltonismo cuando cualquier par puede
// quedar contiguo, que es justo el caso de un mapa de puntos.
const FORMAS_SERVICIO = {
  CEM: { glifo: 'circulo',   nombre: 'Centro Emergencia Mujer' },
  SAR: { glifo: 'cuadrado',  nombre: 'Atención Rural' },
  SAU: { glifo: 'triangulo', nombre: 'Atención Urgente' },
  HRT: { glifo: 'rombo',     nombre: 'Refugio Temporal' },
  CAI: { glifo: 'cruz',      nombre: 'Atención Institucional' }
};
const COLOR_SERVICIO = '#1D4ED8';

function glifoSvg(glifo, x, y, r, relleno) {
  const a = `fill="${relleno}" stroke="#fff" stroke-width="1.2"`;
  switch (glifo) {
    case 'cuadrado':  return `<rect x="${x-r}" y="${y-r}" width="${r*2}" height="${r*2}" rx="1" ${a}/>`;
    case 'triangulo': return `<polygon points="${x},${y-r*1.2} ${x+r*1.1},${y+r} ${x-r*1.1},${y+r}" ${a}/>`;
    case 'rombo':     return `<polygon points="${x},${y-r*1.3} ${x+r*1.3},${y} ${x},${y+r*1.3} ${x-r*1.3},${y}" ${a}/>`;
    case 'cruz':      return `<path d="M${x-r},${y-r*0.38} h${r*0.62} v-${r*0.62} h${r*0.76} v${r*0.62} h${r*0.62}
                                       v${r*0.76} h-${r*0.62} v${r*0.62} h-${r*0.76} v-${r*0.62} h-${r*0.62} Z" ${a}/>`;
    default:          return `<circle cx="${x}" cy="${y}" r="${r}" ${a}/>`;
  }
}

function leyendaServicios(presentes, conUbicacion) {
  const items = Object.entries(FORMAS_SERVICIO)
    .filter(([k]) => presentes.has(k))
    .map(([k, cfg]) => `<div class="mapa-leyenda-item">
      <svg width="16" height="16" viewBox="0 0 16 16" aria-hidden="true">
        ${glifoSvg(cfg.glifo, 8, 8, 5, COLOR_SERVICIO)}
      </svg><span>${k} · ${cfg.nombre}</span></div>`).join('');
  const ubic = conUbicacion
    ? `<div class="mapa-leyenda-item"><svg width="16" height="16" viewBox="0 0 16 16" aria-hidden="true">
         <circle cx="8" cy="8" r="4.5" fill="#DC2626" stroke="#fff" stroke-width="2"/>
       </svg><span>Tu ubicación</span></div>` : '';
  return `<div class="mapa-leyenda">${items}${ubic}</div>`;
}

// Dibuja el nivel administrativo que corresponde a la selección y encuadra en él.
// Sin departamento: el país. Con departamento: sus provincias. Con provincia: sus
// distritos. El encuadre es siempre la unidad más específica elegida.
function renderMapaServicios(wrapId, servicios, sel) {
  const wrap = document.getElementById(wrapId);
  if (!wrap) return;
  sel = sel || { dep: '', prov: '', dist: '' };

  const pintar = (geo, paquete) => {
    // El alto es constante y lo fija el CSS (.p6-mapa-lienzo). Medir el contenedor
    // no sirve: la leyenda y las notas viven bajo el lienzo y lo harían crecer en
    // cada repintado.
    const ancho = wrap.clientWidth || 420;
    const alto = ALTO_MAPA;

    // Capa de detalle disponible para este departamento
    const provincias = (paquete && paquete.provincias) || [];
    const distritos = (paquete && paquete.distritos) || [];

    let contorno, marco, etiquetaNivel;
    if (sel.dist && distritos.length) {
      contorno = distritos.filter(f => f.properties.p === sel.prov);
      marco = distritos.filter(f => f.properties.u === sel.dist);
      etiquetaNivel = 'distritos';
    } else if (sel.prov && distritos.length) {
      contorno = distritos.filter(f => f.properties.p === sel.prov);
      marco = contorno;
      etiquetaNivel = 'distritos';
    } else if (sel.dep && provincias.length) {
      contorno = provincias;
      marco = provincias;
      etiquetaNivel = 'provincias';
    } else if (sel.dep) {
      contorno = geo.features;
      marco = geo.features.filter(f => f.properties.u === sel.dep);
      etiquetaNivel = 'departamentos';
    } else {
      contorno = geo.features;
      marco = geo.features;
      etiquetaNivel = 'departamentos';
    }
    if (!marco.length) marco = contorno.length ? contorno : geo.features;

    const proyectar = proyeccion(marco, ancho, alto, 14);
    const resaltado = sel.dist || sel.prov || sel.dep;

    const caminos = contorno.map(f => {
      const u = f.properties.u;
      const activo = !resaltado ||
        (sel.dist ? u === sel.dist : sel.prov ? f.properties.p === sel.prov || u === sel.prov
                                              : u === sel.dep || etiquetaNivel !== 'departamentos');
      // El vecindario se dibuja atenuado pero visible: sirve de referencia para
      // ubicarse.
      return `<path d="${trazo(f.geometry, proyectar)}"
        fill="${activo ? '#DDE5F4' : '#F0F3F9'}"
        stroke="${activo ? '#8497BC' : '#D6DDEA'}"
        stroke-width="${activo ? 1 : 0.8}" vector-effect="non-scaling-stroke"
        ><title>${f.properties.n || deptLabel(f.properties.dep || '')}</title></path>`;
    }).join('');

    const conCoord = servicios.filter(s => s.lat != null && s.lon != null);
    const presentes = new Set(conCoord.map(s => s.tipo));
    const radio = sel.prov ? 6 : sel.dep ? 5 : 3.2;
    const puntos = conCoord.map(s => {
      const [x, y] = proyectar([s.lon, s.lat]);
      const cfg = FORMAS_SERVICIO[s.tipo] || FORMAS_SERVICIO.CEM;
      return `<g>${glifoSvg(cfg.glifo, x, y, radio, COLOR_SERVICIO)}` +
             `<title>${s.nombre} (${s.tipo}) — ${s.distrito}</title></g>`;
    }).join('');

    // Marca de la persona: círculo con halo, distinto de los glifos de servicio.
    let marcaUbicacion = '';
    if (sel.ubicacion) {
      const [x, y] = proyectar([sel.ubicacion.lon, sel.ubicacion.lat]);
      marcaUbicacion = `<g class="p6-marca-ubicacion">
        <circle cx="${x.toFixed(1)}" cy="${y.toFixed(1)}" r="11" fill="rgba(220,38,38,.18)"/>
        <circle cx="${x.toFixed(1)}" cy="${y.toFixed(1)}" r="4.5" fill="#DC2626"
                stroke="#fff" stroke-width="2"><title>Tu ubicación aproximada</title></circle>
      </g>`;
    }

    const sinCoord = servicios.length - conCoord.length;
    wrap.innerHTML = `
      <div class="p6-mapa-lienzo">
        <svg viewBox="0 0 ${ancho} ${alto}" width="100%" height="100%"
             preserveAspectRatio="xMidYMid meet" role="img"
             aria-label="Mapa de servicios de atención del MIMP en ${p6NombreSeleccion()}">
          ${caminos}${puntos}${marcaUbicacion}
        </svg>
      </div>
      ${leyendaServicios(presentes, !!sel.ubicacion)}
      ${sinCoord ? `<p class="mapa-nota">${sinCoord} servicio${sinCoord!==1?'s':''} sin coordenada, solo en el listado.</p>` : ''}`;
  };

  cargarGeo()
    .then(geo => sel.dep
      ? cargarGeoDep(sel.dep).then(p => pintar(geo, p)).catch(() => pintar(geo, null))
      : pintar(geo, null))
    .catch(e => {
      wrap.innerHTML = `<p class="mapa-error">No se pudo cargar la geometría (${e.message}).</p>`;
    });
}

// ════════════════════════════════════════════════════════════════
//  HELPERS Chart.js
// ════════════════════════════════════════════════════════════════
// Una serie, un color. Colorear cada barra según su posición en el ranking gasta el
// canal de color repitiendo lo que la longitud ya dice, y sugiere categorías donde
// solo hay una medida: el color se reserva para cuando hay algo que distinguir.
function monoColors(vals, palette) {
  return new Array(vals.length).fill(palette[2]);
}

// Para variables **ordinales** (poco → mucho) el color sí aporta: recorre la rampa
// en el orden de las categorías, no en el del valor.
function rampaOrdinal(n, palette) {
  if (n <= 1) return [palette[2]];
  const paso = (palette.length - 3) / (n - 1);
  return Array.from({ length: n }, (_, i) => palette[Math.round(1 + i * paso)]);
}

function monoHBar(labels, vals, palette, maxX) {
  const colors = monoColors(vals, palette);
  const m = maxX || Math.ceil(Math.max(...vals)*1.3/5)*5||10;
  return {
    type:'bar',
    data:{ labels, datasets:[{ data:vals, backgroundColor:colors, borderRadius:4 }] },
    options: hBarOpts(m, false, true)
  };
}

function monoVBar(labels, vals, palette, maxY) {
  const colors = monoColors(vals, palette);
  const m = maxY || Math.ceil(Math.max(...vals)*1.4)||5;
  return {
    type:'bar',
    data:{ labels, datasets:[{ data:vals, backgroundColor:colors, borderRadius:[4,4,0,0] }] },
    options: vBarOpts(m)
  };
}

function hBarOpts(maxX, showLegend, showLabels) {
  return {
    indexAxis:'y', responsive:true, maintainAspectRatio:false,
    plugins:{
      legend:{ display: showLegend||false, position:'bottom', labels:{boxWidth:12,font:{size:11},padding:10} },
      datalabels:{
        display: showLabels||false,
        anchor:'end', align:'end',
        color: C.text, font:{size:11, weight:'600'},
        formatter:v=>v.toFixed(1)+'%'
      }
    },
    scales:{
      x:{ max:maxX, grid:{color:'rgba(0,0,0,.05)'}, ticks:{callback:v=>v+'%', font:{size:11}} },
      y:{ grid:{display:false}, ticks:{font:{size:11}} }
    }
  };
}

function vBarOpts(maxY) {
  return {
    responsive:true, maintainAspectRatio:false,
    plugins:{
      legend:{display:false},
      datalabels:{
        anchor:'end', align:'top',
        color:C.text, font:{size:11, weight:'600'},
        formatter:v=>v.toFixed(1)+'%'
      }
    },
    scales:{
      x:{ grid:{display:false}, ticks:{font:{size:11}} },
      y:{ max:maxY, grid:{color:'rgba(0,0,0,.05)'}, ticks:{callback:v=>v+'%', font:{size:11}} }
    }
  };
}

function vBarOptsLegend(maxY) {
  return {
    responsive:true, maintainAspectRatio:false,
    plugins:{
      legend:{ display:true, position:'bottom', labels:{boxWidth:12, font:{size:11}, padding:10} },
      datalabels:{
        anchor:'end', align:'top',
        color:C.text, font:{size:10, weight:'600'},
        formatter:v=>v.toFixed(1)+'%'
      }
    },
    scales:{
      x:{ grid:{display:false}, ticks:{font:{size:11}} },
      y:{ max:maxY, grid:{color:'rgba(0,0,0,.05)'}, ticks:{callback:v=>v+'%', font:{size:11}} }
    }
  };
}

function lineOpts() {
  return {
    responsive:true, maintainAspectRatio:false,
    plugins:{
      legend:{ display:true, position:'bottom', labels:{boxWidth:12, font:{size:11}} },
      datalabels:{
        anchor:'top', align:'top',
        color:C.text, font:{size:10, weight:'600'},
        formatter:v=>v.toFixed(1)+'%'
      }
    },
    scales:{
      x:{ grid:{color:'rgba(0,0,0,.04)'}, ticks:{font:{size:11}} },
      y:{ grid:{color:'rgba(0,0,0,.04)'}, ticks:{callback:v=>v+'%', font:{size:11}} }
    }
  };
}
