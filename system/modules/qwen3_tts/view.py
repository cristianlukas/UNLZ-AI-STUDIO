import customtkinter as ctk
import logging
import os
import subprocess
import threading
from pathlib import Path
from tkinter import filedialog, messagebox
import webbrowser

from modules.base import StudioModule


class Qwen3TTSModule(StudioModule):
    def __init__(self, parent):
        super().__init__(parent, "qwen3_tts", "Qwen3-TTS")
        self.view = None
        self.app = parent

    def get_view(self) -> ctk.CTkFrame:
        self.view = Qwen3TTSView(self.app.main_container, self.app)
        return self.view

    def on_enter(self):
        pass

    def on_leave(self):
        pass


class Qwen3TTSView(ctk.CTkFrame):
    def __init__(self, master, app, **kwargs):
        super().__init__(master, **kwargs)
        self.app = app
        self.tr = app.tr
        self._busy = False

        self.app_root = Path(__file__).resolve().parents[3]
        self.backend_dir = self.app_root / "system" / "ai-backends" / "Qwen3-TTS"
        self.output_dir = self.app_root / "system" / "qwen3-tts-out"
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.build_ui()
        self.refresh_buttons()

    def build_ui(self):
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=10, pady=(10, 5))
        ctk.CTkLabel(header, text=self.tr("qwen3_tts_title"), font=ctk.CTkFont(size=24, weight="bold")).pack(anchor="w")
        ctk.CTkLabel(header, text=self.tr("qwen3_tts_subtitle"), text_color="gray").pack(anchor="w")
        ctk.CTkLabel(header, text=self.tr("qwen3_tts_plain"), text_color="gray").pack(anchor="w")

        actions = ctk.CTkFrame(self, fg_color="transparent")
        actions.pack(fill="x", padx=10, pady=(10, 5))
        self.btn_install = ctk.CTkButton(actions, text=self.tr("qwen3_tts_btn_install"), command=self.install_backend)
        self.btn_install.pack(side="left", padx=5)
        self.btn_uninstall = ctk.CTkButton(actions, text=self.tr("qwen3_tts_btn_uninstall"), command=self.uninstall_backend)
        self.btn_uninstall.pack(side="left", padx=5)
        self.btn_deps = ctk.CTkButton(actions, text=self.tr("qwen3_tts_btn_deps"), command=self.install_deps)
        self.btn_deps.pack(side="left", padx=5)
        self.btn_open = ctk.CTkButton(actions, text=self.tr("qwen3_tts_btn_open_folder"), command=self.open_backend_folder)
        self.btn_open.pack(side="left", padx=5)

        links = ctk.CTkFrame(self, fg_color="transparent")
        links.pack(fill="x", padx=10, pady=(5, 5))
        ctk.CTkButton(links, text=self.tr("qwen3_tts_btn_open_repo"), command=self.open_repo).pack(side="left", padx=5)
        ctk.CTkButton(links, text=self.tr("qwen3_tts_btn_open_model"), command=self.open_models).pack(side="left", padx=5)
        ctk.CTkButton(links, text=self.tr("qwen3_tts_btn_open_demo"), command=self.open_demo).pack(side="left", padx=5)
        ctk.CTkButton(links, text=self.tr("qwen3_tts_btn_open_blog"), command=self.open_blog).pack(side="left", padx=5)
        ctk.CTkButton(links, text=self.tr("qwen3_tts_btn_open_paper"), command=self.open_paper).pack(side="left", padx=5)

        status_frame = ctk.CTkFrame(self, fg_color="transparent")
        status_frame.pack(fill="x", padx=10, pady=(5, 0))
        ctk.CTkLabel(status_frame, text=self.tr("qwen3_tts_status_label")).pack(side="left")
        self.status_value = ctk.CTkLabel(status_frame, text=self.tr("qwen3_tts_status_idle"), text_color="gray")
        self.status_value.pack(side="left", padx=(6, 0))

        body = ctk.CTkFrame(self)
        body.pack(fill="both", expand=True, padx=10, pady=(10, 10))
        body.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(body, text=self.tr("qwen3_tts_mode_label")).grid(row=0, column=0, sticky="w", padx=10, pady=(10, 4))
        self.mode_var = ctk.StringVar(value=self.tr("qwen3_tts_mode_custom"))
        ctk.CTkOptionMenu(
            body,
            variable=self.mode_var,
            values=[
                self.tr("qwen3_tts_mode_custom"),
                self.tr("qwen3_tts_mode_design"),
                self.tr("qwen3_tts_mode_clone"),
            ],
        ).grid(row=0, column=1, sticky="ew", padx=10, pady=(10, 4))

        ctk.CTkLabel(body, text=self.tr("qwen3_tts_model_label")).grid(row=1, column=0, sticky="w", padx=10, pady=(0, 4))
        self.model_entry = ctk.CTkEntry(body)
        self.model_entry.insert(0, "Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice")
        self.model_entry.grid(row=1, column=1, sticky="ew", padx=10, pady=(0, 4))

        ctk.CTkLabel(body, text=self.tr("qwen3_tts_text_label")).grid(row=2, column=0, sticky="w", padx=10, pady=(0, 4))
        self.text_entry = ctk.CTkTextbox(body, height=120)
        self.text_entry.grid(row=3, column=0, columnspan=3, sticky="ew", padx=10, pady=(0, 6))

        ctk.CTkLabel(body, text=self.tr("qwen3_tts_language_label")).grid(row=4, column=0, sticky="w", padx=10, pady=(0, 4))
        self.language_entry = ctk.CTkEntry(body)
        self.language_entry.insert(0, "Auto")
        self.language_entry.grid(row=4, column=1, sticky="ew", padx=10, pady=(0, 4))

        ctk.CTkLabel(body, text=self.tr("qwen3_tts_speaker_label")).grid(row=5, column=0, sticky="w", padx=10, pady=(0, 4))
        self.speaker_entry = ctk.CTkEntry(body)
        self.speaker_entry.insert(0, "Vivian")
        self.speaker_entry.grid(row=5, column=1, sticky="ew", padx=10, pady=(0, 4))

        ctk.CTkLabel(body, text=self.tr("qwen3_tts_instruct_label")).grid(row=6, column=0, sticky="w", padx=10, pady=(0, 4))
        self.instruct_entry = ctk.CTkEntry(body)
        self.instruct_entry.grid(row=6, column=1, sticky="ew", padx=10, pady=(0, 4))

        ctk.CTkLabel(body, text=self.tr("qwen3_tts_ref_audio_label")).grid(row=7, column=0, sticky="w", padx=10, pady=(0, 4))
        self.ref_audio_entry = ctk.CTkEntry(body)
        self.ref_audio_entry.grid(row=7, column=1, sticky="ew", padx=10, pady=(0, 4))
        ctk.CTkButton(body, text=self.tr("btn_browse"), command=self.select_ref_audio).grid(row=7, column=2, padx=(0, 10), pady=(0, 4))

        ctk.CTkLabel(body, text=self.tr("qwen3_tts_ref_text_label")).grid(row=8, column=0, sticky="w", padx=10, pady=(0, 4))
        self.ref_text_entry = ctk.CTkEntry(body)
        self.ref_text_entry.grid(row=8, column=1, sticky="ew", padx=10, pady=(0, 4))

        ctk.CTkLabel(body, text=self.tr("qwen3_tts_device_label")).grid(row=9, column=0, sticky="w", padx=10, pady=(0, 4))
        self.device_var = ctk.StringVar(value="auto")
        ctk.CTkOptionMenu(body, variable=self.device_var, values=["auto", "cuda:0", "cpu"]).grid(
            row=9, column=1, sticky="w", padx=10, pady=(0, 4)
        )

        ctk.CTkLabel(body, text=self.tr("qwen3_tts_dtype_label")).grid(row=10, column=0, sticky="w", padx=10, pady=(0, 4))
        self.dtype_var = ctk.StringVar(value="bfloat16")
        ctk.CTkOptionMenu(body, variable=self.dtype_var, values=["bfloat16", "float16", "float32"]).grid(
            row=10, column=1, sticky="w", padx=10, pady=(0, 4)
        )

        ctk.CTkLabel(body, text=self.tr("qwen3_tts_attn_label")).grid(row=11, column=0, sticky="w", padx=10, pady=(0, 4))
        self.attn_entry = ctk.CTkEntry(body)
        self.attn_entry.insert(0, "flash_attention_2")
        self.attn_entry.grid(row=11, column=1, sticky="ew", padx=10, pady=(0, 4))

        ctk.CTkLabel(body, text=self.tr("qwen3_tts_output_label")).grid(row=12, column=0, sticky="w", padx=10, pady=(0, 4))
        self.output_entry = ctk.CTkEntry(body, placeholder_text=str(self.output_dir))
        self.output_entry.grid(row=12, column=1, sticky="ew", padx=10, pady=(0, 4))
        ctk.CTkButton(body, text=self.tr("qwen3_tts_btn_open_output"), command=self.open_output_folder).grid(
            row=12, column=2, padx=(0, 10), pady=(0, 4)
        )

        buttons = ctk.CTkFrame(body, fg_color="transparent")
        buttons.grid(row=13, column=0, columnspan=2, sticky="w", padx=10, pady=(10, 10))
        self.btn_run = ctk.CTkButton(buttons, text=self.tr("qwen3_tts_btn_run"), command=self.run_action)
        self.btn_run.pack(side="left", padx=(0, 8))

        note = ctk.CTkLabel(self, text=self.tr("qwen3_tts_note"), text_color="gray", wraplength=720, justify="left")
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
                text=self.tr("status_in_progress") if busy else self.tr("qwen3_tts_status_idle")
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
            self.log(self.tr("qwen3_tts_msg_already_installed"))
            self.refresh_buttons()
            return
        if not self.check_git_available():
            messagebox.showwarning(self.tr("status_error"), self.tr("qwen3_tts_msg_git_missing"))
            return
        self.backend_dir.parent.mkdir(parents=True, exist_ok=True)
        self.log(self.tr("qwen3_tts_msg_installing"))
        self.set_busy(True)
        self.run_process(
            ["git", "clone", "--depth", "1", "https://github.com/QwenLM/Qwen3-TTS", str(self.backend_dir)],
            on_done=self.on_process_done,
        )

    def uninstall_backend(self):
        if not self.backend_dir.exists():
            self.log(self.tr("qwen3_tts_msg_not_installed"))
            self.refresh_buttons()
            return
        try:
            import shutil
            shutil.rmtree(self.backend_dir)
            self.log(self.tr("qwen3_tts_msg_uninstalled"))
        except Exception as exc:
            self.log(f"{self.tr('status_error')}: {exc}")
        self.refresh_buttons()

    def install_deps(self):
        if not self.backend_dir.exists():
            messagebox.showwarning(self.tr("status_error"), self.tr("qwen3_tts_msg_not_installed"))
            return
        python_path = sys.executable.replace("pythonw.exe", "python.exe")
        self.log(self.tr("qwen3_tts_msg_running"))
        self.set_busy(True)
        self.run_process([python_path, "-m", "pip", "install", "-e", "."], on_done=self.on_process_done)

    def run_action(self):
        if not self.backend_dir.exists():
            messagebox.showwarning(self.tr("status_error"), self.tr("qwen3_tts_msg_not_installed"))
            return
        text = self.text_entry.get("1.0", "end").strip()
        if not text:
            messagebox.showwarning(self.tr("status_error"), self.tr("qwen3_tts_msg_missing_text"))
            return
        mode = self.mode_var.get()
        mode_key = "custom_voice"
        if mode == self.tr("qwen3_tts_mode_design"):
            mode_key = "voice_design"
        elif mode == self.tr("qwen3_tts_mode_clone"):
            mode_key = "voice_clone"

        ref_audio = self.ref_audio_entry.get().strip()
        ref_text = self.ref_text_entry.get().strip()
        if mode_key == "voice_clone" and (not ref_audio or not ref_text):
            messagebox.showwarning(self.tr("status_error"), self.tr("qwen3_tts_msg_missing_ref"))
            return

        output_dir = Path(self.output_entry.get().strip() or str(self.output_dir))
        output_dir.mkdir(parents=True, exist_ok=True)
        python_path = sys.executable.replace("pythonw.exe", "python.exe")
        cmd = [
            python_path,
            str(self.app_root / "system" / "data" / "qwen3_tts" / "qwen3_tts_infer.py"),
            "--mode",
            mode_key,
            "--model_id",
            self.model_entry.get().strip() or "Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice",
            "--text",
            text,
            "--language",
            self.language_entry.get().strip() or "Auto",
            "--speaker",
            self.speaker_entry.get().strip() or "Vivian",
            "--output_dir",
            str(output_dir),
            "--device",
            self.device_var.get(),
            "--dtype",
            self.dtype_var.get(),
            "--attn_implementation",
            self.attn_entry.get().strip() or "flash_attention_2",
        ]
        instruct = self.instruct_entry.get().strip()
        if instruct:
            cmd.extend(["--instruct", instruct])
        if ref_audio:
            cmd.extend(["--ref_audio", ref_audio])
        if ref_text:
            cmd.extend(["--ref_text", ref_text])

        self.log(self.tr("qwen3_tts_msg_running"))
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
        webbrowser.open("https://github.com/QwenLM/Qwen3-TTS")

    def open_models(self):
        webbrowser.open("https://huggingface.co/collections/Qwen/qwen3-tts")

    def open_demo(self):
        webbrowser.open("https://huggingface.co/spaces/Qwen/Qwen3-TTS")

    def open_blog(self):
        webbrowser.open("https://qwen.ai/blog?id=qwen3tts-0115")

    def open_paper(self):
        webbrowser.open("https://arxiv.org/abs/2601.15621")

    def select_ref_audio(self):
        file_path = filedialog.askopenfilename(
            title=self.tr("qwen3_tts_ref_audio_label"),
            filetypes=[("Audio", "*.wav;*.mp3;*.flac;*.m4a"), ("All files", "*.*")],
        )
        if file_path:
            self.ref_audio_entry.delete(0, "end")
            self.ref_audio_entry.insert(0, file_path)

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
            self.log(self.tr("qwen3_tts_msg_done"))
        else:
            self.log(self.tr("qwen3_tts_msg_failed").format(returncode))
        self.refresh_buttons()
