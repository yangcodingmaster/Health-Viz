"""
visualize.py — Apple Health Interactive Dashboard (Phase 1-4)
Usage: python3 src/visualize.py
"""
from __future__ import annotations
import json, sys
from pathlib import Path
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from parse_health import load_sleep, load_heart_rate, load_steps

OUTPUT_PATH = "dashboard.html"

def _to_records(df):
    if df.empty: return []
    out = []
    for _, row in df.iterrows():
        rec = {}
        for col in df.columns:
            v = row[col]
            if hasattr(v, "isoformat"): rec[col] = v.isoformat()[:10]
            elif pd.isna(v): rec[col] = None
            elif isinstance(v, float): rec[col] = round(float(v), 4)
            else: rec[col] = int(v)
        out.append(rec)
    return out

def _avg7(df, col):
    if df.empty: return None
    cut = pd.Timestamp.today() - pd.Timedelta(days=7)
    r = df[df["date"] >= cut][col]
    return r.mean() if not r.empty else df[col].iloc[-1]

_HTML = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>健康洞察</title>
<script src="https://cdn.plot.ly/plotly-2.27.0.min.js" charset="utf-8"></script>
<style>
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
body{min-height:100vh;font-family:-apple-system,BlinkMacSystemFont,"SF Pro Display","Helvetica Neue",sans-serif;color:#1a1a2e;overflow-x:hidden}
#bg{position:fixed;inset:0;z-index:-1;background:linear-gradient(-45deg,#dbeafe,#ede9fe,#fce7f3,#d1fae5);background-size:400% 400%;animation:bgIdle 18s ease infinite;transition:background 0.8s ease}
@keyframes bgIdle{0%{background-position:0% 50%}50%{background-position:100% 50%}100%{background-position:0% 50%}}
.glass{background:rgba(255,255,255,0.52);backdrop-filter:blur(28px) saturate(180%);-webkit-backdrop-filter:blur(28px) saturate(180%);border:1px solid rgba(255,255,255,0.78);border-radius:24px;box-shadow:0 8px 32px rgba(100,100,200,.10),inset 0 1px 0 rgba(255,255,255,.95)}
.page{max-width:1200px;margin:0 auto;padding:40px 24px 80px}
header{text-align:center;margin-bottom:40px}
header h1{font-size:2.4rem;font-weight:700;letter-spacing:-.04em;background:linear-gradient(135deg,#6366f1,#a855f7,#ec4899);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text}
header p{color:rgba(0,0,0,.4);font-size:.88rem;margin-top:6px}

/* Bento grid */
.bento{display:grid;grid-template-columns:repeat(3,1fr);grid-template-rows:auto auto;gap:16px}
.card{padding:24px;cursor:pointer;position:relative;overflow:hidden;transition:transform .28s cubic-bezier(.34,1.56,.64,1),box-shadow .28s ease;min-height:200px;display:flex;flex-direction:column}
.card:hover{transform:translateY(-5px) scale(1.01);box-shadow:0 20px 48px rgba(100,100,200,.15),inset 0 1px 0 rgba(255,255,255,1)}
.card::before{content:'';position:absolute;top:0;left:0;right:0;height:3px;border-radius:24px 24px 0 0}
.card-steps{grid-column:1/3;grid-row:1}.card-steps::before{background:linear-gradient(90deg,#34d399,#059669)}
.card-sleep{grid-column:3;grid-row:1}.card-sleep::before{background:linear-gradient(90deg,#a78bfa,#7c3aed)}
.card-hr{grid-column:1;grid-row:2}.card-hr::before{background:linear-gradient(90deg,#fb7185,#e11d48)}
.card-explore{grid-column:2/4;grid-row:2}.card-explore::before{background:linear-gradient(90deg,#60a5fa,#3b82f6)}

.card-head{display:flex;align-items:center;gap:12px;margin-bottom:12px}
.card-icon{width:44px;height:44px;border-radius:14px;display:flex;align-items:center;justify-content:center;flex-shrink:0}
.icon-steps{background:linear-gradient(135deg,#6ee7b7,#059669)}
.icon-sleep{background:linear-gradient(135deg,#c4b5fd,#7c3aed)}
.icon-hr{background:linear-gradient(135deg,#fda4af,#e11d48)}
.icon-explore{background:linear-gradient(135deg,#93c5fd,#3b82f6)}
.card-label{font-size:.95rem;font-weight:600;color:rgba(0,0,0,.65)}
.metric-val{font-size:3rem;font-weight:700;letter-spacing:-.05em;line-height:1;font-variant-numeric:tabular-nums;transition:all .12s ease}
.metric-unit{font-size:1rem;font-weight:500;opacity:.5;margin-left:3px}
.metric-sub{font-size:.75rem;color:rgba(0,0,0,.38);margin:4px 0 12px}
.val-steps{color:#059669}.val-sleep{color:#7c3aed}.val-hr{color:#e11d48}.val-explore{color:#3b82f6}
.card-hint{font-size:.7rem;color:rgba(0,0,0,.28);margin-top:auto;padding-top:8px;text-align:center;letter-spacing:.03em}

/* Sparkline + scrub */
.spark-wrap{position:relative;height:60px;flex-shrink:0}
.sparkline{width:100%;height:100%;border-radius:10px;overflow:hidden}
.scrub-overlay{position:absolute;inset:0;cursor:crosshair;z-index:10}
.scrub-line{position:absolute;top:0;bottom:0;width:1.5px;background:rgba(0,0,0,.25);pointer-events:none;opacity:0;transition:opacity .1s}

/* SVG animations */
@keyframes heartbeat{0%,100%{transform:scale(1)}14%{transform:scale(1.25)}28%{transform:scale(1)}42%{transform:scale(1.15)}70%{transform:scale(1)}}
@keyframes moonGlow{0%,100%{filter:drop-shadow(0 0 4px rgba(167,139,250,.6))}50%{filter:drop-shadow(0 0 10px rgba(167,139,250,1))}}
.svg-moon{animation:moonGlow 3s ease-in-out infinite}

/* Detail panel */
.detail-panel{position:fixed;inset:0;z-index:100;display:flex;align-items:center;justify-content:center;padding:20px;pointer-events:none;opacity:0;transition:opacity .3s ease}
.detail-panel.open{pointer-events:all;opacity:1}
.detail-bg{position:absolute;inset:0;background:rgba(100,100,160,.18);backdrop-filter:blur(8px);-webkit-backdrop-filter:blur(8px)}
.detail-card{position:relative;z-index:1;width:100%;max-width:980px;max-height:92vh;display:flex;flex-direction:column;padding:28px;background:rgba(255,255,255,.82);backdrop-filter:blur(44px) saturate(200%);-webkit-backdrop-filter:blur(44px) saturate(200%);border:1px solid rgba(255,255,255,.92);border-radius:32px;box-shadow:0 24px 80px rgba(80,80,180,.22),inset 0 1px 0 rgba(255,255,255,1);transform:scale(.92) translateY(20px);transition:transform .4s cubic-bezier(.34,1.56,.64,1);overflow-y:auto}
.detail-panel.open .detail-card{transform:scale(1) translateY(0)}
.detail-top{display:flex;align-items:center;justify-content:space-between;margin-bottom:16px;flex-shrink:0;flex-wrap:wrap;gap:10px}
.detail-title{font-size:1.4rem;font-weight:700;letter-spacing:-.03em}
.detail-controls{display:flex;align-items:center;gap:10px;flex-wrap:wrap}
.btn-close{width:34px;height:34px;border-radius:50%;background:rgba(0,0,0,.08);border:none;cursor:pointer;font-size:.9rem;color:rgba(0,0,0,.45);display:flex;align-items:center;justify-content:center;transition:background .2s}
.btn-close:hover{background:rgba(0,0,0,.14)}
.tabs{display:flex;gap:4px;background:rgba(0,0,0,.06);border-radius:12px;padding:4px}
.tab{padding:6px 18px;border-radius:9px;border:none;background:transparent;font-size:.82rem;font-weight:600;color:rgba(0,0,0,.42);cursor:pointer;transition:all .2s;font-family:inherit}
.tab.active{background:rgba(255,255,255,.9);color:rgba(0,0,0,.82);box-shadow:0 2px 8px rgba(0,0,0,.10)}
.toggle-wrap{display:flex;align-items:center;gap:8px;font-size:.82rem;color:rgba(0,0,0,.55)}
.toggle{position:relative;width:36px;height:20px;background:rgba(0,0,0,.15);border-radius:10px;cursor:pointer;transition:background .25s}
.toggle.on{background:#6366f1}
.toggle::after{content:'';position:absolute;top:2px;left:2px;width:16px;height:16px;background:white;border-radius:50%;transition:transform .25s cubic-bezier(.34,1.56,.64,1);box-shadow:0 1px 4px rgba(0,0,0,.2)}
.toggle.on::after{transform:translateX(16px)}
.detail-chart{min-height:300px;flex:1}
.detail-heatmap{margin-top:12px;flex-shrink:0}
.stats{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin-top:16px;flex-shrink:0}
.pill{background:rgba(0,0,0,.04);border-radius:14px;padding:12px 14px;text-align:center}
.pill-label{font-size:.68rem;color:rgba(0,0,0,.38);text-transform:uppercase;letter-spacing:.07em;margin-bottom:4px}
.pill-val{font-size:1.15rem;font-weight:700;letter-spacing:-.03em}

@media(max-width:768px){.bento{grid-template-columns:1fr 1fr}.card-steps{grid-column:1/3}.card-sleep{grid-column:1}.card-hr{grid-column:2}.card-explore{grid-column:1/3}.metric-val{font-size:2.2rem}}
@media(max-width:480px){.bento{grid-template-columns:1fr}.card-steps,.card-sleep,.card-hr,.card-explore{grid-column:1}}
</style>
</head>
<body>
<div id="bg"></div>
<div class="page">
  <header>
    <h1>健康洞察</h1>
    <p>你的身体，你的故事 · Apple Health 历史数据分析</p>
  </header>
  <div class="bento">

    <!-- Steps (wide) -->
    <div class="card glass card-steps" data-metric="steps"
         onmouseenter="hoverBg('steps')" onmouseleave="idleBg()" onclick="openDetail('steps')">
      <div class="card-head">
        <div class="card-icon icon-steps">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
            <path d="M8 17l3-8 3 3 2-5 2 5" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            <circle cx="15" cy="5" r="1.5" fill="white"/>
          </svg>
        </div>
        <span class="card-label">每日步数</span>
      </div>
      <div class="metric-val val-steps" id="val-steps">__STEPS_VAL__<span class="metric-unit">步</span></div>
      <div class="metric-sub" id="sub-steps">近 7 天平均</div>
      <div class="spark-wrap">
        <div class="sparkline" id="sp-steps"></div>
        <div class="scrub-overlay" id="scrub-steps"></div>
        <div class="scrub-line" id="line-steps"></div>
      </div>
      <div class="card-hint">点击查看详情 · 悬停图表查看当日数据</div>
    </div>

    <!-- Sleep -->
    <div class="card glass card-sleep" data-metric="sleep"
         onmouseenter="hoverBg('sleep')" onmouseleave="idleBg()" onclick="openDetail('sleep')">
      <div class="card-head">
        <div class="card-icon icon-sleep">
          <svg class="svg-moon" width="24" height="24" viewBox="0 0 24 24">
            <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" fill="white" opacity=".9"/>
            <circle cx="18" cy="5" r="1" fill="white" opacity=".6"/>
            <circle cx="20" cy="9" r=".6" fill="white" opacity=".4"/>
          </svg>
        </div>
        <span class="card-label">睡眠</span>
      </div>
      <div class="metric-val val-sleep" id="val-sleep">__SLEEP_VAL__<span class="metric-unit">h</span></div>
      <div class="metric-sub" id="sub-sleep">近 7 天平均</div>
      <div class="spark-wrap">
        <div class="sparkline" id="sp-sleep"></div>
        <div class="scrub-overlay" id="scrub-sleep"></div>
        <div class="scrub-line" id="line-sleep"></div>
      </div>
      <div class="card-hint">点击查看详情</div>
    </div>

    <!-- HR -->
    <div class="card glass card-hr" data-metric="hr"
         onmouseenter="hoverBg('hr')" onmouseleave="idleBg()" onclick="openDetail('hr')">
      <div class="card-head">
        <div class="card-icon icon-hr">
          <svg id="heart-svg" width="24" height="24" viewBox="0 0 24 24">
            <path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z" fill="white"/>
          </svg>
        </div>
        <span class="card-label">静息心率</span>
      </div>
      <div class="metric-val val-hr" id="val-hr">__HR_VAL__<span class="metric-unit">bpm</span></div>
      <div class="metric-sub" id="sub-hr">近 7 天平均</div>
      <div class="spark-wrap">
        <div class="sparkline" id="sp-hr"></div>
        <div class="scrub-overlay" id="scrub-hr"></div>
        <div class="scrub-line" id="line-hr"></div>
      </div>
      <div class="card-hint">点击查看详情</div>
    </div>

    <!-- Explore -->
    <div class="card glass card-explore" data-metric="explore"
         onmouseenter="hoverBg('explore')" onmouseleave="idleBg()" onclick="openDetail('explore')">
      <div class="card-head">
        <div class="card-icon icon-explore">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
            <circle cx="7" cy="16" r="2" fill="white" opacity=".7"/>
            <circle cx="11" cy="10" r="2" fill="white" opacity=".6"/>
            <circle cx="16" cy="13" r="2" fill="white" opacity=".8"/>
            <circle cx="19" cy="7" r="2" fill="white"/>
            <line x1="4" y1="19" x2="21" y2="4" stroke="white" stroke-width="1.5" stroke-dasharray="3,2" opacity=".45"/>
          </svg>
        </div>
        <span class="card-label">指标关联探索</span>
      </div>
      <div style="font-size:.9rem;color:rgba(0,0,0,.5);margin-top:8px;line-height:1.7">
        探索不同健康指标之间的关联关系<br>
        <span style="color:#3b82f6;font-weight:600">步数 × 睡眠 &nbsp;·&nbsp; 心率 × 步数</span><br>
        <span style="font-size:.78rem;color:rgba(0,0,0,.35)">含线性回归趋势线 · 异常点标记</span>
      </div>
      <div class="card-hint">点击打开关联分析</div>
    </div>

  </div>
</div>

<!-- Detail Panel -->
<div class="detail-panel" id="detail-panel">
  <div class="detail-bg" onclick="closeDetail()"></div>
  <div class="detail-card">
    <div class="detail-top">
      <div class="detail-title" id="detail-title"></div>
      <div class="detail-controls">
        <div class="toggle-wrap" id="wd-wrap" style="display:none">
          <span>工作日/周末</span>
          <div class="toggle" id="wd-toggle" onclick="toggleWD()"></div>
        </div>
        <div class="tabs" id="detail-tabs">
          <button class="tab" onclick="setTab('week',this)">周</button>
          <button class="tab active" onclick="setTab('month',this)">月</button>
          <button class="tab" onclick="setTab('year',this)">年</button>
        </div>
        <button class="btn-close" onclick="closeDetail()">✕</button>
      </div>
    </div>
    <div class="detail-chart" id="detail-chart"></div>
    <div class="detail-heatmap" id="detail-heatmap" style="display:none"></div>
    <div class="stats" id="detail-stats"></div>
  </div>
</div>

<script>
// ── Embedded data ──────────────────────────────────────────────────────────
const SLEEP_RAW  = __SLEEP_JSON__;
const HR_RAW     = __HR_JSON__;
const STEPS_RAW  = __STEPS_JSON__;

// Mock fallback (90-day if real data empty)
function genMock(n=365){
  const out={sleep:[],hr:[],steps:[]};
  const anchor=new Date('2026-04-16');
  for(let i=n;i>=1;i--){
    const d=new Date(anchor);d.setDate(d.getDate()-i);
    const ds=d.toISOString().slice(0,10);
    const we=d.getDay()===0||d.getDay()===6;
    out.sleep.push({date:ds,sleep_hours:+(5.5+Math.random()*3.5+(we?.8:0)).toFixed(2)});
    out.hr.push({date:ds,hr_min:Math.round(52+Math.random()*20)});
    out.steps.push({date:ds,steps:Math.round(we?(4000+Math.random()*12000):(5000+Math.random()*10000))});
  }
  return out;
}
const useMock=SLEEP_RAW.length<5||HR_RAW.length<5||STEPS_RAW.length<5;
const mock=useMock?genMock():null;

function parse(arr,key){
  if(!arr||!arr.length)return[];
  return arr.map(d=>({...d,_d:new Date(d[key])})).sort((a,b)=>a._d-b._d);
}
const SD=parse(useMock?mock.sleep:SLEEP_RAW,'date');
const HD=parse(useMock?mock.hr:HR_RAW,'date');
const TD=parse(useMock?mock.steps:STEPS_RAW,'date');

// ── Background ────────────────────────────────────────────────────────────
const BG={
  idle:  'linear-gradient(-45deg,#dbeafe,#ede9fe,#fce7f3,#d1fae5)',
  steps: 'linear-gradient(-45deg,#d1fae5,#a7f3d0,#fef9c3,#fde68a)',
  sleep: 'linear-gradient(-45deg,#1e1b4b,#312e81,#4c1d95,#1e1b4b)',
  hr:    'linear-gradient(-45deg,#fff1f2,#ffe4e6,#fecdd3,#fda4af)',
  explore:'linear-gradient(-45deg,#eff6ff,#dbeafe,#e0f2fe,#bae6fd)',
};
let bgT=null;
function setBg(k){
  const bg=document.getElementById('bg');
  bg.style.animation='none';
  bg.style.background=BG[k];
  bg.style.backgroundSize='400% 400%';
  document.querySelectorAll('.glass').forEach(el=>{
    el.style.background=k==='sleep'?'rgba(255,255,255,.70)':'';
  });
}
function hoverBg(k){clearTimeout(bgT);setBg(k);}
function idleBg(){bgT=setTimeout(()=>{
  const bg=document.getElementById('bg');
  bg.style.animation='bgIdle 18s ease infinite';
  bg.style.background=BG.idle;
  document.querySelectorAll('.glass').forEach(el=>el.style.background='');
},400);}

// ── Heart animation ───────────────────────────────────────────────────────
(function(){
  const last=HD.slice(-7);
  const bpm=last.length?last.reduce((s,d)=>s+d.hr_min,0)/last.length:65;
  const dur=(60/bpm).toFixed(2)+'s';
  document.getElementById('heart-svg').style.animation=`heartbeat ${dur} ease-in-out infinite`;
})();

// ── Helpers ───────────────────────────────────────────────────────────────
function rolling(vals,w=7){
  return vals.map((_,i)=>{
    const sl=vals.slice(Math.max(0,i-Math.floor(w/2)),i+Math.ceil(w/2)).filter(v=>v!=null);
    return sl.length?sl.reduce((a,b)=>a+b,0)/sl.length:null;
  });
}
function anomalies(vals){
  const v=vals.filter(x=>x!=null);
  if(!v.length)return{mean:0,std:0,flags:vals.map(()=>false)};
  const mean=v.reduce((a,b)=>a+b,0)/v.length;
  const std=Math.sqrt(v.map(x=>(x-mean)**2).reduce((a,b)=>a+b,0)/v.length);
  return{mean,std,flags:vals.map(x=>x!=null&&Math.abs(x-mean)>2*std)};
}
const ANCHOR=new Date('2026-04-16');
function filterP(data,period){
  const days={week:7,month:30,year:365}[period];
  const cut=new Date(ANCHOR-days*864e5);
  return data.filter(d=>d._d>=cut);
}
function monthGrp(data,key,agg='avg'){
  const g={};
  data.forEach(d=>{const m=d.date.slice(0,7);if(!g[m])g[m]=[];if(d[key]!=null)g[m].push(d[key]);});
  return Object.entries(g).sort().map(([m,vs])=>({
    month:m+'-15',
    val:agg==='sum'?vs.reduce((a,b)=>a+b,0):vs.reduce((a,b)=>a+b,0)/vs.length
  }));
}
const BASE_L={
  paper_bgcolor:'rgba(0,0,0,0)',plot_bgcolor:'rgba(0,0,0,0)',
  font:{family:'-apple-system,BlinkMacSystemFont,"SF Pro Display",sans-serif',size:12,color:'rgba(0,0,0,.5)'},
  margin:{t:10,b:44,l:52,r:16},
  xaxis:{gridcolor:'rgba(0,0,0,.05)',linecolor:'rgba(0,0,0,.08)',zeroline:false,tickcolor:'rgba(0,0,0,0)'},
  yaxis:{gridcolor:'rgba(0,0,0,.05)',linecolor:'rgba(0,0,0,.08)',zeroline:false,tickcolor:'rgba(0,0,0,0)'},
  showlegend:true,legend:{orientation:'h',y:-0.22,x:0,font:{size:11}},
  hovermode:'x unified',
};
const CFG={displayModeBar:false,responsive:true};

// ── Sparklines + Scrubbing ────────────────────────────────────────────────
function initSpark(spId,scrubId,lineId,valId,subId,data,key,color,fill,unit){
  const d30=data.filter(d=>d._d>=new Date(ANCHOR-30*864e5));
  if(!d30.length)return;
  const vals=d30.map(d=>d[key]),dates=d30.map(d=>d.date);
  Plotly.newPlot(spId,
    [{x:dates,y:vals,type:'scatter',mode:'lines',fill:'tozeroy',fillcolor:fill,
      line:{color,width:1.5,shape:'spline',smoothing:.8},hoverinfo:'none'}],
    {paper_bgcolor:'rgba(0,0,0,0)',plot_bgcolor:'rgba(0,0,0,0)',
     margin:{t:2,b:2,l:2,r:2},xaxis:{visible:false},yaxis:{visible:false},showlegend:false},
    {displayModeBar:false,responsive:true,staticPlot:true}
  );
  const overlay=document.getElementById(scrubId);
  const line=document.getElementById(lineId);
  const valEl=document.getElementById(valId);
  const subEl=document.getElementById(subId);
  const recent7=data.slice(-7);
  const avgVal=recent7.reduce((s,d)=>s+(d[key]||0),0)/Math.max(recent7.length,1);
  function fmt(v){
    return key==='steps'?Math.round(v).toLocaleString():
           key==='sleep_hours'?v.toFixed(1):Math.round(v);
  }
  overlay.addEventListener('mousemove',e=>{
    const r=overlay.getBoundingClientRect();
    const pct=(e.clientX-r.left)/r.width;
    const idx=Math.max(0,Math.min(d30.length-1,Math.round(pct*(d30.length-1))));
    line.style.left=(pct*100)+'%';line.style.opacity='1';
    valEl.innerHTML=`${fmt(d30[idx][key])}<span class="metric-unit">${unit}</span>`;
    subEl.textContent=d30[idx].date;
  });
  overlay.addEventListener('mouseleave',()=>{
    line.style.opacity='0';
    valEl.innerHTML=`${fmt(avgVal)}<span class="metric-unit">${unit}</span>`;
    subEl.textContent='近 7 天平均';
  });
}

// Update card values if using mock
if(useMock){
  const a7=(d,k)=>d.slice(-7).reduce((s,x)=>s+(x[k]||0),0)/Math.max(d.slice(-7).length,1);
  document.getElementById('val-steps').innerHTML=Math.round(a7(TD,'steps')).toLocaleString()+'<span class="metric-unit">步</span>';
  document.getElementById('val-sleep').innerHTML=a7(SD,'sleep_hours').toFixed(1)+'<span class="metric-unit">h</span>';
  document.getElementById('val-hr').innerHTML=Math.round(a7(HD,'hr_min'))+'<span class="metric-unit">bpm</span>';
}

initSpark('sp-steps','scrub-steps','line-steps','val-steps','sub-steps',TD,'steps','#059669','rgba(5,150,105,.15)','步');
initSpark('sp-sleep','scrub-sleep','line-sleep','val-sleep','sub-sleep',SD,'sleep_hours','#7c3aed','rgba(124,58,237,.15)','h');
initSpark('sp-hr','scrub-hr','line-hr','val-hr','sub-hr',HD,'hr_min','#e11d48','rgba(225,29,72,.15)','bpm');

// ── Detail panel ──────────────────────────────────────────────────────────
let CUR='steps',PERIOD='month',WD_ON=false;

function pills(items){
  document.getElementById('detail-stats').innerHTML=items.map(p=>
    `<div class="pill"><div class="pill-label">${p.l}</div><div class="pill-val" style="color:${p.c}">${p.v}</div></div>`
  ).join('');
}

function openDetail(m){
  CUR=m;PERIOD='month';WD_ON=false;
  document.getElementById('wd-toggle').classList.remove('on');
  document.getElementById('detail-title').textContent=
    {steps:'🏃  每日步数',sleep:'🌙  睡眠分析',hr:'♥  静息心率',explore:'🔍  指标关联探索'}[m];
  document.getElementById('wd-wrap').style.display=(m==='explore')?'none':'flex';
  document.getElementById('detail-tabs').style.display=(m==='explore')?'none':'flex';
  document.querySelectorAll('.tab').forEach((t,i)=>t.classList.toggle('active',i===1));
  document.getElementById('detail-panel').classList.add('open');
  document.body.style.overflow='hidden';
  hoverBg(m);
  render();
}
function closeDetail(){
  document.getElementById('detail-panel').classList.remove('open');
  document.body.style.overflow='';
  idleBg();
}
document.addEventListener('keydown',e=>{if(e.key==='Escape')closeDetail();});
function setTab(p,btn){
  PERIOD=p;
  document.querySelectorAll('.tab').forEach(t=>t.classList.remove('active'));
  btn.classList.add('active');
  render();
}
function toggleWD(){WD_ON=!WD_ON;document.getElementById('wd-toggle').classList.toggle('on',WD_ON);render();}

function render(){
  const div=document.getElementById('detail-chart');
  const hDiv=document.getElementById('detail-heatmap');
  hDiv.style.display='none';hDiv.innerHTML='';
  if(CUR==='steps')  renderSteps(div,PERIOD);
  if(CUR==='sleep')  renderSleep(div,PERIOD);
  if(CUR==='hr')     renderHR(div,PERIOD);
  if(CUR==='explore')renderExplore(div);
}

// ── Steps chart ───────────────────────────────────────────────────────────
function renderSteps(div,period){
  const data=filterP(TD,period);
  if(!data.length){div.innerHTML='<p style="padding:60px;text-align:center;color:#bbb">暂无数据</p>';return;}
  let traces=[],layout={...BASE_L};
  if(period==='year'){
    const mg=monthGrp(data,'steps','sum');
    traces=[{x:mg.map(d=>d.month),y:mg.map(d=>Math.round(d.val)),type:'bar',name:'月总步数',
      marker:{color:'rgba(5,150,105,.65)',line:{width:0}},hovertemplate:'%{x|%Y年%m月}<br>%{y:,} 步<extra></extra>'}];
  } else {
    const dates=data.map(d=>d.date),vals=data.map(d=>d.steps);
    const avg=rolling(vals),anom=anomalies(vals);
    const colors=vals.map((v,i)=>anom.flags[i]?'rgba(239,68,68,.9)':v>=10000?'rgba(5,150,105,.7)':'rgba(225,29,72,.65)');
    traces=[
      {x:dates,y:vals,type:'bar',name:'每日步数',marker:{color:colors,line:{width:0}},hovertemplate:'%{x}<br>%{y:,} 步<extra></extra>'},
      {x:dates,y:avg.map(v=>v?Math.round(v):null),type:'scatter',mode:'lines',name:'7日均值',
       line:{color:'#059669',width:2.5,shape:'spline',smoothing:.8},hovertemplate:'均值 %{y:,} 步<extra></extra>'},
    ];
    layout.shapes=[{type:'line',x0:dates[0],x1:dates[dates.length-1],y0:10000,y1:10000,
      line:{color:'rgba(0,0,0,.18)',dash:'dash',width:1}}];
  }
  layout.yaxis={...BASE_L.yaxis,title:'步数',tickformat:',',rangemode:'tozero'};
  Plotly.react(div,traces,layout,CFG);
  // Heatmap
  const hDiv=document.getElementById('detail-heatmap');
  hDiv.style.display='block';
  drawHeatmap(hDiv,TD,'steps');
  const vs=data.map(d=>d.steps).filter(v=>v);
  pills([
    {l:'日均',v:Math.round(vs.reduce((a,b)=>a+b,0)/vs.length).toLocaleString()+' 步',c:'#059669'},
    {l:'最多',v:Math.max(...vs).toLocaleString()+' 步',c:'#059669'},
    {l:'达标天数',v:vs.filter(v=>v>=10000).length+' / '+vs.length,c:'#059669'},
  ]);
}

// ── Sleep chart ───────────────────────────────────────────────────────────
function renderSleep(div,period){
  const data=filterP(SD,period);
  if(!data.length){div.innerHTML='<p style="padding:60px;text-align:center;color:#bbb">暂无数据</p>';return;}
  const C='#7c3aed';let traces=[],layout={...BASE_L};
  if(period==='year'){
    const mg=monthGrp(data,'sleep_hours','avg');
    traces=[{x:mg.map(d=>d.month),y:mg.map(d=>+d.val.toFixed(2)),type:'bar',name:'月均睡眠',
      marker:{color:'rgba(167,139,250,.6)',line:{width:0}},hovertemplate:'%{x|%Y年%m月}<br>%{y:.1f} h<extra></extra>'}];
  } else {
    const dates=data.map(d=>d.date),vals=data.map(d=>d.sleep_hours);
    const avg=rolling(vals),anom=anomalies(vals);
    if(WD_ON){
      const wdD=[],weD=[],wdV=[],weV=[];
      data.forEach(d=>{const day=d._d.getDay();if(day===0||day===6){weD.push(d.date);weV.push(d.sleep_hours);}else{wdD.push(d.date);wdV.push(d.sleep_hours);}});
      traces=[
        {x:wdD,y:wdV,type:'bar',name:'工作日',marker:{color:'rgba(124,58,237,.6)',line:{width:0}},hovertemplate:'工作日 %{x}<br>%{y:.1f} h<extra></extra>'},
        {x:weD,y:weV,type:'bar',name:'周末',marker:{color:'rgba(236,72,153,.65)',line:{width:0}},hovertemplate:'周末 %{x}<br>%{y:.1f} h<extra></extra>'},
      ];
    } else {
      const aX=[],aY=[];
      data.forEach((d,i)=>{if(anom.flags[i]){aX.push(d.date);aY.push(vals[i]);}});
      traces=[
        {x:dates,y:vals.map(v=>+v.toFixed(2)),type:'bar',name:'每日睡眠',marker:{color:'rgba(167,139,250,.5)',line:{width:0}},hovertemplate:'%{x}<br>%{y:.1f} h<extra></extra>'},
        {x:dates,y:avg.map(v=>v?+v.toFixed(2):null),type:'scatter',mode:'lines',name:'7日均值',line:{color:C,width:2.5,shape:'spline',smoothing:.8},hovertemplate:'均值 %{y:.1f} h<extra></extra>'},
      ];
      if(aX.length) traces.push({x:aX,y:aY,type:'scatter',mode:'markers',name:'异常',marker:{color:'#ef4444',size:10,symbol:'diamond',line:{color:'white',width:1}},hovertemplate:'⚠ 异常: %{y:.1f} h<extra></extra>'});
    }
    layout.shapes=[{type:'line',x0:dates[0],x1:dates[dates.length-1],y0:7,y1:7,line:{color:'rgba(0,0,0,.18)',dash:'dash',width:1}}];
  }
  layout.yaxis={...BASE_L.yaxis,title:'小时',rangemode:'tozero'};
  Plotly.react(div,traces,layout,CFG);
  const vs=data.map(d=>d.sleep_hours).filter(v=>v);
  pills([
    {l:'平均',v:(vs.reduce((a,b)=>a+b,0)/vs.length).toFixed(1)+' h',c:C},
    {l:'最佳',v:Math.max(...vs).toFixed(1)+' h',c:'#059669'},
    {l:'达标天数',v:vs.filter(v=>v>=7).length+' / '+vs.length,c:C},
  ]);
}

// ── HR chart ──────────────────────────────────────────────────────────────
function renderHR(div,period){
  const data=filterP(HD,period);
  if(!data.length){div.innerHTML='<p style="padding:60px;text-align:center;color:#bbb">暂无数据</p>';return;}
  const C='#e11d48';let traces=[],layout={...BASE_L};
  if(period==='year'){
    const mg=monthGrp(data,'hr_min','avg');
    traces=[{x:mg.map(d=>d.month),y:mg.map(d=>Math.round(d.val)),type:'scatter',mode:'lines+markers',name:'月均心率',
      line:{color:C,width:2.5,shape:'spline'},marker:{color:C,size:6},hovertemplate:'%{x|%Y年%m月}<br>%{y} bpm<extra></extra>'}];
  } else {
    const dates=data.map(d=>d.date),vals=data.map(d=>d.hr_min);
    const avg=rolling(vals),anom=anomalies(vals);
    if(WD_ON){
      const wdD=[],weD=[],wdV=[],weV=[];
      data.forEach(d=>{const day=d._d.getDay();if(day===0||day===6){weD.push(d.date);weV.push(d.hr_min);}else{wdD.push(d.date);wdV.push(d.hr_min);}});
      traces=[
        {x:wdD,y:wdV,type:'scatter',mode:'markers',name:'工作日',marker:{color:'rgba(225,29,72,.5)',size:5},hovertemplate:'工作日 %{x}<br>%{y} bpm<extra></extra>'},
        {x:weD,y:weV,type:'scatter',mode:'markers',name:'周末',marker:{color:'rgba(245,158,11,.7)',size:5},hovertemplate:'周末 %{x}<br>%{y} bpm<extra></extra>'},
      ];
    } else {
      const aX=[],aY=[],aText=[];
      data.forEach((d,i)=>{
        if(anom.flags[i]){
          aX.push(d.date);aY.push(vals[i]);
          const st=TD.find(t=>t.date===d.date),sl=SD.find(s=>s.date===d.date);
          let tip=`⚠ 心率异常: ${vals[i]} bpm`;
          if(sl&&sl.sleep_hours<5)tip+=`<br>睡眠不足 ${sl.sleep_hours.toFixed(1)} h`;
          if(st&&st.steps<5000)tip+=`<br>步数偏少 ${st.steps.toLocaleString()} 步`;
          aText.push(tip);
        }
      });
      traces=[
        {x:dates,y:vals,type:'scatter',mode:'none',fill:'tozeroy',fillcolor:'rgba(225,29,72,.09)',hoverinfo:'skip',showlegend:false},
        {x:dates,y:vals,type:'scatter',mode:'markers',name:'每日最低',marker:{color:'rgba(225,29,72,.45)',size:4},hovertemplate:'%{x}<br>%{y} bpm<extra></extra>'},
        {x:dates,y:avg.map(v=>v?Math.round(v):null),type:'scatter',mode:'lines',name:'7日均值',line:{color:C,width:2.5,shape:'spline',smoothing:.8},hovertemplate:'均值 %{y} bpm<extra></extra>'},
      ];
      if(aX.length) traces.push({x:aX,y:aY,type:'scatter',mode:'markers',name:'异常',marker:{color:'#ef4444',size:12,symbol:'diamond',line:{color:'white',width:1}},text:aText,hovertemplate:'%{text}<extra></extra>'});
    }
  }
  layout.yaxis={...BASE_L.yaxis,title:'bpm'};
  Plotly.react(div,traces,layout,CFG);
  const vs=data.map(d=>d.hr_min).filter(v=>v);
  pills([
    {l:'平均',v:Math.round(vs.reduce((a,b)=>a+b,0)/vs.length)+' bpm',c:C},
    {l:'最低',v:Math.min(...vs)+' bpm',c:'#059669'},
    {l:'最高',v:Math.max(...vs)+' bpm',c:C},
  ]);
}

// ── GitHub Heatmap (SVG) ──────────────────────────────────────────────────
function drawHeatmap(container,data,key){
  container.innerHTML='<div style="font-size:.75rem;color:rgba(0,0,0,.4);margin-bottom:6px;font-weight:600">活跃热力图 · 过去 12 个月 &nbsp;<span style="color:#6366f1;font-size:.7rem">■ 今天 2026-04-16</span></div>';
  const lookup={};data.forEach(d=>{lookup[d.date]=d[key]||0;});
  const maxVal=Math.max(...Object.values(lookup),1);
  const cs=13,gap=3,NS=['日','一','二','三','四','五','六'],MS=['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
  // Build weeks
  const start=new Date(ANCHOR);start.setFullYear(start.getFullYear()-1);
  while(start.getDay()!==0)start.setDate(start.getDate()-1);
  const weeks=[];let cur=new Date(start);
  while(cur<=ANCHOR||weeks.length<53){
    const wk=[];for(let i=0;i<7;i++){wk.push(new Date(cur));cur.setDate(cur.getDate()+1);}
    weeks.push(wk);if(weeks.length>=53)break;
  }
  const W=weeks.length*(cs+gap)+38,H=7*(cs+gap)+46;
  const svg=document.createElementNS('http://www.w3.org/2000/svg','svg');
  svg.setAttribute('width',W);svg.setAttribute('height',H);svg.setAttribute('viewBox',`0 0 ${W} ${H}`);
  // Month labels
  let pm=-1;
  weeks.forEach((wk,wi)=>{const m=wk[0].getMonth();if(m!==pm){pm=m;const t=document.createElementNS('http://www.w3.org/2000/svg','text');t.setAttribute('x',36+wi*(cs+gap));t.setAttribute('y',10);t.setAttribute('font-size','9');t.setAttribute('fill','rgba(0,0,0,.4)');t.textContent=MS[m];svg.appendChild(t);}});
  // Day labels
  [1,3,5].forEach(i=>{const t=document.createElementNS('http://www.w3.org/2000/svg','text');t.setAttribute('x',2);t.setAttribute('y',14+i*(cs+gap)+cs*.7);t.setAttribute('font-size','8');t.setAttribute('fill','rgba(0,0,0,.35)');t.textContent=NS[i];svg.appendChild(t);});
  // Cells
  weeks.forEach((wk,wi)=>{
    wk.forEach((day,di)=>{
      const ds=day.toISOString().slice(0,10);
      const val=lookup[ds]||0,pct=val/maxVal;
      const isToday=ds==='2026-04-16',isFuture=day>ANCHOR;
      const color=isFuture?'rgba(0,0,0,.04)':key==='steps'?`rgba(5,150,105,${.08+pct*.85})`:`rgba(124,58,237,${.08+pct*.85})`;
      const r=document.createElementNS('http://www.w3.org/2000/svg','rect');
      r.setAttribute('x',36+wi*(cs+gap));r.setAttribute('y',14+di*(cs+gap));
      r.setAttribute('width',cs);r.setAttribute('height',cs);r.setAttribute('rx',3);r.setAttribute('fill',color);
      if(isToday){r.setAttribute('stroke','#6366f1');r.setAttribute('stroke-width','2');}
      const title=document.createElementNS('http://www.w3.org/2000/svg','title');
      title.textContent=ds+(isFuture?' (未来)':val?'\n'+Math.round(val).toLocaleString()+(key==='steps'?' 步':' h'):'\n无数据');
      r.appendChild(title);svg.appendChild(r);
      if(isToday){const t=document.createElementNS('http://www.w3.org/2000/svg','text');t.setAttribute('x',36+wi*(cs+gap)+cs/2);t.setAttribute('y',14+di*(cs+gap)-2);t.setAttribute('font-size','7');t.setAttribute('fill','#6366f1');t.setAttribute('text-anchor','middle');t.setAttribute('font-weight','700');t.textContent='今';svg.appendChild(t);}
    });
  });
  // Legend
  const ly=H-16;
  const ll=document.createElementNS('http://www.w3.org/2000/svg','text');ll.setAttribute('x',36);ll.setAttribute('y',ly+9);ll.setAttribute('font-size','8');ll.setAttribute('fill','rgba(0,0,0,.35)');ll.textContent='少';svg.appendChild(ll);
  [0,.25,.5,.75,1].forEach((p,i)=>{const r=document.createElementNS('http://www.w3.org/2000/svg','rect');r.setAttribute('x',52+i*16);r.setAttribute('y',ly);r.setAttribute('width',12);r.setAttribute('height',12);r.setAttribute('rx',2);r.setAttribute('fill',key==='steps'?`rgba(5,150,105,${.08+p*.85})`:`rgba(124,58,237,${.08+p*.85})`);svg.appendChild(r);});
  const ll2=document.createElementNS('http://www.w3.org/2000/svg','text');ll2.setAttribute('x',136);ll2.setAttribute('y',ly+9);ll2.setAttribute('font-size','8');ll2.setAttribute('fill','rgba(0,0,0,.35)');ll2.textContent='多';svg.appendChild(ll2);
  const wrap=document.createElement('div');wrap.style.overflowX='auto';wrap.appendChild(svg);container.appendChild(wrap);
}

// ── Correlation + Regression ──────────────────────────────────────────────
function renderExplore(div){
  div.innerHTML=`
    <div style="display:flex;align-items:center;gap:12px;margin-bottom:16px;flex-wrap:wrap">
      <span style="font-size:.85rem;color:rgba(0,0,0,.5)">X 轴</span>
      <select id="xa" onchange="updCorr()" style="padding:7px 12px;border-radius:10px;border:1px solid rgba(0,0,0,.12);background:rgba(255,255,255,.85);font-family:inherit;font-size:.85rem">
        <option value="steps">每日步数</option><option value="sleep">睡眠时长</option><option value="hr">静息心率</option>
      </select>
      <span style="font-size:.85rem;color:rgba(0,0,0,.5)">Y 轴</span>
      <select id="ya" onchange="updCorr()" style="padding:7px 12px;border-radius:10px;border:1px solid rgba(0,0,0,.12);background:rgba(255,255,255,.85);font-family:inherit;font-size:.85rem">
        <option value="sleep">睡眠时长</option><option value="steps">每日步数</option><option value="hr">静息心率</option>
      </select>
    </div>
    <div id="corr-plot" style="height:300px"></div>
    <div id="corr-note" style="font-size:.8rem;color:rgba(0,0,0,.4);margin-top:8px;text-align:center"></div>
  `;
  document.getElementById('detail-stats').innerHTML='';
  updCorr();
}
function getMD(m){
  if(m==='steps')return TD.map(d=>({date:d.date,v:d.steps}));
  if(m==='sleep')return SD.map(d=>({date:d.date,v:d.sleep_hours}));
  if(m==='hr')   return HD.map(d=>({date:d.date,v:d.hr_min}));
  return[];
}
function mLabel(m){return{steps:'步数（步）',sleep:'睡眠（小时）',hr:'心率（bpm）'}[m];}
function linReg(xs,ys){
  const n=xs.length;if(n<2)return null;
  const mx=xs.reduce((a,b)=>a+b)/n,my=ys.reduce((a,b)=>a+b)/n;
  let num=0,den=0;
  for(let i=0;i<n;i++){num+=(xs[i]-mx)*(ys[i]-my);den+=(xs[i]-mx)**2;}
  if(!den)return null;
  const m=num/den,b=my-m*mx;
  const ss_res=ys.reduce((s,y,i)=>s+(y-(m*xs[i]+b))**2,0);
  const ss_tot=ys.reduce((s,y)=>s+(y-my)**2,0);
  const r2=1-ss_res/Math.max(ss_tot,1e-9);
  return{m,b,xMin:Math.min(...xs),xMax:Math.max(...xs),r2};
}
function updCorr(){
  const xa=document.getElementById('xa')?.value||'steps';
  const ya=document.getElementById('ya')?.value||'sleep';
  const div=document.getElementById('corr-plot');if(!div)return;
  const xd=getMD(xa),yd=getMD(ya);
  const pts=[];xd.forEach(x=>{const y=yd.find(y=>y.date===x.date);if(y&&x.v!=null&&y.v!=null)pts.push({date:x.date,x:x.v,y:y.v});});
  if(pts.length<3){div.innerHTML='<p style="padding:60px;text-align:center;color:#bbb">数据不足</p>';return;}
  const xs=pts.map(p=>p.x),ys=pts.map(p=>p.y);
  const reg=linReg(xs,ys);
  const anom=anomalies(ys);
  const colors=pts.map((_,i)=>anom.flags[i]?'rgba(239,68,68,.85)':'rgba(99,102,241,.55)');
  const traces=[{x:xs,y:ys,mode:'markers',type:'scatter',name:'每日数据',text:pts.map(p=>p.date),
    marker:{color:colors,size:7,line:{color:colors.map(c=>c.includes('239')?'rgba(239,68,68,1)':'rgba(99,102,241,.9)'),width:1}},
    hovertemplate:'%{text}<br>X: %{x}<br>Y: %{y}<extra></extra>'}];
  if(reg){
    traces.push({x:[reg.xMin,reg.xMax],y:[reg.m*reg.xMin+reg.b,reg.m*reg.xMax+reg.b],
      mode:'lines',name:'趋势线',line:{color:'#6366f1',width:2,dash:'dot'},hoverinfo:'skip'});
    document.getElementById('corr-note').textContent=`R² = ${reg.r2.toFixed(3)}  ·  斜率 ${reg.m>0?'+':''}${reg.m.toFixed(4)}  ·  ${Math.abs(reg.r2)>0.3?'存在相关性':'相关性较弱'}  ·  红色标记为异常点(±2σ)`;
  }
  const layout={...BASE_L,xaxis:{...BASE_L.xaxis,title:mLabel(xa)},yaxis:{...BASE_L.yaxis,title:mLabel(ya)},margin:{...BASE_L.margin,b:60,l:60}};
  Plotly.react(div,traces,layout,CFG);
}
</script>
</body>
</html>"""

def build_html(sleep_df, hr_df, steps_df):
    s = _avg7(sleep_df, "sleep_hours")
    h = _avg7(hr_df,    "hr_min")
    t = _avg7(steps_df, "steps")
    return (
        _HTML
        .replace("__SLEEP_JSON__", json.dumps(_to_records(sleep_df)))
        .replace("__HR_JSON__",    json.dumps(_to_records(hr_df)))
        .replace("__STEPS_JSON__", json.dumps(_to_records(steps_df)))
        .replace("__SLEEP_VAL__",  f"{s:.1f}" if s else "—")
        .replace("__HR_VAL__",     f"{int(h)}" if h else "—")
        .replace("__STEPS_VAL__",  f"{int(t):,}" if t else "—")
    )

def main():
    print("Parsing Apple Health data …")
    sleep_df = load_sleep("data/export.xml")
    hr_df    = load_heart_rate("data/export.xml")
    steps_df = load_steps("data/export.xml")
    print(f"  Sleep {len(sleep_df)}d  HR {len(hr_df)}d  Steps {len(steps_df)}d")
    print("Building dashboard …")
    Path(OUTPUT_PATH).write_text(build_html(sleep_df, hr_df, steps_df), encoding="utf-8")
    print(f"  Saved → {OUTPUT_PATH}\nOpen dashboard.html in your browser.")

if __name__ == "__main__":
    main()
