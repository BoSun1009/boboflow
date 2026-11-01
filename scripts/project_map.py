#!/usr/bin/env python3
"""Local static dependency mapper. Standard library only; never imports target code."""
import argparse
import ast
import hashlib
import html
import json
import os
from pathlib import Path
import re
import stat
import sys

EXTS = {'.py', '.js', '.jsx', '.ts', '.tsx', '.mjs', '.cjs'}
SKIP = {'node_modules','vendor','venv','__pycache__','dist','build','coverage','target','data','datasets','logs','log','audit','metadata','generated','plans','learning','backups','archive','fixtures','testdata'}
SENSITIVE = re.compile(r'(?:^|[._-])(?:env|secret|secrets|credential|credentials|token|tokens|password|passwords|private|key|keys)(?:[._-]|$)', re.I)
MAX_FILE = 512 * 1024
MAX_TOTAL = 20 * 1024 * 1024
MAX_FILES = 1500

def allowed(name):
    return not name.startswith('.') and not SENSITIVE.search(name)

def read_regular(path, limit):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, 'rb') as f:
        info = os.fstat(f.fileno())
        if not stat.S_ISREG(info.st_mode):
            raise ValueError('not a regular file')
        if info.st_size > limit:
            raise ValueError('file exceeds size limit')
        raw = f.read(limit + 1)
        if len(raw) > limit: raise ValueError('file exceeds size limit')
        return raw

def python_imports(source, relative):
    tree = ast.parse(source)
    parts = list(Path(relative).with_suffix('').parts)
    package = parts[:-1]
    imports = []
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            imports.extend((a.name, n.lineno, 'observed') for a in n.names)
        elif isinstance(n, ast.ImportFrom):
            if n.level:
                if n.level > len(package): continue
                base = package[:len(package)-n.level+1] + ((n.module or '').split('.') if n.module else [])
                module = '.'.join(base)
            else: module = n.module or ''
            for a in n.names:
                imports.append((module + ('.' + a.name if module and a.name != '*' else ''), n.lineno, 'observed'))
    return imports

def js_imports(source):
    # Mask comments, preserving newlines and string contents. Parsing remains heuristic.
    pattern = r'("(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|`(?:\\.|[^`\\])*`)|(//[^\n]*|/\*[\s\S]*?\*/)'
    source = re.sub(pattern, lambda m: m[1] if m[1] else re.sub(r'[^\n]', ' ', m[2]), source)
    pattern = r'(?m)^\s*(?:import\s+(?:type\s+)?(?:[^;\n]*?\s+from\s+)?|export\s+[^;\n]*?\s+from\s+)["\']([^"\'\n]+)["\']'
    return [(m[1], source.count('\n',0,m.start())+1, 'inferred') for m in re.finditer(pattern, source)]

def scan(root):
    root = Path(root).resolve(strict=True)
    if not root.is_dir(): raise ValueError('project must be a directory')
    report = {'files':0,'bytes':0,'excluded_entries':0,'truncated':False,'errors':[], 'unresolved_imports':0,
              'limitations':['Static imports only; no runtime execution or complete call graph.', 'JS/TS imports are heuristic; aliases and dynamic imports are unresolved.', 'Hidden, sensitive-named, data, log, dependency and generated paths excluded.', 'No code snippets are stored; names alone may still reveal project structure.']}
    contents = {}
    for base, dirs, files in os.walk(root, followlinks=False):
        keep=[]
        for d in sorted(dirs):
            p=Path(base)/d
            if allowed(d) and d.lower() not in SKIP and not p.is_symlink(): keep.append(d)
            else: report['excluded_entries']+=1
        dirs[:]=keep
        for name in sorted(files):
            p=Path(base)/name
            if p.suffix not in EXTS or not allowed(name) or p.is_symlink():
                report['excluded_entries']+=1; continue
            if len(contents)>=MAX_FILES or report['bytes']>=MAX_TOTAL:
                report['truncated']=True; break
            rel=p.relative_to(root).as_posix()
            try:
                resolved=p.resolve(strict=True)
                if not resolved.is_relative_to(root): raise ValueError('outside project')
                raw=read_regular(p,min(MAX_FILE,MAX_TOTAL-report['bytes']))
                report['bytes']+=len(raw)
                source=raw.decode('utf-8-sig')
                imports=python_imports(source,rel) if p.suffix=='.py' else js_imports(source)
                contents[rel]=imports
            except (OSError, ValueError, SyntaxError, UnicodeError) as e:
                # Do not include exception messages: SyntaxError can contain source.
                report['errors'].append({'file':rel,'reason':type(e).__name__})
        if report['truncated']: break
    report['files']=len(contents)
    modules={}
    for rel in contents:
        if rel.endswith('.py'):
            m=rel[:-3].replace('/','.')
            if m.endswith('.__init__'):m=m[:-9]
            modules[m]=rel
    nodes=[{'id':rel,'label':Path(rel).name,'group':str(Path(rel).parent) if '/' in rel else '入口', 'detail':rel,'evidence':[{'file':rel,'line':1}]} for rel in contents]
    edges={}
    for rel, imports in contents.items():
        for imp,line,confidence in imports:
            target=None
            if rel.endswith('.py'):
                bits=imp.split('.')
                while bits:
                    target=modules.get('.'.join(bits))
                    if target:break
                    bits.pop()
            elif imp.startswith('.'):
                # Pure lexical resolution; no reading outside the scan inventory.
                base=os.path.normpath(str(Path(rel).parent/imp)).replace(os.sep,'/')
                candidates=[base]+[base+x for x in sorted(EXTS-{'.py'})]+[base+'/index'+x for x in sorted(EXTS-{'.py'})]
                if base.endswith('.js'): candidates += [base[:-3]+'.ts',base[:-3]+'.tsx']
                target=next((x for x in candidates if x in contents),None)
            if not target:
                report['unresolved_imports']+=1;continue
            key=(rel,target)
            edge=edges.setdefault(key,{'source':rel,'target':target,'label':'导入','confidence':confidence,'evidence':[]})
            if len(edge['evidence'])<20:edge['evidence'].append({'file':rel,'line':line})
    if len(edges)>10000:
        report['truncated']=True
        edges=dict(list(edges.items())[:10000])
    graph={'version':1,'kind':'architecture','title':root.name+' · 模块依赖','nodes':nodes,'edges':list(edges.values())}
    return graph,report

