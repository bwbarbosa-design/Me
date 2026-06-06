#!/usr/bin/env python3
"""
graphify.py — Gerador de mapa de litígio para projetos jurídicos A-CEM / Bloco Galeão
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Uso:
  python graphify.py                        → gera graph.html a partir de graphify.json
  python graphify.py --output mapa.html     → output personalizado
  python graphify.py --data outro.json      → usa schema diferente
  python graphify.py --validate             → valida o JSON sem gerar HTML
  python graphify.py --stats                → mostra estatísticas do grafo

Workflow de atualização:
  1. Edita graphify.json (adiciona/remove nós e ligações)
  2. python graphify.py --validate
  3. python graphify.py --output graph.html
  4. Abre graph.html no browser
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

import json
import sys
import os
import argparse
from pathlib import Path
from datetime import datetime

# ─── CLI ─────────────────────────────────────────────────────────────────────

def parse_args():
    p = argparse.ArgumentParser(
        description='graphify — Mapa interativo de litígio',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    p.add_argument('--data', default='graphify.json', help='Ficheiro JSON com nós e ligações')
    p.add_argument('--output', default='graph.html', help='Ficheiro HTML de saída')
    p.add_argument('--validate', action='store_true', help='Valida o JSON e sai')
    p.add_argument('--stats', action='store_true', help='Mostra estatísticas do grafo')
    return p.parse_args()

# ─── VALIDATION ──────────────────────────────────────────────────────────────

def validate(data):
    errors = []
    warnings = []

    node_ids = {n['id'] for n in data.get('nodes', [])}

    for n in data.get('nodes', []):
        for field in ['id', 'label', 'type', 'color']:
            if field not in n:
                errors.append(f"Nó '{n.get('id','?')}': falta campo '{field}'")
        if 'r' not in n:
            warnings.append(f"Nó '{n.get('id','?')}': sem raio 'r' — será 12")

    for i, l in enumerate(data.get('links', [])):
        for field in ['s', 't']:
            if field not in l:
                errors.append(f"Ligação #{i}: falta campo '{field}'")
        if l.get('s') not in node_ids:
            errors.append(f"Ligação #{i}: nó origem '{l.get('s')}' não existe")
        if l.get('t') not in node_ids:
            errors.append(f"Ligação #{i}: nó destino '{l.get('t')}' não existe")

    # Check for isolated nodes
    connected = set()
    for l in data.get('links', []):
        connected.add(l.get('s')); connected.add(l.get('t'))
    for n in data.get('nodes', []):
        if n['id'] not in connected:
            warnings.append(f"Nó '{n['id']}': isolado (sem ligações)")

    return errors, warnings

# ─── STATS ───────────────────────────────────────────────────────────────────

def print_stats(data):
    nodes = data.get('nodes', [])
    links = data.get('links', [])

    by_type = {}
    for n in nodes:
        t = n.get('type', 'unknown')
        by_type[t] = by_type.get(t, 0) + 1

    degree = {}
    for l in links:
        degree[l['s']] = degree.get(l['s'], 0) + 1
        degree[l['t']] = degree.get(l['t'], 0) + 1

    top = sorted(degree.items(), key=lambda x: -x[1])[:5]
    node_map = {n['id']: n['label'].replace('\n', ' ') for n in nodes}

    print(f"\n{'─'*50}")
    print(f"  graphify · Estatísticas do Grafo")
    print(f"  {data.get('_meta',{}).get('project','')}")
    print(f"{'─'*50}")
    print(f"  Nós:     {len(nodes)}")
    print(f"  Ligações: {len(links)}")
    print(f"\n  Por tipo:")
    type_labels = {
        'core': 'Core / Autora', 'proc': 'Processos', 'hist': 'Histórico',
        'lawyer': 'Advogados', 'adverse': 'Adversos', 'entity': 'Entidades',
        'event': 'Eventos', 'witness': 'Testemunhas'
    }
    for t, c in sorted(by_type.items()):
        label = type_labels.get(t, t)
        print(f"    {label:<20} {c}")
    print(f"\n  Nós mais conectados:")
    for nid, deg in top:
        print(f"    {node_map.get(nid, nid):<30} {deg} ligações")
    print(f"{'─'*50}\n")

# ─── HTML TEMPLATE ────────────────────────────────────────────────────────────

HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="pt">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{{TITLE}}</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/d3/7.8.5/d3.min.js"></script>
<style>
  @import url('https://fonts.googleapis.com/css2?family=EB+Garamond:ital,wght@0,400;0,500;0,700;1,400&family=JetBrains+Mono:wght@300;400;500&display=swap');
  *{margin:0;padding:0;box-sizing:border-box;}
  :root{
    --bg:#0a0a0f;--surface:#111118;--border:#1e1e2a;
    --gold:#c9a84c;--gold-dim:#7a6330;--red:#cc3333;
    --blue:#3a6fa8;--green:#2d7a4f;--purple:#6b3fa0;
    --text:#d4c9b0;--text-dim:#7a7060;--text-muted:#4a4540;
  }
  body{background:var(--bg);color:var(--text);font-family:'JetBrains Mono',monospace;font-size:11px;overflow:hidden;height:100vh;width:100vw;user-select:none;}
  #canvas{position:fixed;inset:0;}
  #header{position:fixed;top:0;left:0;right:0;height:52px;background:linear-gradient(180deg,rgba(10,10,15,.98) 0%,rgba(10,10,15,0) 100%);display:flex;align-items:center;padding:0 24px;gap:16px;z-index:100;border-bottom:1px solid var(--border);backdrop-filter:blur(8px);}
  #header .title{font-family:'EB Garamond',serif;font-size:18px;font-weight:500;color:var(--gold);letter-spacing:.05em;}
  #header .sub{font-size:9px;color:var(--text-dim);letter-spacing:.15em;text-transform:uppercase;}
  #header .sep{color:var(--text-muted);}
  #legend{position:fixed;bottom:20px;left:20px;background:rgba(17,17,24,.92);border:1px solid var(--border);padding:14px 18px;border-radius:4px;z-index:100;backdrop-filter:blur(8px);min-width:200px;}
  #legend h4{font-family:'EB Garamond',serif;font-size:11px;color:var(--text-dim);letter-spacing:.2em;text-transform:uppercase;margin-bottom:10px;border-bottom:1px solid var(--border);padding-bottom:6px;}
  .li{display:flex;align-items:center;gap:8px;margin-bottom:6px;font-size:10px;color:var(--text-dim);}
  .ld{width:10px;height:10px;border-radius:50%;flex-shrink:0;border:1px solid rgba(255,255,255,.15);}
  #detail{position:fixed;top:60px;right:20px;width:300px;background:rgba(17,17,24,.95);border:1px solid var(--border);border-radius:4px;z-index:100;backdrop-filter:blur(12px);overflow:hidden;display:none;animation:si .15s ease-out;}
  @keyframes si{from{opacity:0;transform:translateX(8px)}to{opacity:1;transform:translateX(0)}}
  #dh{padding:12px 16px;border-bottom:1px solid var(--border);display:flex;justify-content:space-between;align-items:center;}
  #dt{font-size:9px;letter-spacing:.2em;text-transform:uppercase;color:var(--text-muted);}
  #dn{font-family:'EB Garamond',serif;font-size:16px;font-weight:500;color:var(--text);margin-top:2px;line-height:1.2;}
  #dc{cursor:pointer;color:var(--text-muted);font-size:16px;line-height:1;padding:4px;transition:color .15s;}
  #dc:hover{color:var(--text);}
  #db{padding:12px 16px;max-height:400px;overflow-y:auto;}
  #db::-webkit-scrollbar{width:4px;}#db::-webkit-scrollbar-track{background:var(--surface);}#db::-webkit-scrollbar-thumb{background:var(--border);border-radius:2px;}
  .ds{margin-bottom:12px;}.ds h5{font-size:9px;letter-spacing:.15em;text-transform:uppercase;color:var(--text-muted);margin-bottom:6px;}.ds p{font-size:10px;color:var(--text-dim);line-height:1.6;}
  #controls{position:fixed;bottom:20px;right:20px;display:flex;gap:6px;z-index:100;}
  .cb{width:30px;height:30px;background:rgba(17,17,24,.92);border:1px solid var(--border);color:var(--text-dim);border-radius:4px;display:flex;align-items:center;justify-content:center;cursor:pointer;font-size:14px;transition:all .15s;backdrop-filter:blur(8px);}
  .cb:hover{border-color:var(--gold-dim);color:var(--gold);}
  .node circle{transition:filter .2s;cursor:pointer;}.node:hover circle{filter:brightness(1.3);}
  .node text{font-family:'JetBrains Mono',monospace;pointer-events:none;fill:var(--text);}
  .link{stroke-opacity:.5;transition:stroke-opacity .2s;}.link:hover{stroke-opacity:1;}
  #tooltip{position:fixed;background:rgba(17,17,24,.95);border:1px solid var(--border);padding:6px 10px;border-radius:3px;font-size:10px;color:var(--text-dim);pointer-events:none;display:none;z-index:200;max-width:200px;line-height:1.5;}
  #sw{position:fixed;top:60px;left:20px;z-index:100;}
  #search{background:rgba(17,17,24,.85);border:1px solid var(--border);color:var(--text);font-family:'JetBrains Mono',monospace;font-size:10px;padding:6px 12px;border-radius:4px;outline:none;width:200px;backdrop-filter:blur(8px);transition:border-color .2s;}
  #search:focus{border-color:var(--gold-dim);}
  #search::placeholder{color:var(--text-muted);}
  #updated{position:fixed;top:60px;right:20px;font-size:8px;color:var(--text-muted);letter-spacing:.1em;text-transform:uppercase;opacity:.5;}
</style>
</head>
<body>
<div id="header">
  <div><div class="title">{{TITLE}}</div></div>
  <span class="sep">|</span>
  <div class="sub">{{SUBTITLE}}</div>
  <span class="sep">|</span>
  <div class="sub">{{UPDATED}}</div>
</div>
<svg id="canvas"></svg>
<div id="sw"><input id="search" type="text" placeholder="pesquisar…"/></div>
<div id="updated">gerado {{GEN_DATE}}</div>
<div id="legend">
  <h4>Legenda</h4>
  <div class="li"><div class="ld" style="background:#c9a84c"></div>ACEM / Parte Autora</div>
  <div class="li"><div class="ld" style="background:#cc3333"></div>Processo Ativo</div>
  <div class="li"><div class="ld" style="background:#b5602a"></div>Processo Histórico</div>
  <div class="li"><div class="ld" style="background:#3a6fa8"></div>Advogado ACEM</div>
  <div class="li"><div class="ld" style="background:#884444"></div>Parte Adversa</div>
  <div class="li"><div class="ld" style="background:#2d7a4f"></div>Entidade / Tribunal</div>
  <div class="li"><div class="ld" style="background:#6b3fa0"></div>Evento / Projeto</div>
  <div class="li"><div class="ld" style="background:#4a6a4a"></div>Testemunha Favorável</div>
</div>
<div id="detail">
  <div id="dh"><div><div id="dt"></div><div id="dn"></div></div><div id="dc">×</div></div>
  <div id="db"></div>
</div>
<div id="tooltip"></div>
<div id="controls">
  <div class="cb" id="zi" title="Zoom in">+</div>
  <div class="cb" id="zo" title="Zoom out">−</div>
  <div class="cb" id="zr" title="Reset">⌂</div>
  <div class="cb" id="pin" title="Fixar nós">⊕</div>
</div>
<script>
const GRAPH_DATA = {{GRAPH_DATA}};
const nodes = GRAPH_DATA.nodes.map(n=>({...n}));
const links = GRAPH_DATA.links.map(l=>({...l}));

const W=window.innerWidth,H=window.innerHeight;
const svg=d3.select('#canvas').attr('width',W).attr('height',H);
const defs=svg.append('defs');
defs.append('marker').attr('id','arrow').attr('viewBox','0 -4 8 8').attr('refX',8).attr('refY',0).attr('markerWidth',6).attr('markerHeight',6).attr('orient','auto').append('path').attr('d','M0,-3L8,0L0,3').attr('fill','#333');
const grid=svg.append('g');
for(let x=0;x<W;x+=60)grid.append('line').attr('x1',x).attr('y1',0).attr('x2',x).attr('y2',H).attr('stroke','#1a1a22').attr('stroke-width',.5);
for(let y=0;y<H;y+=60)grid.append('line').attr('x1',0).attr('y1',y).attr('x2',W).attr('y2',y).attr('stroke','#1a1a22').attr('stroke-width',.5);
const g=svg.append('g');
const zoom=d3.zoom().scaleExtent([.2,4]).on('zoom',e=>g.attr('transform',e.transform));
svg.call(zoom);
const T0=d3.zoomIdentity.translate(W/2,H/2).scale(.85);
svg.call(zoom.transform,T0);
const sim=d3.forceSimulation(nodes)
  .force('link',d3.forceLink(links).id(d=>d.id).strength(d=>d.strength||.3).distance(d=>d.s==='acem'||d.t==='acem'?140:100))
  .force('charge',d3.forceManyBody().strength(d=>-(d.r||12)*18))
  .force('collision',d3.forceCollide().radius(d=>(d.r||12)+18))
  .force('center',d3.forceCenter(0,0))
  .force('x',d3.forceX(0).strength(.04))
  .force('y',d3.forceY(0).strength(.04))
  .alphaDecay(.02);
const le=g.append('g').selectAll('line').data(links).join('line').attr('class','link').attr('stroke',d=>d.color||'#333').attr('stroke-width',1.2).attr('stroke-dasharray',d=>d.dash||null).attr('marker-end','url(#arrow)');
let pinned=false;
const ne=g.append('g').selectAll('g').data(nodes).join('g').attr('class','node')
  .call(d3.drag().on('start',(e,d)=>{if(!e.active)sim.alphaTarget(.3).restart();d.fx=d.x;d.fy=d.y;}).on('drag',(e,d)=>{d.fx=e.x;d.fy=e.y;}).on('end',(e,d)=>{if(!e.active)sim.alphaTarget(0);if(!pinned){d.fx=null;d.fy=null;}}))
  .on('click',(e,d)=>showDetail(d))
  .on('mouseenter',(e,d)=>showTip(e,d)).on('mousemove',moveTip).on('mouseleave',hideTip);
ne.append('circle').attr('r',d=>d.r||12).attr('fill',d=>d.color+'22').attr('stroke',d=>d.color).attr('stroke-width',d=>d.type==='core'?2:1.5);
ne.filter(d=>d.type==='proc').append('circle').attr('r',d=>(d.r||12)+4).attr('fill','none').attr('stroke',d=>d.color).attr('stroke-width',.5).attr('stroke-opacity',.3).attr('stroke-dasharray','3,3');
ne.append('text').attr('text-anchor','middle').attr('dominant-baseline','central').attr('font-size',d=>(d.r||12)>20?9:8).attr('font-weight',d=>d.type==='core'?'500':'400').attr('fill',d=>d.color).each(function(d){const lines=(d.label||d.id).split('\n');const el=d3.select(this);const lh=11;const yo=-((lines.length-1)*lh)/2;lines.forEach((l,i)=>el.append('tspan').attr('x',0).attr('y',yo+i*lh).text(l));});
sim.on('tick',()=>{
  le.attr('x1',d=>d.source.x).attr('y1',d=>d.source.y)
    .attr('x2',d=>{const dx=d.target.x-d.source.x,dy=d.target.y-d.source.y,dist=Math.sqrt(dx*dx+dy*dy)||1;return d.target.x-(dx/dist)*((d.target.r||12)+8);})
    .attr('y2',d=>{const dx=d.target.x-d.source.x,dy=d.target.y-d.source.y,dist=Math.sqrt(dx*dx+dy*dy)||1;return d.target.y-(dy/dist)*((d.target.r||12)+8);});
  ne.attr('transform',d=>`translate(${d.x},${d.y})`);
});
function showDetail(d){
  document.getElementById('dt').textContent=d.detail?.type||d.type;
  document.getElementById('dn').textContent=(d.label||d.id).replace(/\n/g,' ');
  const db=document.getElementById('db');db.innerHTML='';
  (d.detail?.info||[]).forEach(i=>{const s=document.createElement('div');s.className='ds';s.innerHTML=`<h5>${i.h}</h5><p>${i.t}</p>`;db.appendChild(s);});
  document.getElementById('detail').style.display='block';
}
document.getElementById('dc').onclick=()=>{document.getElementById('detail').style.display='none';};
const tip=document.getElementById('tooltip');
function showTip(e,d){tip.textContent=(d.label||d.id).replace(/\n/g,' ');tip.style.display='block';moveTip(e);}
function moveTip(e){tip.style.left=(e.clientX+14)+'px';tip.style.top=(e.clientY-8)+'px';}
function hideTip(){tip.style.display='none';}
document.getElementById('zi').onclick=()=>svg.transition().duration(300).call(zoom.scaleBy,1.4);
document.getElementById('zo').onclick=()=>svg.transition().duration(300).call(zoom.scaleBy,.7);
document.getElementById('zr').onclick=()=>svg.transition().duration(500).call(zoom.transform,T0);
document.getElementById('pin').onclick=function(){pinned=!pinned;this.style.color=pinned?'var(--gold)':'';this.style.borderColor=pinned?'var(--gold-dim)':'';if(!pinned){nodes.forEach(d=>{d.fx=null;d.fy=null;});sim.alpha(.3).restart();}};
document.getElementById('search').addEventListener('input',function(){
  const q=this.value.toLowerCase();
  ne.select('circle').attr('fill',d=>!q?d.color+'22':(d.label||'').toLowerCase().includes(q)?d.color+'55':d.color+'08').attr('stroke-opacity',d=>!q?1:(d.label||'').toLowerCase().includes(q)?1:.2);
  ne.select('text').attr('opacity',d=>!q?1:(d.label||'').toLowerCase().includes(q)?1:.2);
  le.attr('stroke-opacity',d=>!q?.5:(d.source.label?.toLowerCase().includes(q)||d.target.label?.toLowerCase().includes(q))?.8:.05);
});
svg.on('click',e=>{if(e.target===svg.node()||e.target.tagName==='line')document.getElementById('detail').style.display='none';});
</script>
</body>
</html>"""

