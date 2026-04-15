"""
visualize.py — Apple Health Interactive Dashboard
Generates a single self-contained dashboard.html with liquid-glass UI.
Usage: python3 src/visualize.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from parse_health import load_sleep, load_heart_rate, load_steps

OUTPUT_PATH = "dashboard.html"


def _to_records(df: pd.DataFrame) -> list:
    if df.empty:
        return []
    out = []
    for _, row in df.iterrows():
        rec = {}
        for col in df.columns:
            v = row[col]
            if hasattr(v, "isoformat"):
                rec[col] = v.isoformat()[:10]
            elif pd.isna(v):
                rec[col] = None
            elif isinstance(v, float):
                rec[col] = round(float(v), 4)
            else:
                rec[col] = int(v)
        out.append(rec)
    return out


def _recent_avg(df: pd.DataFrame, col: str, days: int = 7):
    if df.empty:
        return None
    cutoff = pd.Timestamp.today() - pd.Timedelta(days=days)
    recent = df[df["date"] >= cutoff][col]
    return recent.mean() if not recent.empty else df[col].iloc[-1]


_HTML = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>健康数据</title>
<script src="https://cdn.plot.ly/plotly-2.27.0.min.js" charset="utf-8"></script>
<style>
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}

body {
  min-height: 100vh;
  font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", "Helvetica Neue", Arial, sans-serif;
  background: linear-gradient(-45deg, #dbeafe, #ede9fe, #fce7f3, #d1fae5);
  background-size: 400% 400%;
  animation: bgMove 18s ease infinite;
  padding: 40px 24px 60px;
  color: #1a1a2e;
}
@keyframes bgMove {
  0%  { background-position: 0% 50%; }
  50% { background-position: 100% 50%; }
  100%{ background-position: 0% 50%; }
}

.glass {
  background: rgba(255,255,255,0.52);
  backdrop-filter: blur(28px) saturate(180%);
  -webkit-backdrop-filter: blur(28px) saturate(180%);
  border: 1px solid rgba(255,255,255,0.78);
  border-radius: 26px;
  box-shadow: 0 8px 32px rgba(100,100,200,0.10),
              inset 0 1px 0 rgba(255,255,255,0.95);
}

/* ── Header ── */
header {
  text-align: center;
  margin-bottom: 44px;
}
header h1 {
  font-size: 2.6rem;
  font-weight: 700;
  letter-spacing: -0.04em;
  background: linear-gradient(135deg, #6366f1, #a855f7, #ec4899);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}
header p {
  margin-top: 8px;
  color: rgba(0,0,0,0.38);
  font-size: 0.88rem;
  letter-spacing: 0.01em;
}

/* ── Card grid ── */
.cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(290px, 1fr));
  gap: 20px;
  max-width: 1060px;
  margin: 0 auto;
}

/* ── Card ── */
.card {
  padding: 28px 26px 18px;
  cursor: pointer;
  position: relative;
  overflow: hidden;
  transition: transform .28s cubic-bezier(.34,1.56,.64,1),
              box-shadow .28s ease;
}
.card:hover {
  transform: translateY(-7px) scale(1.015);
  box-shadow: 0 24px 56px rgba(100,100,200,0.16),
              inset 0 1px 0 rgba(255,255,255,1);
}
.card:active { transform: translateY(-2px) scale(0.99); }

.card::before {
  content:'';
  position:absolute;
  top:0;left:0;right:0;
  height:3px;
  border-radius:26px 26px 0 0;
}
.card-sleep::before { background:linear-gradient(90deg,#a78bfa,#7c3aed); }
.card-hr::before    { background:linear-gradient(90deg,#fb7185,#e11d48); }
.card-steps::before { background:linear-gradient(90deg,#34d399,#059669); }

.card-head { display:flex; align-items:center; gap:12px; margin-bottom:18px; }
.card-icon {
  width:46px; height:46px; border-radius:14px;
  display:flex; align-items:center; justify-content:center;
  font-size:1.35rem; flex-shrink:0;
}
.icon-sleep { background:linear-gradient(135deg,#c4b5fd,#7c3aed); }
.icon-hr    { background:linear-gradient(135deg,#fda4af,#e11d48); }
.icon-steps { background:linear-gradient(135deg,#6ee7b7,#059669); }
.card-label { font-size:.95rem; font-weight:600; color:rgba(0,0,0,0.65); }

.card-val {
  font-size:3.2rem; font-weight:700;
  letter-spacing:-0.05em; line-height:1;
  font-variant-numeric: tabular-nums;
}
.val-sleep { color:#7c3aed; }
.val-hr    { color:#e11d48; }
.val-steps { color:#059669; }
.card-unit { font-size:.95rem; font-weight:500; opacity:.5; margin-left:3px; }
.card-sub  { font-size:.75rem; color:rgba(0,0,0,0.38); margin:5px 0 14px; }

.sparkline { height:58px; width:100%; border-radius:10px; overflow:hidden; }
.card-hint { text-align:center; font-size:.7rem; color:rgba(0,0,0,0.28); margin-top:10px; letter-spacing:.03em; }

/* ── Modal overlay ── */
.overlay {
  position:fixed; inset:0;
  background:rgba(120,120,180,0.20);
  backdrop-filter:blur(10px);
  -webkit-backdrop-filter:blur(10px);
  display:flex; align-items:center; justify-content:center;
  z-index:999; padding:16px;
  opacity:0; pointer-events:none;
  transition:opacity .3s ease;
}
.overlay.open { opacity:1; pointer-events:all; }

.modal {
  width:100%; max-width:920px; max-height:92vh;
  display:flex; flex-direction:column;
  padding:30px 28px 24px;
  background:rgba(255,255,255,0.80);
  backdrop-filter:blur(44px) saturate(200%);
  -webkit-backdrop-filter:blur(44px) saturate(200%);
  border:1px solid rgba(255,255,255,0.92);
  border-radius:34px;
  box-shadow:0 28px 80px rgba(80,80,180,0.22),
             inset 0 1px 0 rgba(255,255,255,1);
  transform:translateY(36px) scale(.96);
  transition:transform .38s cubic-bezier(.34,1.56,.64,1);
}
.overlay.open .modal { transform:translateY(0) scale(1); }

.modal-top {
  display:flex; align-items:center;
  justify-content:space-between; margin-bottom:18px;
}
.modal-title { font-size:1.45rem; font-weight:700; letter-spacing:-.03em; }
.btn-close {
  width:34px; height:34px; border-radius:50%;
  background:rgba(0,0,0,0.08); border:none; cursor:pointer;
  font-size:.9rem; color:rgba(0,0,0,0.45);
  display:flex; align-items:center; justify-content:center;
  transition:background .2s;
}
.btn-close:hover { background:rgba(0,0,0,0.14); }

/* ── Tabs ── */
.tabs {
  display:flex; gap:5px;
  background:rgba(0,0,0,0.06);
  border-radius:12px; padding:4px;
  width:fit-content; margin-bottom:18px;
}
.tab {
  padding:6px 22px; border-radius:9px; border:none;
  background:transparent; font-size:.84rem; font-weight:600;
  color:rgba(0,0,0,0.42); cursor:pointer;
  transition:all .2s; font-family:inherit; letter-spacing:-.01em;
}
.tab.active {
  background:rgba(255,255,255,0.92);
  color:rgba(0,0,0,0.82);
  box-shadow:0 2px 8px rgba(0,0,0,0.10);
}

.modal-chart { flex:1; min-height:320px; }

/* ── Stats pills ── */
.stats {
  display:grid; grid-template-columns:repeat(3,1fr);
  gap:10px; margin-top:18px;
}
.pill {
  background:rgba(0,0,0,0.04);
  border-radius:14px; padding:13px 14px; text-align:center;
}
.pill-label {
  font-size:.68rem; color:rgba(0,0,0,0.38);
  text-transform:uppercase; letter-spacing:.07em; margin-bottom:4px;
}
.pill-val { font-size:1.15rem; font-weight:700; letter-spacing:-.03em; }

@media(max-width:600px){
  body{padding:20px 14px 40px;}
  header h1{font-size:2rem;}
  .card-val{font-size:2.4rem;}
  .stats{grid-template-columns:1fr 1fr;}
  .modal{padding:20px 16px 18px; border-radius:26px;}
  .modal-title{font-size:1.2rem;}
}
</style>
</head>
<body>

<header>
  <h1>健康数据</h1>
  <p>来自 Apple Health 的个人健康报告</p>
</header>

<div class="cards">

  <div class="card glass card-sleep" onclick="openModal('sleep')">
    <div class="card-head">
      <div class="card-icon icon-sleep">🌙</div>
      <span class="card-label">睡眠</span>
    </div>
    <div class="card-val val-sleep">__SLEEP_VAL__<span class="card-unit">小时</span></div>
    <div class="card-sub">近 7 天平均</div>
    <div class="sparkline" id="sp-sleep"></div>
    <div class="card-hint">点击查看详情</div>
  </div>

  <div class="card glass card-hr" onclick="openModal('hr')">
    <div class="card-head">
      <div class="card-icon icon-hr">♥</div>
      <span class="card-label">静息心率</span>
    </div>
    <div class="card-val val-hr">__HR_VAL__<span class="card-unit">bpm</span></div>
    <div class="card-sub">近 7 天平均</div>
    <div class="sparkline" id="sp-hr"></div>
    <div class="card-hint">点击查看详情</div>
  </div>

  <div class="card glass card-steps" onclick="openModal('steps')">
    <div class="card-head">
      <div class="card-icon icon-steps">🏃</div>
      <span class="card-label">步数</span>
    </div>
    <div class="card-val val-steps">__STEPS_VAL__<span class="card-unit">步</span></div>
    <div class="card-sub">近 7 天平均</div>
    <div class="sparkline" id="sp-steps"></div>
    <div class="card-hint">点击查看详情</div>
  </div>

</div>

<div class="overlay" id="overlay" onclick="bgClick(event)">
  <div class="modal">
    <div class="modal-top">
      <div class="modal-title" id="modal-title">睡眠</div>
      <button class="btn-close" onclick="closeModal()">✕</button>
    </div>
    <div class="tabs">
      <button class="tab" onclick="setTab('week',this)">周</button>
      <button class="tab active" onclick="setTab('month',this)">月</button>
      <button class="tab" onclick="setTab('year',this)">年</button>
    </div>
    <div class="modal-chart" id="modal-chart"></div>
    <div class="stats" id="stats"></div>
  </div>
</div>

<script>
const SLEEP_DATA  = __SLEEP_JSON__;
const HR_DATA     = __HR_JSON__;
const STEPS_DATA  = __STEPS_JSON__;

// Parse ISO date strings to Date objects
function parse(arr, dateKey) {
  return arr.map(d => ({...d, _d: new Date(d[dateKey])}))
            .sort((a,b) => a._d - b._d);
}
const SD = parse(SLEEP_DATA, 'date');
const HD = parse(HR_DATA,    'date');
const TD = parse(STEPS_DATA, 'date');

function filter(data, period) {
  const days = {week:7, month:30, year:365}[period];
  const cut  = new Date(Date.now() - days * 864e5);
  return data.filter(d => d._d >= cut);
}

function rolling(vals, w=7) {
  return vals.map((_,i) => {
    const s = vals.slice(Math.max(0,i-Math.floor(w/2)), i+Math.ceil(w/2)).filter(v=>v!=null);
    return s.length ? s.reduce((a,b)=>a+b,0)/s.length : null;
  });
}

function monthGroup(data, key, agg='avg') {
  const g = {};
  data.forEach(d => {
    const m = d.date.slice(0,7);
    if (!g[m]) g[m] = [];
    if (d[key] != null) g[m].push(d[key]);
  });
  return Object.entries(g).sort().map(([m,vs]) => ({
    month: m+'-15',
    val: agg==='sum' ? vs.reduce((a,b)=>a+b,0)
                     : vs.reduce((a,b)=>a+b,0)/vs.length
  }));
}

const BASE_LAYOUT = {
  paper_bgcolor: 'rgba(0,0,0,0)',
  plot_bgcolor:  'rgba(0,0,0,0)',
  font: { family:'-apple-system,BlinkMacSystemFont,"SF Pro Display",sans-serif', size:12, color:'rgba(0,0,0,0.5)' },
  margin: {t:10,b:44,l:52,r:16},
  xaxis: { gridcolor:'rgba(0,0,0,0.05)', linecolor:'rgba(0,0,0,0.08)', zeroline:false, tickcolor:'rgba(0,0,0,0)' },
  yaxis: { gridcolor:'rgba(0,0,0,0.05)', linecolor:'rgba(0,0,0,0.08)', zeroline:false, tickcolor:'rgba(0,0,0,0)' },
  showlegend: true,
  legend: { orientation:'h', y:-0.18, x:0, font:{size:11} },
  hovermode: 'x unified',
};

const CFG = {displayModeBar:false, responsive:true};

// ── Sparklines ────────────────────────────────────────────────────────────
function spark(id, dates, vals, color, fill) {
  Plotly.newPlot(id,
    [{x:dates, y:vals, type:'scatter', mode:'lines', fill:'tozeroy',
      fillcolor:fill, line:{color,width:1.5,shape:'spline',smoothing:.8},
      hoverinfo:'none'}],
    {paper_bgcolor:'rgba(0,0,0,0)', plot_bgcolor:'rgba(0,0,0,0)',
     margin:{t:2,b:2,l:2,r:2},
     xaxis:{visible:false}, yaxis:{visible:false}, showlegend:false},
    {displayModeBar:false, responsive:true, staticPlot:true}
  );
}

(function initSparks() {
  const c30 = d => { const cut=new Date(Date.now()-30*864e5); return d.filter(x=>x._d>=cut); };
  const s = c30(SD);
  if (s.length) spark('sp-sleep', s.map(d=>d.date), s.map(d=>d.sleep_hours), '#7c3aed','rgba(124,58,237,.15)');
  const h = c30(HD);
  if (h.length) spark('sp-hr',    h.map(d=>d.date), h.map(d=>d.hr_min),      '#e11d48','rgba(225,29,72,.15)');
  const t = c30(TD);
  if (t.length) spark('sp-steps', t.map(d=>d.date), t.map(d=>d.steps),       '#059669','rgba(5,150,105,.15)');
})();

// ── Modal ─────────────────────────────────────────────────────────────────
let CUR_METRIC = 'sleep', CUR_PERIOD = 'month';

function openModal(m) {
  CUR_METRIC = m; CUR_PERIOD = 'month';
  document.querySelectorAll('.tab').forEach((t,i)=>t.classList.toggle('active',i===1));
  document.getElementById('modal-title').textContent =
    {sleep:'🌙  睡眠', hr:'♥  静息心率', steps:'🏃  步数'}[m];
  document.getElementById('overlay').classList.add('open');
  document.body.style.overflow = 'hidden';
  render();
}
function closeModal() {
  document.getElementById('overlay').classList.remove('open');
  document.body.style.overflow = '';
}
function bgClick(e) { if(e.target===document.getElementById('overlay')) closeModal(); }
document.addEventListener('keydown', e=>{ if(e.key==='Escape') closeModal(); });

function setTab(p, btn) {
  CUR_PERIOD = p;
  document.querySelectorAll('.tab').forEach(t=>t.classList.remove('active'));
  btn.classList.add('active');
  render();
}

function render() {
  if (CUR_METRIC==='sleep')  renderSleep(CUR_PERIOD);
  if (CUR_METRIC==='hr')     renderHR(CUR_PERIOD);
  if (CUR_METRIC==='steps')  renderSteps(CUR_PERIOD);
}

function pills(items) {
  document.getElementById('stats').innerHTML = items.map(p =>
    `<div class="pill"><div class="pill-label">${p.label}</div>
     <div class="pill-val" style="color:${p.color}">${p.val}</div></div>`
  ).join('');
}

// ── Sleep ─────────────────────────────────────────────────────────────────
function renderSleep(period) {
  const div = document.getElementById('modal-chart');
  const COLOR = '#7c3aed';
  const data  = filter(SD, period);
  if (!data.length) { div.innerHTML='<p style="padding:60px;text-align:center;color:#bbb">暂无数据</p>'; return; }

  let traces, layout;

  if (period === 'year') {
    const mg = monthGroup(data, 'sleep_hours', 'avg');
    traces = [{
      x:mg.map(d=>d.month), y:mg.map(d=>Math.round(d.val*10)/10),
      type:'bar', name:'月均睡眠',
      marker:{color:'rgba(167,139,250,.6)', line:{width:0}},
      hovertemplate:'%{x|%Y年%m月}<br>月均 %{y:.1f} 小时<extra></extra>',
    }];
    layout = {...BASE_LAYOUT, yaxis:{...BASE_LAYOUT.yaxis, title:'小时', rangemode:'tozero'}};
  } else {
    const dates = data.map(d=>d.date);
    const vals  = data.map(d=>d.sleep_hours);
    const avg   = rolling(vals);
    traces = [
      {x:dates, y:vals.map(v=>Math.round(v*10)/10), type:'bar', name:'每日睡眠',
       marker:{color:'rgba(167,139,250,.5)', line:{width:0}},
       hovertemplate:'%{x}<br>%{y:.1f} 小时<extra></extra>'},
      {x:dates, y:avg.map(v=>v?Math.round(v*10)/10:null), type:'scatter',
       mode:'lines', name:'7日均值',
       line:{color:COLOR,width:2.5,shape:'spline',smoothing:.8},
       hovertemplate:'均值 %{y:.1f} 小时<extra></extra>'},
    ];
    layout = {
      ...BASE_LAYOUT,
      shapes:[
        {type:'line',x0:dates[0],x1:dates[dates.length-1],y0:7,y1:7,
         line:{color:'rgba(0,0,0,.18)',dash:'dash',width:1}},
      ],
      yaxis:{...BASE_LAYOUT.yaxis, title:'小时', rangemode:'tozero'},
    };
  }

  Plotly.react(div, traces, layout, CFG);
  const vs = data.map(d=>d.sleep_hours).filter(v=>v);
  pills([
    {label:'平均',   val:(vs.reduce((a,b)=>a+b,0)/vs.length).toFixed(1)+' h', color:COLOR},
    {label:'最佳',   val:Math.max(...vs).toFixed(1)+' h', color:'#059669'},
    {label:'达标天数', val:vs.filter(v=>v>=7).length+' / '+vs.length,         color:COLOR},
  ]);
}

// ── Heart Rate ────────────────────────────────────────────────────────────
function renderHR(period) {
  const div = document.getElementById('modal-chart');
  const COLOR = '#e11d48';
  const data  = filter(HD, period);
  if (!data.length) { div.innerHTML='<p style="padding:60px;text-align:center;color:#bbb">暂无数据</p>'; return; }

  let traces, layout;

  if (period === 'year') {
    const mg = monthGroup(data, 'hr_min', 'avg');
    traces = [{
      x:mg.map(d=>d.month), y:mg.map(d=>Math.round(d.val)),
      type:'scatter', mode:'lines+markers', name:'月均静息心率',
      line:{color:COLOR,width:2.5,shape:'spline'},
      marker:{color:COLOR,size:6},
      hovertemplate:'%{x|%Y年%m月}<br>月均 %{y} bpm<extra></extra>',
    }];
    layout = {...BASE_LAYOUT, yaxis:{...BASE_LAYOUT.yaxis, title:'bpm'}};
  } else {
    const dates = data.map(d=>d.date);
    const vals  = data.map(d=>d.hr_min);
    const avg   = rolling(vals);
    traces = [
      {x:dates, y:vals, type:'scatter', mode:'none', fill:'tozeroy',
       fillcolor:'rgba(225,29,72,.09)', hoverinfo:'skip', showlegend:false},
      {x:dates, y:vals, type:'scatter', mode:'markers', name:'每日最低',
       marker:{color:'rgba(225,29,72,.45)',size:4},
       hovertemplate:'%{x}<br>%{y:.0f} bpm<extra></extra>'},
      {x:dates, y:avg.map(v=>v?Math.round(v):null), type:'scatter',
       mode:'lines', name:'7日均值',
       line:{color:COLOR,width:2.5,shape:'spline',smoothing:.8},
       hovertemplate:'均值 %{y:.0f} bpm<extra></extra>'},
    ];
    layout = {...BASE_LAYOUT, yaxis:{...BASE_LAYOUT.yaxis, title:'bpm'}};
  }

  Plotly.react(div, traces, layout, CFG);
  const vs = data.map(d=>d.hr_min).filter(v=>v);
  pills([
    {label:'平均', val:Math.round(vs.reduce((a,b)=>a+b,0)/vs.length)+' bpm', color:COLOR},
    {label:'最低', val:Math.min(...vs)+' bpm', color:'#059669'},
    {label:'最高', val:Math.max(...vs)+' bpm', color:COLOR},
  ]);
}

// ── Steps ─────────────────────────────────────────────────────────────────
function renderSteps(period) {
  const div = document.getElementById('modal-chart');
  const COLOR = '#059669';
  const data  = filter(TD, period);
  if (!data.length) { div.innerHTML='<p style="padding:60px;text-align:center;color:#bbb">暂无数据</p>'; return; }

  let traces, layout;

  if (period === 'year') {
    const mg = monthGroup(data, 'steps', 'sum');
    traces = [{
      x:mg.map(d=>d.month), y:mg.map(d=>Math.round(d.val)),
      type:'bar', name:'月总步数',
      marker:{color:'rgba(5,150,105,.65)', line:{width:0}},
      hovertemplate:'%{x|%Y年%m月}<br>%{y:,} 步<extra></extra>',
    }];
    layout = {...BASE_LAYOUT, yaxis:{...BASE_LAYOUT.yaxis, title:'步数', tickformat:',', rangemode:'tozero'}};
  } else {
    const dates  = data.map(d=>d.date);
    const vals   = data.map(d=>d.steps);
    const colors = vals.map(v=>v>=10000?'rgba(5,150,105,.7)':'rgba(225,29,72,.65)');
    traces = [{
      x:dates, y:vals, type:'bar', name:'每日步数',
      marker:{color:colors, line:{width:0}},
      hovertemplate:'%{x}<br>%{y:,} 步<extra></extra>',
    }];
    layout = {
      ...BASE_LAYOUT,
      shapes:[
        {type:'line',x0:dates[0],x1:dates[dates.length-1],y0:10000,y1:10000,
         line:{color:'rgba(0,0,0,.18)',dash:'dash',width:1}},
      ],
      yaxis:{...BASE_LAYOUT.yaxis, title:'步数', tickformat:',', rangemode:'tozero'},
    };
  }

  Plotly.react(div, traces, layout, CFG);
  const vs = data.map(d=>d.steps).filter(v=>v);
  pills([
    {label:'日均',   val:Math.round(vs.reduce((a,b)=>a+b,0)/vs.length).toLocaleString()+' 步', color:COLOR},
    {label:'最多',   val:Math.max(...vs).toLocaleString()+' 步', color:COLOR},
    {label:'达标天数', val:vs.filter(v=>v>=10000).length+' / '+vs.length, color:COLOR},
  ]);
}
</script>
</body>
</html>"""