def validate(g):
    if not isinstance(g,dict) or g.get('version')!=1 or g.get('kind') not in {'architecture','workflow'}:raise ValueError('invalid graph header')
    if not isinstance(g.get('title'),str) or len(g['title'])>200:raise ValueError('invalid title')
    nodes,edges=g.get('nodes'),g.get('edges')
    if not isinstance(nodes,list) or not isinstance(edges,list) or len(nodes)>2000 or len(edges)>10000:raise ValueError('invalid graph size')
    ids=set()
    for n in nodes:
        if not isinstance(n,dict):raise ValueError('invalid node')
        for k in ['id','label']:
            if not isinstance(n.get(k),str) or not n[k] or len(n[k])>500:raise ValueError('invalid node text')
        if n['id'] in ids:raise ValueError('duplicate node')
        ids.add(n['id'])
        for k in ['group','detail']:
            if k in n and (not isinstance(n[k],str) or len(n[k])>1000):raise ValueError('invalid node detail')
    for e in edges:
        if not isinstance(e,dict) or e.get('source') not in ids or e.get('target') not in ids:raise ValueError('dangling edge')
        if e.get('confidence','manual') not in {'observed','inferred','manual'}:raise ValueError('invalid confidence')
        if not isinstance(e.get('label',''),str) or len(e.get('label',''))>200:raise ValueError('invalid edge label')
    views=g.get('views',[])
    if not isinstance(views,list) or len(views)>5:raise ValueError('invalid story chapters')
    chapter_ids=set()
    for view in views:
        if not isinstance(view,dict) or not isinstance(view.get('id'),str) or not view['id'] or len(view['id'])>100 or view['id'] in chapter_ids:raise ValueError('invalid chapter id')
        chapter_ids.add(view['id'])
        stops=view.get('nodes')
        if not isinstance(stops,list) or not 2<=len(stops)<=100 or any(not isinstance(n,str) or n not in ids for n in stops):raise ValueError('invalid chapter stops')
        for a,b in zip(stops,stops[1:]):
            if sum(e['source']==a and e['target']==b for e in edges)!=1:raise ValueError('chapter requires unique directed transitions')
        label=view.get('label',view['id'])
        if isinstance(label,dict):
            if any(not isinstance(v,str) or len(v)>200 for v in label.values()):raise ValueError('invalid chapter label')
        elif not isinstance(label,str) or len(label)>200:raise ValueError('invalid chapter label')
    for item in nodes+edges:
        ev=item.get('evidence',[])
        if not isinstance(ev,list) or len(ev)>100:raise ValueError('invalid evidence')
        for v in ev:
            if not isinstance(v,dict):raise ValueError('invalid evidence entry')
            f=v.get('file','');line=v.get('line')
            if not isinstance(f,str) or not f or len(f)>500 or Path(f).is_absolute() or '..' in Path(f).parts or '\\' in f or re.match(r'^[A-Za-z]:',f):raise ValueError('unsafe evidence path')
            if type(line)!=int or line<1:raise ValueError('invalid evidence line')
    return g

def overview(g):
    groups={n['id']:n.get('group','未分组') for n in g['nodes']}
    names=sorted(set(groups.values()))
    nodes=[{'id':s,'label':s,'group':s,'detail':str(sum(v==s for v in groups.values()))+' 个文件','evidence':[]} for s in names]
    links={}
    for e in g['edges']:
        a,b=groups[e['source']],groups[e['target']]
        if a==b:continue
        x=links.setdefault((a,b),{'source':a,'target':b,'label':'','confidence':e.get('confidence','manual'),'evidence':[],'count':0})
        x['count']+=1
        if e.get('confidence')=='inferred':x['confidence']='inferred'
        x['evidence']=(x['evidence']+e.get('evidence',[]))[:20]
    for x in links.values():x['label']=str(x.pop('count'))+' 条依赖'
    return {'version':1,'kind':'architecture','title':g['title'].replace('模块依赖','分组概览'),'nodes':nodes,'edges':list(links.values())}

