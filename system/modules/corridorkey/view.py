import logging
import os
import re
import shutil
import subprocess
import sys
import threading
import webbrowser
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk

from modules.base import StudioModule


REPO_URL = "https://github.com/nikopueringer/CorridorKey"


class CorridorKeyModule(StudioModule):
    def __init__(self, parent):
        super().__init__(parent, "corridorkey", "CorridorKey")
        self.app = parent

    def get_view(self):
        return CorridorKeyView(self.app.main_container, self.app)


class CorridorKeyView(ctk.CTkFrame):
    def __init__(self, master, app, **kwargs):
        super().__init__(master, **kwargs)
        self.app = app
        self.root_dir = Path(__file__).resolve().parents[3]
        self.backend = self.root_dir / "system" / "ai-backends" / "CorridorKey"
        self.runner = Path(__file__).with_name("runner.py")
        self.busy = False
        self.input_var = ctk.StringVar()
        self.alpha_var = ctk.StringVar()
        self.job_var = ctk.StringVar(value="shot")
        self.device_var = ctk.StringVar(value="auto")
        self.screen_var = ctk.StringVar(value="auto")
        self.colorspace_var = ctk.StringVar(value="srgb")
        self.size_var = ctk.StringVar(value="2048")
        self.despill_var = ctk.StringVar(value="5")
        self.build_ui()
        self.refresh()

    def build_ui(self):
        ctk.CTkLabel(self, text="CorridorKey", font=ctk.CTkFont(size=24, weight="bold")).pack(anchor="w", padx=12, pady=(12, 2))
        ctk.CTkLabel(self, text="Extracción neural de chroma con color foreground y alpha lineal.", text_color="gray").pack(anchor="w", padx=12)
        ctk.CTkLabel(
            self,
            text="Backend externo CC BY-NC-SA 4.0. No se redistribuye con UNLZ AI Studio.",
            text_color="#d4a72c",
        ).pack(anchor="w", padx=12, pady=(3, 8))

        setup = ctk.CTkFrame(self)
        setup.pack(fill="x", padx=12, pady=6)
        self.status = ctk.CTkLabel(setup, text="")
        self.status.pack(side="left", padx=10, pady=10)
        self.install_btn = ctk.CTkButton(setup, text="Instalar backend", command=self.install)
        self.install_btn.pack(side="left", padx=5)
        self.deps_btn = ctk.CTkButton(setup, text="Preparar CUDA", command=self.install_deps)
        self.deps_btn.pack(side="left", padx=5)
        ctk.CTkButton(setup, text="Repositorio oficial", command=lambda: webbrowser.open(REPO_URL)).pack(side="left", padx=5)

        form = ctk.CTkFrame(self)
        form.pack(fill="both", expand=True, padx=12, pady=6)
        form.grid_columnconfigure(1, weight=1)
        self.path_row(form, 0, "Video/secuencia", self.input_var, self.select_input)
        self.path_row(form, 1, "Alpha Hint", self.alpha_var, self.select_alpha)
        ctk.CTkLabel(form, text="Nombre del trabajo").grid(row=2, column=0, sticky="w", padx=10, pady=6)
        ctk.CTkEntry(form, textvariable=self.job_var).grid(row=2, column=1, sticky="ew", padx=10, pady=6)

        options = ctk.CTkFrame(form, fg_color="transparent")
        options.grid(row=3, column=0, columnspan=3, sticky="ew", padx=5, pady=8)
        for label, variable, values in [
            ("Dispositivo", self.device_var, ["auto", "cuda", "cpu"]),
            ("Pantalla", self.screen_var, ["auto", "green", "blue"]),
            ("Color", self.colorspace_var, ["srgb", "linear"]),
            ("Resolución", self.size_var, ["512", "1024", "2048"]),
        ]:
            box = ctk.CTkFrame(options, fg_color="transparent")
            box.pack(side="left", padx=5)
            ctk.CTkLabel(box, text=label).pack(anchor="w")
            ctk.CTkOptionMenu(box, variable=variable, values=values, width=125).pack()
        box = ctk.CTkFrame(options, fg_color="transparent")
        box.pack(side="left", padx=5)
        ctk.CTkLabel(box, text="Despill (0-10)").pack(anchor="w")
        ctk.CTkEntry(box, textvariable=self.despill_var, width=100).pack()

        actions = ctk.CTkFrame(form, fg_color="transparent")
        actions.grid(row=4, column=0, columnspan=3, sticky="w", padx=10, pady=10)
        self.run_btn = ctk.CTkButton(actions, text="Procesar", command=self.run)
        self.run_btn.pack(side="left", padx=(0, 8))
        ctk.CTkButton(actions, text="Abrir resultados", command=self.open_output).pack(side="left")

    def path_row(self, parent, row, label, variable, command):
        ctk.CTkLabel(parent, text=label).grid(row=row, column=0, sticky="w", padx=10, pady=6)
        ctk.CTkEntry(parent, textvariable=variable).grid(row=row, column=1, sticky="ew", padx=10, pady=6)
        ctk.CTkButton(parent, text="Elegir", width=80, command=command).grid(row=row, column=2, padx=10, pady=6)

    def choose_path(self, title):
        path = filedialog.askopenfilename(title=title)
        return path or filedialog.askdirectory(title=f"{title} (carpeta)")

    def select_input(self):
        value = self.choose_path("Elegir video o secuencia")
        if value:
            self.input_var.set(value)
            if self.job_var.get() == "shot":
                self.job_var.set(Path(value).stem)

    def select_alpha(self):
        value = self.choose_path("Elegir Alpha Hint")
        if value:
            self.alpha_var.set(value)

    def refresh(self):
        installed = (self.backend / "corridorkey_cli.py").exists()
        ready = (self.backend / ".venv").exists()
        self.status.configure(text=("Listo" if ready else "Backend instalado" if installed else "No instalado"))
        self.install_btn.configure(state="disabled" if installed or self.busy else "normal")
        self.deps_btn.configure(state="normal" if installed and not self.busy else "disabled")
        self.run_btn.configure(state="normal" if ready and not self.busy else "disabled")

    def process(self, cmd, cwd=None, on_done=None):
        self.busy = True
        self.refresh()
        def worker():
            code = 1
            try:
                proc = subprocess.Popen(cmd, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
                for line in proc.stdout:
                    self.after(0, lambda text=line.rstrip(): logging.info(text))
                code = proc.wait()
            except Exception as exc:
                self.after(0, lambda: logging.error(str(exc)))
            self.after(0, lambda: self.done(code, on_done))
        threading.Thread(target=worker, daemon=True).start()

    def done(self, code, on_done=None):
        self.busy = False
        logging.info("CorridorKey finalizó correctamente." if code == 0 else f"CorridorKey terminó con código {code}.")
        self.refresh()
        if on_done and code == 0:
            on_done()

    def install(self):
        if shutil.which("git") is None:
            messagebox.showerror("CorridorKey", "Git no está disponible.")
            return
        self.backend.parent.mkdir(parents=True, exist_ok=True)
        self.process(["git", "clone", "--depth", "1", REPO_URL, str(self.backend)], self.backend.parent)

    def install_deps(self):
        python = sys.executable.replace("pythonw.exe", "python.exe")
        self.process(
            [python, "-m", "pip", "install", "-U", "uv"],
            on_done=self.sync_deps,
        )

    def sync_deps(self):
        python = sys.executable.replace("pythonw.exe", "python.exe")
        extra = "cuda" if self.device_var.get() in ("auto", "cuda") else None
        cmd = [python, "-m", "uv", "sync"] + (["--extra", extra] if extra else [])
        self.process(cmd, self.backend)

    def run(self):
        if not self.input_var.get() or not self.alpha_var.get():
            messagebox.showwarning("CorridorKey", "Elegí el material de entrada y el Alpha Hint.")
            return
        cmd = [
            sys.executable.replace("pythonw.exe", "python.exe"), "-u", str(self.runner),
            "--backend", str(self.backend), "--input", self.input_var.get(), "--alpha", self.alpha_var.get(),
            "--job", self.job_var.get(), "--device", self.device_var.get(),
            "--screen-color", self.screen_var.get(), "--colorspace", self.colorspace_var.get(),
            "--image-size", self.size_var.get(), "--despill", self.despill_var.get(),
        ]
        self.process(cmd, self.backend)

    def open_output(self):
        job_name = re.sub(r"[^A-Za-z0-9_-]+", "_", self.job_var.get()).strip("_") or "shot"
        target = self.root_dir / "system" / "corridorkey-out" / job_name
        target.mkdir(parents=True, exist_ok=True)
        os.startfile(str(target))
