import customtkinter as ctk
import logging
import webbrowser

from modules.base import StudioModule


class FlowActR1Module(StudioModule):
    def __init__(self, parent):
        super().__init__(parent, "flowact_r1", "FlowAct-R1")
        self.view = None
        self.app = parent

    def get_view(self) -> ctk.CTkFrame:
        self.view = FlowActR1View(self.app.main_container, self.app)
        return self.view

    def on_enter(self):
        pass

    def on_leave(self):
        pass


class FlowActR1View(ctk.CTkFrame):
    def __init__(self, master, app, **kwargs):
        super().__init__(master, **kwargs)
        self.app = app
        self.tr = app.tr
        self.build_ui()

    def build_ui(self):
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=10, pady=(10, 5))
        ctk.CTkLabel(header, text=self.tr("flowact_r1_title"), font=ctk.CTkFont(size=24, weight="bold")).pack(anchor="w")
        ctk.CTkLabel(header, text=self.tr("flowact_r1_subtitle"), text_color="gray").pack(anchor="w")
        ctk.CTkLabel(header, text=self.tr("flowact_r1_plain"), text_color="gray").pack(anchor="w")

        actions = ctk.CTkFrame(self, fg_color="transparent")
        actions.pack(fill="x", padx=10, pady=(10, 5))
        ctk.CTkButton(actions, text=self.tr("flowact_r1_btn_open_project"), command=self.open_project).pack(side="left", padx=5)
        ctk.CTkButton(actions, text=self.tr("flowact_r1_btn_open_paper"), command=self.open_paper).pack(side="left", padx=5)

        note = ctk.CTkLabel(self, text=self.tr("flowact_r1_note"), text_color="gray", wraplength=720, justify="left")
        note.pack(fill="x", padx=15, pady=(10, 10))

    def log(self, message):
        logging.info(message)

    def open_project(self):
        webbrowser.open("https://grisoon.github.io/FlowAct-R1/")

    def open_paper(self):
        webbrowser.open("https://arxiv.org/pdf/2601.10103")
