import customtkinter as ctk
import logging
import os
import subprocess
import threading
from pathlib import Path
from tkinter import messagebox
import webbrowser

from modules.base import StudioModule


class OmniTransferModule(StudioModule):
    def __init__(self, parent):
        super().__init__(parent, "omni_transfer", "OmniTransfer")
        self.view = None
        self.app = parent

    def get_view(self) -> ctk.CTkFrame:
        self.view = OmniTransferView(self.app.main_container, self.app)
        return self.view

    def on_enter(self):
        pass

    def on_leave(self):
        pass


class OmniTransferView(ctk.CTkFrame):
    def __init__(self, master, app, **kwargs):
        super().__init__(master, **kwargs)
        self.app = app
        self.tr = app.tr
        self._busy = False

        self.app_root = Path(__file__).resolve().parents[3]
        self.backend_dir = self.app_root / "system" / "ai-backends" / "OmniTransfer"

        self.build_ui()
        self.refresh_buttons()

    def build_ui(self):
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=10, pady=(10, 5))
        ctk.CTkLabel(header, text=self.tr("omni_transfer_title"), font=ctk.CTkFont(size=24, weight="bold")).pack(anchor="w")
        ctk.CTkLabel(header, text=self.tr("omni_transfer_subtitle"), text_color="gray").pack(anchor="w")
        ctk.CTkLabel(header, text=self.tr("omni_transfer_plain"), text_color="gray").pack(anchor="w")

        actions = ctk.CTkFrame(self, fg_color="transparent")
        actions.pack(fill="x", padx=10, pady=(10, 5))
        self.btn_install = ctk.CTkButton(actions, text=self.tr("omni_transfer_btn_install"), command=self.install_backend)
        self.btn_install.pack(side="left", padx=5)
        self.btn_uninstall = ctk.CTkButton(actions, text=self.tr("omni_transfer_btn_uninstall"), command=self.uninstall_backend)
        self.btn_uninstall.pack(side="left", padx=5)
        self.btn_open = ctk.CTkButton(actions, text=self.tr("omni_transfer_btn_open_folder"), command=self.open_backend_folder)
        self.btn_open.pack(side="left", padx=5)

        links = ctk.CTkFrame(self, fg_color="transparent")
        links.pack(fill="x", padx=10, pady=(5, 5))
        ctk.CTkButton(links, text=self.tr("omni_transfer_btn_open_repo"), command=self.open_repo).pack(side="left", padx=5)
        ctk.CTkButton(links, text=self.tr("omni_transfer_btn_open_project"), command=self.open_project).pack(side="left", padx=5)
        ctk.CTkButton(links, text=self.tr("omni_transfer_btn_open_paper"), command=self.open_paper).pack(side="left", padx=5)

        status_frame = ctk.CTkFrame(self, fg_color="transparent")
        status_frame.pack(fill="x", padx=10, pady=(5, 0))
        ctk.CTkLabel(status_frame, text=self.tr("omni_transfer_status_label")).pack(side="left")
        self.status_value = ctk.CTkLabel(status_frame, text=self.tr("omni_transfer_status_idle"), text_color="gray")
        self.status_value.pack(side="left", padx=(6, 0))

        note = ctk.CTkLabel(self, text=self.tr("omni_transfer_note"), text_color="gray", wraplength=720, justify="left")
        note.pack(fill="x", padx=15, pady=(10, 10))

    def refresh_buttons(self):
        if self._busy:
            for btn in (self.btn_install, self.btn_uninstall, self.btn_open):
                btn.configure(state="disabled")
            return

        installed = self.backend_dir.exists()
        if installed:
            self.btn_install.pack_forget()
            if not self.btn_uninstall.winfo_manager():
                self.btn_uninstall.pack(side="left", padx=5)
            if not self.btn_open.winfo_manager():
                self.btn_open.pack(side="left", padx=5)
        else:
            self.btn_uninstall.pack_forget()
            self.btn_open.pack_forget()
            if not self.btn_install.winfo_manager():
                self.btn_install.pack(side="left", padx=5)

        for btn in (self.btn_install, self.btn_uninstall, self.btn_open):
            btn.configure(state="normal")

    def set_busy(self, busy):
        self._busy = busy
        if self.status_value:
            self.status_value.configure(
                text=self.tr("status_in_progress") if busy else self.tr("omni_transfer_status_idle")
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
            self.log(self.tr("omni_transfer_msg_already_installed"))
            self.refresh_buttons()
            return
        if not self.check_git_available():
            messagebox.showwarning(self.tr("status_error"), self.tr("omni_transfer_msg_git_missing"))
            return
        self.backend_dir.parent.mkdir(parents=True, exist_ok=True)
        self.log(self.tr("omni_transfer_msg_installing"))
        self.set_busy(True)
        self.run_process(
            ["git", "clone", "--depth", "1", "https://github.com/PangzeCheung/OmniTransfer", str(self.backend_dir)],
            on_done=self.on_process_done,
        )

    def uninstall_backend(self):
        if not self.backend_dir.exists():
            self.log(self.tr("omni_transfer_msg_not_installed"))
            self.refresh_buttons()
            return
        try:
            import shutil
            shutil.rmtree(self.backend_dir)
            self.log(self.tr("omni_transfer_msg_uninstalled"))
        except Exception as exc:
            self.log(f"{self.tr('status_error')}: {exc}")
        self.refresh_buttons()

    def open_backend_folder(self):
        if self.backend_dir.exists():
            os.startfile(str(self.backend_dir))

    def open_repo(self):
        webbrowser.open("https://github.com/PangzeCheung/OmniTransfer")

    def open_project(self):
        webbrowser.open("https://pangzecheung.github.io/OmniTransfer/")

    def open_paper(self):
        webbrowser.open("https://arxiv.org/abs/2601.14250")

    def run_process(self, cmd, on_done=None):
        def worker():
            try:
                process = subprocess.Popen(
                    cmd,
                    cwd=str(self.backend_dir.parent) if self.backend_dir.parent.exists() else None,
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
            self.log(self.tr("omni_transfer_msg_done"))
        else:
            self.log(self.tr("omni_transfer_msg_failed").format(returncode))
        self.refresh_buttons()
