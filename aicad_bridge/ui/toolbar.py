"""Fusion 360 araç çubuğu butonu ve komut tanımları."""

import os
import traceback

import adsk.core

from aicad_bridge import runtime
from aicad_bridge.runtime import CMD_ID, CMD_NAME, CMD_DESC, TOOLBAR_PANEL_ID, TOOLBAR_PANEL_NAME, aicad_log
from aicad_bridge.ui.palette import create_palette, show_palette


class ShowPaletteCommandExecuteHandler(adsk.core.CommandEventHandler):
    def notify(self, args):
        try:
            show_palette()
        except Exception as e:
            tb = traceback.format_exc()
            aicad_log(f"Palet açılırken hata oluştu: {e}\n{tb}")
            try:
                create_palette()
            except Exception:
                pass


class ShowPaletteCommandCreatedHandler(adsk.core.CommandCreatedEventHandler):
    def notify(self, args):
        try:
            cmd = args.command
            on_execute = ShowPaletteCommandExecuteHandler()
            cmd.execute.add(on_execute)
            runtime.handlers.append(on_execute)
        except Exception:
            traceback.print_exc()


def setup_toolbar_button():
    try:
        current_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        icon_folder = os.path.join(current_dir, 'resources')
        if not os.path.exists(icon_folder):
            icon_folder = os.path.join(current_dir, 'commands', 'paletteShow', 'resources')

        workspace = runtime.ui.workspaces.itemById('FusionSolidEnvironment')
        if not workspace:
            aicad_log("FusionSolidEnvironment bulunamadı!")
            return

        cmd_def = runtime.ui.commandDefinitions.itemById(CMD_ID)
        if cmd_def:
            try:
                cmd_def.deleteMe()
            except Exception:
                pass
            cmd_def = None

        cmd_def = runtime.ui.commandDefinitions.addButtonDefinition(
            CMD_ID,
            CMD_NAME,
            CMD_DESC,
            icon_folder
        )
        on_cmd_created = ShowPaletteCommandCreatedHandler()
        cmd_def.commandCreated.add(on_cmd_created)
        runtime.handlers.append(on_cmd_created)

        # 1. Modern Ribbon Tab: FusionSolidEnvironment -> SolidTab
        panel = None
        try:
            solid_tab = workspace.toolbarTabs.itemById('SolidTab')
            if solid_tab:
                panel = solid_tab.toolbarPanels.itemById(TOOLBAR_PANEL_ID)
                if not panel:
                    try:
                        # Position right after SolidSelectPanel (SEÇ)
                        panel = solid_tab.toolbarPanels.add(TOOLBAR_PANEL_ID, TOOLBAR_PANEL_NAME, 'SolidSelectPanel', False)
                        aicad_log("SolidTab üzerinde SolidSelectPanel (SEÇ) yanına AI CAD paneli eklendi.")
                    except Exception as e1:
                        aicad_log(f"SolidSelectPanel yanına eklenemedi ({e1}), tab sonuna ekleniyor...")
                        panel = solid_tab.toolbarPanels.add(TOOLBAR_PANEL_ID, TOOLBAR_PANEL_NAME)
        except Exception as e:
            aicad_log(f"toolbarTabs üzerinden panel ekleme hatası: {e}")

        # 2. Fallback: workspace.toolbarPanels
        if not panel:
            try:
                panel = workspace.toolbarPanels.itemById(TOOLBAR_PANEL_ID)
                if not panel:
                    try:
                        panel = workspace.toolbarPanels.add(TOOLBAR_PANEL_ID, TOOLBAR_PANEL_NAME, 'SolidSelectPanel', False)
                    except Exception:
                        panel = workspace.toolbarPanels.add(TOOLBAR_PANEL_ID, TOOLBAR_PANEL_NAME)
            except Exception as e:
                aicad_log(f"workspace.toolbarPanels üzerinden panel ekleme hatası: {e}")

        # 3. Add command to panel and promote it to ribbon
        if panel:
            ctrl = panel.controls.itemById(CMD_ID)
            if not ctrl:
                ctrl = panel.controls.addCommand(cmd_def)
            ctrl.isPromoted = True
            ctrl.isPromotedByDefault = True
            ctrl.isVisible = True
            aicad_log(f"AI CAD Studio butonu {panel.id} paneline eklendi ve ribbon üzerinde öne çıkarıldı (promoted).")

        # 4. Fallback in SolidScriptsAddinsPanel as secondary location
        try:
            scripts_panel = workspace.toolbarPanels.itemById('SolidScriptsAddinsPanel')
            if scripts_panel and not scripts_panel.controls.itemById(CMD_ID):
                scripts_panel.controls.addCommand(cmd_def)
        except Exception:
            pass

    except Exception as e:
        tb = traceback.format_exc()
        aicad_log(f"setup_toolbar_button HATA: {e}\n{tb}")


def cleanup_toolbar():
    """Araç çubuğu ve komut tanımlarını Fusion'dan temizler."""
    if not runtime.ui:
        return
    ui = runtime.ui
    try:
        workspace = ui.workspaces.itemById('FusionSolidEnvironment')
        if workspace:
            # Clean from SolidTab
            try:
                solid_tab = workspace.toolbarTabs.itemById('SolidTab')
                if solid_tab:
                    p = solid_tab.toolbarPanels.itemById(TOOLBAR_PANEL_ID)
                    if p:
                        c = p.controls.itemById(CMD_ID)
                        if c:
                            c.deleteMe()
                        p.deleteMe()
            except Exception:
                pass

            # Clean from workspace.toolbarPanels
            try:
                p = workspace.toolbarPanels.itemById(TOOLBAR_PANEL_ID)
                if p:
                    c = p.controls.itemById(CMD_ID)
                    if c:
                        c.deleteMe()
                    p.deleteMe()
            except Exception:
                pass

            # Clean from SolidScriptsAddinsPanel
            try:
                p = workspace.toolbarPanels.itemById('SolidScriptsAddinsPanel')
                if p:
                    c = p.controls.itemById(CMD_ID)
                    if c:
                        c.deleteMe()
            except Exception:
                pass

        cmd_def = ui.commandDefinitions.itemById(CMD_ID)
        if cmd_def:
            cmd_def.deleteMe()
    except Exception:
        pass