def build_html(sleep_df: pd.DataFrame, hr_df: pd.DataFrame,
               steps_df: pd.DataFrame) -> str:
    s_avg = _recent_avg(sleep_df, "sleep_hours", 7)
    h_avg = _recent_avg(hr_df,    "hr_min",      7)
    t_avg = _recent_avg(steps_df, "steps",        7)

    return (
        _HTML
        .replace("__SLEEP_JSON__",  json.dumps(_to_records(sleep_df)))
        .replace("__HR_JSON__",     json.dumps(_to_records(hr_df)))
        .replace("__STEPS_JSON__",  json.dumps(_to_records(steps_df)))
        .replace("__SLEEP_VAL__",   f"{s_avg:.1f}" if s_avg else "—")
        .replace("__HR_VAL__",      f"{int(h_avg)}" if h_avg else "—")
        .replace("__STEPS_VAL__",   f"{int(t_avg):,}" if t_avg else "—")
    )


def main() -> None:
    export_path = "data/export.xml"
    print("Parsing Apple Health data …")
    sleep_df = load_sleep(export_path)
    hr_df    = load_heart_rate(export_path)
    steps_df = load_steps(export_path)
    print(f"  Sleep  : {len(sleep_df)} days")
    print(f"  HR     : {len(hr_df)} days")
    print(f"  Steps  : {len(steps_df)} days")
    print("\nBuilding dashboard …")
    Path(OUTPUT_PATH).write_text(build_html(sleep_df, hr_df, steps_df), encoding="utf-8")
    print(f"  Saved → {OUTPUT_PATH}")
    print("\nDone! Open dashboard.html in your browser.")


if __name__ == "__main__":
    main()
