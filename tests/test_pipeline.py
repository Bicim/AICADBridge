"""İki aşamalı üretim hattı (pipeline) birim testleri — adsk gerektirmez."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from aicad_bridge.llm.pipeline import (  # noqa: E402
    CODER_PROMPT,
    PLANNER_PROMPT,
    build_correction_prompt,
    build_coder_prompt,
    is_simple_command,
    parse_plan_json,
    run_pipeline_helper,
    validate_plan,
    verify_plan,
)


# --------------------------------------------------------------------------
# parse_plan_json
# --------------------------------------------------------------------------
def test_parse_plan_json_fenced():
    text = 'İşte plan:\n```json\n{"chat": false, "features": []}\n```\nTamam.'
    assert parse_plan_json(text) == {'chat': False, 'features': []}


def test_parse_plan_json_raw():
    assert parse_plan_json('{"chat": true}') == {'chat': True}


def test_parse_plan_json_braces_slice():
    assert parse_plan_json('sonuç: {"chat": true} oldu') == {'chat': True}


def test_parse_plan_json_garbage():
    assert parse_plan_json('lorem ipsum') is None
    assert parse_plan_json('') is None
    assert parse_plan_json(None) is None
    assert parse_plan_json('[1, 2, 3]') is None  # nesne değil, liste


# --------------------------------------------------------------------------
# validate_plan
# --------------------------------------------------------------------------
def _raw_plan():
    return {
        'parameters': [{'name': 'cap_mm', 'value': 40, 'unit': 'mm'}],
        'features': [
            {'id': 'govde', 'type': 'extrude', 'description': 'silindir gövde',
             'params': {'shape': 'circle', 'diameter_mm': 40}},
            {'id': 'delikler', 'type': 'holes', 'description': '4 adet montaj deliği',
             'params': {'count': 4, 'diameter_mm': 5}},
        ],
    }


def test_validate_plan_ok_and_alias():
    ok, plan, err = validate_plan(_raw_plan())
    assert ok, err
    assert plan['features'][1]['type'] == 'hole'  # 'holes' -> 'hole' alias
    assert plan['features'][0]['type'] == 'extrude'
    assert plan['parameters'][0]['name'] == 'cap_mm'
    assert plan['chat'] is False


def test_validate_plan_bad_type():
    raw = _raw_plan()
    raw['features'][0]['type'] = 'teleport'
    ok, plan, err = validate_plan(raw)
    assert not ok
    assert 'bilinmiyor' in err
    assert 'extrude' in err  # izinli türler listeleniyor


def test_validate_plan_empty_features():
    ok, _, err = validate_plan({'features': []})
    assert not ok
    assert 'features' in err


def test_validate_plan_chat_escape():
    ok, plan, err = validate_plan({'chat': True})
    assert ok
    assert plan['chat'] is True
    assert plan['features'] == []


def test_validate_plan_duplicate_ids():
    raw = _raw_plan()
    raw['features'][1]['id'] = 'govde'
    ok, plan, err = validate_plan(raw)
    assert ok, err
    ids = [f['id'] for f in plan['features']]
    assert len(ids) == len(set(ids))
    assert ids[1].startswith('govde_')


def test_validate_plan_params_normalized():
    raw = {'features': [{'id': 'a', 'type': 'fillet'}], 'parameters': ['hatalı', {'name': 'r', 'value': 3}]}
    ok, plan, err = validate_plan(raw)
    assert ok, err
    assert plan['parameters'] == [{'name': 'r', 'value': 3, 'unit': 'mm'}]
    assert plan['features'][0]['params'] == {}


# --------------------------------------------------------------------------
# Basit komut kuralı
# --------------------------------------------------------------------------
def test_simple_command_cylinder():
    plan = is_simple_command('çapı 40 mm yüksekliği 20 mm olan bir silindir yap')
    assert plan is not None
    assert len(plan['features']) == 1
    f = plan['features'][0]
    assert f['type'] == 'extrude'
    assert f['params']['shape'] == 'circle'
    assert f['params']['diameter_mm'] == 40
    assert f['params']['height_mm'] == 20


def test_simple_command_box():
    plan = is_simple_command('50 x 30 mm taban, 10 mm yüksekliğinde dikdörtgen kutu')
    assert plan is not None
    f = plan['features'][0]
    assert f['params']['shape'] == 'rect'


def test_simple_command_complex_is_not_simple():
    assert is_simple_command('4 deliği olan bir silindir yap') is None
    assert is_simple_command('silindirin kenarlarını yuvarlat') is None
    assert is_simple_command('bir kutu ve üzerine bir silindir ekle') is None  # iki şekil birden
    assert is_simple_command('') is None


def test_simple_command_long_prompt_not_simple():
    assert is_simple_command('silindir ' + 'çok ayrıntılı ' * 30) is None


# --------------------------------------------------------------------------
# Geometrik doğrulama
# --------------------------------------------------------------------------
def _state(bodies, totals=True):
    res = {
        'has_design': True,
        'bodies_count': len(bodies),
        'bodies': bodies,
    }
    if totals:
        res['total_faces'] = sum(b['faces_count'] for b in bodies)
        res['total_edges'] = sum(b['edges_count'] for b in bodies)
        res['total_cylinder_faces'] = sum(b['cylinder_faces_count'] for b in bodies)
        res['total_volume_cm3'] = sum(b['volume_cm3'] for b in bodies)
    return res


def _body(faces=6, edges=12, cyl=0, vol=10.0):
    return {'faces_count': faces, 'edges_count': edges, 'cylinder_faces_count': cyl, 'volume_cm3': vol}


def _plan(features):
    return {'chat': False, 'parameters': [], 'features': features}


def test_verify_plan_ok_holes_match():
    # Senaryo: boş tasarım → plandaki extrude 1 gövde oluşturur, 4 delik açılır
    plan = _plan([{'id': 'govde', 'type': 'extrude', 'params': {}},
                  {'id': 'delik', 'type': 'hole', 'params': {'count': 4}}])
    before = _state([])
    after = _state([_body(faces=10, edges=16, cyl=4, vol=8.0)])
    res = verify_plan(plan, before, after)
    assert res['ok'] is True
    assert res['issues'] == []
    assert 'silindirik yüz 0→4' in res['metrics']


def test_verify_plan_hole_mismatch():
    plan = _plan([{'id': 'govde', 'type': 'extrude', 'params': {}},
                  {'id': 'delik', 'type': 'hole', 'params': {'count': 4}}])
    before = _state([])
    after = _state([_body(faces=8, edges=14, cyl=2, vol=9.0)])
    res = verify_plan(plan, before, after)
    assert res['ok'] is False
    assert len(res['issues']) == 1
    assert '4 delik' in res['issues'][0]['text']
    assert res['issues'][0]['features'] == ['delik']


def test_verify_plan_body_count_mismatch():
    plan = _plan([{'id': 'a', 'type': 'extrude', 'params': {}},
                  {'id': 'b', 'type': 'extrude', 'params': {}}])
    before = _state([])
    after = _state([_body()])
    res = verify_plan(plan, before, after)
    assert res['ok'] is False
    assert any('2 yeni katı gövde' in i['text'] for i in res['issues'])


def test_verify_plan_volume_not_increased():
    plan = _plan([{'id': 'a', 'type': 'extrude', 'params': {}}])
    before = _state([_body(vol=10.0)])
    after = _state([_body(vol=10.0)])
    res = verify_plan(plan, before, after)
    assert res['ok'] is False
    assert any('hacim' in i['text'] for i in res['issues'])


def test_verify_plan_cut_feature_does_not_expect_new_body():
    # cut/combine içeren planlarda gövde artışı beklentisi uygulanmaz
    plan = _plan([{'id': 'yuva', 'type': 'cut', 'params': {}}])
    before = _state([_body(vol=10.0)])
    after = _state([_body(faces=8, vol=8.0)])
    res = verify_plan(plan, before, after)
    assert res['ok'] is True


def test_verify_plan_without_before_state():
    plan = _plan([{'id': 'a', 'type': 'extrude', 'params': {}}])
    after = _state([_body(vol=5.0)])
    res = verify_plan(plan, None, after)
    assert res['before_known'] is False
    assert res['ok'] is True  # önceki durum bilinmiyorsa delta kontrolleri atlanır


def test_verify_plan_pattern_multiplies_expected_bodies():
    plan = _plan([{'id': 'a', 'type': 'extrude', 'params': {}},
                  {'id': 'p', 'type': 'pattern', 'params': {'count': 6}}])
    before = _state([])
    after = _state([_body()] * 6)
    res = verify_plan(plan, before, after)
    assert res['ok'] is True


# --------------------------------------------------------------------------
# Coder / düzeltme promptları
# --------------------------------------------------------------------------
def test_build_coder_prompt_contains_snippets_and_feature():
    plan = _plan([{'id': 'yuvarlat', 'type': 'fillet', 'description': 'kenar yuvarlatma', 'params': {'radius_mm': 3}}])
    res = build_coder_prompt(plan, plan['features'][0], ['✓ govde: gövde eklendi'], 'mevcut tasarım özeti')
    assert res['system'] == CODER_PROMPT
    assert 'yuvarlat' in res['user']
    assert 'kenar yuvarlatma' in res['user']
    assert 'ÖNCEKİ ADIMLAR' in res['user']
    assert 'MEVCUT TASARIM DURUMU' in res['user']
    # fillet snippet'i few-shot olarak eklenmiş olmalı
    assert 'addConstantRadiusEdgeSet' in res['user']


def test_build_correction_prompt_contains_issues_and_code():
    plan = _plan([{'id': 'delik', 'type': 'hole', 'description': 'delikler', 'params': {'count': 4}}])
    res = build_correction_prompt(plan, plan['features'][0],
                                  [{'text': 'Planda 4 delik istendi ancak 2 yeni silindirik yüz oluştu.', 'features': ['delik']}],
                                  current_code='print(1)')
    assert 'UYUŞMAZLIKLAR' in res['user']
    assert '4 delik' in res['user']
    assert 'MEVCUT KOD' in res['user']
    assert 'print(1)' in res['user']


# --------------------------------------------------------------------------
# run_pipeline_helper op göndericisi
# --------------------------------------------------------------------------
def test_helper_simplecheck():
    res = run_pipeline_helper({'op': 'simpleCheck', 'prompt': 'bir silindir yap'})
    assert res['ok'] is True
    assert res['simple'] is True
    assert res['plan']['features'][0]['type'] == 'extrude'


def test_helper_simplecheck_negative():
    res = run_pipeline_helper({'op': 'simpleCheck', 'prompt': 'uçak yap'})
    assert res['ok'] is True
    assert res['simple'] is False
    assert res['plan'] is None


def test_helper_planner_prompt():
    res = run_pipeline_helper({'op': 'plannerPrompt'})
    assert res['ok'] is True
    assert res['system'] == PLANNER_PROMPT
    assert 'ONLY valid JSON' in res['system']


def test_helper_validate_plan_roundtrip():
    import json
    raw = '```json\n' + json.dumps(_raw_plan()) + '\n```'
    res = run_pipeline_helper({'op': 'validatePlan', 'raw': raw})
    assert res['ok'] is True
    assert res['chat'] is False
    assert res['plan']['features'][1]['type'] == 'hole'


def test_helper_validate_plan_invalid():
    res = run_pipeline_helper({'op': 'validatePlan', 'raw': 'bu json değil'})
    assert res['ok'] is False
    assert 'JSON' in res['error']


def test_helper_verify_plan_with_injected_inspect():
    plan = _plan([{'id': 'govde', 'type': 'extrude', 'params': {}},
                  {'id': 'delik', 'type': 'hole', 'params': {'count': 2}}])
    after = _state([_body(faces=8, edges=14, cyl=2, vol=9.0)])
    res = run_pipeline_helper(
        {'op': 'verifyPlan', 'plan': plan, 'before': _state([])},
        inspect_state=lambda: after)
    assert res['ok'] is True
    assert res['issues'] == []
    assert 'gövde 0→1' in res['metrics']


def test_helper_verify_plan_skips_without_inspect():
    res = run_pipeline_helper({'op': 'verifyPlan', 'plan': _plan([])})
    assert res['ok'] is True
    assert res.get('skipped') is True


def test_helper_unknown_op():
    res = run_pipeline_helper({'op': 'bilinmeyen'})
    assert res['ok'] is False
    assert 'Bilinmeyen op' in res['error']


def test_helper_invalid_payload():
    res = run_pipeline_helper('geçersiz')
    assert res['ok'] is False