def render(g):
    validate(g)
    template=(Path(__file__).resolve().parent.parent/'assets/viewer.html').read_text()
    if g.get('layout',{}).get('mode')=='authored':
        import importlib.util
        spec=importlib.util.spec_from_file_location('workflow_layout',Path(__file__).with_name('workflow_layout.py'))
        mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
        template=(Path(__file__).resolve().parent.parent/'assets/workflow.html').read_text()
        template=template.replace('__EXPLORER_SCRIPT__',(Path(__file__).resolve().parent.parent/'assets/explorer.js').read_text())
        template=template.replace('__SIGNAL_SCRIPT__',(Path(__file__).resolve().parent.parent/'assets/signal.js').read_text())
        locspec=importlib.util.spec_from_file_location('localization',Path(__file__).with_name('localization.py'))
        loc=importlib.util.module_from_spec(locspec);locspec.loader.exec_module(loc)
        localized={lang:loc.localize(g,lang) for lang in ['zh','en']}
        for lang,lg in localized.items():
            width,height,boxes,routes=mod.prepare(lg)
            lg['layout'].update(width=width,height=height)
            for node in lg['nodes']:
                x,y,w,h=boxes[node['id']];node['position']=[x,y];node['size']=[w,h]
            for edge,points in zip(lg['edges'],routes):edge['points']=points
            for theme in ['light','dark']:
                template=template.replace('__'+lang.upper()+'_'+theme.upper()+'_SVG__',mod.build_svg(lg,theme=='dark'))
        english=localized['en']
        template=template.replace('__SUBTITLE__',html.escape(english.get('subtitle',''))).replace('__CARDS__',''.join('<div class="card"><strong>'+html.escape(c['title'])+'</strong><p>'+html.escape(c['body'])+'</p></div>' for c in english.get('cards',[])))
        template=template.replace('__PAGE_TITLE__',html.escape(english['title']))
        template=template.replace('__LOCALIZED_DATA__',json.dumps(localized,ensure_ascii=False).replace('<','\\u003c').replace('>','\\u003e').replace('&','\\u0026'))
    payload=json.dumps(g,ensure_ascii=False).replace('<','\\u003c').replace('>','\\u003e').replace('&','\\u0026')
    return template.replace('__GRAPH_DATA__',payload).replace('__PAGE_TITLE__',html.escape(g['title']))

def write_outputs(g, out, report=None):
    validate(g)
    page=render(g)
    out=Path(out)
    out.mkdir(parents=True,exist_ok=False)
    (out/'diagram.json').write_text(json.dumps(g,ensure_ascii=False,indent=2))
    (out/'diagram.html').write_text(page)
    if g.get('layout',{}).get('mode')=='authored':
        for language in ['en','zh']:
            for theme in ['light','dark']:
                block=page.split('id="svg-'+language+'-'+theme+'">',1)[1].split('</svg>',1)[0]+'</svg>'
                (out/('diagram-'+language+'-'+theme+'.svg')).write_text(block)
    if report is not None:
        (out/'scan-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
        (out/'overview.html').write_text(render(overview(g)))
    if g.get('layout',{}).get('mode')=='authored':
        import importlib.util
        helpers={}
        for name in ['workflow_layout','localization']:
            spec=importlib.util.spec_from_file_location(name,Path(__file__).with_name(name+'.py'))
            module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);helpers[name]=module
        checks={language:helpers['workflow_layout'].inspect_layout(helpers['localization'].localize(g,language)) for language in ['en','zh']}
        (out/'layout-checks.json').write_text(json.dumps(checks,ensure_ascii=False,indent=2))
    receipt={'nodes':len(g['nodes']),'edges':len(g['edges']),'html_sha256':hashlib.sha256(page.encode()).hexdigest(),'network':'none','project_execution':False,'validation':'schema and references only; no runtime claims'}
    (out/'receipt.json').write_text(json.dumps(receipt,indent=2))
    return receipt

def main():
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='command',required=True)
    for command in ['scan','render']:
        q=sub.add_parser(command);q.add_argument('input');q.add_argument('--out',required=True)
    a=p.parse_args()
    try:
        if a.command=='scan':
            root=Path(a.input).resolve(strict=True);out=Path(a.out).resolve()
            if out.is_relative_to(root):raise ValueError('output must be outside scanned project')
            if out.exists():raise ValueError('output directory already exists')
            g,report=scan(root);receipt=write_outputs(g,out,report)
            print(json.dumps({'output':str(out),'files':report['files'],'edges':receipt['edges'],'errors':len(report['errors']),'truncated':report['truncated']},ensure_ascii=False))
        else:
            raw=read_regular(Path(a.input),8*1024*1024)
            receipt=write_outputs(json.loads(raw),a.out)
            print(json.dumps({'output':str(Path(a.out).resolve()),**receipt},ensure_ascii=False))
    except (OSError,ValueError,RecursionError) as e:
        print('Error: '+str(e),file=sys.stderr);return 1
    return 0

if __name__=='__main__':sys.exit(main())
