import urllib.request, json

# Code that only creates a sketch with a circle, but NO extrude!
test_cad_code = '''
app = adsk.core.Application.get()
design = adsk.fusion.Design.cast(app.activeProduct)
root = design.rootComponent
sk = root.sketches.add(root.xYConstructionPlane)
sk.sketchCurves.sketchCircles.addByCenterRadius(adsk.core.Point3D.create(0, 0, 0), 2.0)
'''

req = urllib.request.Request(
    'http://127.0.0.1:49876/execute',
    data=json.dumps({'code': test_cad_code}).encode('utf-8'),
    headers={'Content-Type': 'application/json'}
)

try:
    with urllib.request.urlopen(req, timeout=10) as resp:
        res = json.loads(resp.read().decode('utf-8'))
        print("RESULT FOR SKETCH-ONLY CODE:")
        print(json.dumps(res, indent=2, ensure_ascii=False))
except Exception as e:
    print("Error:", e)
