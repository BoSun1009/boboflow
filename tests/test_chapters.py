import importlib.util
from pathlib import Path
import unittest
s=importlib.util.spec_from_file_location('mapper',Path(__file__).resolve().parents[1]/'scripts/project_map.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
class ChapterTests(unittest.TestCase):
 def graph(self):return {'version':1,'kind':'workflow','title':'Example','nodes':[{'id':'a','label':'A'},{'id':'b','label':'B'}],'edges':[{'source':'a','target':'b'}],'views':[{'id':'main','nodes':['a','b'],'label':{'en':'Main','zh':'主线'}}]}
 def test_valid_directed_chapter(self):m.validate(self.graph())
 def test_nonexistent_reverse_transition_rejected(self):
  g=self.graph();g['views'][0]['nodes']=['b','a']
  with self.assertRaises(ValueError):m.validate(g)
 def test_ambiguous_parallel_edges_rejected(self):
  g=self.graph();g['edges'].append({'source':'a','target':'b'})
  with self.assertRaises(ValueError):m.validate(g)
 def test_invalid_chapter_structure_rejected(self):
  g=self.graph();g['views']={'nodes':['a','b']}
  with self.assertRaises(ValueError):m.validate(g)
