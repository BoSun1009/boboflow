"""Deterministic orthogonal layout and SVG output. No project execution or network."""
import html
import math
from collections import deque

WIDTH, HEIGHT = 224, 100

def overlap(a,b,pad=0):
    return a[0]<b[0]+b[2]+pad and a[0]+a[2]+pad>b[0] and a[1]<b[1]+b[3]+pad and a[1]+a[3]+pad>b[1]

def crosses(p,q,r):
    x,y,w,h=r
    if p[0]==q[0]:return x+1<p[0]<x+w-1 and max(min(p[1],q[1]),y+1)<min(max(p[1],q[1]),y+h-1)
    return y+1<p[1]<y+h-1 and max(min(p[0],q[0]),x+1)<min(max(p[0],q[0]),x+w-1)

def levels(g):
    # Remove DFS back edges for layout only, preserving every authored edge for rendering.
    adj={n['id']:[] for n in g['nodes']}
    for e in g['edges']:adj[e['source']].append(e['target'])
    color={};back=set();order=[]
    for key in adj:
        if color.get(key):continue
        stack=[(key,0)];color[key]=1
        while stack:
            v,i=stack[-1]
            if i==len(adj[v]):color[v]=2;order.append(v);stack.pop();continue
            w=adj[v][i];stack[-1]=(v,i+1)
            if color.get(w)==1:back.add((v,w))
            elif not color.get(w):color[w]=1;stack.append((w,0))
    rank={v:0 for v in adj}
    for v in reversed(order):
        for w in adj[v]:
            if (v,w) not in back:rank[w]=max(rank[w],rank[v]+1)
    return rank

def geometry(g):
    rank=levels(g);counts={};rects={}
    manual=all('position' in n for n in g['nodes'])
    for n in g['nodes']:
        if manual:x,y=n['position']
        else:
            r=rank[n['id']];slot=counts.get(r,0);counts[r]=slot+1
            if g['kind']=='workflow':x,y=80+slot*360,80+r*200
            else:x,y=80+r*360,80+slot*170
        rects[n['id']]=(x,y,WIDTH,HEIGHT)
    return rects

def port(rect,side):
    x,y,w,h=rect
    return {'left':(x,y+h/2),'right':(x+w,y+h/2),'top':(x+w/2,y),'bottom':(x+w/2,y+h)}[side]

def simplify(points):
    out=[]
    for p in points:
        if out and p==out[-1]:continue
        if len(out)>1 and (out[-2][0]==out[-1][0]==p[0] or out[-2][1]==out[-1][1]==p[1]):out[-1]=p
        else:out.append(p)
    return out

def route(a,b,rects,edge):
    ar,br=rects[a],rects[b]
    if 'route' in edge:return [tuple(p) for p in edge['route']]
    if br[0]>ar[0]:sa,sb='right','left'
    elif br[1]>ar[1]:sa,sb='bottom','top'
    elif br[0]<ar[0]:sa,sb='left','right'
    else:sa,sb='top','bottom'
    start,end=port(ar,sa),port(br,sb)
    candidates=[]
    if start[0]==end[0] or start[1]==end[1]:candidates.append([start,end])
    candidates.extend([[start,(start[0],end[1]),end],[start,(end[0],start[1]),end]])
    for r in rects.values():
        for x in [r[0]-28,r[0]+r[2]+28]:candidates.append([start,(x,start[1]),(x,end[1]),end])
        for y in [r[1]-28,r[1]+r[3]+28]:candidates.append([start,(start[0],y),(end[0],y),end])
    def score(points):
        hits=sum(crosses(p,q,r) for p,q in zip(points,points[1:]) for r in rects.values())
        length=sum(abs(p[0]-q[0])+abs(p[1]-q[1]) for p,q in zip(points,points[1:]))
        return hits*100000+length+len(points)*20
    return simplify(min(candidates,key=score))

def text_width(s):return sum(13 if ord(c)>255 else 7 for c in s)

