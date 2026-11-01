"""Explicit local translations; never infer or fetch translated content."""
from copy import deepcopy
ROLES={'自动处理':'Automatic','人工操作':'Human action','检查条件':'Decision','交付结果':'Output','异常处理':'Exception'}
def localize(graph,language):
    result=deepcopy(graph)
    if language=='zh':return result
    translations=graph.get('translations',{}).get('en',{})
    def tr(value):return translations.get(value,value)
    for key in ['title','subtitle']:
        if key in result:result[key]=tr(result[key])
    for node in result['nodes']:
        for key in ['label','detail','group']:
            if key in node:node[key]=tr(node[key])
        if 'summary' in node:node['summary']=[tr(x) for x in node['summary']]
    for edge in result['edges']:
        if 'label' in edge:edge['label']=tr(edge['label'])
    for band in result.get('bands',[]):band['label']=tr(band['label'])
    for card in result.get('cards',[]):
        for key in ['title','body']:card[key]=tr(card[key])
    result['_roles']=ROLES
    return result
