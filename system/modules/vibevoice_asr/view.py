import customtkinter as ctk
import os
import sys
import threading
import subprocess
import logging
from pathlib import Path
from tkinter import filedialog, messagebox

from modules.base import StudioModule


class VibeVoiceASRModule(StudioModule):
    def __init__(self, parent):
        super().__init__(parent, "vibevoice_asr", "VibeVoice ASR")
        self.view = None
        self.app = parent

    def get_view(self) -> ctk.CTkFrame:
        self.view = VibeVoiceASRView(self.app.main_container, self.app)
        return self.view

    def on_enter(self):
        pass

    def on_leave(self):
        pass


class VibeVoiceASRView(ctk.CTkFrame):
    def __init__(self, master, app, **kwargs):
        super().__init__(master, **kwargs)
        self.app = app
        self.tr = app.tr
        self._busy = False

        self.app_root = Path(__file__).resolve().parents[3]
        self.backend_dir = self.app_root / "system" / "ai-backends" / "VibeVoice"
        self.output_dir = self.app_root / "system" / "vibevoice-asr-out"
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.build_ui()
        self.refresh_buttons()

    def build_ui(self):
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=10, pady=(10, 5))
        ctk.CTkLabel(header, text=self.tr("vibevoice_asr_title"), font=ctk.CTkFont(size=24, weight="bold")).pack(anchor="w")
        ctk.CTkLabel(header, text=self.tr("vibevoice_asr_subtitle"), text_color="gray").pack(anchor="w")
        ctk.CTkLabel(header, text=self.tr("vibevoice_asr_plain"), text_color="gray").pack(anchor="w")

        actions = ctk.CTkFrame(self, fg_color="transparent")
        actions.pack(fill="x", padx=10, pady=(10, 5))
        self.btn_install = ctk.CTkButton(actions, text=self.tr("vibevoice_asr_btn_install"), command=self.install_backend)
        self.btn_install.pack(side="left", padx=5)
        self.btn_uninstall = ctk.CTkButton(actions, text=self.tr("vibevoice_asr_btn_uninstall"), command=self.uninstall_backend)
        self.btn_uninstall.pack(side="left", padx=5)
        self.btn_deps = ctk.CTkButton(actions, text=self.tr("vibevoice_asr_btn_deps"), command=self.install_deps)
        self.btn_deps.pack(side="left", padx=5)
        self.btn_open = ctk.CTkButton(actions, text=self.tr("vibevoice_asr_btn_open_folder"), command=self.open_backend_folder)
        self.btn_open.pack(side="left", padx=5)

        links = ctk.CTkFrame(self, fg_color="transparent")
        links.pack(fill="x", padx=10, pady=(5, 5))
        ctk.CTkButton(links, text=self.tr("vibevoice_asr_btn_open_repo"), command=self.open_repo).pack(side="left", padx=5)
        ctk.CTkButton(links, text=self.tr("vibevoice_asr_btn_open_project"), command=self.open_project).pack(side="left", padx=5)
        ctk.CTkButton(links, text=self.tr("vibevoice_asr_btn_open_demo"), command=self.open_demo).pack(side="left", padx=5)

        status_frame = ctk.CTkFrame(self, fg_color="transparent")
        status_frame.pack(fill="x", padx=10, pady=(5, 0))
        ctk.CTkLabel(status_frame, text=self.tr("vibevoice_asr_status_label")).pack(side="left")
        self.status_value = ctk.CTkLabel(status_frame, text=self.tr("vibevoice_asr_status_idle"), text_color="gray")
        self.status_value.pack(side="left", padx=(6, 0))

        body = ctk.CTkFrame(self)
        body.pack(fill="both", expand=True, padx=10, pady=(10, 10))
        body.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(body, text=self.tr("vibevoice_asr_model_label")).grid(row=0, column=0, sticky="w", padx=10, pady=(10, 4))
        self.model_entry = ctk.CTkEntry(body)
        self.model_entry.insert(0, "microsoft/VibeVoice-ASR")
        self.model_entry.grid(row=0, column=1, sticky="ew", padx=10, pady=(10, 4))

        ctk.CTkLabel(body, text=self.tr("vibevoice_asr_audio_label")).grid(row=1, column=0, sticky="w", padx=10, pady=(0, 4))
        self.audio_entry = ctk.CTkEntry(body, placeholder_text="audio.wav")
        self.audio_entry.grid(row=1, column=1, sticky="ew", padx=10, pady=(0, 4))
        ctk.CTkButton(body, text=self.tr("btn_browse"), command=self.select_audio).grid(row=1, column=2, padx=(0, 10), pady=(0, 4))

        ctk.CTkLabel(body, text=self.tr("vibevoice_asr_device_label")).grid(row=2, column=0, sticky="w", padx=10, pady=(0, 4))
        self.device_var = ctk.StringVar(value="auto")
        ctk.CTkOptionMenu(body, variable=self.device_var, values=["auto", "cuda", "cpu"]).grid(
            row=2, column=1, sticky="w", padx=10, pady=(0, 4)
        )

        params = ctk.CTkFrame(body, fg_color="transparent")
        params.grid(row=3, column=0, columnspan=3, sticky="ew", padx=10, pady=(0, 4))
        ctk.CTkLabel(params, text=self.tr("vibevoice_asr_max_tokens_label")).grid(row=0, column=0, sticky="w")
        self.max_tokens_entry = ctk.CTkEntry(params, width=100)
        self.max_tokens_entry.insert(0, "32768")
        self.max_tokens_entry.grid(row=0, column=1, padx=(6, 12))
        ctk.CTkLabel(params, text=self.tr("vibevoice_asr_temp_label")).grid(row=0, column=2, sticky="w")
        self.temp_entry = ctk.CTkEntry(params, width=80)
        self.temp_entry.insert(0, "0.0")
        self.temp_entry.grid(row=0, column=3, padx=(6, 12))
        ctk.CTkLabel(params, text=self.tr("vibevoice_asr_top_p_label")).grid(row=0, column=4, sticky="w")
        self.top_p_entry = ctk.CTkEntry(params, width=80)
        self.top_p_entry.insert(0, "1.0")
        self.top_p_entry.grid(row=0, column=5, padx=(6, 12))
        ctk.CTkLabel(params, text=self.tr("vibevoice_asr_beams_label")).grid(row=0, column=6, sticky="w")
        self.beams_entry = ctk.CTkEntry(params, width=80)
        self.beams_entry.insert(0, "1")
        self.beams_entry.grid(row=0, column=7, padx=(6, 12))
        ctk.CTkLabel(params, text=self.tr("vibevoice_asr_attn_label")).grid(row=0, column=8, sticky="w")
        self.attn_entry = ctk.CTkEntry(params, width=140)
        self.attn_entry.insert(0, "flash_attention_2")
        self.attn_entry.grid(row=0, column=9, padx=(6, 0))

        ctk.CTkLabel(body, text=self.tr("vibevoice_asr_output_label")).grid(row=4, column=0, sticky="w", padx=10, pady=(0, 4))
        self.output_entry = ctk.CTkEntry(body, placeholder_text=str(self.output_dir))
        self.output_entry.grid(row=4, column=1, sticky="ew", padx=10, pady=(0, 4))
        ctk.CTkButton(body, text=self.tr("vibevoice_asr_btn_open_output"), command=self.open_output_folder).grid(
            row=4, column=2, padx=(0, 10), pady=(0, 4)
        )

        buttons = ctk.CTkFrame(body, fg_color="transparent")
        buttons.grid(row=5, column=0, columnspan=2, sticky="w", padx=10, pady=(10, 10))
        self.btn_run = ctk.CTkButton(buttons, text=self.tr("vibevoice_asr_btn_run"), command=self.run_action)
        self.btn_run.pack(side="left", padx=(0, 8))

        note = ctk.CTkLabel(self, text=self.tr("vibevoice_asr_note"), text_color="gray", wraplength=720, justify="left")
        note.pack(fill="x", padx=15, pady=(0, 10))

    def refresh_buttons(self):
        if self._busy:
            for btn in (self.btn_install, self.btn_uninstall, self.btn_deps, self.btn_open, self.btn_run):
                btn.configure(state="disabled")
            return

        installed = self.backend_dir.exists()
        if installed:
            self.btn_install.pack_forget()
            if not self.btn_uninstall.winfo_manager():
                self.btn_uninstall.pack(side="left", padx=5)
            if not self.btn_deps.winfo_manager():
                self.btn_deps.pack(side="left", padx=5)
            if not self.btn_open.winfo_manager():
                self.btn_open.pack(side="left", padx=5)
        else:
            self.btn_uninstall.pack_forget()
            self.btn_deps.pack_forget()
            self.btn_open.pack_forget()
            if not self.btn_install.winfo_manager():
                self.btn_install.pack(side="left", padx=5)

        for btn in (self.btn_install, self.btn_uninstall, self.btn_deps, self.btn_open, self.btn_run):
            btn.configure(state="normal")

    def set_busy(self, busy):
        self._busy = busy
        if self.status_value:
            self.status_value.configure(
                text=self.tr("status_in_progress") if busy else self.tr("vibevoice_asr_status_idle")
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
            self.log(self.tr("vibevoice_asr_msg_already_installed"))
            self.refresh_buttons()
            return
        if not self.check_git_available():
            messagebox.showwarning(self.tr("status_error"), self.tr("vibevoice_asr_msg_git_missing"))
            return
        self.backend_dir.parent.mkdir(parents=True, exist_ok=True)
        self.log(self.tr("vibevoice_asr_msg_installing"))
        self.set_busy(True)
        self.run_process(
            ["git", "clone", "--depth", "1", "https://github.com/microsoft/VibeVoice", str(self.backend_dir)],
            on_done=self.on_process_done,
        )

    def uninstall_backend(self):
        if not self.backend_dir.exists():
            self.log(self.tr("vibevoice_asr_msg_not_installed"))
            self.refresh_buttons()
            return
        try:
            import shutil
            shutil.rmtree(self.backend_dir)
            self.log(self.tr("vibevoice_asr_msg_uninstalled"))
        except Exception as exc:
            self.log(f"{self.tr('status_error')}: {exc}")
        self.refresh_buttons()

    def install_deps(self):
        if not self.backend_dir.exists():
            messagebox.showwarning(self.tr("status_error"), self.tr("vibevoice_asr_msg_not_installed"))
            return
        python_path = sys.executable.replace("pythonw.exe", "python.exe")
        self.log(self.tr("vibevoice_asr_msg_running"))
        self.set_busy(True)
        self.run_process([python_path, "-m", "pip", "install", "-e", ".[asr]"], on_done=self.on_process_done)

    def run_action(self):
        if not self.backend_dir.exists():
            messagebox.showwarning(self.tr("status_error"), self.tr("vibevoice_asr_msg_not_installed"))
            return
        audio_path = self.audio_entry.get().strip()
        if not audio_path:
            messagebox.showwarning(self.tr("status_error"), self.tr("vibevoice_asr_msg_missing_audio"))
            return
        output_dir = Path(self.output_entry.get().strip() or str(self.output_dir))
        output_dir.mkdir(parents=True, exist_ok=True)
        python_path = sys.executable.replace("pythonw.exe", "python.exe")
        cmd = [
            python_path,
            str(self.app_root / "system" / "data" / "vibevoice_asr" / "vibevoice_asr_infer.py"),
            "--model_path",
            self.model_entry.get().strip() or "microsoft/VibeVoice-ASR",
            "--audio_file",
            audio_path,
            "--output_dir",
            str(output_dir),
            "--device",
            self.device_var.get(),
            "--max_new_tokens",
            self.max_tokens_entry.get().strip() or "32768",
            "--temperature",
            self.temp_entry.get().strip() or "0.0",
            "--top_p",
            self.top_p_entry.get().strip() or "1.0",
            "--num_beams",
            self.beams_entry.get().strip() or "1",
            "--attn_implementation",
            self.attn_entry.get().strip() or "flash_attention_2",
        ]
        self.log(self.tr("vibevoice_asr_msg_running"))
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
        webbrowser.open("https://github.com/microsoft/VibeVoice")

    def open_project(self):
        import webbrowser
        webbrowser.open("https://huggingface.co/microsoft/VibeVoice-ASR")

    def open_demo(self):
        import webbrowser
        webbrowser.open("https://aka.ms/vibevoice-asr")

    def select_audio(self):
        file_path = filedialog.askopenfilename(
            title=self.tr("vibevoice_asr_audio_label"),
            filetypes=[("Audio", "*.wav;*.mp3;*.flac;*.m4a;*.mp4;*.webm"), ("All files", "*.*")],
        )
        if file_path:
            self.audio_entry.delete(0, "end")
            self.audio_entry.insert(0, file_path)

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
            self.log(self.tr("vibevoice_asr_msg_done"))
        else:
            self.log(self.tr("vibevoice_asr_msg_failed").format(returncode))
        self.refresh_buttons()
