import importlib.util
from pathlib import Path
import unittest
s=importlib.util.spec_from_file_location('layout',Path(__file__).resolve().parents[1]/'scripts/workflow_layout.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
class LayoutTests(unittest.TestCase):
 def graph(self):return {'title':'Example','nodes':[{'id':'a','label':'开始','position':[20,50]},{'id':'b','label':'结束','position':[400,50]}],'edges':[{'source':'a','target':'b','points':[[270,104],[400,104]]}]}
 def test_valid_svg(self):
  import xml.etree.ElementTree as ET
  g=self.graph();m.prepare(g);ET.fromstring(m.build_svg(g))
 def test_overlap(self):
  g=self.graph();g['nodes'][1]['position']=[50,50]
  with self.assertRaises(ValueError):m.prepare(g)
 def test_bad_endpoint(self):
  g=self.graph();g['edges'][0]['points'][0]=[280,104]
  with self.assertRaises(ValueError):m.prepare(g)
 def test_crossing_node(self):
  g=self.graph();g['nodes'].append({'id':'c','label':'阻挡','position':[280,50],'size':[160,90]});g['nodes'][1]['position']=[600,50];g['edges'][0]['points'][-1]=[600,104]
  with self.assertRaises(ValueError):m.prepare(g)
 def test_script_label_escaped(self):
  g=self.graph();g['nodes'][0]['label']='<script>alert(1)</script>';self.assertNotIn('<script>',m.build_svg(g))
 def test_label_repositions_away_from_node(self):
  g=self.graph();g['edges'][0].update(label='Submit',label_position=[100,90])
  w,h,boxes,routes=m.prepare(g);pos=m.labels_for(g,boxes,routes,w,h)[0]
  self.assertNotEqual(pos[:2],(100,90));self.assertFalse(any(m.overlap((pos[0]-pos[2]/2,pos[1]-17,pos[2],26),b) for b in boxes.values()))
 def test_long_summary_rejected(self):
  g=self.graph();g['nodes'][0]['summary']=['This is a very long summary that will not fit inside two lines of a normal workflow node without losing some of its content.']
  with self.assertRaises(ValueError):m.inspect_layout(g)
 def test_render_is_deterministic(self):
  self.assertEqual(m.build_svg(self.graph()),m.build_svg(self.graph()))
 def test_translations_preserve_graph_identity(self):
  spec=importlib.util.spec_from_file_location('localization',Path(__file__).resolve().parents[1]/'scripts/localization.py');loc=importlib.util.module_from_spec(spec);spec.loader.exec_module(loc)
  g=self.graph();g['translations']={'en':{'开始':'Start','结束':'Finish'}}
  result=loc.localize(g,'en');self.assertEqual(result['nodes'][0]['id'],'a');self.assertEqual(result['nodes'][0]['label'],'Start');self.assertEqual(g['nodes'][0]['label'],'开始');self.assertEqual(result['edges'],g['edges'])
 def test_swimlane_rejects_non_numeric_attributes(self):
  g=self.graph();g['bands']=[{'y':'60" onload="alert(1)','label':'Unsafe'}]
  with self.assertRaises(ValueError):m.build_svg(g)
 def test_swimlane_rejects_inverted_bounds(self):
  g=self.graph();g['bands']=[{'y':100,'bottom':50,'label':'Invalid'}]
  with self.assertRaises(ValueError):m.build_svg(g)
