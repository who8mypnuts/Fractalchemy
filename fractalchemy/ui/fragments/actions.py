"""The Fragments window's actions, menus and toolbars — built here so the window stays coordination only.

The menu layout follows FragM's (File / Edit / Build / Render / Parameters / Animation / Library / Windows / Help; see
appendix A of the plan) with FragM's shortcuts where they do not collide: `F1` reset all, `F2` / `F3` copy / paste
settings, `F4` group → preset, `F5` build, `F8` add preset, `F9` select preset. Shortcuts are window-local.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import QUrl
from PySide6.QtGui import QActionGroup, QDesktopServices, QKeySequence
from PySide6.QtWidgets import QMenu, QToolBar

from ...fragments.examples import example_tree, examples_dir
from ...fragments.templates import BUILTIN_TEMPLATES, CODE_SNIPPETS, SNIPPETS, user_templates
from ...widgets.actions import make_action, populate
from ...widgets.icons import action_icon, editor_icon
from . import help

if TYPE_CHECKING:
    from .window import FragmentsWindow


class FragmentActions:
    """Creates and holds the window's QActions (attributes named after FragM's), menus and toolbars."""

    def __init__(self, window: "FragmentsWindow"):
        self.w = window
        w = window
        act = lambda text, icon, slot, shortcut=None, tip="", checkable=False: make_action(w, text, icon, slot, shortcut, tip, checkable)  # noqa: E731
        # file
        self.new_2d = act("New 2D fragment", editor_icon("new-2d"), lambda: w.new_from_template(BUILTIN_TEMPLATES[0]), "Ctrl+N",
                          "A new 2D fragment (a Mandelbrot on Progressive2D.frag)")
        self.new_3d = act("New 3D fragment", editor_icon("new-3d"), lambda: w.new_from_template(BUILTIN_TEMPLATES[1]), "Ctrl+Shift+N",
                          "A new 3D fragment (a distance estimator on DE-Raytracer.frag)")
        self.open = act("Open…", action_icon("open"), w.files.open, QKeySequence.StandardKey.Open, "Open a .frag / .fafrag file")
        self.reload = act("Reload", editor_icon("reload"), w.files.reload, "Ctrl+Shift+R", "Re-read the current tab's file")
        self.save = act("Save", action_icon("save"), w.files.save, QKeySequence.StandardKey.Save, "Save the fragment")
        self.save_as = act("Save as…", action_icon("save-as"), lambda: w.files.save_as(), QKeySequence.StandardKey.SaveAs,
                           "Save the fragment under a new name (.fafrag or .frag)")
        self.import_shadertoy = act("Import from Shadertoy…", None, w.import_shadertoy, None,
                                    "Paste Shadertoy's Image (and Buffer A) code and get a fragment")
        self.save_template = act("Save as template…", None, w.save_as_template, None, "Keep the current source as one of your templates")
        self.open_templates_folder = act("Open templates folder", None, w.open_templates_folder, None, "Your templates are plain .fafrag files")
        self.save_params = act("Save parameters to file…", None, w.files.save_parameters, None, "The settings text as a .fragparams file")
        self.load_params = act("Load parameters from file…", None, lambda: w.files.load_parameters(), None,
                               "Apply a .fragparams file or the settings embedded in an image")
        self.save_session = act("Save session…", None, w.sessions.save_session, None,
                                "Every open tab (unsaved text included) with its settings as one .fasession file")
        self.open_session = act("Open session…", None, lambda: w.sessions.open_session(), None, "Open the tabs of a saved session")
        self.recover_session = act("Recover last session", None, w.sessions.recover, None,
                                   "Bring back the tabs of a run that did not end cleanly (from the session autosave)")
        self.screenshot = act("Save screenshot…", editor_icon("render-fragment"), w.save_screenshot, None,
                              "Save the viewport's image with the settings embedded")
        self.close_tab = act("Close tab", None, w.tabs.close_current, "Ctrl+W", "Close the current tab")
        self.close_window = act("Close window", None, w.close, "Ctrl+Q", "Close the Fragments window")
        # edit
        self.undo = act("Undo", action_icon("undo"), w.undo, QKeySequence.StandardKey.Undo, "Undo (parameters, or the editor when it has focus)")
        self.redo = act("Redo", action_icon("redo"), w.redo, QKeySequence.StandardKey.Redo, "Redo")
        self.find = act("Find…", action_icon("find"), lambda: w.show_find(False), QKeySequence.StandardKey.Find, "Find in the source")
        self.replace = act("Replace…", None, lambda: w.show_find(True), QKeySequence.StandardKey.Replace, "Find and replace")
        self.goto = act("Go to line…", None, w.goto_line, "Ctrl+G", "Go to a line of the source")
        self.indent = act("Indent script", action_icon("indent"), w.indent_script, None, "Re-indent the whole source by brace depth (FragM's Indent Script)")
        self.compare = act("Compare with original…", None, w.compare_with_original, None,
                           "A diff against the bundled example this fragment came from (or its saved file), with Revert")
        # build
        self.build = act("Build", editor_icon("build"), w.build, "F5", "Preprocess, compile and render the fragment")
        self.auto_build = act("Auto-build", None, w.set_auto_build, None, "Rebuild by itself a moment after the source changes", checkable=True)
        self.manual_render = act("Manual rendering", None, w.set_manual_render, None,
                                 "Parameter changes do not re-render; use Render now (Shift+F5) or Build (F5)", checkable=True)
        self.render_now = act("Render now", None, w.driver.render_now, "Shift+F5", "Start a fresh accumulation with the current values")
        self.view_picture = act("Picture", None, lambda: w.set_debug_view(""), None, "The rendered image", checkable=True)
        self.view_depth = act("Depth buffer", None, lambda: w.set_debug_view("depth"), None,
                              "The depth the raytracer wrote: near bright, far dark, background black", checkable=True)
        views = QActionGroup(w)
        views.addAction(self.view_picture)
        views.addAction(self.view_depth)
        self.view_picture.setChecked(True)
        self.composer = act("DE Composer…", None, w.show_composer, None, "Compose a distance estimator from folds, transforms and a primitive")
        self.de_slice = act("DE slice…", None, w.show_de_slice, None, "The distance estimator on a plane as a heat map with contours")
        self.preprocessed = act("Show preprocessed source…", None, w.show_preprocessed, None,
                                "The exact GLSL handed to the driver, with the original file:line of every line")
        self.preferences = act("Preferences…", None, w.show_preferences, None, "Editor, build, animation, paths and log options")
        self.insert_gradient = act("Insert gradient…", None, w.insert_gradient, None,
                                   "A gradient (the Gradient Library's, a file, a GIMP .ggr) as a GLSL function at the cursor")
        self.test_versions = act("Test GLSL versions", None, w.test_glsl_versions, None,
                                 "Compile the fragment at every GLSL version the driver offers and report the outcome")
        self.clear_textures = act("Clear texture cache", None, w.clear_texture_cache, None, "Drop the cached textures; they reload from disk")
        self.clear_log = act("Clear log", action_icon("clear"), w.log.clear, None, "Clear the log")
        # render
        self.render = act("Render…", editor_icon("render-fragment"), w.show_render_window, "Ctrl+R",
                          "High resolution and animation render: tiles, subframes, every image format, EXR with depth")
        self.batch = act("Batch render presets…", None, w.rendering.show_batch_dialog, None, "One image per preset or keyframe of the saved fragment")
        self.queue_add = act("Add to render queue", None, w.queue_current_render, "Ctrl+Shift+Q",
                             "Queue the current tab with the render window's settings; the queue renders its entries in turn")
        self.queue = act("Render queue…", None, w.rendering.show_queue, None, "The queued renders and their progress")
        self.export_mesh = act("Export mesh…", None, w.rendering.show_mesh_export, None,
                               "Sample the fragment's distance estimator on a voxel grid and export it as a printable mesh")
        self.export_de = act("Export DE as code…", None, w.rendering.show_export_de, None,
                             "The distance estimator with its values baked in, as GLSL, a Shadertoy, a Unity shader or an Unreal include")
        self.show_editor = act("Editor pane", None, w.toggle_editor, "Ctrl+E", "Show / hide the source editor (the viewport takes the width)", checkable=True)
        self.show_editor.setChecked(True)
        self.next_preset = act("Next preset", None, lambda: w.step_preset(1), "Ctrl+PgDown", "Apply the next preset")
        self.previous_preset = act("Previous preset", None, lambda: w.step_preset(-1), "Ctrl+PgUp", "Apply the previous preset")
        self.preset_gallery = act("Preset gallery…", None, w.show_preset_gallery, "Ctrl+F9", "Every preset rendered small; double-click applies one")
        self.controllers = act("Controllers…", None, w.show_controllers, None, "Bind MIDI knobs and gamepad sticks to sliders (Linux device files)")
        self.hud = act("Performance HUD", None, w.viewport.set_hud, "Ctrl+H",
                       "Images per second, ms per subframe against the watchdog budget, tiling, size, GPU load — over the viewport", checkable=True)
        self.fullscreen = act("Fullscreen", None, w.toggle_fullscreen, "Esc", "Show only the viewport (Esc toggles)", checkable=True)
        self.minimap = act("Mini-map", None, w.viewport.set_minimap, "Ctrl+M", "A plan of the scene in the corner: origin, target, eye, camera path",
                           checkable=True)
        self.freeze = act("Freeze reference (A)", None, w.freeze_reference, "Ctrl+Shift+A", "Keep the current picture as the A side of the compare wipe")
        self.compare = act("A/B compare", None, w.viewport.set_compare, "Ctrl+Shift+B",
                           "Show the frozen reference left of a draggable divider, the live render right of it", checkable=True)
        # library
        self.show_library = act("Show library pane", None, w.library_dock.setVisible, "Ctrl+L", "Show / hide the fragment library", checkable=True)
        self.add_folder = act("Add folder to library…", None, w.library_host.add_folder, None, "Add a folder of .frag / .fafrag files")
        self.edit_library = act("Edit library…", None, w.library_host.edit, None, "The folders that make up the fragment library")
        self.refresh_library = act("Refresh library", None, w.library.rescan_all, None, "Rescan the library folders")
        self.thumbnails = act("Thumbnails", None, w.library_panel.set_thumbnail_view, None, "Render a thumbnail for every fragment", checkable=True)
        # parameters
        self.reset_all = act("Reset all", None, w.params.reset_all, "F1", "Every parameter back to its default")
        self.copy_settings = act("Copy settings", action_icon("copy"), w.params.copy_settings, "F2", "The parameters as text on the clipboard")
        self.copy_group = act("Copy group", None, lambda: w.parameters.group_action("copy"), "Shift+F2", "The current tab's parameters as text")
        self.paste_settings = act("Paste from clipboard", action_icon("paste"), w.params.paste_settings, "F3", "Apply settings text from the clipboard")
        self.paste_selected = act("Paste from selected text", None, w.params.paste_selected, "Shift+F3", "Apply the text selected in the editor as settings")
        self.group_preset = act("Group to preset…", None, lambda: w.params.group_to_preset(None), "F4", "Insert a preset holding the current tab's parameters")
        self.randomize_group = act("Randomize group", None, lambda: w.parameters.group_action("randomize"), "F6",
                                   "Random values within the sliders' ranges for the current tab (camera and locked parameters excluded)")
        self.mutate = act("Mutate", None, lambda: w.explore.mutate(w.explore.strip.strength.value() / 100.0, w.explore.strip.group_only.isChecked()),
                          "Shift+F6", "Nudge the unlocked parameters at random by the History dock's strength (a snapshot is taken first)")
        self.snapshot = act("Snapshot to history", None, lambda: w.explore.snapshot("snapshot"), "Ctrl+F6",
                            "Keep the current look in the History dock")
        self.reset_group = act("Reset group", None, lambda: w.parameters.group_action("reset"), None, "The current tab's parameters back to their defaults")
        self.lock_group = act("Lock group", editor_icon("lock"), lambda: w.parameters.group_action("lock"), None, "Lock every parameter of the current tab")
        self.unlock_group = act("Unlock group", editor_icon("unlock"), lambda: w.parameters.group_action("unlock"), None, "Unlock every parameter of the current tab")
        self.colors_library = act("Colours from the Gradient Library", None, lambda: w.params.colors_from_library(False), None,
                                  "Every colour parameter takes a colour sampled along the Gradient Library's current gradient")
        self.colors_library_group = act("Colours of this tab from the Gradient Library", None, lambda: w.params.colors_from_library(True), None,
                                        "Only the current tab's colour parameters")
        self.colors_file = act("Colours from gradient file…", None, w.params.colors_from_file, None, "Sample the colours from a .ugr / .ggr / .map / .flame / image")
        self.hide_unused = act("Hide unused parameters", None, w.parameters.set_hide_unused, None,
                               "Hide parameters the compiler optimised away (locked ones stay)", checkable=True)
        self.hide_unused.setChecked(True)
        # presets
        self.insert_preset = act("Insert preset from current settings…", None, w.params.insert_preset, "F8",
                                 "Write the current settings into the source as a #preset (a KeyFrame for 3D cameras)")
        self.select_preset = act("Select preset in source", None, w.params.select_preset, "F9", "Select the current preset's text in the editor")
        # animation
        self.copy_image = act("Copy image", action_icon("copy"), w.copy_image, "Ctrl+Shift+C", "The viewport's picture on the clipboard")
        self.reset_camera = act("Reset camera", None, w.reset_camera, "Ctrl+Shift+0", "Back to the current preset's camera")
        vp = w.viewport
        self.nav_orbit = act("Orbit navigation (DCC style)", None, lambda: w.set_navigation("orbit"), None,
                             "Left-drag orbits the target, middle-drag pans, right-drag / wheel dolly; Shift+left looks around", checkable=True)
        self.nav_fragm = act("Fly navigation (FragM)", None, lambda: w.set_navigation("fragm"), None,
                             "Left-drag turns the view, right-drag pans, both / wheel dolly, W A S D fly", checkable=True)
        nav = QActionGroup(w)
        nav.addAction(self.nav_orbit)
        nav.addAction(self.nav_fragm)
        self.nav_orbit.setChecked(True)
        self.views = {side: act(side.capitalize(), None, lambda s=side: vp.view_from(s), shortcut,
                                f"Look at the target from the {side} (numpad {key})")
                      for side, shortcut, key in (("front", "Alt+1", "1"), ("back", "Ctrl+Alt+1", "Ctrl+1"), ("right", "Alt+3", "3"),
                                                  ("left", "Ctrl+Alt+3", "Ctrl+3"), ("top", "Alt+7", "7"), ("bottom", "Ctrl+Alt+7", "Ctrl+7"))}
        self.flip_view = act("Opposite side", None, vp.flip_view, "Alt+9", "The other side of the target (numpad 9)")
        self.frame_origin = act("Frame the origin", None, vp.frame_origin, "Alt+.", "Put the target on the origin (numpad .)")
        self.turntable = act("Turntable", None, vp.set_turntable, "Alt+T", "Slowly orbit the target (a motorised turntable)", checkable=True)
        self.add_bookmark = act("Add camera bookmark…", None, w.camera.add_bookmark, "Ctrl+B", "Keep the current camera under a name (saved in the .fafrag)")
        self.record_path = act("Record camera path", None, w.camera.set_recording, "Ctrl+Shift+P",
                               "Sample the camera while you fly; turning it off writes KeyFrame presets", checkable=True)
        self.easing = act("Add easing curve…", None, w.animation.add_easing_curve, "F7", "Animate the last edited slider between two frames")
        self.timeline = act("Timeline editor…", None, w.animation.show_timeline, None, "Keyframes and easing curves on a ruler")
        self.clear_animation = act("Clear animation actions", None, w.animation.clear_animation, None, "Drop every easing curve")
        self.loop_play = act("Loop play", None, w.animation.set_loop_play, None, "Start again at the end", checkable=True)
        self.loop_path = act("Loop camera path", None, w.animation.set_loop_path, None, "The camera path wraps back to the first keyframe", checkable=True)
        self.draw_paths = act("Draw camera paths", None, w.animation.set_draw_paths, None, "Show the keyframe paths over the viewport", checkable=True)
        self.interpolate_camera = act("Camera path only", None, lambda: w.animation.set_interpolation("camera"), None,
                                      "FragM's animation: the camera follows the keyframes, sliders follow their easing curves", checkable=True)
        self.interpolate_all = act("All parameters", None, lambda: w.animation.set_interpolation("all"), None,
                                   "Every numeric parameter is blended between the keyframe presets as well", checkable=True)
        group = QActionGroup(w)
        group.addAction(self.interpolate_camera)
        group.addAction(self.interpolate_all)
        self.interpolate_camera.setChecked(True)
        self.save_easing = act("Presets contain easing curves", None, w.animation.set_save_easing, None,
                               "Inserted presets carry the easing-curve settings (else only Range presets do)", checkable=True)

    # --- menus --------------------------------------------------------------------------------------------------------------
    def build_menus(self) -> None:
        w = self.w
        bar = w.menuBar()
        self.file_menu = bar.addMenu("&File")
        self.recent_menu = QMenu("Recent files", w)
        self.templates_menu = QMenu("New from template", w)
        populate(self.file_menu, self.new_2d, self.new_3d)
        self.file_menu.addMenu(self.templates_menu)
        populate(self.file_menu, None, self.open, self.reload, self.save, self.save_as, None, self.import_shadertoy, None,
                 self.save_session, self.open_session, self.recover_session, None)
        self.file_menu.addMenu(self.recent_menu)
        populate(self.file_menu, None, self.screenshot, self.copy_image, None, self.close_tab, self.close_window)
        self.refresh_templates()
        edit = bar.addMenu("&Edit")
        populate(edit, self.undo, self.redo, None, self.find, self.replace, self.goto, self.indent, self.compare, None)
        insert = edit.addMenu("Insert command")
        self._build_snippets(insert)
        populate(edit, self.insert_gradient, None, self.preferences)
        build = bar.addMenu("&Build")
        populate(build, self.build, self.auto_build, None, self.manual_render, self.render_now, None, self.composer, None, self.preprocessed, self.test_versions, self.clear_textures)
        debug = build.addMenu("Debug view")
        populate(debug, self.view_picture, self.view_depth, None, self.de_slice)
        populate(build, None, self.clear_log)
        render = bar.addMenu("&Render")
        populate(render, self.render, self.batch, self.queue_add, self.queue, self.export_mesh, self.export_de, None, self.screenshot, None, self.freeze, self.compare, self.minimap, None, self.fullscreen)
        params = bar.addMenu("&Parameters")
        populate(params, self.reset_all, self.reset_group, self.randomize_group, self.mutate, self.snapshot, None, self.copy_settings, self.copy_group, self.paste_settings, self.paste_selected,
                 None, self.group_preset, self.insert_preset, self.select_preset, self.preset_gallery, self.next_preset, self.previous_preset, None, self.lock_group, self.unlock_group, None, self.hide_unused,
                 None, self.colors_library, self.colors_library_group, self.colors_file, None, self.save_params, self.load_params)
        animation = bar.addMenu("&Animation")
        populate(animation, *w.anim.actions_list, None, self.easing, self.insert_preset, self.select_preset, None, self.timeline,
                 self.clear_animation, None, self.loop_play, self.loop_path, self.draw_paths, self.save_easing)
        interpolation = animation.addMenu("Interpolation")
        populate(interpolation, self.interpolate_camera, self.interpolate_all)
        w.camera.menu = bar.addMenu("&Camera")
        w.camera.refresh_menu()
        self.library_menu = bar.addMenu("&Library")
        self._build_examples(self.library_menu)
        populate(self.library_menu, None, self.show_library, self.thumbnails, self.refresh_library, None, self.add_folder, self.edit_library)
        self.windows_menu = bar.addMenu("&Windows")
        help_menu = bar.addMenu("&Help")
        help_menu.addAction("Fragment language and guide…", lambda: help.show_guide(w))
        help_menu.addAction("Mouse and keyboard", w.show_controls_help)
        help_menu.addAction("Start the tutorials (walkthrough)", w.start_tutorials)
        help_menu.addAction("Batch rendering from the command line…", lambda: help.show_cli_help(w))
        help_menu.addAction("Welcome note", lambda: help.show_welcome(w))
        help_menu.addSeparator()
        for title, url in help.LINKS:
            help_menu.addAction(title, lambda u=url: QDesktopServices.openUrl(QUrl(u)))

    def refresh_templates(self) -> None:
        """The *New from template* menu: the built-in starters, then the user's own, then the template actions."""
        menu = self.templates_menu
        menu.clear()
        for template in BUILTIN_TEMPLATES:
            action = menu.addAction(template.name, lambda t=template: self.w.new_from_template(t))
            action.setStatusTip(template.description)
        mine = user_templates()
        if mine:
            menu.addSeparator()
            for template in mine:
                menu.addAction(template.name, lambda t=template: self.w.new_from_template(t))
        menu.addSeparator()
        populate(menu, self.save_template, self.open_templates_folder)

    def _build_snippets(self, menu: QMenu) -> None:
        code = menu.addMenu("Code snippets (Tab walks the stops)")
        for label, template in CODE_SNIPPETS.items():
            code.addAction(label, lambda text=template: self.w.insert_template(text))
        for group, lines in SNIPPETS.items():
            sub = menu.addMenu(group)
            for line in lines:
                sub.addAction(line, lambda text=line: self.w.insert_snippet(text))
        include = menu.addMenu("Include")
        for name in self.w.include_names():
            include.addAction(f'#include "{name}"', lambda text=f'#include "{name}"': self.w.insert_snippet(text))
        menu.addSeparator()
        menu.addAction(self.insert_preset)

    def _build_examples(self, menu: QMenu) -> None:
        """FragM's Examples menu: the bundled library as nested menus (`Include` excluded)."""
        examples = menu.addMenu("Examples")
        root = examples_dir()
        menus: dict = {root: examples}
        for folder, fragments in example_tree(root):
            target = menus.get(folder)
            if target is None:
                parent = menus.get(folder.parent, examples)
                target = menus[folder] = parent.addMenu(folder.name)
            for path in fragments:
                target.addAction(path.name, lambda p=path: self.w.open_example(p))

    # --- toolbars ---------------------------------------------------------------------------------------------------------------
    def build_toolbars(self) -> None:
        w = self.w
        tb = QToolBar("Fragments", w)
        tb.setObjectName("fragmentsToolbar")
        tb.setMovable(False)
        populate(tb, self.new_2d, self.new_3d, self.open, self.save, self.save_as, None, self.undo, self.redo, None, self.build)
        tb.addWidget(w.build_label)
        tb.addSeparator()
        tb.addWidget(w.subframe_widget)
        tb.addSeparator()
        tb.addWidget(w.buffer_bar)
        tb.addSeparator()
        populate(tb, self.render, self.screenshot)
        w.addToolBar(tb)
        self.toolbar = tb
        self.mode_toolbar = w.anim.mode_toolbar(w)
        w.addToolBar(self.mode_toolbar)
        w.addToolBarBreak()
        self.nav_toolbar = QToolBar("Navigation", w)
        self.nav_toolbar.setObjectName("fragmentsNavigation")
        populate(self.nav_toolbar, *self.views.values(), self.flip_view, self.frame_origin, None, self.turntable)
        w.addToolBar(self.nav_toolbar)
        self.time_toolbar = w.anim.time_toolbar(w)
        w.addToolBar(self.time_toolbar)

    def add_dock_toggles(self, docks: list) -> None:
        for dock in docks:
            self.windows_menu.addAction(dock.toggleViewAction())
        self.windows_menu.addSeparator()
        for toolbar in (self.toolbar, self.nav_toolbar, self.mode_toolbar, self.time_toolbar):
            self.windows_menu.addAction(toolbar.toggleViewAction())
        self.windows_menu.addSeparator()
        self.windows_menu.addAction(self.show_editor)
        self.windows_menu.addAction(self.hud)
        self.windows_menu.addSeparator()
        self.windows_menu.addAction(self.controllers)

    def refresh_recent(self, paths: list) -> None:
        self.recent_menu.clear()
        for path in paths:
            self.recent_menu.addAction(str(path), lambda p=path: self.w.files.open_path(p))
        self.recent_menu.setEnabled(bool(paths))


__all__ = ["FragmentActions"]
