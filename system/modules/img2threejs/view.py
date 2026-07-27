import os
import shutil
import subprocess
import sys
import threading
import webbrowser
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk

from modules.base import StudioModule


REPO_URL = "https://github.com/img2threejs/img2threejs"


class Img2ThreeJSModule(StudioModule):
    def __init__(self, parent):
        super().__init__(parent, "img2threejs", "img2threejs")
        self.app = parent
        self.view = None

    def get_view(self):
        self.view = Img2ThreeJSView(self.app.main_container, self.app)
        return self.view

    def on_enter(self):
        if self.view:
            self.view.refresh()

    def on_leave(self):
        pass


class Img2ThreeJSView(ctk.CTkFrame):
    def __init__(self, master, app, **kwargs):
        super().__init__(master, **kwargs)
        self.app = app
        self.root_dir = Path(__file__).resolve().parents[3]
        self.backend_dir = self.root_dir / "system" / "ai-backends" / "img2threejs"
        self.output_dir = self.root_dir / "system" / "img2threejs-out"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.busy = False
        self._build()
        self.refresh()

    def _build(self):
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=12, pady=(12, 5))
        ctk.CTkLabel(header, text="img2threejs", font=ctk.CTkFont(size=25, weight="bold")).pack(anchor="w")
        ctk.CTkLabel(
            header,
            text="Reconstrucción procedural de una imagen como modelo Three.js, con especificación y controles de calidad.",
            text_color="gray",
        ).pack(anchor="w")

        actions = ctk.CTkFrame(self, fg_color="transparent")
        actions.pack(fill="x", padx=12, pady=8)
        self.install_btn = ctk.CTkButton(actions, text="Instalar", command=self.install)
        self.install_btn.pack(side="left", padx=4)
        self.update_btn = ctk.CTkButton(actions, text="Actualizar", command=self.update)
        self.update_btn.pack(side="left", padx=4)
        ctk.CTkButton(actions, text="Repositorio", command=lambda: webbrowser.open(REPO_URL)).pack(side="left", padx=4)
        ctk.CTkButton(actions, text="Abrir resultados", command=self.open_output).pack(side="left", padx=4)

        form = ctk.CTkFrame(self)
        form.pack(fill="x", padx=12, pady=8)
        form.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(form, text="Imagen").grid(row=0, column=0, padx=10, pady=10, sticky="w")
        self.image_entry = ctk.CTkEntry(form)
        self.image_entry.grid(row=0, column=1, padx=8, pady=10, sticky="ew")
        ctk.CTkButton(form, text="Elegir…", width=90, command=self.choose_image).grid(row=0, column=2, padx=10)
        ctk.CTkLabel(form, text="Nombre").grid(row=1, column=0, padx=10, pady=10, sticky="w")
        self.name_entry = ctk.CTkEntry(form, placeholder_text="Mi objeto")
        self.name_entry.grid(row=1, column=1, columnspan=2, padx=8, pady=10, sticky="ew")
        self.run_btn = ctk.CTkButton(form, text="Preparar proyecto y generar base", command=self.run)
        self.run_btn.grid(row=2, column=0, columnspan=3, padx=10, pady=12)

        ctk.CTkLabel(
            self,
            text="La salida base debe ser revisada visualmente por un agente antes de avanzar por todos los pases. "
            "Las caras no visibles en la imagen son aproximaciones.",
            wraplength=850,
            justify="left",
            text_color="gray",
        ).pack(fill="x", padx=18, pady=(0, 8))
        self.status = ctk.CTkLabel(self, text="")
        self.status.pack(anchor="w", padx=18)
        self.logs = ctk.CTkTextbox(self, font=ctk.CTkFont(family="Consolas", size=11))
        self.logs.pack(fill="both", expand=True, padx=12, pady=10)

    def log(self, text):
        self.logs.insert("end", str(text) + "\n")
        self.logs.see("end")
        if getattr(self.app, "log_viewer_widget", None):
            self.app.log_viewer_widget.append_log(f"[img2threejs] {text}")

    def refresh(self):
        installed = (self.backend_dir / "SKILL.md").exists()
        self.status.configure(text="Backend instalado" if installed else "Backend no instalado")
        self.install_btn.configure(state="disabled" if installed or self.busy else "normal")
        self.update_btn.configure(state="normal" if installed and not self.busy else "disabled")
        self.run_btn.configure(state="normal" if installed and not self.busy else "disabled")

    def choose_image(self):
        path = filedialog.askopenfilename(filetypes=[("Imágenes", "*.png *.jpg *.jpeg *.webp"), ("Todos", "*.*")])
        if path:
            self.image_entry.delete(0, "end")
            self.image_entry.insert(0, path)
            if not self.name_entry.get():
                self.name_entry.insert(0, Path(path).stem.replace("_", " ").title())

    def _async(self, work):
        self.busy = True
        self.refresh()
        def worker():
            try:
                work()
            except Exception as exc:
                self.after(0, lambda: self.log(f"ERROR: {exc}"))
            finally:
                self.after(0, self._done)
        threading.Thread(target=worker, daemon=True).start()

    def _done(self):
        self.busy = False
        self.refresh()

    def _command(self, cmd, cwd=None):
        self.after(0, lambda: self.log("$ " + " ".join(map(str, cmd))))
        proc = subprocess.Popen(cmd, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace")
        for line in proc.stdout:
            self.after(0, lambda value=line.rstrip(): self.log(value))
        if proc.wait():
            raise RuntimeError(f"El comando terminó con código {proc.returncode}")

    def install(self):
        def work():
            self.backend_dir.parent.mkdir(parents=True, exist_ok=True)
            self._command(["git", "clone", "--depth", "1", REPO_URL, str(self.backend_dir)], self.backend_dir.parent)
        self._async(work)

    def update(self):
        self._async(lambda: self._command(["git", "pull", "--ff-only"], self.backend_dir))

    def run(self):
        image = Path(self.image_entry.get().strip())
        if not image.is_file():
            messagebox.showwarning("img2threejs", "Seleccioná una imagen válida.")
            return
        name = self.name_entry.get().strip() or image.stem
        project = self.output_dir / "".join(c if c.isalnum() or c in "-_" else "_" for c in name)
        def work():
            project.mkdir(parents=True, exist_ok=True)
            reference = project / ("reference" + image.suffix.lower())
            shutil.copy2(image, reference)
            python = sys.executable.replace("pythonw.exe", "python.exe")
            commands = [
                [python, "forge/stage1_intake/probe_image.py", str(reference)],
                [python, "forge/stage2_spec/new_pre_spec_assessment.py", name, "--image", str(reference), "--out", str(project / "assessment.json"), "--force"],
                [python, "forge/stage2_spec/new_sculpt_spec.py", name, "--image", str(reference), "--assessment", str(project / "assessment.json"), "--out", str(project / "spec.json"), "--force"],
                [python, "forge/stage2_spec/validate_sculpt_spec.py", str(project / "spec.json")],
                [python, "forge/stage3_build/generate_threejs_factory.py", str(project / "spec.json"), "--out", str(project / "createObjectModel.ts"), "--force"],
            ]
            for cmd in commands:
                self._command(cmd, self.backend_dir)
            self.after(0, lambda: self.log(f"Proyecto creado: {project}"))
        self._async(work)

    def open_output(self):
        self.output_dir.mkdir(parents=True, exist_ok=True)
        os.startfile(str(self.output_dir))
