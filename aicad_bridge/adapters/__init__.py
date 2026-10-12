"""Çoklu CAD adaptör yönlendiricisi (Fusion 360 & SolidWorks / Adam-CAD)."""

from aicad_bridge import config as app_config, runtime

SUPPORTED_TARGETS = ('fusion360', 'solidworks')


def normalize_cad_target(target):
    """CAD hedef adını ('fusion360' veya 'solidworks') normalize eder."""
    if not target:
        return None
    t = str(target).strip().lower()
    if t in ('sw', 'solidworks', 'solid', 'sldworks', 'adacad', 'adamcad', 'cadam'):
        return 'solidworks'
    if t in ('fusion', 'fusion360', 'adsk', 'autodesk'):
        return 'fusion360'
    return None


def get_active_cad_target(override=None):
    """Aktif CAD hedefini döndürür: override > runtime.active_cad_target > .env > ortam algılama."""
    norm = normalize_cad_target(override)
    if norm:
        return norm

    rt_target = normalize_cad_target(getattr(runtime, 'active_cad_target', None))
    if rt_target:
        return rt_target

    try:
        cfg_target = normalize_cad_target(app_config.get_settings().get('cad_target'))
        if cfg_target:
            return cfg_target
    except Exception:
        pass

    # Fusion 360 CPython ortamında değilsek ve runtime.app yoksa varsayılan olarak fusion360 döner
    return 'fusion360'


def set_active_cad_target(target):
    """Çalışma zamanı aktif CAD hedefini değiştirir ('fusion360' veya 'solidworks')."""
    norm = normalize_cad_target(target)
    if not norm:
        raise ValueError(f"Desteklenmeyen CAD hedefi: {target}. İzin verilenler: {SUPPORTED_TARGETS}")
    runtime.active_cad_target = norm
    return norm


def get_adapter(target=None):
    """Seçili CAD hedefine ait adaptör modülünü döndürür."""
    resolved = get_active_cad_target(target)
    if resolved == 'solidworks':
        from aicad_bridge.adapters import solidworks
        return solidworks
    from aicad_bridge.adapters import fusion360
    return fusion360
