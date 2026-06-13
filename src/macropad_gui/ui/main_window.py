"""Main application window: settings panel, layer tabs, pad view,
file handling, dirty-state tracking and safety prompts."""

from __future__ import annotations

import tempfile
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from .. import cli_bridge, yaml_io
from ..actions import parse_action
from ..model import (
    KEYBOARD_MODELS,
    MAX_COLUMNS,
    MAX_KNOBS,
    MAX_LAYERS,
    MAX_ROWS,
    MIN_COLUMNS,
    MIN_KNOBS,
    MIN_LAYERS,
    MIN_ROWS,
    ORIENTATIONS,
    Config,
    Layout,
)
from ..yaml_io import ConfigFileError, SchemaError
from .action_editor import ActionEditor
from .pad_view import PadView

_APP_TITLE = "Macropad Config GUI"
_FILETYPES = [("YAML config", "*.yaml *.yml"), ("All files", "*.*")]


class MainWindow(tk.Tk):
    def __init__(self, config: Config):
        super().__init__()
        self.cfg = config
        self.minsize(560, 360)

        self._build_menu()
        self._build_settings_panel()
        self._build_layer_tabs()
        self._status_var = tk.StringVar()
        ttk.Label(self, textvariable=self._status_var, relief="sunken",
                  anchor="w", padding=(4, 2)).pack(fill="x", side="bottom")
        self._build_action_bar()
        self.pad_view = PadView(self, self.cfg, self._on_position_selected)
        self.pad_view.pack(fill="both", expand=True)

        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self._sync_widgets_from_config()
        self._refresh_title()
        self._set_status("Ready — click a button or knob to assign an action.")

    # ------------------------------------------------------------------
    # construction
    # ------------------------------------------------------------------

    def _build_menu(self) -> None:
        menubar = tk.Menu(self)
        file_menu = tk.Menu(menubar, tearoff=False)
        file_menu.add_command(label="New", accelerator="Ctrl+N",
                              command=self._on_new)
        file_menu.add_command(label="Open…", accelerator="Ctrl+O",
                              command=self._on_open)
        file_menu.add_command(label="Save", accelerator="Ctrl+S",
                              command=self._on_save)
        file_menu.add_command(label="Save As…", command=self._on_save_as)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self._on_close)
        menubar.add_cascade(label="File", menu=file_menu)

        tools_menu = tk.Menu(menubar, tearoff=False)
        self._tool_available = cli_bridge.find_tool() is not None
        tool_state = "normal" if self._tool_available else "disabled"
        tools_menu.add_command(
            label="Validate with CLI Tool", command=self._on_validate,
            state=tool_state)
        tools_menu.add_command(
            label="Upload to Device", command=self._on_upload,
            state=tool_state)
        menubar.add_cascade(label="Tools", menu=tools_menu)
        self.configure(menu=menubar)

        self.bind("<Control-n>", lambda _e: self._on_new())
        self.bind("<Control-o>", lambda _e: self._on_open())
        self.bind("<Control-s>", lambda _e: self._on_save())

    def _build_settings_panel(self) -> None:
        panel = ttk.LabelFrame(self, text="Layout", padding=6)

        ttk.Label(panel, text="Model:").grid(row=0, column=0, sticky="w")
        self._model_var = tk.StringVar()
        model_box = ttk.Combobox(panel, textvariable=self._model_var,
                                 values=("",) + KEYBOARD_MODELS,
                                 state="readonly", width=9)
        model_box.grid(row=0, column=1, padx=(2, 10))
        model_box.bind("<<ComboboxSelected>>", lambda _e: self._on_model_changed())

        ttk.Label(panel, text="Orientation:").grid(row=0, column=2, sticky="w")
        self._orientation_var = tk.StringVar()
        orient_box = ttk.Combobox(panel, textvariable=self._orientation_var,
                                  values=ORIENTATIONS, state="readonly",
                                  width=16)
        orient_box.grid(row=0, column=3, padx=(2, 10))
        orient_box.bind("<<ComboboxSelected>>",
                        lambda _e: self._on_orientation_changed())

        self._rows_var = tk.IntVar()
        self._columns_var = tk.IntVar()
        self._knobs_var = tk.IntVar()
        self._layers_var = tk.IntVar()
        for column, (label, var, lo, hi) in enumerate((
                ("Rows:", self._rows_var, MIN_ROWS, MAX_ROWS),
                ("Columns:", self._columns_var, MIN_COLUMNS, MAX_COLUMNS),
                ("Knobs:", self._knobs_var, MIN_KNOBS, MAX_KNOBS),
                ("Layers:", self._layers_var, MIN_LAYERS, MAX_LAYERS)),
                start=4):
            ttk.Label(panel, text=label).grid(row=0, column=2 * column - 4,
                                              sticky="w")
            command = (self._on_layers_changed if label == "Layers:"
                       else self._on_dimensions_changed)
            spin = ttk.Spinbox(panel, from_=lo, to=hi, textvariable=var,
                               width=3, command=command, state="readonly")
            spin.grid(row=0, column=2 * column - 3, padx=(2, 10))
        panel.pack(fill="x", padx=8, pady=(8, 0))

    def _build_action_bar(self) -> None:
        bar = ttk.Frame(self, padding=(8, 4))
        self._upload_btn = ttk.Button(
            bar, text="⬆ Upload to Device", command=self._on_upload)
        self._upload_btn.pack(side="right")
        if not self._tool_available:
            self._upload_btn.state(["disabled"])
            ttk.Label(bar, foreground="#888888",
                      text="(ch57x-keyboard-tool binary not found — "
                           "upload unavailable)").pack(side="right", padx=(0, 8))
        bar.pack(fill="x", side="bottom")

    def _build_layer_tabs(self) -> None:
        self._tabs = ttk.Notebook(self, height=0)
        self._tabs.bind("<<NotebookTabChanged>>", self._on_layer_tab_changed)
        self._tabs.pack(fill="x", padx=8, pady=(6, 0))

    # ------------------------------------------------------------------
    # widget <-> model sync
    # ------------------------------------------------------------------

    def _sync_widgets_from_config(self) -> None:
        self._model_var.set(self.cfg.model or "")
        self._orientation_var.set(self.cfg.orientation)
        self._rows_var.set(self.cfg.layout.rows)
        self._columns_var.set(self.cfg.layout.columns)
        self._knobs_var.set(self.cfg.layout.knobs)
        self._layers_var.set(len(self.cfg.layers))
        self._rebuild_layer_tabs()

    def _rebuild_layer_tabs(self) -> None:
        for tab_id in self._tabs.tabs():
            self._tabs.forget(tab_id)
        for i in range(len(self.cfg.layers)):
            self._tabs.add(ttk.Frame(self._tabs, height=1),
                           text=f"Layer {i + 1}")
        self._tabs.select(0)

    def _refresh_title(self) -> None:
        name = self.cfg.source_path.name if self.cfg.source_path else "untitled"
        star = "*" if self.cfg.dirty else ""
        self.title(f"{_APP_TITLE} — {name}{star}")

    def _set_status(self, text: str) -> None:
        self._status_var.set(text)

    def _mark_dirty(self) -> None:
        self.cfg.dirty = True
        self._refresh_title()

    def _active_layer(self) -> int:
        try:
            return self._tabs.index(self._tabs.select())
        except tk.TclError:
            return 0

    # ------------------------------------------------------------------
    # settings handlers
    # ------------------------------------------------------------------

    def _on_model_changed(self) -> None:
        value = self._model_var.get() or None
        if value != self.cfg.model:
            self.cfg.model = value
            self._mark_dirty()

    def _on_orientation_changed(self) -> None:
        value = self._orientation_var.get()
        if value != self.cfg.orientation:
            self.cfg.set_orientation(value)
            self.pad_view.refresh(self.cfg)
            self._refresh_title()

    def _on_dimensions_changed(self) -> None:
        try:
            new_layout = Layout(self._rows_var.get(), self._columns_var.get(),
                                self._knobs_var.get())
        except (tk.TclError, ValueError):
            return
        if new_layout == self.cfg.layout:
            return
        lost = self.cfg.resize(new_layout, dry_run=True)
        if lost and not self._confirm_loss(lost, "Resize layout"):
            self._rows_var.set(self.cfg.layout.rows)
            self._columns_var.set(self.cfg.layout.columns)
            self._knobs_var.set(self.cfg.layout.knobs)
            return
        self.cfg.resize(new_layout)
        self.pad_view.refresh(self.cfg)
        self._refresh_title()

    def _on_layers_changed(self) -> None:
        try:
            count = self._layers_var.get()
        except tk.TclError:
            return
        if count == len(self.cfg.layers):
            return
        lost = self.cfg.set_layer_count(count, dry_run=True)
        if lost and not self._confirm_loss(lost, "Remove layers"):
            self._layers_var.set(len(self.cfg.layers))
            return
        self.cfg.set_layer_count(count)
        self._rebuild_layer_tabs()
        self.pad_view.refresh(self.cfg, layer_index=0)
        self._refresh_title()

    def _confirm_loss(self, lost: set, title: str) -> bool:
        per_layer: dict[int, int] = {}
        for entry in lost:
            per_layer[entry[1]] = per_layer.get(entry[1], 0) + 1
        detail = ", ".join(f"layer {layer + 1}: {count}"
                           for layer, count in sorted(per_layer.items()))
        return messagebox.askyesno(
            title,
            f"{len(lost)} assignment(s) would be discarded ({detail}).\n"
            "Continue?",
            parent=self)

    def _on_layer_tab_changed(self, _event) -> None:
        if hasattr(self, "pad_view"):
            self.pad_view.refresh(layer_index=self._active_layer())

    # ------------------------------------------------------------------
    # assignment editing
    # ------------------------------------------------------------------

    def _on_position_selected(self, position) -> None:
        layer = self.cfg.layers[self._active_layer()]
        if position[0] == "button":
            _, r, c = position
            current = layer.buttons[r][c]
            label = f"button row {r + 1}, column {c + 1}"
        else:
            _, k, part = position
            current = layer.knobs[k].get(part)
            label = f"knob {k + 1} {part}"

        limited = ((self.cfg.layout.rows == 1 or self.cfg.layout.columns == 1)
                   and self.cfg.layout.knobs == 1)
        editor = ActionEditor(self, label,
                              initial_text=current.text if current else "",
                              limited_pad=limited)
        self.wait_window(editor)
        if editor.result is None:
            return

        action = parse_action(editor.result) if editor.result else None
        key = (self._active_layer(),) + position
        if action is None and editor.result:
            return  # unreachable: editor only returns valid text
        self.cfg.errors.pop(key, None)
        if position[0] == "button":
            layer.buttons[position[1]][position[2]] = action
        else:
            layer.knobs[position[1]].set(position[2], action)
        self._mark_dirty()
        self.pad_view.refresh(self.cfg)
        self._set_status(f"{label} ← {action.text if action else '(unassigned)'}")

    # ------------------------------------------------------------------
    # file handling
    # ------------------------------------------------------------------

    def _confirm_discard_unsaved(self) -> bool:
        """True when it is OK to drop the current config."""
        if not self.cfg.dirty:
            return True
        answer = messagebox.askyesnocancel(
            "Unsaved changes",
            "Save changes to the current configuration first?",
            parent=self)
        if answer is None:
            return False
        if answer:
            return self._on_save()
        return True

    def _on_new(self) -> None:
        if not self._confirm_discard_unsaved():
            return
        self.cfg = Config.new()
        self._sync_widgets_from_config()
        self.pad_view.refresh(self.cfg, layer_index=0)
        self._refresh_title()
        self._set_status("New configuration.")

    def _on_open(self) -> None:
        if not self._confirm_discard_unsaved():
            return
        filename = filedialog.askopenfilename(parent=self,
                                              filetypes=_FILETYPES)
        if not filename:
            return
        try:
            self.cfg = yaml_io.load(filename)
        except (ConfigFileError, SchemaError) as e:
            messagebox.showerror("Cannot open file", str(e), parent=self)
            return
        self._sync_widgets_from_config()
        self.pad_view.refresh(self.cfg, layer_index=0)
        self._refresh_title()
        self._set_status(f"Opened {filename}")

    def _invalid_entries_block(self, verb: str = "saving") -> bool:
        if not self.cfg.errors:
            return False
        listing = "\n".join(str(key) for key in sorted(self.cfg.errors))
        messagebox.showerror(
            "Invalid entries",
            f"These positions have invalid actions; fix them before "
            f"{verb}:\n{listing}",
            parent=self)
        return True

    def _on_save(self) -> bool:
        if self._invalid_entries_block():
            return False
        if self.cfg.source_path is None:
            return self._on_save_as()
        return self._save_to(self.cfg.source_path)

    def _on_save_as(self) -> bool:
        if self._invalid_entries_block():
            return False
        filename = filedialog.asksaveasfilename(
            parent=self, defaultextension=".yaml", filetypes=_FILETYPES)
        if not filename:
            return False
        return self._save_to(Path(filename))

    def _save_to(self, path: Path) -> bool:
        try:
            yaml_io.save(self.cfg, path)
        except (ConfigFileError, SchemaError) as e:
            messagebox.showerror("Cannot save file", str(e), parent=self)
            return False
        self._refresh_title()
        self._set_status(f"Saved {path}")
        return True

    def _run_cli(self, action):
        """Save the current config to a temp file (without disturbing
        source_path/dirty state) and pass it to ``action(tool, path)``."""
        tool = cli_bridge.find_tool()
        if tool is None:
            messagebox.showerror(
                "CLI tool", "ch57x-keyboard-tool binary not found.",
                parent=self)
            return None
        source_path, dirty = self.cfg.source_path, self.cfg.dirty
        with tempfile.TemporaryDirectory() as tmp:
            tmp_file = Path(tmp) / "config.yaml"
            try:
                yaml_io.save(self.cfg, tmp_file)
            finally:
                self.cfg.source_path, self.cfg.dirty = source_path, dirty
            return action(tool, tmp_file)

    def _on_validate(self) -> None:
        if self._invalid_entries_block("validating"):
            return
        result = self._run_cli(
            lambda tool, path: cli_bridge.validate(path, tool))
        if result is None:
            return
        passed, output = result
        if passed:
            messagebox.showinfo("Validate", output, parent=self)
        else:
            messagebox.showerror("Validate", f"Validation failed:\n{output}",
                                 parent=self)

    def _on_upload(self) -> None:
        if self._invalid_entries_block("uploading"):
            return
        if not messagebox.askyesno(
                "Upload to Device",
                "This will program the currently shown configuration onto "
                "the connected macropad, replacing its current mappings.\n\n"
                "Make sure the device is plugged in. Continue?",
                parent=self):
            return
        self._set_status("Uploading to device…")
        self.update_idletasks()
        result = self._run_cli(
            lambda tool, path: cli_bridge.upload(path, tool))
        if result is None:
            self._set_status("Upload cancelled — CLI tool not found.")
            return
        succeeded, output = result
        if succeeded:
            messagebox.showinfo("Upload to Device", output, parent=self)
            self._set_status("Upload complete.")
        else:
            messagebox.showerror(
                "Upload to Device", f"Upload failed:\n{output}", parent=self)
            self._set_status("Upload failed.")

    def _on_close(self) -> None:
        if not self._confirm_discard_unsaved():
            return
        self.destroy()