# ─── GENERATOR ───────────────────────────────────────────────────────────────

def generate_html(data, output_path):
    meta = data.get('_meta', {})
    title = meta.get('project', 'Mapa de Litígio')
    updated = meta.get('updated', '—')
    subtitle = f"A-CEM Fração A/100 · Olhão · {len(data['nodes'])} nós · {len(data['links'])} ligações"
    gen_date = datetime.now().strftime('%d/%m/%Y %H:%M')

    graph_data_json = json.dumps({
        'nodes': data['nodes'],
        'links': data['links']
    }, ensure_ascii=False, indent=2)

    html = HTML_TEMPLATE
    html = html.replace('{{TITLE}}', title)
    html = html.replace('{{SUBTITLE}}', subtitle)
    html = html.replace('{{UPDATED}}', f'KB actualizado: {updated}')
    html = html.replace('{{GEN_DATE}}', gen_date)
    html = html.replace('{{GRAPH_DATA}}', graph_data_json)

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)

    size_kb = os.path.getsize(output_path) / 1024
    print(f"\n  ✅  {output_path} gerado ({size_kb:.0f} KB)")
    print(f"      {len(data['nodes'])} nós · {len(data['links'])} ligações")
    print(f"      gerado em {gen_date}\n")

# ─── MAIN ─────────────────────────────────────────────────────────────────────

