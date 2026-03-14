import customtkinter as ctk
import os
import sys
import threading
import subprocess
import logging
from pathlib import Path
from tkinter import filedialog, messagebox
from urllib.request import urlopen

from modules.base import StudioModule


class VigaModule(StudioModule):
    def __init__(self, parent):
        super().__init__(parent, "viga", "VIGA")
        self.view = None
        self.app = parent

    def get_view(self) -> ctk.CTkFrame:
        self.view = VigaView(self.app.main_container, self.app)
        return self.view

    def on_enter(self):
        pass

    def on_leave(self):
        pass


class VigaView(ctk.CTkFrame):
    def __init__(self, master, app, **kwargs):
        super().__init__(master, **kwargs)
        self.app = app
        self.tr = app.tr
        self._busy = False

        self.app_root = Path(__file__).resolve().parents[3]
        self.backend_dir = self.app_root / "system" / "ai-backends" / "VIGA"
        self.output_dir = self.app_root / "system" / "viga-out"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.sam_url = "https://dl.fbaipublicfiles.com/segment_anything/sam_vit_h_4b8939.pth"

        self._deps_options = {
            self.tr("viga_deps_agent"): "agent",
            self.tr("viga_deps_blender"): "blender",
            self.tr("viga_deps_sam"): "sam",
        }
        self.deps_var = ctk.StringVar(value=self.tr("viga_deps_agent"))

        self._runner_options = {
            self.tr("viga_runner_dynamic"): "dynamic_scene",
            self.tr("viga_runner_static"): "static_scene",
        }
        self.runner_var = ctk.StringVar(value=self.tr("viga_runner_dynamic"))

        self.build_ui()
        self._last_default_dataset = "data/dynamic_scene"
        self.runner_var.trace_add("write", self.on_runner_change)
        self.refresh_buttons()

    def build_ui(self):
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=10, pady=(10, 5))
        ctk.CTkLabel(header, text=self.tr("viga_title"), font=ctk.CTkFont(size=24, weight="bold")).pack(anchor="w")
        ctk.CTkLabel(header, text=self.tr("viga_subtitle"), text_color="gray").pack(anchor="w")
        ctk.CTkLabel(header, text=self.tr("viga_plain"), text_color="gray").pack(anchor="w")

        actions = ctk.CTkFrame(self, fg_color="transparent")
        actions.pack(fill="x", padx=10, pady=(10, 5))
        self.btn_install = ctk.CTkButton(actions, text=self.tr("viga_btn_install"), command=self.install_backend)
        self.btn_install.pack(side="left", padx=5)
        self.btn_uninstall = ctk.CTkButton(actions, text=self.tr("viga_btn_uninstall"), command=self.uninstall_backend)
        self.btn_uninstall.pack(side="left", padx=5)
        self.btn_deps = ctk.CTkButton(actions, text=self.tr("viga_btn_deps"), command=self.install_deps)
        self.btn_deps.pack(side="left", padx=5)
        self.btn_download = ctk.CTkButton(actions, text=self.tr("viga_btn_download_sam"), command=self.download_sam)
        self.btn_download.pack(side="left", padx=5)
        self.btn_open = ctk.CTkButton(actions, text=self.tr("viga_btn_open_folder"), command=self.open_backend_folder)
        self.btn_open.pack(side="left", padx=5)

        links = ctk.CTkFrame(self, fg_color="transparent")
        links.pack(fill="x", padx=10, pady=(5, 5))
        ctk.CTkButton(links, text=self.tr("viga_btn_open_repo"), command=self.open_repo).pack(side="left", padx=5)
        ctk.CTkButton(links, text=self.tr("viga_btn_open_project"), command=self.open_project).pack(side="left", padx=5)
        ctk.CTkButton(links, text=self.tr("viga_btn_open_docs"), command=self.open_docs).pack(side="left", padx=5)

        status_frame = ctk.CTkFrame(self, fg_color="transparent")
        status_frame.pack(fill="x", padx=10, pady=(5, 0))
        ctk.CTkLabel(status_frame, text=self.tr("viga_status_label")).pack(side="left")
        self.status_value = ctk.CTkLabel(status_frame, text=self.tr("viga_status_idle"), text_color="gray")
        self.status_value.pack(side="left", padx=(6, 0))

        body = ctk.CTkFrame(self)
        body.pack(fill="both", expand=True, padx=10, pady=(10, 10))
        body.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(body, text=self.tr("viga_deps_label")).grid(row=0, column=0, sticky="w", padx=10, pady=(10, 4))
        self.deps_menu = ctk.CTkOptionMenu(body, variable=self.deps_var, values=list(self._deps_options.keys()))
        self.deps_menu.grid(row=0, column=1, sticky="ew", padx=10, pady=(10, 4))

        ctk.CTkLabel(body, text=self.tr("viga_runner_label")).grid(row=1, column=0, sticky="w", padx=10, pady=(0, 4))
        self.runner_menu = ctk.CTkOptionMenu(body, variable=self.runner_var, values=list(self._runner_options.keys()))
        self.runner_menu.grid(row=1, column=1, sticky="ew", padx=10, pady=(0, 4))

        ctk.CTkLabel(body, text=self.tr("viga_dataset_label")).grid(row=2, column=0, sticky="w", padx=10, pady=(0, 4))
        self.dataset_entry = ctk.CTkEntry(body, placeholder_text=self.tr("viga_dataset_placeholder"))
        self.dataset_entry.insert(0, "data/dynamic_scene")
        self.dataset_entry.grid(row=2, column=1, sticky="ew", padx=10, pady=(0, 4))
        ctk.CTkButton(body, text=self.tr("viga_btn_open_folder"), command=self.select_dataset).grid(row=2, column=2, padx=(0, 10), pady=(0, 4))

        ctk.CTkLabel(body, text=self.tr("viga_task_label")).grid(row=3, column=0, sticky="w", padx=10, pady=(0, 4))
        self.task_entry = ctk.CTkEntry(body, placeholder_text=self.tr("viga_task_placeholder"))
        self.task_entry.insert(0, "artist")
        self.task_entry.grid(row=3, column=1, sticky="ew", padx=10, pady=(0, 4))

        ctk.CTkLabel(body, text=self.tr("viga_model_label")).grid(row=4, column=0, sticky="w", padx=10, pady=(0, 4))
        self.model_entry = ctk.CTkEntry(body, placeholder_text=self.tr("viga_model_placeholder"))
        self.model_entry.insert(0, "gpt-5")
        self.model_entry.grid(row=4, column=1, sticky="ew", padx=10, pady=(0, 4))

        ctk.CTkLabel(body, text=self.tr("viga_max_rounds_label")).grid(row=5, column=0, sticky="w", padx=10, pady=(0, 4))
        self.rounds_entry = ctk.CTkEntry(body)
        self.rounds_entry.insert(0, "100")
        self.rounds_entry.grid(row=5, column=1, sticky="ew", padx=10, pady=(0, 4))

        ctk.CTkLabel(body, text=self.tr("viga_output_label")).grid(row=6, column=0, sticky="w", padx=10, pady=(0, 4))
        self.output_entry = ctk.CTkEntry(body, placeholder_text=str(self.output_dir))
        self.output_entry.grid(row=6, column=1, sticky="ew", padx=10, pady=(0, 4))
        ctk.CTkButton(body, text=self.tr("viga_btn_open_output"), command=self.open_output_folder).grid(row=6, column=2, padx=(0, 10), pady=(0, 4))

        buttons = ctk.CTkFrame(body, fg_color="transparent")
        buttons.grid(row=7, column=0, columnspan=2, sticky="w", padx=10, pady=(10, 10))
        self.btn_run = ctk.CTkButton(buttons, text=self.tr("viga_btn_run"), command=self.run_action)
        self.btn_run.pack(side="left", padx=(0, 8))

        note = ctk.CTkLabel(self, text=self.tr("viga_note"), text_color="gray", wraplength=720, justify="left")
        note.pack(fill="x", padx=15, pady=(0, 10))

    def refresh_buttons(self):
        if self._busy:
            for btn in (
                self.btn_install, self.btn_uninstall, self.btn_deps, self.btn_download,
                self.btn_open, self.btn_run
            ):
                btn.configure(state="disabled")
            return

        installed = self.backend_dir.exists()
        if installed:
            self.btn_install.pack_forget()
            if not self.btn_uninstall.winfo_manager():
                self.btn_uninstall.pack(side="left", padx=5)
            if not self.btn_deps.winfo_manager():
                self.btn_deps.pack(side="left", padx=5)
            if not self.btn_download.winfo_manager():
                self.btn_download.pack(side="left", padx=5)
            if not self.btn_open.winfo_manager():
                self.btn_open.pack(side="left", padx=5)
        else:
            self.btn_uninstall.pack_forget()
            self.btn_deps.pack_forget()
            self.btn_download.pack_forget()
            self.btn_open.pack_forget()
            if not self.btn_install.winfo_manager():
                self.btn_install.pack(side="left", padx=5)

        for btn in (self.btn_install, self.btn_uninstall, self.btn_deps, self.btn_download, self.btn_open, self.btn_run):
            btn.configure(state="normal")

    def set_busy(self, busy):
        self._busy = busy
        if self.status_value:
            self.status_value.configure(
                text=self.tr("status_in_progress") if busy else self.tr("viga_status_idle")
            )
        self.refresh_buttons()

    def log(self, message):
        logging.info(message)

    def safe_log(self, message):
        self.after(0, lambda: logging.info(message))

    def check_git_available(self):
        try:
            result = subprocess.run(["git", "--version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return result.returncode == 0
        except Exception:
            return False

    def install_backend(self):
        if self.backend_dir.exists():
            self.log(self.tr("viga_msg_already_installed"))
            self.refresh_buttons()
            return
        if not self.check_git_available():
            messagebox.showwarning(self.tr("status_error"), self.tr("viga_msg_git_missing"))
            return
        self.backend_dir.parent.mkdir(parents=True, exist_ok=True)
        self.log(self.tr("viga_msg_installing"))
        self.set_busy(True)

        def worker():
            rc = self.run_cmd_blocking(
                ["git", "clone", "--depth", "1", "https://github.com/Fugtemypt123/VIGA", str(self.backend_dir)],
                cwd=self.backend_dir.parent,
            )
            if rc == 0:
                rc = self.run_cmd_blocking(
                    ["git", "submodule", "update", "--init", "--recursive"],
                    cwd=self.backend_dir,
                )
            self.after(0, lambda: self.on_process_done(rc))

        threading.Thread(target=worker, daemon=True).start()

    def uninstall_backend(self):
        if not self.backend_dir.exists():
            self.log(self.tr("viga_msg_not_installed"))
            self.refresh_buttons()
            return
        try:
            import shutil
            shutil.rmtree(self.backend_dir)
            self.log(self.tr("viga_msg_uninstalled"))
        except Exception as exc:
            self.log(f"{self.tr('status_error')}: {exc}")
        self.refresh_buttons()

    def install_deps(self):
        if not self.backend_dir.exists():
            messagebox.showwarning(self.tr("status_error"), self.tr("viga_msg_not_installed"))
            return
        target_key = self._deps_options.get(self.deps_var.get(), "agent")
        req_map = {
            "agent": "requirements/requirement_agent.txt",
            "blender": "requirements/requirement_blender.txt",
            "sam": "requirements/requirement_sam.txt",
        }
        req_rel = req_map.get(target_key)
        req_path = self.backend_dir / req_rel
        if not req_path.exists():
            messagebox.showwarning(self.tr("status_error"), self.tr("viga_msg_requirements_missing").format(req_rel))
            return
        python_path = sys.executable.replace("pythonw.exe", "python.exe")
        self.log(self.tr("viga_msg_installing_deps").format(req_rel))
        self.set_busy(True)
        self.run_process([python_path, "-m", "pip", "install", "-r", str(req_path)], on_done=self.on_process_done)

    def download_sam(self):
        if not self.backend_dir.exists():
            messagebox.showwarning(self.tr("status_error"), self.tr("viga_msg_not_installed"))
            return
        target = self.backend_dir / "utils" / "third_party" / "sam" / "sam_vit_h_4b8939.pth"
        target.parent.mkdir(parents=True, exist_ok=True)
        self.log(self.tr("viga_msg_downloading_sam"))
        self.set_busy(True)

        def worker():
            rc = 0
            try:
                with urlopen(self.sam_url) as response, target.open("wb") as handle:
                    while True:
                        chunk = response.read(1024 * 1024)
                        if not chunk:
                            break
                        handle.write(chunk)
                self.safe_log(self.tr("viga_msg_sam_done"))
            except Exception as exc:
                rc = 1
                self.safe_log(f"{self.tr('status_error')}: {exc}")
            self.after(0, lambda: self.on_process_done(rc))

        threading.Thread(target=worker, daemon=True).start()

    def run_action(self):
        if not self.backend_dir.exists():
            messagebox.showwarning(self.tr("status_error"), self.tr("viga_msg_not_installed"))
            return
        task = self.task_entry.get().strip()
        if not task:
            messagebox.showwarning(self.tr("status_error"), self.tr("viga_msg_missing_task"))
            return
        model = self.model_entry.get().strip() or "gpt-5"
        runner = self._runner_options.get(self.runner_var.get(), "dynamic_scene")
        dataset_path = self.dataset_entry.get().strip()
        if not dataset_path:
            dataset_path = "data/dynamic_scene" if runner == "dynamic_scene" else "data/static_scene"
        output_dir = Path(self.output_entry.get().strip() or str(self.output_dir))
        output_dir.mkdir(parents=True, exist_ok=True)
        max_rounds = self.rounds_entry.get().strip()

        python_path = sys.executable.replace("pythonw.exe", "python.exe")
        cmd = [
            python_path,
            str(self.backend_dir / "runners" / f"{runner}.py"),
            "--task",
            task,
            "--model",
            model,
            "--dataset-path",
            dataset_path,
            "--output-dir",
            str(output_dir),
        ]
        if max_rounds:
            cmd.extend(["--max-rounds", max_rounds])

        self.log(self.tr("viga_msg_running"))
        self.set_busy(True)
        self.run_process(cmd, on_done=self.on_process_done)

    def open_backend_folder(self):
        if self.backend_dir.exists():
            os.startfile(str(self.backend_dir))

    def open_output_folder(self):
        output_dir = Path(self.output_entry.get().strip() or str(self.output_dir))
        output_dir.mkdir(parents=True, exist_ok=True)
        os.startfile(str(output_dir))

    def open_repo(self):
        import webbrowser
        webbrowser.open("https://github.com/Fugtemypt123/VIGA")

    def open_project(self):
        import webbrowser
        webbrowser.open("https://fugtemypt123.github.io/VIGA-website/")

    def open_docs(self):
        import webbrowser
        webbrowser.open("https://arxiv.org/abs/2601.11109")

    def select_dataset(self):
        folder = filedialog.askdirectory(title=self.tr("viga_dataset_label"))
        if folder:
            self.dataset_entry.delete(0, "end")
            self.dataset_entry.insert(0, folder)

    def on_runner_change(self, *_):
        runner = self._runner_options.get(self.runner_var.get(), "dynamic_scene")
        default_path = "data/dynamic_scene" if runner == "dynamic_scene" else "data/static_scene"
        current = self.dataset_entry.get().strip()
        if not current or current == self._last_default_dataset:
            self.dataset_entry.delete(0, "end")
            self.dataset_entry.insert(0, default_path)
        self._last_default_dataset = default_path

    def run_cmd_blocking(self, cmd, cwd=None):
        self.safe_log(f"$ {' '.join(cmd)}")
        try:
            process = subprocess.Popen(
                cmd,
                cwd=str(cwd) if cwd else None,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0,
            )
            if process.stdout:
                for line in process.stdout:
                    self.safe_log(line.rstrip())
            process.wait()
            return process.returncode
        except Exception as exc:
            self.safe_log(f"{self.tr('status_error')}: {exc}")
            return 1

    def run_process(self, cmd, on_done=None):
        def worker():
            try:
                process = subprocess.Popen(
                    cmd,
                    cwd=str(self.backend_dir) if self.backend_dir.exists() else None,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0,
                )
                if process.stdout:
                    for line in process.stdout:
                        self.safe_log(line.rstrip())
                process.wait()
                returncode = process.returncode
            except Exception as exc:
                returncode = 1
                self.safe_log(f"{self.tr('status_error')}: {exc}")
            if on_done:
                self.after(0, lambda: on_done(returncode))
            else:
                self.after(0, lambda: self.on_process_done(returncode))

        threading.Thread(target=worker, daemon=True).start()

    def on_process_done(self, returncode):
        self.set_busy(False)
        if returncode == 0:
            self.log(self.tr("viga_msg_done"))
        else:
            self.log(self.tr("viga_msg_failed").format(returncode))
        self.refresh_buttons()
