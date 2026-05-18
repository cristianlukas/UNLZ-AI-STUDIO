import customtkinter as ctk
import webbrowser

from modules.base import StudioModule


SCENEMA_REDDIT_URL = "https://www.reddit.com/r/StableDiffusion/comments/1tbzgi3/scenema_audio_zeroshot_expressive_voice_cloning/"


class ScenemaAudioModule(StudioModule):
    def __init__(self, parent):
        super().__init__(parent, "scenema_audio", "Scenema Audio")
        self.view = None
        self.app = parent

    def get_view(self) -> ctk.CTkFrame:
        self.view = ScenemaAudioView(self.app.main_container, self.app)
        return self.view

    def on_enter(self):
        pass

    def on_leave(self):
        pass


class ScenemaAudioView(ctk.CTkFrame):
    def __init__(self, master, app, **kwargs):
        super().__init__(master, **kwargs)
        self.app = app
        self.tr = app.tr
        self.build_ui()

    def build_ui(self):
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=10, pady=(10, 5))
        ctk.CTkLabel(header, text=self.tr("scenema_title"), font=ctk.CTkFont(size=24, weight="bold")).pack(anchor="w")
        ctk.CTkLabel(header, text=self.tr("scenema_subtitle"), text_color="gray").pack(anchor="w")

        notice = ctk.CTkFrame(self)
        notice.pack(fill="x", padx=10, pady=(20, 10))
        ctk.CTkLabel(notice, text=self.tr("scenema_notice_title"), font=ctk.CTkFont(size=16, weight="bold")).pack(
            anchor="w", padx=10, pady=(10, 0)
        )
        ctk.CTkLabel(notice, text=self.tr("scenema_notice_desc"), text_color="gray").pack(anchor="w", padx=10, pady=(0, 10))

        links = ctk.CTkFrame(self, fg_color="transparent")
        links.pack(fill="x", padx=10, pady=(5, 10))
        ctk.CTkButton(links, text=self.tr("scenema_btn_open_source"), command=self.open_source).pack(side="left", padx=5)

    def open_source(self):
        webbrowser.open(SCENEMA_REDDIT_URL)