def main():
    args = parse_args()

    # Load JSON
    data_path = Path(args.data)
    if not data_path.exists():
        print(f"\n  ❌  Ficheiro não encontrado: {data_path}")
        print(f"      Cria um graphify.json ou especifica --data caminho/para/ficheiro.json\n")
        sys.exit(1)

    with open(data_path, 'r', encoding='utf-8') as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError as e:
            print(f"\n  ❌  Erro no JSON: {e}\n")
            sys.exit(1)

    # Validate
    errors, warnings = validate(data)

    if warnings:
        print(f"\n  ⚠️   {len(warnings)} aviso(s):")
        for w in warnings:
            print(f"      · {w}")

    if errors:
        print(f"\n  ❌  {len(errors)} erro(s):")
        for e in errors:
            print(f"      · {e}")
        if not args.validate:
            print(f"\n  Corrige os erros antes de gerar o HTML.\n")
        sys.exit(1)

    if args.validate:
        print(f"\n  ✅  JSON válido — {len(data.get('nodes',[]))} nós, {len(data.get('links',[]))} ligações, 0 erros\n")
        sys.exit(0)

    if args.stats:
        print_stats(data)
        sys.exit(0)

    # Generate HTML
    generate_html(data, args.output)

if __name__ == '__main__':
    main()