def compile_layout(g):
    rects=geometry(g);edges=[];issues=[]
    for i,(a,r) in enumerate(rects.items()):
        for b,s in list(rects.items())[i+1:]:
            if overlap(r,s,12):issues.append({'code':'node-overlap','subjects':[a,b]})
    used=[]
    for index,e in enumerate(g['edges']):
        points=route(e['source'],e['target'],rects,e)
        if len(points)<2 or any(not (p[0]==q[0] or p[1]==q[1]) for p,q in zip(points,points[1:])):
            issues.append({'code':'non-orthogonal-route','edge':index})
        for p,q in zip(points,points[1:]):
            for key,r in rects.items():
                if crosses(p,q,r):issues.append({'code':'route-through-node','edge':index,'node':key})
        for point,key in [(points[0],e['source']),(points[-1],e['target'])]:
            r=rects[key];x,y=point
            if not ((x in (r[0],r[0]+r[2]) and r[1]<=y<=r[1]+r[3]) or (y in (r[1],r[1]+r[3]) and r[0]<=x<=r[0]+r[2])):
                issues.append({'code':'endpoint-not-on-node','edge':index,'node':key})
        label=e.get('label','');box=None
        if label:
            w=text_width(label)+20;h=26
            candidates=[]
            for p,q in zip(points,points[1:]):
                mx,my=(p[0]+q[0])/2,(p[1]+q[1])/2
                if p[1]==q[1]:candidates.append((mx-w/2,my-13,w,h))
                else:candidates.append((mx-w/2,my-13,w,h))
            if 'label_position' in e:
                x,y=e['label_position'];candidates=[(x-w/2,y-13,w,h)]
            def bad(b):return sum(overlap(b,r,5) for r in rects.values())*100+sum(overlap(b,r,5) for r in used)*100
            box=min(candidates,key=bad)
            if bad(box):issues.append({'code':'label-overlap','edge':index})
            used.append(box)
        edges.append({'index':index,'points':points,'label_box':box})
    # Report crossings separately, never silently certify a generic dense graph.
    crossings=[]
    for i,a in enumerate(edges):
        for b in edges[i+1:]:
            for p,q in zip(a['points'],a['points'][1:]):
                for u,v in zip(b['points'],b['points'][1:]):
                    if p[0]==q[0] and u[1]==v[1] and min(u[0],v[0])<p[0]<max(u[0],v[0]) and min(p[1],q[1])<u[1]<max(p[1],q[1]):crossings.append([a['index'],b['index']])
                    if p[1]==q[1] and u[0]==v[0] and min(p[0],q[0])<u[0]<max(p[0],q[0]) and min(u[1],v[1])<p[1]<max(u[1],v[1]):crossings.append([a['index'],b['index']])
    xvals=[0];yvals=[0]
    for r in rects.values():xvals.append(r[0]+r[2]);yvals.append(r[1]+r[3])
    for e in edges:
        for x,y in e['points']:xvals.append(x);yvals.append(y)
        if e['label_box']:
            x,y,w,h=e['label_box'];xvals.append(x+w);yvals.append(y+h)
    return {'nodes':rects,'edges':edges,'width':max(xvals)+60,'height':max(yvals)+60,'issues':issues,'crossings':crossings,'status':'pass' if not issues and not crossings else 'needs-review'}

PALETTE={'human':('#eaf3ff','#4579bb'),'ai':('#edf7f3','#3b8d74'),'gate':('#fff6e7','#b78135'),'output':('#f0edfc','#8470b4'),'failure':('#fff0ee','#c36a61')}

def svg_document(g,layout):
    esc=lambda s:html.escape(str(s),quote=True)
    out=[f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {layout["width"]} {layout["height"]}" role="img" aria-label="{esc(g["title"])}">', '<defs><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M0 0 L10 5 L0 10z" fill="#81949d"/></marker></defs>']
    for lane in g.get('lanes',[]):
        out.append(f'<rect x="{lane["x"]}" y="{lane["y"]}" width="{lane["width"]}" height="{lane["height"]}" rx="20" fill="#eef2f3" fill-opacity=".55"/><text x="{lane["x"]+20}" y="{lane["y"]+28}" fill="#77868d" font-size="12" font-family="sans-serif" letter-spacing="1.5">{esc(lane["label"])}</text>')
    for edge in layout['edges']:
        e=g['edges'][edge['index']];path=' '.join(('M' if i==0 else 'L')+f'{x} {y}' for i,(x,y) in enumerate(edge['points']))
        out.append(f'<g class="edge" data-source="{esc(e["source"])}" data-target="{esc(e["target"])}"><path d="{path}" fill="none" stroke="#81949d" stroke-width="1.7" stroke-linejoin="round" marker-end="url(#arrow)"'+(' stroke-dasharray="5 5"' if e.get('optional') else '')+'/></g>')
    for edge in layout['edges']:
        if not edge['label_box']:continue
        e=g['edges'][edge['index']];x,y,w,h=edge['label_box']
        out.append(f'<g class="edge-label" data-source="{esc(e["source"])}" data-target="{esc(e["target"])}"><rect x="{x}" y="{y}" width="{w}" height="{h}" rx="6" fill="#f8faf9"/><text x="{x+w/2}" y="{y+18}" text-anchor="middle" fill="#687d83" font-size="12" font-family="sans-serif">{esc(e["label"])}</text></g>')
    for i,n in enumerate(g['nodes']):
        x,y,w,h=layout['nodes'][n['id']];fill,stroke=PALETTE.get(n.get('role'),('#ffffff','#889ca8'))
        out.append(f'<g class="node" data-id="{esc(n["id"])}" tabindex="0" role="button" aria-label="{esc(n["label"])}" transform="translate({x},{y})"><rect width="{w}" height="{h}" rx="14" fill="{fill}" stroke="{stroke}" stroke-opacity=".5"/><circle cx="24" cy="25" r="12" fill="{stroke}" fill-opacity=".12"/><text x="24" y="29" text-anchor="middle" fill="{stroke}" font-family="sans-serif" font-size="11">{i+1:02}</text><text x="46" y="29" fill="{stroke}" font-family="sans-serif" font-size="11">{esc(n.get("group","步骤"))}</text><text x="18" y="58" fill="#243e49" font-family="sans-serif" font-size="17" font-weight="600">{esc(n["label"])}</text><text x="18" y="82" fill="#70868d" font-family="sans-serif" font-size="12">{esc(n.get("summary","点击查看说明与依据"))}</text><title>{esc(n.get("detail",n["label"]))}</title></g>')
    out.append('</svg>');return ''.join(out)
