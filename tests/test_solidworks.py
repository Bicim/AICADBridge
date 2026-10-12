import unittest
from unittest.mock import MagicMock, patch

from aicad_bridge import adapters
from aicad_bridge.adapters import solidworks
from aicad_bridge.llm import pipeline, prompt as llm_prompt
from snippets import loader as snippet_loader


class FakeBody:
    def __init__(self, name='Boss-Extrude1', box=(-0.05, -0.05, 0.0, 0.05, 0.05, 0.02)):
        self.Name = name
        self._box = box

    def GetBodyBox(self):
        return self._box

    def GetFaceCount(self):
        return 6

    def GetEdgeCount(self):
        return 12

    def GetFaces(self):
        return []

    def GetMassProperties(self, _):
        # 4th element (index 3) is volume in m^3
        return (0.0, 0.0, 0.0, 0.00015, 0.0)


class FakeModelDoc:
    def __init__(self):
        self.bodies = [FakeBody('Boss-Extrude1')]
        self.Extension = MagicMock()
        self.Extension.SelectByID2 = MagicMock(return_value=True)
        self.SketchManager = MagicMock()
        self.FeatureManager = MagicMock()
        self.FeatureManager.FeatureExtrusion2 = MagicMock(return_value=MagicMock(Name='Boss-Extrude2'))
        self.FeatureManager.FeatureCut4 = MagicMock(return_value=MagicMock(Name='Cut-Extrude1'))
        self.FeatureManager.FeatureRevolve2 = MagicMock(return_value=MagicMock(Name='Revolve1'))
        self.FeatureManager.FeatureFillet3 = MagicMock(return_value=MagicMock(Name='Fillet1'))
        self.FeatureManager.InsertFeatureChamfer = MagicMock(return_value=MagicMock(Name='Chamfer1'))

    def GetType(self):
        return solidworks.SW_DOC_PART

    def GetTitle(self):
        return 'Flans_Modeli.SLDPRT'

    def GetBodies2(self, body_type, visible_only):
        return list(self.bodies)

    def ClearSelection2(self, _):
        return True

    def EditRebuild3(self):
        return True

    def ViewZoomtofit2(self):
        return True

    def ShowNamedView2(self, name, view_id):
        return True

    def FirstFeature(self):
        return None


class TestSolidWorksAdapterAndPipeline(unittest.TestCase):
    def test_adapter_router_normalization(self):
        self.assertEqual(adapters.normalize_cad_target('solidworks'), 'solidworks')
        self.assertEqual(adapters.normalize_cad_target('sw'), 'solidworks')
        self.assertEqual(adapters.normalize_cad_target('adacad'), 'solidworks')
        self.assertEqual(adapters.normalize_cad_target('adamcad'), 'solidworks')
        self.assertEqual(adapters.normalize_cad_target('fusion360'), 'fusion360')
        self.assertIsNone(adapters.normalize_cad_target('unknown'))

        adapters.set_active_cad_target('solidworks')
        self.assertEqual(adapters.get_active_cad_target(), 'solidworks')
        self.assertIs(adapters.get_adapter('solidworks'), solidworks)
        adapters.set_active_cad_target('fusion360')

    def test_solidworks_cad_helper_methods(self):
        fake_model = FakeModelDoc()
        fake_app = MagicMock()
        helper = solidworks.SolidWorksCADHelper(fake_app, fake_model)

        feat_cyl = helper.extrude_cylinder(100, 20, plane='Top')
        self.assertIsNotNone(feat_cyl)
        fake_model.SketchManager.CreateCircleByRadius.assert_called_with(0.0, 0.0, 0.0, 0.05)

        feat_box = helper.extrude_box(80, 60, 15, plane='Top')
        self.assertIsNotNone(feat_box)
        fake_model.SketchManager.CreateCenterRectangle.assert_called_with(0.0, 0.0, 0.0, 0.04, 0.03, 0.0)

        feat_hole = helper.cut_hole(30, 25, plane='Top')
        self.assertIsNotNone(feat_hole)

        feat_bolt = helper.cut_bolt_circle(70, 8, 6, 25, plane='Top')
        self.assertIsNotNone(feat_bolt)

        param_val = helper.define_parameter('DIS_CAP', 120)
        self.assertEqual(param_val, 120.0)
        self.assertEqual(helper.parameters['DIS_CAP']['value'], 120.0)

    def test_inspect_current_design_with_mock_com(self):
        fake_model = FakeModelDoc()
        fake_app = MagicMock()
        fake_app.ActiveDoc = fake_model

        with patch.object(solidworks, 'get_sw_app', return_value=fake_app):
            state = solidworks.inspect_current_design()
            self.assertTrue(state['has_design'])
            self.assertEqual(state['cad_target'], 'solidworks')
            self.assertEqual(state['bodies_count'], 1)
            self.assertEqual(state['bodies'][0]['dimensions_mm']['width_x'], 100.0)
            self.assertEqual(state['bodies'][0]['dimensions_mm']['height_z'], 20.0)
            self.assertIn('SolidWorks', state['summary_text'])

    def test_execute_code_with_mock_com(self):
        fake_model = FakeModelDoc()
        fake_app = MagicMock()
        fake_app.ActiveDoc = fake_model

        def add_body_on_extrude(*args, **kwargs):
            new_b = FakeBody(f'Boss-Extrude{len(fake_model.bodies) + 1}')
            fake_model.bodies.append(new_b)
            return MagicMock(Name=new_b.Name)

        fake_model.FeatureManager.FeatureExtrusion3.side_effect = add_body_on_extrude
        fake_model.FeatureManager.FeatureExtrusion2.side_effect = add_body_on_extrude

        with patch.object(solidworks, 'get_sw_app', return_value=fake_app):
            code = "sw.extrude_cylinder(100, 20, plane='Top')\nsw.rebuild()"
            res = solidworks.execute_code(code)
            self.assertTrue(res['success'])
            self.assertEqual(res['cad_target'], 'solidworks')
            self.assertEqual(res['new_bodies_count'], 1)
            self.assertIn('Boss-Extrude2', res['new_bodies'])

    def test_solidworks_snippets_and_pipeline_prompts(self):
        sw_index = snippet_loader.load_index(cad_target='solidworks')
        self.assertGreaterEqual(len(sw_index.get('snippets', [])), 5)

        snips = snippet_loader.find_snippets(feature_type='extrude', include_code=True, cad_target='solidworks')
        self.assertGreaterEqual(len(snips), 1)
        self.assertIn('sw.', snips[0]['code'])

        plan = {
            'summary': 'Test flanş planı',
            'parameters': [{'name': 'dis_cap', 'value': 100, 'unit': 'mm'}],
            'features': [{'id': 'f1', 'type': 'extrude', 'description': 'Ana gövde', 'params_used': ['dis_cap'], 'depends_on': []}],
        }
        cp = pipeline.build_coder_prompt(plan, plan['features'][0], cad_target='solidworks')
        self.assertIn('SolidWorks', cp['system'])
        self.assertIn('sw.extrude_cylinder', cp['system'])
        self.assertIn('SolidWorks (Adam-CAD', cp['user'])

        sys_p = llm_prompt.get_system_prompt('solidworks')
        self.assertIn('SolidWorks', sys_p)


if __name__ == '__main__':
    unittest.main()
