"""Local web dashboard for scanned contact analysis.

Serves a single-page UI via Python's stdlib http.server and reads the
contacts.json produced by the extractor. No third-party dependencies.
"""
from __future__ import annotations

import csv
import io
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

_STATE_DIR = os.environ.get(
    "MYWA_STATE", os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "state")
)
ROADMAP_PATH = os.path.join(_STATE_DIR, "roadmap.json")

_DEFAULT_ROADMAP = {
    "goal": "Become agentic: export -> analyze -> engage -> learn",
    "phases": [
        {"name": "Phase 1 - Foundation", "state": "complete", "items": []},
        {"name": "Phase 2 - Automation", "state": "active", "items": []},
        {"name": "Phase 3 - Agentic", "state": "next", "items": []},
    ],
}


def load_roadmap() -> dict:
    try:
        with open(ROADMAP_PATH, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        if isinstance(data, dict) and data.get("phases"):
            return data
    except (OSError, json.JSONDecodeError):
        pass
    return _DEFAULT_ROADMAP


def save_roadmap(data: dict) -> dict:
    os.makedirs(_STATE_DIR, exist_ok=True)
    try:
        with open(ROADMAP_PATH, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2, ensure_ascii=False)
    except OSError:
        pass
    return data


def update_roadmap(payload: dict) -> dict:
    data = load_roadmap()
    mid, status = str(payload.get("id") or ""), str(payload.get("status") or "")
    if mid and status in ("done", "in_progress", "planned"):
        for phase in data.get("phases", []):
            for item in phase.get("items", []):
                if item.get("id") == mid:
                    item["status"] = status
                    return save_roadmap(data)
    return data

_INDEX_HTML = r"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>mywa Dashboard</title>
<link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 16 16'><rect width='16' height='16' rx='3' fill='%23075E54'/><text x='8' y='12' font-size='10' fill='white' text-anchor='middle' font-family='Arial' font-weight='bold'>m</text></svg>">
<style>
:root{
  --green:#075E54;--teal:#128C7E;--deep:#064a43;
  --ink:#0f172a;--mut:#64748b;--bg:#f3f5f8;--card:#ffffff;--line:#e7eaf0;
  --sh-sm:0 1px 2px rgba(15,23,42,.05);
  --sh-md:0 6px 18px rgba(15,23,42,.06),0 1px 2px rgba(15,23,42,.04);
  --rad:14px;
}
*{box-sizing:border-box}
html,body{margin:0}
body{font-family:'Inter','Segoe UI',system-ui,-apple-system,Arial,sans-serif;color:var(--ink);
  background:radial-gradient(1200px 600px at 88% -10%,rgba(18,140,126,.10),transparent 60%),
             radial-gradient(900px 500px at -10% 0%,rgba(7,94,84,.08),transparent 55%),var(--bg);
  min-height:100vh;-webkit-font-smoothing:antialiased}
header{position:relative;overflow:hidden;background:linear-gradient(120deg,#053f39,#075E54 46%,#128C7E);color:#fff;padding:1.3rem 1.6rem}
header::after{content:'';position:absolute;inset:0;background:radial-gradient(640px 220px at 92% -20%,rgba(255,255,255,.18),transparent 60%);pointer-events:none}
.brand{position:relative;z-index:1;display:flex;align-items:center;gap:.9rem;flex-wrap:wrap}
.logo{width:42px;height:42px;border-radius:12px;background:rgba(255,255,255,.14);border:1px solid rgba(255,255,255,.28);display:grid;place-items:center;font-weight:800;font-size:1.2rem;backdrop-filter:blur(4px)}
.brand h1{margin:0;font-size:1.28rem;font-weight:750;letter-spacing:-.01em}
.brand p{margin:.08rem 0 0;opacity:.88;font-size:.8rem}
.pill{display:inline-flex;align-items:center;gap:.35rem;border:1px solid rgba(255,255,255,.32);border-radius:999px;padding:.2rem .68rem;font-size:.66rem;font-weight:800;letter-spacing:.09em;text-transform:uppercase;color:#fff;background:rgba(255,255,255,.12)}
.brand-right{margin-left:auto;display:flex;align-items:center;gap:.65rem;flex-wrap:wrap}
.live{display:inline-flex;align-items:center;gap:.45rem;color:#d9f99d;font-size:.75rem;font-weight:650}
.live i{width:8px;height:8px;border-radius:50%;background:#a3e635;animation:pulse 2s infinite}
@keyframes pulse{0%{box-shadow:0 0 0 0 rgba(163,230,53,.55)}70%{box-shadow:0 0 0 9px rgba(163,230,53,0)}100%{box-shadow:0 0 0 0 rgba(163,230,53,0)}}
.wrap{max-width:1280px;margin:1.4rem auto;padding:0 1.4rem}
.tabs{display:inline-flex;gap:4px;background:var(--card);border:1px solid var(--line);padding:4px;border-radius:12px;box-shadow:var(--sh-sm);margin-bottom:1.2rem}
.tabbtn{border:none;background:transparent;border-radius:9px;padding:.5rem 1.1rem;font-size:.85rem;font-weight:650;cursor:pointer;color:var(--mut);transition:all .18s ease}
.tabbtn:hover{color:var(--green)}
.tabbtn.active{background:var(--green);color:#fff;box-shadow:var(--sh-sm)}
.bar{background:#e5e9ef;border-radius:999px;height:.6rem;overflow:hidden;margin:.5rem 0 1rem}
.fill{height:100%;background:linear-gradient(90deg,var(--green),var(--teal));transition:width .35s ease}
.rm-item{display:flex;gap:.9rem;align-items:flex-start;padding:.8rem .2rem;border-bottom:1px solid var(--line)}
.rm-item:last-child{border-bottom:none}
.rm-item h4{margin:0;font-size:.9rem}
.rm-item p{margin:.16rem 0 0;font-size:.78rem;color:var(--mut)}
.st{display:inline-block;border-radius:999px;padding:.26rem .7rem;font-size:.72rem;font-weight:700;cursor:pointer;border:none;color:#fff;min-width:92px;text-align:center;transition:transform .12s ease,filter .12s ease}
.st:hover{transform:translateY(-1px);filter:brightness(1.06)}
.st.done{background:#059669}.st.in_progress{background:#d97706}.st.planned{background:#94a3b8}
.rm-phase{margin-bottom:.4rem}
.rm-phase>h3{color:var(--green);font-size:.95rem;margin:.7rem 0 .1rem}
.chartgrid{display:grid;grid-template-columns:repeat(auto-fit,minmax(250px,1fr));gap:.9rem;margin-bottom:1rem}
.panel{background:var(--card);border:1px solid var(--line);border-radius:var(--rad);padding:1rem 1.1rem;box-shadow:var(--sh-md)}
.panel h3{margin:0 0 .55rem;font-size:.86rem;color:var(--green);letter-spacing:.02em}
.panel svg{display:block;margin:0 auto}
.leg{display:flex;flex-wrap:wrap;gap:.4rem .8rem;margin-top:.6rem;font-size:.72rem;color:var(--mut)}
.leg i{display:inline-block;width:.6rem;height:.6rem;border-radius:3px;margin-right:.3rem;vertical-align:middle}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(158px,1fr));gap:.9rem;margin-bottom:1rem}
.card{background:var(--card);border:1px solid var(--line);border-radius:var(--rad);padding:1rem 1.1rem;box-shadow:var(--sh-sm);position:relative;overflow:hidden;transition:transform .15s ease,box-shadow .15s ease}
.card:hover{transform:translateY(-2px);box-shadow:var(--sh-md)}
.card::before{content:'';position:absolute;top:0;left:0;right:0;height:3px;background:linear-gradient(90deg,var(--green),var(--teal))}
.card .n{font-size:1.75rem;font-weight:800;color:var(--green);letter-spacing:-.02em}
.card .l{font-size:.7rem;text-transform:uppercase;letter-spacing:.07em;color:var(--mut);font-weight:600;margin-top:.15rem}
.tags{margin-bottom:.9rem;display:flex;flex-wrap:wrap;gap:.45rem}
.tag{background:#e9f4f1;color:var(--green);border-radius:999px;padding:.28rem .78rem;font-size:.78rem;cursor:pointer;border:1px solid transparent;user-select:none;font-weight:600;transition:all .15s ease}
.tag:hover{border-color:var(--teal)}
.tag.on{background:var(--green);color:#fff}
.controls{display:flex;flex-wrap:wrap;gap:.65rem;align-items:flex-end;background:var(--card);border:1px solid var(--line);padding:.85rem .95rem;border-radius:var(--rad);box-shadow:var(--sh-sm);margin-bottom:1rem}
.search{position:relative;flex:1;min-width:210px}
.search svg{position:absolute;left:.7rem;top:50%;transform:translateY(-50%);width:15px;height:15px;stroke:var(--mut);pointer-events:none}
.controls input[type=search]{width:100%;padding:.55rem .75rem .55rem 2rem;border:1px solid var(--line);border-radius:10px;font-size:.9rem;outline:none;transition:border-color .15s ease,box-shadow .15s ease;background:#fafbfc}
.controls input[type=search]:focus{border-color:var(--teal);box-shadow:0 0 0 3px rgba(18,140,126,.14);background:#fff}
.control{display:flex;flex-direction:column;font-size:.7rem;color:var(--mut);font-weight:600;letter-spacing:.02em}
.control select{padding:.5rem .6rem;border:1px solid var(--line);border-radius:10px;font-size:.85rem;background:#fafbfc;color:var(--ink);outline:none;cursor:pointer;transition:border-color .15s ease}
.control select:focus{border-color:var(--teal);box-shadow:0 0 0 3px rgba(18,140,126,.12)}
.controls .spacer{flex:1}
.btn{border:none;border-radius:10px;padding:.55rem .95rem;cursor:pointer;font-size:.84rem;font-weight:700;background:linear-gradient(120deg,var(--green),var(--teal));color:#fff;box-shadow:var(--sh-sm);transition:transform .12s ease,box-shadow .12s ease}
.btn:hover{transform:translateY(-1px);box-shadow:var(--sh-md)}
.btn.ghost{background:#fff;color:var(--teal);border:1px solid var(--teal);box-shadow:none}
.btn.ghost:hover{background:#eefaf8}
.btn.active{background:var(--green)}
.tablewrap{background:var(--card);border:1px solid var(--line);border-radius:var(--rad);box-shadow:var(--sh-md);overflow:hidden}
table{width:100%;border-collapse:collapse;font-size:.85rem}
th,td{padding:.68rem .9rem;text-align:left;border-bottom:1px solid var(--line);white-space:nowrap}
th{background:#0b5e52;color:#fff;position:sticky;top:0;font-size:.7rem;text-transform:uppercase;letter-spacing:.06em;font-weight:700}
tbody tr:nth-child(even){background:#fafbfc}
tbody tr:hover td{background:#edf7f4}
tbody tr{transition:background .12s ease}
.badge{display:inline-block;border-radius:999px;padding:.2rem .62rem;font-size:.72rem;font-weight:700}
.hot{background:#fee2e2;color:#b91c1c}.warm{background:#fef3c7;color:#b45309}.recent{background:#dbeafe;color:#1d4ed8}.cold{background:#eef2f6;color:#64748b}
.business{background:#ede9fe;color:#6d28d9}.admin{background:#dbeafe;color:#1e40af}.saved{background:#d1fae5;color:#047857}.dia{background:#fce7f3;color:#be185d}
.mut{color:var(--mut);font-size:.8rem}
.groups{background:var(--card);border:1px solid var(--line);border-radius:var(--rad);padding:1rem 1.1rem;margin-top:1rem;box-shadow:var(--sh-sm)}
.groups h3{margin:0 0 .6rem;font-size:.95rem;color:var(--green)}
.glist{display:flex;flex-wrap:wrap;gap:.5rem}
.gpill{background:#f3f7f6;border:1px solid var(--line);border-radius:9px;padding:.34rem .8rem;font-size:.8rem;font-weight:500}
.gpill b{color:var(--green)}
.footer{margin:1.2rem 0 2.2rem;color:var(--mut);font-size:.8rem}
.shell{display:flex;min-height:100vh}
.side{width:256px;flex:0 0 256px;position:sticky;top:0;height:100vh;background:linear-gradient(180deg,#053f39 0%,#075E54 100%);color:#fff;display:flex;flex-direction:column;padding:1.1rem .9rem}
.side .brand{display:flex;align-items:center;gap:.7rem;padding:.1rem .4rem 1rem;border-bottom:1px solid rgba(255,255,255,.14)}
.side .brand p{margin-top:.1rem;font-size:.74rem;opacity:.85;max-width:150px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.side nav{margin-top:1rem;display:flex;flex-direction:column;gap:4px}
.navbtn{display:flex;align-items:center;gap:.7rem;background:transparent;border:none;color:rgba(255,255,255,.82);font-size:.87rem;font-weight:600;padding:.62rem .8rem;border-radius:10px;cursor:pointer;text-align:left;position:relative;transition:background .15s ease,color .15s ease}
.navbtn svg{width:17px;height:17px;stroke:currentColor;flex:0 0 auto}
.navbtn:hover{background:rgba(255,255,255,.10);color:#fff}
.navbtn.active{background:rgba(255,255,255,.16);color:#fff}
.navbtn.active::before{content:'';position:absolute;left:0;top:9px;bottom:9px;width:3px;border-radius:3px;background:#a3e635}
.side-foot{margin-top:auto;border-top:1px solid rgba(255,255,255,.14);padding-top:.9rem;display:flex;flex-direction:column;gap:.6rem;font-size:.75rem;color:rgba(255,255,255,.78)}
.main{flex:1;min-width:0}
.main .wrap{margin:0 auto}
@media(max-width:900px){
  .shell{flex-direction:column}
  .side{position:static;width:100%;height:auto;flex:0 0 auto;flex-direction:row;align-items:center;flex-wrap:wrap;gap:.6rem;padding:.6rem .8rem}
  .side .brand{border-bottom:none;padding:0}
  .side .brand p{display:none}
  .side nav{flex-direction:row;margin-top:0;flex:1}
  .navbtn{flex:1;justify-content:center}
  .navbtn.active::before{left:8px;right:8px;top:auto;bottom:0;width:auto;height:3px}
  .side-foot{margin-top:0;border-top:none;flex-direction:row;padding:0}
}
::-webkit-scrollbar{width:10px;height:10px}
::-webkit-scrollbar-thumb{background:#cdd4dd;border-radius:999px;border:2px solid var(--bg)}
::-webkit-scrollbar-thumb:hover{background:#b6beca}
</style></head><body>
<div class="shell">
  <aside class="side">
    <div class="brand">
      <div class="logo">m</div>
      <div>
        <h1>mywa <span class="pill">Enterprise</span></h1>
        <p id="meta">Loading…</p>
      </div>
    </div>
    <nav>
      <button class="navbtn active" id="navInsights"><svg viewBox="0 0 24 24" fill="none" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="7" height="9" rx="1.5"></rect><rect x="14" y="3" width="7" height="5" rx="1.5"></rect><rect x="14" y="12" width="7" height="9" rx="1.5"></rect><rect x="3" y="16" width="7" height="5" rx="1.5"></rect></svg>Dashboard</button>
      <button class="navbtn" id="navGroups"><svg viewBox="0 0 24 24" fill="none" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="9" cy="8" r="3.2"></circle><path d="M3.5 19c.6-3 2.7-5 5.5-5s4.9 2 5.5 5"></path><circle cx="17" cy="9" r="2.4"></circle><path d="M15 14.4c2.6.4 4.6 2.2 5.2 4.6"></path></svg>Groups</button>
      <button class="navbtn" id="navOpportunities"><svg viewBox="0 0 24 24" fill="none" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="9"></circle><path d="M9 12l2.2 2.2L15.5 9.5"></path><path d="M12 3v3M12 18v3M3 12h3M18 12h3"></path></svg>Opportunities</button>
      <button class="navbtn" id="navSegments"><svg viewBox="0 0 24 24" fill="none" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="2.6"></circle><path d="M5.6 5.6c3.5-3.5 9.3-3.5 12.8 0"></path><path d="M3 12c0-4.4 2.6-7.6 5.5-9.3M21 12c0-4.4-2.6-7.6-5.5-9.3"></path></svg>Segments</button>
      <button class="navbtn" id="navRoadmap"><svg viewBox="0 0 24 24" fill="none" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="6" cy="6" r="2.4"></circle><circle cx="6" cy="18" r="2.4"></circle><line x1="8.4" y1="6" x2="21" y2="6"></line><line x1="8.4" y1="18" x2="14" y2="18"></line><line x1="14" y1="18" x2="14" y2="10"></line><line x1="21" y1="6" x2="21" y2="12"></line></svg>Roadmap</button>
    </nav>
    <div class="side-foot">
      <span class="live"><i></i> LIVE</span>
      <span class="pill">Agentic-ready</span>
    </div>
  </aside>
  <main class="main">
  <div class="wrap">
  <div id="viewInsights">
  <div class="cards" id="cards"></div>
  <div class="chartgrid" id="charts"></div>
  <div class="tags" id="tags"></div>
  <div class="controls">
    <div class="search"><svg viewBox="0 0 24 24" fill="none" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="7"></circle><line x1="21" y1="21" x2="16.5" y2="16.5"></line></svg><input type="search" id="q" aria-label="Search contacts" placeholder="Search name, phone, group…"></div>
    <div class="control"><label for="fActivity">Activity</label><select id="fActivity"><option value="">All</option></select></div>
    <div class="control"><label for="fCarrier">Carrier</label><select id="fCarrier"><option value="">All</option></select></div>
    <div class="control"><label for="fCountry">Country</label><select id="fCountry"><option value="">All</option></select></div>
    <div class="control"><label for="fDiaspora">Segment</label><select id="fDiaspora"><option value="">All</option><option value="1">Diaspora</option><option value="0">Home</option></select></div>
    <div class="control"><label for="fOrigin">Origin</label><select id="fOrigin"><option value="">All</option></select></div>
    <div class="control"><label for="fValid">Status</label><select id="fValid"><option value="">All</option><option value="1">Valid</option><option value="0">Invalid</option></select></div>
    <div class="control"><label for="fNamed">Has name</label><select id="fNamed"><option value="">All</option><option value="1">Named</option><option value="0">Unnamed</option></select></div>
    <div class="spacer"></div>
    <button class="btn ghost" id="btnOpp">Opportunities only</button>
    <button class="btn" id="exportCsv">Export CSV</button>
  </div>
  <div class="tablewrap" id="tblwrap"><table><thead><tr>
    <th>Name</th><th>Phone</th><th>Caller</th><th>Carrier</th><th>Country</th><th>Activity</th><th>Origin</th><th>Msgs</th><th>Groups</th>
  </tr></thead><tbody id="rows"></tbody></table></div>
  <div class="groups" id="groups"><h3>Groups</h3><div class="glist" id="glist"></div></div>
  <div class="footer" id="footer"></div>
  </div>
  <div id="viewRoadmap" style="display:none">
    <div class="panel">
      <h3 id="rmGoal"></h3>
      <div class="bar"><div class="fill" id="rmFill" style="width:0%"></div></div>
      <div id="rmPhases"></div>
    </div>
  </div>
  </div>
  </main>
</div>
<script>
var DATA=[];
var esc=function(s){return String(s==null?'':s).replace(/[&<>"']/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c];});};
var get=function(id){return document.getElementById(id);};

function buildCards(){
  var total=DATA.length;
  var valid=DATA.filter(function(c){return c.valid;}).length;
  var hot=DATA.filter(function(c){return c.activity==='hot';}).length;
  var groups={};
  var tags={};
  DATA.forEach(function(c){
    String(c.groups||'').split(';').forEach(function(g){g=g.trim();if(g)groups[g]=1;});
    String(c.group_tags||'').split(';').forEach(function(t){t=t.trim();if(t)tags[t]=1;});
  });
  get('meta').textContent=total.toLocaleString()+' contacts · '+Object.keys(groups).length+' groups · '+hot.toLocaleString()+' hot · '+valid.toLocaleString()+' valid mobile';
  var cards=[['Total contacts',total],['Valid mobile',valid],['Hot leads',hot],
    ['Unnamed',DATA.filter(function(c){return !c.named;}).length],
    ['Caller-ID found',DATA.filter(function(c){return !c.named&&c.caller;}).length],
    ['Business',DATA.filter(function(c){return c.is_business;}).length],
    ['Diaspora',DATA.filter(function(c){return c.diaspora;}).length],
    ['Tagged opportunities',Object.keys(tags).length],['Groups',Object.keys(groups).length]];
  get('cards').innerHTML=cards.map(function(item){return '<div class="card"><div class="n">'+item[1]+'</div><div class="l">'+item[0]+'</div></div>';}).join('');
}

function buildTags(){
  var counts={};
  DATA.forEach(function(c){
    String(c.group_tags||'').split(';').forEach(function(t){t=t.trim();if(t)counts[t]=(counts[t]||0)+1;});
  });
  var html='';
  Object.keys(counts).forEach(function(t){
    html+='<span class="tag on" data-tag="'+esc(t)+'" onclick="this.classList.toggle(\'on\');render();">'+esc(t)+' ('+counts[t]+')</span>';
  });
  get('tags').innerHTML=html||'No opportunity tags. Re-run with --opportunity-groups "kw1, kw2".';
}

function fillSelect(id,key){
  var sel=get(id);
  var set={};
  DATA.forEach(function(c){set[c[key]||'']=1;});
  var html='<option value="">All</option>';
  Object.keys(set).filter(String).sort().forEach(function(v){html+='<option>'+esc(v)+'</option>';});
  sel.innerHTML=html;
}

function selectedTags(){
  var out=[];
  get('tags').querySelectorAll('.tag.on').forEach(function(el){out.push(el.getAttribute('data-tag'));});
  return out;
}

function rowMatches(c){
  var q=(get('q').value||'').trim().toLowerCase();
  if(q){var hay=(String(c.name)+' '+String(c.phone)+' '+String(c.groups||'')).toLowerCase();if(hay.indexOf(q)<0)return false;}
  var f=function(id){return get(id).value;};
  if(f('fActivity')&&c.activity!==f('fActivity'))return false;
  if(f('fCarrier')&&c.carrier!==f('fCarrier'))return false;
  if(f('fCountry')&&c.country!==f('fCountry'))return false;
  if(f('fDiaspora')!==''&&String(c.diaspora?1:0)!==f('fDiaspora'))return false;
  if(f('fOrigin')&&c.origin!==f('fOrigin'))return false;
  if(f('fValid')!==''&&String(c.valid?1:0)!==f('fValid'))return false;
  if(f('fNamed')!==''&&String(c.named?1:0)!==f('fNamed'))return false;
  if(get('btnOpp').classList.contains('active')){
    var tagged=String(c.group_tags||'').trim();
    if(!tagged)return false;
    var sel=selectedTags();
    if(sel.length){
      var match=false;
      sel.forEach(function(t){if(String(c.group_tags||'').split(';').map(function(x){return x.trim();}).indexOf(t)>=0)match=true;});
      if(!match)return false;
    }
  }
  return true;
}

function actBadge(a){return '<span class="badge '+a+'">'+esc(a)+'</span>';}

function callerCell(c){
  var shown = c.lookup || (!c.name ? (c.caller||'') : '');
  if(c.name&&String(c.name).trim())return '<span class="mut">—</span>';
  if(shown)return '<span class="ca" style="color:var(--teal);font-weight:600">'+esc(shown)+' <span style="font-size:.68rem;color:#7c7c7c">('+esc(c.lookup_src||'resolved')+')</span></span>';
  return '<span class="ca unknown">Unknown</span>';
}

var cells={};
cells.name=function(c){
  var html=esc(c.name||'—');
  if(c.diaspora)html+=' <span class="badge dia">Diaspora</span>';
  if(c.is_business)html+=' <span class="badge business" title="WhatsApp business account">Biz</span>';
  if(c.is_admin)html+=' <span class="badge admin">Admin</span>';
  if(c.my_contact)html+=' <span class="badge saved">Saved</span>';
  return html;
};

function render(){
  var count=0;
  var html='';
  DATA.forEach(function(c){
    if(!rowMatches(c))return;
    count++;
    html+='<tr><td>'+cells.name(c)+'</td><td>'+esc(c.phone)+'</td><td>'+callerCell(c)+'</td><td>'+esc(c.carrier)+'</td>'+
      '<td>'+esc(c.country)+'</td><td>'+actBadge(c.activity)+'</td><td>'+esc(c.origin)+'</td>'+
      '<td>'+c.msg_count+'</td><td class="mut">'+esc(c.groups)+'</td></tr>';
  });
  get('rows').innerHTML=html||'<tr><td colspan="9" class="mut">No contacts match.</td></tr>';
  get('footer').textContent='Showing '+count+' of '+DATA.length+' contacts';
  buildGroups();
  buildCharts();
}

var cells={};
var PAL=['#075E54','#128C7E','#2bb673','#7c3aed','#2563eb','#f59e0b','#dc2626','#3b82f6','#14b8a6','#94a3b8'];

function aggregate(list,key){
  var m={};
  list.forEach(function(c){var k=c[key]||'Unknown';if(!k||k==='Unknown')return;m[k]=(m[k]||0)+1;});
  var items=Object.keys(m).map(function(k){return {k:k,v:m[k]};}).sort(function(a,b){return b.v-a.v;});
  var total=items.reduce(function(s,x){return s+x.v;},0);
  return {items:items,total:total};
}

function donutSVG(items,total,size){
  var r=size/2,cx=r,cy=r,a=-Math.PI/2,sg='<svg viewBox="0 0 '+size+' '+size+'" width="'+size+'" height="'+size+'">';
  items.forEach(function(it,i){
    var frac=it.v/total,a1=a+frac*Math.PI*2;
    var x0=cx+r*Math.cos(a),y0=cy+r*Math.sin(a),x1=cx+r*Math.cos(a1),y1=cy+r*Math.sin(a1);
    sg+='<path d="M'+cx+' '+cy+' L'+x0+' '+y0+' A'+r+' '+r+' 0 '+(frac>0.5?1:0)+' 1 '+x1+' '+y1+' Z" fill="'+PAL[i%PAL.length]+'"/>';
    a=a1;
  });
  sg+='<circle cx="'+cx+'" cy="'+cy+'" r="'+(r*0.42)+'" fill="var(--card)"/>';
  sg+='<text x="'+cx+'" y="'+(cy+5)+'" text-anchor="middle" font-size="18" font-weight="700" fill="var(--ink)">'+total+'</text>';
  sg+='<text x="'+cx+'" y="'+(cy+20)+'" text-anchor="middle" font-size="10" fill="var(--mut)">contacts</text></svg>';
  return sg;
}

function legend(items){
  return '<div class="leg">'+items.map(function(it,i){
    return '<span><i style="background:'+PAL[i%PAL.length]+'"></i>'+esc(it.k)+' <b>'+it.v+'</b></span>';
  }).join('')+'</div>';
}

function barsSVG(items,hbar){
  if(!items.length)return '<div class="mut">No data</div>';
  var maxv=items[0].v, w=280, rowh=hbar;
  var sg='<svg viewBox="0 0 '+w+' '+((Math.min(items.length,8))*rowh+6)+'" width="100%" height="auto">';
  items.slice(0,8).forEach(function(it,i){
    var bw=Math.max(2,(it.v/maxv)*(w-38));
    var y=i*rowh+2;
    sg+='<rect x="0" y="'+y+'" width="'+bw+'" height="'+(rowh-8)+'" rx="3" fill="'+PAL[i%PAL.length]+'"/>';
    sg+='<text x="'+(bw+6)+'" y="'+(y+rowh-6)+'" font-size="11" fill="var(--mut)">'+esc(it.k)+'</text>';
    sg+='<text x="'+(w-2)+'" y="'+(y+rowh-6)+'" font-size="11" text-anchor="end" fill="var(--green)" font-weight="700">'+it.v+'</text>';
  });
  sg+='</svg>';
  return sg;
}

function panel(title,inner){
  return '<div class="panel"><h3>'+esc(title)+'</h3>'+inner+'</div>';
}

function buildCharts(){
  var visible=DATA.filter(rowMatches);
  var byCarrier=aggregate(visible,'carrier');
  var byCountry=aggregate(visible,'country');
  var byActivity=aggregate(visible,'activity');
  var byOrigin=aggregate(visible,'origin');
  var html='';
  html+=panel('Carriers '+byCarrier.total, donutSVG(byCarrier.items.slice(0,8),byCarrier.total,150)+legend(byCarrier.items.slice(0,6)));
  html+=panel('Countries', donutSVG(byCountry.items.slice(0,6),byCountry.total,150)+legend(byCountry.items.slice(0,6)));
  html+=panel('Activity funnel', barsSVG(byActivity.items,24));
  html+=panel('Origin / source', barsSVG(byOrigin.items,22));
  get('charts').innerHTML=html;
}

function buildGroups(){
  var counts={};
  DATA.forEach(function(c){String(c.groups||'').split(';').map(function(g){return g.trim();}).filter(Boolean).forEach(function(g){counts[g]=(counts[g]||0)+1;});});
  var html='';
  Object.keys(counts).sort(function(a,b){return counts[b]-counts[a];}).slice(0,30).forEach(function(g){
    html+='<span class="gpill">'+esc(g)+' · <b>'+counts[g]+'</b></span>';
  });
  get('glist').innerHTML=html||'No groups found.';
}

get('q').addEventListener('input',render);
['fActivity','fCarrier','fCountry','fDiaspora','fOrigin','fValid','fNamed'].forEach(function(id){get(id).addEventListener('change',render);});
get('btnOpp').addEventListener('click',function(e){
  e.target.classList.toggle('active');
  e.target.textContent=(e.target.classList.contains('active'))?'Showing opportunities':'Opportunities only';
  render();
});
get('exportCsv').addEventListener('click',function(){
  var rows=[['name','phone','country','carrier','valid','activity','origin','groups','group_tags','msg_count','sent_count','last_seen','source']];
  DATA.forEach(function(c){
    if(!rowMatches(c))return;
    rows.push([c.name,c.phone,c.country,c.carrier,c.valid,c.activity,c.origin,c.groups,c.group_tags,c.msg_count,c.sent_count,c.last_seen,c.source]);
  });
  var csv=rows.map(function(r){return r.map(function(v){return '"'+String(v==null?'':v).replace(/"/g,'""')+'"';}).join(',');}).join('\n');
  var a=document.createElement('a');
  a.href='data:text/csv;charset=utf-8,'+encodeURIComponent('\ufeff'+csv);
  a.download='contacts_filtered.csv';a.click();
});

fetch('/api/data').then(function(r){return r.json();}).then(function(d){
  DATA=d.contacts||[];
  buildCards();
  buildTags();
  ['fActivity','fCarrier','fCountry','fOrigin'].forEach(function(id){fillSelect(id,{fActivity:'activity',fCarrier:'carrier',fCountry:'country',fOrigin:'origin'}[id]);});
  render();
});

get('navInsights').addEventListener('click',function(){switchView('insights');});
get('navRoadmap').addEventListener('click',function(){switchView('roadmap');buildRoadmap();});
get('navGroups').addEventListener('click',function(){setNavActive('navGroups');switchView('insights');scrollToId('groups');});
get('navOpportunities').addEventListener('click',function(){setNavActive('navOpportunities');switchView('insights');if(!get('btnOpp').classList.contains('active')){get('btnOpp').classList.add('active');get('btnOpp').textContent='Showing opportunities';}render();scrollToId('tblwrap');});
get('navSegments').addEventListener('click',function(){setNavActive('navSegments');switchView('insights');get('fDiaspora').value='1';render();scrollToId('charts');});
function setNavActive(id){
  ['navInsights','navGroups','navOpportunities','navSegments','navRoadmap'].forEach(function(n){get(n).classList.remove('active');});
  get(id).classList.add('active');
}
function scrollToId(id){
  var el=get(id);if(el)el.scrollIntoView({behavior:'smooth',block:'start'});
}
function switchView(name){
  var on=(name==='roadmap');
  get('navInsights').classList.toggle('active',!on);
  get('navRoadmap').classList.toggle('active',on);
  get('viewInsights').style.display=on?'none':'';
  get('viewRoadmap').style.display=on?'':'none';
}
var STATUSES=['planned','in_progress','done'];
var NEXT_ST={'planned':'in_progress','in_progress':'done','done':'planned'};
function buildRoadmap(){
  fetch('/api/roadmap').then(function(r){return r.json();}).then(function(rm){
    var total=0,done=0,html='';
    get('rmGoal').textContent='Agentic build roadmap - '+rm.goal;
    (rm.phases||[]).forEach(function(ph){
      var phDone=0;
      html+='<div class="rm-phase"><h3>'+esc(ph.name)+'</h3>';
      (ph.items||[]).forEach(function(it){
        total++; if(it.status==='done'){done++;phDone++;}
        html+='<div class="rm-item"><button class="st '+it.status+'" data-id="'+esc(it.id)+'">'+it.status.replace('_',' ')+'</button>'+
          '<div><h4>'+esc(it.title)+'</h4><p>'+esc(it.detail)+'</p></div></div>';
      });
      html+='</div>';
    });
    get('rmFill').style.width=total?Math.round(done/total*100)+'%':'0%';
    get('rmPhases').innerHTML=html;
    Array.prototype.forEach.call(document.querySelectorAll('#rmPhases .st'),function(btn){
      btn.addEventListener('click',function(){
        var id=btn.getAttribute('data-id'),ns=NEXT_ST[btn.className.split(' ')[1]]||'planned';
        fetch('/api/roadmap',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id:id,status:ns})})
          .then(function(r){return r.json();}).then(function(){buildRoadmap();});
      });
    });
  });
}
</script></body></html>
"""

FIELDS = ["name", "phone", "country", "carrier", "valid", "named", "caller",
          "diaspora", "lookup", "lookup_src", "line", "activity",
          "origin", "org", "email", "address", "city", "home_country", "website",
          "groups", "group_tags", "my_contact", "is_business", "is_admin", "labels",
          "msg_count", "sent_count", "last_seen", "source"]


class DashboardHandler(BaseHTTPRequestHandler):
    data: list = []

    def _send(self, content_type, body, extra=None):
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = urlparse(self.path).path.rstrip("/") or "/"
        if path == "/":
            self._send("text/html; charset=utf-8", _INDEX_HTML.encode("utf-8"))
        elif path == "/api/data":
            self._send("application/json; charset=utf-8",
                       json.dumps({"count": len(self.data), "contacts": self.data}).encode("utf-8"))
        elif path == "/api/export.csv":
            buf = io.StringIO()
            writer = csv.DictWriter(buf, fieldnames=FIELDS, extrasaction="ignore")
            writer.writeheader()
            for c in self.data:
                writer.writerow(c)
            self._send("text/csv; charset=utf-8",
                       ("\ufeff" + buf.getvalue()).encode("utf-8"),
                       {"Content-Disposition": 'attachment; filename="contacts.csv"'})
        elif path == "/api/roadmap":
            self._send("application/json; charset=utf-8",
                       json.dumps(load_roadmap()).encode("utf-8"))
        elif path == "/api/health":
            self._send("application/json", b'{"ok":true}')
        else:
            self.send_error(404)

    def do_POST(self):
        path = urlparse(self.path).path.rstrip("/") or "/"
        if path == "/api/roadmap":
            length = int(self.headers.get("Content-Length") or 0)
            raw = self.rfile.read(length).decode("utf-8")
            try:
                payload = json.loads(raw)
            except (ValueError, TypeError):
                self.send_error(400)
                return
            self._send("application/json; charset=utf-8",
                       json.dumps(update_roadmap(payload)).encode("utf-8"))
        else:
            self.send_error(404)

    def log_message(self, fmt, *args):
        print("[mywa]", fmt % args)


def load_data(out_dir: str):
    path = os.path.join(out_dir, "contacts.json")
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        return data.get("contacts", [])
    except (json.JSONDecodeError, OSError):
        return []


def serve(out_dir: str, host: str = "127.0.0.1", port: int = 8000,
          launch: bool = False) -> ThreadingHTTPServer:
    DashboardHandler.data = load_data(out_dir)
    httpd = ThreadingHTTPServer((host, port), DashboardHandler)
    url = f"http://{host}:{port}"
    print(f"mywa dashboard running at {url}")
    print(f"loaded {len(DashboardHandler.data)} contacts from {os.path.join(out_dir, 'contacts.json')}")
    if launch:
        import webbrowser
        webbrowser.open(url)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
    return httpd


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(prog="mywa serve", description="mywa web dashboard.")
    ap.add_argument("--out", "-o", default="out", help="output directory with contacts.json")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8000)
    ap.add_argument("--open", action="store_true", help="open in the default browser")
    args = ap.parse_args()
    serve(args.out, host=args.host, port=args.port, launch=args.open)