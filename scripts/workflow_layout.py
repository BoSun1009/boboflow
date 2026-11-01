"""Deterministic authored workflow layout and geometry validation."""
import html
import math

def esc(value): return html.escape(str(value), quote=True)

def prepare(graph):
    layout=graph.get('layout',{})
    width,height=layout.get('width',1440),layout.get('height',850)
    if not all(type(v) in (int,float) and math.isfinite(v) and 400<=v<=10000 for v in (width,height)):
        raise ValueError('invalid workflow canvas')
    for band in graph.get('bands',[]):
        y=band.get('y');bottom=band.get('bottom',y+200 if type(y) in (int,float) else None)
        if not all(type(v) in (int,float) and math.isfinite(v) for v in (y,bottom)) or not 30<=y<bottom<=height:
            raise ValueError('invalid swimlane geometry')
    boxes={};issues=[]
    for i,node in enumerate(graph['nodes']):
        x,y=node.get('position',[90+(i%4)*340,110+(i//4)*240])
        w,h=node.get('size',[250,108])
        if not all(type(v) in (int,float) and math.isfinite(v) for v in (x,y,w,h)) or w<160 or h<72:
            raise ValueError('invalid node geometry')
        if x<0 or y<0 or x+w>width or y+h>height:issues.append('node outside canvas: '+node['id'])
        if node.get('role','process') not in {'process','decision','human','output','stop'}:raise ValueError('invalid node role')
        boxes[node['id']]=(x,y,w,h)
    values=list(boxes.items())
    for i,(a,(x,y,w,h)) in enumerate(values):
        for b,(u,v,s,t) in values[i+1:]:
            if max(x,u)<min(x+w,u+s) and max(y,v)<min(y+h,v+t):issues.append('overlapping nodes: '+a+' / '+b)
    routes=[]
    for edge in graph['edges']:
        a,b=boxes[edge['source']],boxes[edge['target']]
        pts=edge.get('points')
        if pts is None:pts=[[a[0]+a[2],a[1]+a[3]/2],[b[0],b[1]+b[3]/2]]
        if not isinstance(pts,list) or not 2<=len(pts)<=20:raise ValueError('invalid route')
        for pt in pts:
            if not isinstance(pt,list) or len(pt)!=2 or not all(type(v) in (int,float) and math.isfinite(v) for v in pt):raise ValueError('invalid route point')
            if not (0<=pt[0]<=width and 0<=pt[1]<=height):issues.append('route outside canvas')
        def boundary(p,box):
            x,y,w,h=box;u,v=p
            return (abs(u-x)<.01 or abs(u-x-w)<.01) and y<=v<=y+h or (abs(v-y)<.01 or abs(v-y-h)<.01) and x<=u<=x+w
        if not boundary(pts[0],a) or not boundary(pts[-1],b):issues.append('route endpoints do not meet nodes')
        for p,q in zip(pts,pts[1:]):
            if p[0]!=q[0] and p[1]!=q[1]:issues.append('non-orthogonal route')
            for node_id,(x,y,w,h) in boxes.items():
                if p[0]==q[0] and x<p[0]<x+w and max(min(p[1],q[1]),y)<min(max(p[1],q[1]),y+h):issues.append('route crosses node '+node_id)
                if p[1]==q[1] and y<p[1]<y+h and max(min(p[0],q[0]),x)<min(max(p[0],q[0]),x+w):issues.append('route crosses node '+node_id)
        routes.append(pts)
    if issues:raise ValueError('; '.join(sorted(set(issues))))
    return width,height,boxes,routes

def text_width(value, size=13):
    # Conservative deterministic estimate. Actual fonts are separately reviewed.
    return sum(size if ord(c)>127 else size*(0.32 if c in " il.,:;!|'" else 0.88 if c in "MW@%" else 0.57) for c in str(value))

def wrap_text(value, width, size=13):
    words=str(value).split(' ') if ' ' in str(value) else list(str(value))
    joiner=' ' if ' ' in str(value) else ''
    lines=[];line=''
    for word in words:
        candidate=line+joiner+word if line else word
        if line and text_width(candidate,size)>width:
            lines.append(line);line=word
        else:line=candidate
        if text_width(line,size)>width:
            raise ValueError('Text token exceeds node width: '+line)
    if line:lines.append(line)
    return lines

def overlap(a,b,padding=0):
    x,y,w,h=a;u,v,s,t=b
    return max(x-padding,u)<min(x+w+padding,u+s) and max(y-padding,v)<min(y+h+padding,v+t)

def segment_hits_box(a,b,box,padding=0):
    x,y,w,h=box;x-=padding;y-=padding;w+=2*padding;h+=2*padding
    if a[0]==b[0]:return x<a[0]<x+w and max(min(a[1],b[1]),y)<min(max(a[1],b[1]),y+h)
    return y<a[1]<y+h and max(min(a[0],b[0]),x)<min(max(a[0],b[0]),x+w)

def labels_for(graph,boxes,routes,width,height):
    placed=[];result=[]
    for i,(edge,pts) in enumerate(zip(graph['edges'],routes)):
        label=edge.get('label','')
        if not label:result.append(None);continue
        w=max(40,text_width(label)+20);candidates=[]
        if edge.get('label_position'):candidates.append(edge['label_position'])
        segments=sorted(zip(pts,pts[1:]),key=lambda ab:abs(ab[0][0]-ab[1][0])+abs(ab[0][1]-ab[1][1]),reverse=True)
        for a,b in segments:
            x,y=(a[0]+b[0])/2,(a[1]+b[1])/2
            candidates.extend([[x,y-12],[x,y+24]] if a[1]==b[1] else [[x+w/2+10,y+5],[x-w/2-10,y+5]])
        for x,y in candidates:
            rect=(x-w/2,y-17,w,26)
            if rect[0]<8 or rect[1]<8 or rect[0]+w>width-8 or rect[1]+26>height-8:continue
            if any(overlap(rect,b,5) for b in boxes.values()):continue
            if any(overlap(rect,b,4) for b in placed):continue
            if any(segment_hits_box(a,b,rect,3) for j,path in enumerate(routes) if j!=i for a,b in zip(path,path[1:])):continue
            placed.append(rect);result.append((x,y,w));break
        else:raise ValueError('No clear label position for '+edge['source']+' -> '+edge['target']+'; increase route spacing')
    return result

def inspect_layout(graph):
    width,height,boxes,routes=prepare(graph)
    labels=labels_for(graph,boxes,routes,width,height)
    for n in graph['nodes']:
        w,h=boxes[n['id']][2:]
        title=wrap_text(n['label'],w-40,19)
        summary=[line for t in n.get('summary',[]) for line in wrap_text(t,w-40,13)]
        if len(title)>2 or len(summary)>2:raise ValueError('Node text requires more space: '+n['id'])
        bottom=(103 if len(title)>1 else 98) if summary else (63 if len(title)>1 else 53)
        if bottom>h-10:raise ValueError('Node text exceeds height: '+n['id'])
    crossings=[]
    for i,path in enumerate(routes):
        for j,other in enumerate(routes[:i]):
            for a,b in zip(path,path[1:]):
                for c,d in zip(other,other[1:]):
                    if a[0]==b[0] and c[1]==d[1] and min(c[0],d[0])<a[0]<max(c[0],d[0]) and min(a[1],b[1])<c[1]<max(a[1],b[1]):crossings.append([j,i])
                    elif a[1]==b[1] and c[0]==d[0] and min(a[0],b[0])<c[0]<max(a[0],b[0]) and min(c[1],d[1])<a[1]<max(c[1],d[1]):crossings.append([j,i])
    return {'status':'pass','node_count':len(boxes),'label_count':sum(x is not None for x in labels),'proper_crossings':crossings,'text_measurement':'conservative estimate; not browser font measurement'}

def build_svg(graph,dark=False):
    width,height,boxes,routes=prepare(graph)
    inspect_layout(graph)
    label_positions=labels_for(graph,boxes,routes,width,height)
    bg='#0d1729' if dark else '#f8fafc';ink='#e8effb' if dark else '#203149';muted='#a3b4cc' if dark else '#64758b';card='#17243a' if dark else '#ffffff';border='#33445d' if dark else '#d8e2ee'
    colors={'process':'#059b76','human':'#089fc0','decision':'#ee4168','output':'#089fc0','stop':'#ee4168'}
    s=[f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" height="{height}" role="img" aria-label="{esc(graph["title"])}">',f'<rect width="100%" height="100%" fill="{bg}"/>','<defs>']
    for color in sorted(set(colors.values())|{muted}):
        s.append(f'<marker id="arrow{color[1:]}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0 0L10 5L0 10Z" fill="{color}"/></marker>')
    s.append(f'<pattern id="grid" width="48" height="48" patternUnits="userSpaceOnUse"><path d="M 48 0 L 0 0 0 48" fill="none" stroke="{border}" stroke-width=".5"/></pattern></defs><rect width="100%" height="100%" fill="url(#grid)"/>')
    for band in graph.get('bands',[]):
        y=band['y'];bottom=band.get('bottom',y+200)
        stroke=colors['stop'] if band.get('tone')=='warning' else border
        s.append(f'<g class="swimlane"><rect x="30" y="{y-30}" width="{width-60}" height="{bottom-y+30}" rx="16" fill="{card}" fill-opacity=".5" stroke="{stroke}" stroke-dasharray="7 6"/><text x="52" y="{y}" fill="{stroke if band.get("tone")=="warning" else muted}" font-size="13" font-weight="600" font-family="sans-serif" letter-spacing="1.5">{esc(band["label"])}</text></g>')
    for i,(e,pts) in enumerate(zip(graph['edges'],routes)):
        color=colors['stop'] if e.get('tone')=='warning' else muted
        dash='stroke-dasharray="7 6"' if e.get('tone')=='warning' else ''
        d='M'+' L'.join(f'{x} {y}' for x,y in pts)
        s.append(f'<g class="flow-edge" data-edge="{i}" data-source="{esc(e["source"])}" data-target="{esc(e["target"])}"><path d="{d}" fill="none" stroke="{color}" stroke-width="2" {dash} marker-end="url(#arrow{color[1:]})" stroke-linejoin="round"/>')
        label=e.get('label','')
        if label:
            x,y,w=label_positions[i]
            s.append(f'<rect x="{x-w/2}" y="{y-17}" width="{w}" height="26" rx="7" fill="{bg}"/><text x="{x}" y="{y}" text-anchor="middle" font-family="sans-serif" font-size="13" fill="{color}">{esc(label)}</text>')
        s.append('</g>')
    for i,n in enumerate(graph['nodes']):
        x,y,w,h=boxes[n['id']];color=colors[n.get('role','process')];role={'process':'自动处理','human':'人工操作','decision':'检查条件','output':'交付结果','stop':'异常处理'}[n.get('role','process')]
        title_lines=wrap_text(n['label'],w-40,19)
        summary_lines=[line for t in n.get('summary',[]) for line in wrap_text(t,w-40,13)]
        role=graph.get('_roles',{}).get(role,role)
        s.append(f'<g class="flow-node" data-id="{esc(n["id"])}" data-role="{esc(n.get("role","process"))}" tabindex="0" role="button" aria-label="{esc(n["label"])}"><rect x="{x}" y="{y+4}" width="{w}" height="{h}" rx="15" fill="{border}" opacity=".3"/><rect x="{x}" y="{y}" width="{w}" height="{h}" class="node-card" rx="10" fill="{card}" stroke="{color}" stroke-width="1.8"/><rect x="{x}" y="{y+22}" width="4" height="{h-44}" rx="2" fill="{color}"/><text x="{x+20}" y="{y+25}" fill="{color}" font-size="11" font-family="sans-serif">{i+1:02d} / {role}</text>')
        for j,line in enumerate(title_lines):s.append(f'<text x="{x+20}" y="{y+(43 if len(title_lines)>1 else 53)+j*20}" fill="{ink}" font-size="19" font-weight="600" font-family="sans-serif">{esc(line)}</text>')
        for j,line in enumerate(summary_lines):s.append(f'<text x="{x+20}" y="{y+(84 if len(title_lines)>1 else 78)+j*19}" fill="{muted}" font-size="13" font-family="sans-serif">{esc(line)}</text>')
        s.append('</g>')
    s.append('</svg>');return ''.join(s)
