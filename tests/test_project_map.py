import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

spec=importlib.util.spec_from_file_location('mapper',Path(__file__).resolve().parents[1]/'scripts/project_map.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

class MapperTests(unittest.TestCase):
    def test_scan_does_not_execute_and_excludes_private_paths(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'pkg').mkdir();(root/'pkg/__init__.py').write_text('')
            (root/'pkg/one.py').write_text('from . import two\nraise RuntimeError("MUST NOT EXECUTE")')
            (root/'pkg/two.py').write_text('import pkg.one')
            (root/'secret.py').write_text('SENSITIVE_MARKER = 123')
            for folder in ['.hidden','node_modules','data','logs']:
                (root/folder).mkdir();(root/folder/'bad.py').write_text('SENSITIVE_MARKER = 123')
            (root/'linked.py').symlink_to(root/'secret.py')
            g,r=m.scan(root)
            self.assertEqual(r['files'],3)
            self.assertEqual({(e['source'],e['target']) for e in g['edges']},{('pkg/one.py','pkg/two.py'),('pkg/two.py','pkg/one.py')})
            self.assertNotIn('SENSITIVE_MARKER',json.dumps(g));self.assertNotIn('MUST NOT EXECUTE',json.dumps(g))
    def test_invalid_source_does_not_leak_error_source(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);(p/'broken.py').write_text('top_secret_value !!!')
            g,r=m.scan(p);self.assertEqual(len(r['errors']),1);self.assertNotIn('top_secret',json.dumps(r))
    def test_js_relative_and_comment(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);(p/'main.ts').write_text('// import x from "./fake"\nimport { x } from "./util.js";')
            (p/'util.ts').write_text('export const x = 1;')
            g,r=m.scan(p);self.assertEqual(len(g['edges']),1);self.assertEqual(g['edges'][0]['target'],'util.ts');self.assertEqual(g['edges'][0]['confidence'],'inferred')
    def test_html_injection_is_data(self):
        g={'version':1,'kind':'workflow','title':'</title><script>alert(1)</script>','nodes':[{'id':'x','label':'</script><script>alert(2)</script>'}],'edges':[]}
        page=m.render(g);self.assertNotIn('<script>alert(',page);self.assertIn('\\u003c/script',page)
    def test_validation_rejects_dangling_duplicate_and_unsafe_evidence(self):
        g={'version':1,'kind':'architecture','title':'x','nodes':[{'id':'a','label':'a'}],'edges':[{'source':'a','target':'b'}]}
        with self.assertRaises(ValueError):m.validate(g)
        g['edges']=[];g['nodes']*=2
        with self.assertRaises(ValueError):m.validate(g)
        g['nodes']=g['nodes'][:1];g['nodes'][0]['evidence']=[{'file':'../secrets','line':1}]
        with self.assertRaises(ValueError):m.validate(g)
    def test_no_overwrite(self):
        with tempfile.TemporaryDirectory() as d:
            g={'version':1,'kind':'workflow','title':'x','nodes':[],'edges':[]}
            with self.assertRaises(FileExistsError):m.write_outputs(g,d)
    def test_oversized_file(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);(p/'large.py').write_bytes(b'x'*(m.MAX_FILE+1))
            g,r=m.scan(p);self.assertEqual(r['files'],0);self.assertEqual(len(r['errors']),1)
    def test_overview_preserves_uncertainty(self):
        g={'version':1,'kind':'architecture','title':'x','nodes':[{'id':'a','label':'a','group':'A'},{'id':'b','label':'b','group':'B'}],'edges':[{'source':'a','target':'b','confidence':'inferred'}]}
        v=m.overview(g);m.validate(v);self.assertEqual(v['edges'][0]['confidence'],'inferred')

if __name__=='__main__':unittest.main()
