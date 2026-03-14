import customtkinter as ctk
import os
import threading
import requests
import json
import logging
import base64
import traceback
import time
from pathlib import Path
from modules.base import StudioModule
from tkinter import filedialog, messagebox, simpledialog
from PIL import Image, ImageTk
import io

try:
    import cv2
except Exception:  # pragma: no cover - optional dependency
    cv2 = None

class VLMFrontendModule(StudioModule):
    def __init__(self, parent):
        super().__init__(parent, "vlm_frontend", "Visión y VLM")
        self.view = None
        self.profile_manager = parent.profile_manager
        self.app = parent

    def get_view(self) -> ctk.CTkFrame:
        self.view = VLMFrontendView(self.app.main_container, self.profile_manager, self.app)
        return self.view

    def on_enter(self):
        pass

    def on_leave(self):
        pass


class VLMFrontendView(ctk.CTkFrame):
    def __init__(self, master, profile_manager, app, **kwargs):
        super().__init__(master, **kwargs)
        self.profile_manager = profile_manager
        self.app = app
        self.manager = app.manager
        self.system_root = Path(__file__).resolve().parents[2]
        self.log_dir = self.system_root / "logs"
        self.capture_dir = self.log_dir / "vlm_captures"
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.capture_dir.mkdir(parents=True, exist_ok=True)

        # Dedicated config for VLM Server
        self.vlm_port = 9090
        self.api_url = f"http://127.0.0.1:{self.vlm_port}/v1/chat/completions"
        self.loaded_model = None
        self.current_image_path = None
        self.model_file_map = {}

        # Camera / live mode state
        self.camera = None
        self.camera_running = False
        self.latest_frame_rgb = None
        self.latest_frame_gray_small = None
        self.last_change_ts = 0.0
        self.change_cooldown_sec = 1.2
        self.change_threshold = 12.0

        tr = self.app.tr

        # Layout: Tabs for Vision, Models, Search
        self.tabview = ctk.CTkTabview(self)
        self.tabview.pack(fill="both", expand=True, padx=10, pady=10)

        self.tab_vision = self.tabview.add(tr("tab_vision"))
        self.tab_models = self.tabview.add(tr("tab_models"))
        self.tab_search = self.tabview.add(tr("tab_download"))

        self.build_vision_tab()
        self.build_models_tab()
        self.build_search_tab()

        # Initial model scan
        self.refresh_models()

    # --- Vision Tab ---
    def build_vision_tab(self):
        tr = self.app.tr
        frame = self.tab_vision
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(2, weight=1)

        # Header: Server Status & Model
        header = ctk.CTkFrame(frame, height=50, fg_color=("gray95", "#2A2A2A"))
        header.grid(row=0, column=0, sticky="ew", padx=10, pady=5)

        ctk.CTkLabel(header, text=tr("lbl_server_port"), font=ctk.CTkFont(weight="bold")).pack(side="left", padx=10)
        self.status_indicator = ctk.CTkLabel(
            header,
            text=tr("status_stopped"),
            text_color="red",
            image=self.app.get_status_matrix_image(),
            compound="left",
        )
        self.status_indicator.pack(side="left")

        ctk.CTkLabel(header, text=tr("lbl_active_model"), font=ctk.CTkFont(weight="bold")).pack(side="left", padx=(20, 5))
        self.model_selector = ctk.CTkComboBox(header, width=300, values=[tr("placeholder_select_model")])
        self.model_selector.pack(side="left")

        self.btn_load = ctk.CTkButton(header, text=tr("btn_load"), width=80, command=self.toggle_vlm_server)
        self.btn_load.pack(side="left", padx=10)

        # Content area: Image display and controls
        content = ctk.CTkFrame(frame, fg_color="transparent")
        content.grid(row=1, column=0, sticky="nsew", padx=10, pady=5)
        content.grid_columnconfigure(0, weight=1)
        content.grid_columnconfigure(1, weight=1)

        # Left side: Image Display
        left_frame = ctk.CTkFrame(content, fg_color=("gray90", "#2A2A2A"))
        left_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 5))
        left_frame.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(left_frame, text=tr("lbl_image"), font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, sticky="w", padx=10, pady=5)

        self.image_label = ctk.CTkLabel(left_frame, text=tr("placeholder_no_image"), text_color="gray")
        self.image_label.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)

        btn_frame = ctk.CTkFrame(left_frame, fg_color="transparent")
        btn_frame.grid(row=2, column=0, sticky="ew", padx=10, pady=5)

        ctk.CTkButton(btn_frame, text=tr("btn_load_image"), command=self.load_image).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text=tr("btn_clear_image"), command=self.clear_image).pack(side="left", padx=5)
        self.btn_start_cam = ctk.CTkButton(btn_frame, text="Iniciar cámara", command=self.start_camera)
        self.btn_start_cam.pack(side="left", padx=5)
        self.btn_stop_cam = ctk.CTkButton(btn_frame, text="Detener cámara", command=self.stop_camera, state="disabled")
        self.btn_stop_cam.pack(side="left", padx=5)
        self.btn_capture = ctk.CTkButton(btn_frame, text="Capturar frame", command=self.capture_current_frame, state="disabled")
        self.btn_capture.pack(side="left", padx=5)

        self.track_changes_var = ctk.BooleanVar(value=False)
        self.track_changes = ctk.CTkCheckBox(
            left_frame,
            text="Registrar cambios en vivo",
            variable=self.track_changes_var,
        )
        self.track_changes.grid(row=3, column=0, sticky="w", padx=10, pady=(0, 6))

        # Right side: Analysis & Response
        right_frame = ctk.CTkFrame(content, fg_color=("gray90", "#2A2A2A"))
        right_frame.grid(row=0, column=1, sticky="nsew", padx=(5, 0))
        right_frame.grid_rowconfigure(3, weight=1)  # Set weight on row 3 where textbox is

        ctk.CTkLabel(right_frame, text=tr("lbl_prompt"), font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, sticky="w", padx=10, pady=5)

        self.prompt_input = ctk.CTkEntry(right_frame, placeholder_text=tr("vision_prompt_placeholder"))
        self.prompt_input.grid(row=1, column=0, sticky="ew", padx=10, pady=5)
        self.prompt_input.bind("<Return>", self.send_analysis)

        ctk.CTkLabel(right_frame, text=tr("lbl_response"), font=ctk.CTkFont(weight="bold")).grid(row=2, column=0, sticky="nw", padx=10, pady=(5, 0))

        self.response_text = ctk.CTkTextbox(right_frame, state="disabled", font=ctk.CTkFont(size=12), wrap="word")
        self.response_text.grid(row=3, column=0, sticky="nsew", padx=10, pady=5)

        right_frame.grid_columnconfigure(0, weight=1)

        # Control buttons
        control_frame = ctk.CTkFrame(content, fg_color="transparent")
        control_frame.grid(row=1, column=0, columnspan=2, sticky="ew", padx=10, pady=10)

        self.analyze_btn = ctk.CTkButton(control_frame, text=tr("btn_analyze"), command=self.send_analysis, fg_color="#3B24C8")
        self.analyze_btn.pack(side="left", padx=5)

        self.clear_btn = ctk.CTkButton(control_frame, text=tr("btn_clear_response"), command=self.clear_response)
        self.clear_btn.pack(side="left", padx=5)

        content.grid_columnconfigure(0, weight=1)
        content.grid_columnconfigure(1, weight=1)

        # Status
        self.vision_status = ctk.CTkLabel(frame, text=tr("status_ready"), text_color="gray")
        self.vision_status.grid(row=3, column=0, sticky="e", padx=10)

        # Check initial state
        self.check_server_state()

    def check_server_state(self):
        if self.manager.is_running("vlm_service"):
            self.status_indicator.configure(text=self.app.tr("status_running"), text_color="green")
            self.btn_load.configure(text=self.app.tr("btn_stop"), fg_color="red")
            self.prompt_input.configure(state="normal")
            self.analyze_btn.configure(state="normal")
        else:
            self.status_indicator.configure(text=self.app.tr("status_stopped"), text_color="red")
            self.btn_load.configure(text=self.app.tr("btn_load"), fg_color="green")
            self.prompt_input.configure(state="normal")
            self.analyze_btn.configure(state="normal")

        self.after(2000, self.check_server_state)

    def toggle_vlm_server(self):
        if self.manager.is_running("vlm_service"):
            self.manager.stop("vlm_service")
            self.check_server_state()
            return

        self.btn_load.configure(state="disabled", text=self.app.tr("status_starting"))
        threading.Thread(target=self._start_server_bg, daemon=True).start()

    def _start_server_bg(self):
        try:
            selected_model = self.model_selector.get().strip()
            model_path = self.model_file_map.get(selected_model)
            if not model_path:
                raise RuntimeError("Seleccione un modelo VLM válido antes de iniciar.")
            mmproj_path = self.find_mmproj(Path(model_path))
            if not mmproj_path:
                raise RuntimeError(
                    f"No se encontró mmproj para el modelo seleccionado ({model_path}). "
                    "Agregue mmproj-F16.gguf o mmproj-BF16.gguf en la misma carpeta."
                )

            profile = self.profile_manager.active_profile
            if profile.user_configurable:
                custom_cfg = self.profile_manager.get_custom_settings()
                n_gpu_layers = int(custom_cfg.get("n_gpu_layers", 2))
                ctx_size = int(custom_cfg.get("ctx_size", 8192))
                threads = int(custom_cfg.get("threads", 4))
                batch_size = int(custom_cfg.get("batch_size", 8))
            else:
                n_gpu_layers = int(getattr(profile, "n_gpu_layers", 2))
                # VLM needs more context than text-only models when images are large.
                ctx_size = max(4096, int(getattr(profile, "ctx_size", 4096)))
                threads = int(getattr(profile, "threads", 4))
                batch_size = int(getattr(profile, "batch_size", 8))

            config = {
                "model_path": model_path,
                "mmproj_path": str(mmproj_path),
                "port": self.vlm_port,
                "host": "127.0.0.1",
                "n_gpu_layers": max(0, n_gpu_layers),
                "ctx_size": max(2048, ctx_size),
                "threads": max(1, threads),
                "batch_size": max(1, batch_size),
                "n_predict": 4096,
            }
            self.app.set_setting("vlm_model_dir", str(Path(model_path).parent))
            logging.info(
                "[VLM] Launch config: model=%s mmproj=%s ngl=%s ctx=%s threads=%s batch=%s n_predict=%s",
                config["model_path"],
                config["mmproj_path"],
                config["n_gpu_layers"],
                config["ctx_size"],
                config["threads"],
                config["batch_size"],
                config["n_predict"],
            )
            self.manager.start_process("vlm_service", config)
            self.after(0, self.check_server_state)
        except Exception as e:
            self.after(0, lambda: messagebox.showerror("Start Failed", str(e)))
            self.after(0, self.check_server_state)

    def load_image(self):
        file_path = filedialog.askopenfilename(
            filetypes=[("Images", "*.jpg *.jpeg *.png *.bmp *.gif"), ("All Files", "*.*")]
        )
        if file_path:
            self.stop_camera()
            self.current_image_path = file_path
            self.latest_frame_rgb = None
            self.latest_frame_gray_small = None
            self.display_image(file_path)

    def display_image(self, image_source):
        try:
            if isinstance(image_source, Image.Image):
                img = image_source.copy()
            else:
                img = Image.open(image_source)
            # Resize to fit label (max 300x300)
            img.thumbnail((300, 300), Image.Resampling.LANCZOS)
            photo = ImageTk.PhotoImage(img)
            self.image_label.configure(image=photo, text="")
            self.image_label.image = photo  # Keep a reference
        except Exception as e:
            messagebox.showerror("Error", f"Could not load image: {e}")

    def clear_image(self):
        self.current_image_path = None
        self.latest_frame_rgb = None
        self.latest_frame_gray_small = None
        self.image_label.configure(image=None, text=self.app.tr("placeholder_no_image"), text_color="gray")

    def send_analysis(self, event=None):
        if not self.current_image_path and self.latest_frame_rgb is None:
            messagebox.showwarning("No Image", self.app.tr("msg_no_image_selected"))
            return

        prompt = self.prompt_input.get().strip()
        if not prompt:
            messagebox.showwarning("No Prompt", self.app.tr("msg_prompt_required"))
            return

        if not self.manager.is_running("vlm_service"):
            messagebox.showwarning("Server Stopped", self.app.tr("msg_server_stopped_warning"))
            return

        self.vision_status.configure(text=self.app.tr("status_analyzing"), text_color="#EAB308")
        self.analyze_btn.configure(state="disabled")

        image_source = self.current_image_path if self.current_image_path else self.latest_frame_rgb.copy()
        threading.Thread(target=self._run_vision_inference, args=(image_source, prompt), daemon=True).start()

    def _run_vision_inference(self, image_source, prompt):
        try:
            logging.info("[VLM] Starting vision inference")

            # Resize/compress very large images to avoid exhausting context with visual tokens.
            # Reduced from 1344 to 896 to prevent "failed to find memory slot" errors in llama-server
            max_side = 896
            if isinstance(image_source, Image.Image):
                img_ctx = image_source.copy()
            else:
                img_ctx = Image.open(image_source)

            with img_ctx as img:
                if img.mode not in ("RGB", "L"):
                    img = img.convert("RGB")
                width, height = img.size
                largest_side = max(width, height)
                if largest_side > max_side:
                    ratio = max_side / float(largest_side)
                    new_size = (max(1, int(width * ratio)), max(1, int(height * ratio)))
                    img = img.resize(new_size, Image.Resampling.LANCZOS)
                    logging.info(f"[VLM] Image resized from {width}x{height} to {new_size[0]}x{new_size[1]}")
                else:
                    new_size = (width, height)

                # Use more aggressive compression for large images to reduce visual token count
                buffer = io.BytesIO()
                quality = 85 if max(new_size) > 768 else 90
                img.save(buffer, format="JPEG", quality=quality, optimize=True)
                image_data = base64.b64encode(buffer.getvalue()).decode()
                media_type = "image/jpeg"

            logging.info(f"[VLM] Encoded image payload size: {len(image_data)} bytes")

            vlm_settings = self.profile_manager.get_endpoint_settings("vlm")
            max_new_tokens = int(vlm_settings.get("max_new_tokens", 1024))
            max_new_tokens = max(256, min(max_new_tokens, 4096))
            temperature = float(vlm_settings.get("temperature", 0.2))
            top_p = float(vlm_settings.get("top_p", 0.9))

            payload = {
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:{media_type};base64,{image_data}"
                                }
                            },
                            {
                                "type": "text",
                                "text": prompt
                            }
                        ]
                    }
                ],
                "temperature": temperature,
                "top_p": top_p,
                "max_tokens": max_new_tokens,
                # Some llama-server builds honor n_predict more consistently than max_tokens.
                "n_predict": max_new_tokens,
                "stream": True
            }

            logging.info(f"[VLM] Posting to {self.api_url} with streaming enabled")
            logging.info(
                "[VLM] Request params: max_tokens=%s n_predict=%s temp=%s top_p=%s",
                payload.get("max_tokens"),
                payload.get("n_predict"),
                payload.get("temperature"),
                payload.get("top_p"),
            )

            # Use streaming to collect complete response
            response = requests.post(self.api_url, json=payload, timeout=120, stream=True)
            response.raise_for_status()

            # Collect all chunks
            answer = ""
            finish_reason = None
            chunk_count = 0
            logging.info(f"[VLM] Reading response stream...")

            for line in response.iter_lines():
                if line:
                    line_str = line.decode('utf-8') if isinstance(line, bytes) else line

                    # Skip non-data lines
                    if line_str.startswith("data: "):
                        data_str = line_str[6:]  # Remove "data: " prefix
                        if data_str.strip() == "[DONE]":
                            break

                        try:
                            chunk = json.loads(data_str)
                            delta = chunk.get("choices", [{}])[0].get("delta", {})
                            content = delta.get("content", "")
                            finish_reason = chunk.get("choices", [{}])[0].get("finish_reason")

                            if content:
                                answer += content
                                chunk_count += 1
                        except json.JSONDecodeError as e:
                            logging.warning(f"[VLM] Failed to parse chunk: {data_str[:100]}")
                            continue

            logging.info(f"[VLM] Stream complete - received {chunk_count} chunks, {len(answer)} total chars")
            logging.info(f"[VLM] Final finish_reason: {finish_reason}")
            logging.info(f"[VLM] Full answer: {answer}")

            def update_response():
                self.append_response(answer)
                self.vision_status.configure(text=self.app.tr("status_ready"), text_color="gray")
                self.analyze_btn.configure(state="normal")

            self.after(0, update_response)

        except requests.exceptions.HTTPError as e:
            # Special handling for 500 errors which often indicate memory issues
            if e.response and e.response.status_code == 500:
                error_msg = (
                    "Backend memory error: The VLM server ran out of memory processing this image. "
                    "Try with a smaller or less complex image, or restart the VLM service."
                )
            else:
                error_msg = f"HTTP Error: {str(e)}"
            logging.error(f"[VLM] {error_msg}")
            def update_http_error():
                self.append_response(error_msg)
                self.vision_status.configure(text=self.app.tr("status_error"), text_color="red")
                self.analyze_btn.configure(state="normal")
            self.after(0, update_http_error)

        except requests.exceptions.ConnectionError as e:
            error_msg = f"Connection error: Could not connect to VLM server at {self.api_url}. Make sure it's running."
            logging.error(f"[VLM] {error_msg}: {e}")
            def update_error():
                self.append_response(error_msg)
                self.vision_status.configure(text=self.app.tr("status_error"), text_color="red")
                self.analyze_btn.configure(state="normal")
            self.after(0, update_error)

        except requests.exceptions.Timeout as e:
            error_msg = f"Timeout: The VLM server took too long to respond (>120s)."
            logging.error(f"[VLM] {error_msg}: {e}")
            def update_timeout():
                self.append_response(error_msg)
                self.vision_status.configure(text=self.app.tr("status_error"), text_color="red")
                self.analyze_btn.configure(state="normal")
            self.after(0, update_timeout)

        except Exception as e:
            error_msg = f"Error: {type(e).__name__}: {str(e)}"
            tb = traceback.format_exc()
            logging.error(f"[VLM] {error_msg}\n{tb}")
            def update_error():
                self.append_response(error_msg)
                self.vision_status.configure(text=self.app.tr("status_error"), text_color="red")
                self.analyze_btn.configure(state="normal")
            self.after(0, update_error)

    def append_response(self, text):
        logging.info(f"[VLM] append_response called with text length: {len(text)}")
        logging.info(f"[VLM] Text to display: {text}")

        self.response_text.configure(state="normal")
        self.response_text.delete("1.0", "end")
        self.response_text.insert("1.0", text)

        # Get actual text in widget
        actual_text = self.response_text.get("1.0", "end")
        logging.info(f"[VLM] Actual text in widget after insert: {len(actual_text)} chars")
        logging.info(f"[VLM] Widget text: {actual_text[:200]}")  # Log first 200 chars

        self.response_text.see("end")  # Auto-scroll to bottom
        self.response_text.configure(state="disabled")

    def clear_response(self):
        self.response_text.configure(state="normal")
        self.response_text.delete("1.0", "end")
        self.response_text.configure(state="disabled")

    # --- Camera / Live video helpers ---
    def find_mmproj(self, model_path: Path):
        model_dir = Path(model_path).parent
        candidates = [
            model_dir / "mmproj-F16.gguf",
            model_dir / "mmproj-BF16.gguf",
            model_dir / "mmproj-model-f16.gguf",
            model_dir / "Qwen_Qwen2.5-VL-7B-Instruct-mmproj-f16.gguf",
        ]
        for candidate in candidates:
            if candidate.exists():
                return candidate

        for pattern in ("*mmproj*F16*.gguf", "*mmproj*BF16*.gguf", "*mmproj*.gguf"):
            found = sorted(model_dir.glob(pattern))
            if found:
                return found[0]
        return None

    def start_camera(self):
        if cv2 is None:
            messagebox.showerror(
                "OpenCV no disponible",
                "No se encontró OpenCV (cv2). Instalá opencv-python para habilitar cámara/video en vivo.",
            )
            return
        if self.camera_running:
            return

        source_text = simpledialog.askstring(
            "Fuente de video",
            "Ingresá índice de cámara (ej: 0) o ruta de video.\nDejá vacío para usar cámara 0.",
            parent=self,
        )
        source_text = (source_text or "").strip()
        source = 0
        if source_text:
            if source_text.isdigit():
                source = int(source_text)
            else:
                video_path = Path(source_text)
                if not video_path.exists():
                    messagebox.showerror("Fuente inválida", f"No existe la ruta: {video_path}")
                    return
                source = str(video_path)

        camera = cv2.VideoCapture(source)
        if not camera or not camera.isOpened():
            messagebox.showerror(
                "Cámara/Video",
                f"No se pudo abrir la fuente: {source_text or '0'}",
            )
            try:
                camera.release()
            except Exception:
                pass
            return

        self.stop_camera()
        self.camera = camera
        self.camera_running = True
        self.current_image_path = None
        self.latest_frame_gray_small = None
        self.btn_start_cam.configure(state="disabled")
        self.btn_stop_cam.configure(state="normal")
        self.btn_capture.configure(state="normal")
        self.vision_status.configure(text="Cámara activa", text_color="#22c55e")
        self._poll_camera_frame()

    def stop_camera(self):
        self.camera_running = False
        if self.camera is not None:
            try:
                self.camera.release()
            except Exception:
                pass
            self.camera = None
        self.btn_start_cam.configure(state="normal")
        self.btn_stop_cam.configure(state="disabled")
        self.btn_capture.configure(state="disabled")

    def _poll_camera_frame(self):
        if not self.camera_running or self.camera is None:
            return
        try:
            ok, frame = self.camera.read()
            if not ok or frame is None:
                # If this is a video file and we reached EOF, rewind.
                try:
                    self.camera.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    ok, frame = self.camera.read()
                except Exception:
                    ok = False
            if not ok or frame is None:
                self.vision_status.configure(text="No se pudo leer el frame", text_color="red")
                self.stop_camera()
                return

            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            pil_img = Image.fromarray(frame_rgb)
            self.latest_frame_rgb = pil_img
            self.display_image(pil_img)
            self._track_live_changes(frame, pil_img)
        except Exception as exc:
            logging.error("[VLM] Camera polling error: %s", exc)
            self.vision_status.configure(text=f"Error de cámara: {exc}", text_color="red")
            self.stop_camera()
            return

        self.after(70, self._poll_camera_frame)

    def _track_live_changes(self, frame_bgr, pil_img: Image.Image):
        if not self.track_changes_var.get():
            return
        if cv2 is None:
            return
        try:
            gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
            gray_small = cv2.resize(gray, (160, 90), interpolation=cv2.INTER_AREA)
            previous = self.latest_frame_gray_small
            self.latest_frame_gray_small = gray_small
            if previous is None:
                return
            diff = cv2.absdiff(gray_small, previous)
            score = float(diff.mean())
            now = time.time()
            if score < self.change_threshold or (now - self.last_change_ts) < self.change_cooldown_sec:
                return

            self.last_change_ts = now
            ts = time.strftime("%Y%m%d_%H%M%S")
            capture_path = self.capture_dir / f"change_{ts}_{int(score)}.jpg"
            pil_img.save(capture_path, format="JPEG", quality=90, optimize=True)
            live_log = self.log_dir / "vlm_live_changes.log"
            with live_log.open("a", encoding="utf-8") as f:
                f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} | score={score:.2f} | {capture_path}\n")
            self.vision_status.configure(
                text=f"Cambio detectado (score {score:.1f})",
                text_color="#22c55e",
            )
        except Exception as exc:
            logging.warning("[VLM] live change tracking failed: %s", exc)

    def capture_current_frame(self):
        if self.latest_frame_rgb is None:
            messagebox.showwarning("Captura", "No hay frame disponible para guardar.")
            return
        ts = time.strftime("%Y%m%d_%H%M%S")
        capture_path = self.capture_dir / f"capture_{ts}.jpg"
        try:
            self.latest_frame_rgb.save(capture_path, format="JPEG", quality=92, optimize=True)
            self.current_image_path = str(capture_path)
            self.vision_status.configure(text=f"Frame guardado: {capture_path.name}", text_color="#22c55e")
        except Exception as exc:
            messagebox.showerror("Captura", f"No se pudo guardar el frame: {exc}")

    # --- Models Tab ---
    def build_models_tab(self):
        tr = self.app.tr
        frame = self.tab_models

        ctk.CTkLabel(frame, text=tr("lbl_model_library"), font=ctk.CTkFont(size=18, weight="bold")).pack(pady=10)

        dir_frame = ctk.CTkFrame(frame, fg_color="transparent")
        dir_frame.pack(fill="x", padx=10)

        default_dir = self.app.get_setting("vlm_model_dir", r"C:\models\qwen2.5-vl-gguf")
        self.model_dir_var = ctk.StringVar(value=default_dir)
        ctk.CTkEntry(dir_frame, textvariable=self.model_dir_var).pack(side="left", fill="x", expand=True, padx=(0, 10))
        ctk.CTkButton(dir_frame, text=tr("btn_browse"), width=80, command=self.browse_model_dir).pack(side="right")

        ctk.CTkButton(frame, text=tr("btn_refresh_list"), command=self.refresh_models).pack(pady=10)

        self.models_scroll = ctk.CTkScrollableFrame(frame, label_text=tr("lbl_files"))
        self.models_scroll.pack(fill="both", expand=True, padx=10, pady=10)

    def browse_model_dir(self):
        d = filedialog.askdirectory()
        if d:
            self.model_dir_var.set(d)
            self.app.set_setting("vlm_model_dir", d)
            self.refresh_models()

    def refresh_models(self):
        tr = self.app.tr
        for widget in self.models_scroll.winfo_children():
            widget.destroy()

        path = Path(self.model_dir_var.get())
        self.app.set_setting("vlm_model_dir", str(path))
        if not path.exists():
            return

        # Look for GGUF files recursively and keep selector map as label -> full path.
        files = sorted(path.rglob("*.gguf"))
        model_files = [f for f in files if "mmproj" not in f.name.lower()]
        self.model_file_map = {}
        model_names = []
        for f in model_files:
            try:
                label = str(f.relative_to(path))
            except Exception:
                label = f.name
            if label in self.model_file_map:
                label = f"{f.parent.name}/{f.name}"
            if label in self.model_file_map:
                label = str(f)
            self.model_file_map[label] = str(f)
            model_names.append(label)

        # Update dropdown
        if model_names:
            self.model_selector.configure(values=model_names)
            self.model_selector.set(model_names[0])
        else:
            self.model_selector.configure(values=[tr("placeholder_select_model")])
            self.model_selector.set(tr("placeholder_select_model"))

        for f in files:
            card = ctk.CTkFrame(self.models_scroll, fg_color=("gray90", "#2A2A2A"))
            card.pack(fill="x", pady=2)
            try:
                display_name = str(f.relative_to(path))
            except Exception:
                display_name = f.name
            ctk.CTkLabel(card, text=display_name).pack(side="left", padx=10)

            # Delete Button
            del_btn = ctk.CTkButton(card, text=tr("btn_delete"), width=60, fg_color="#EF4444", hover_color="#DC2626",
                                    command=lambda p=f: self.delete_model(p))
            del_btn.pack(side="right", padx=10, pady=5)

    def delete_model(self, file_path: Path):
        """Confirm and delete the selected model file."""
        if not messagebox.askyesno(self.app.tr("title_delete_model"), self.app.tr("msg_delete_confirm").format(file_path.name)):
            return

        try:
            os.remove(file_path)
            self.refresh_models()
            messagebox.showinfo("Deleted", self.app.tr("msg_deleted_success").format(file_path.name))
        except Exception as e:
            messagebox.showerror("Error", self.app.tr("msg_delete_error").format(str(e)))

    # --- Search / Download Tab ---
    def build_search_tab(self):
        tr = self.app.tr
        frame = self.tab_search

        ctk.CTkLabel(frame, text=tr("lbl_download_hf"), font=ctk.CTkFont(size=18, weight="bold")).pack(pady=10)

        grid = ctk.CTkFrame(frame, fg_color="transparent")
        grid.pack(padx=20, pady=10)

        ctk.CTkLabel(grid, text=tr("lbl_repo_id")).grid(row=0, column=0, sticky="e", padx=5, pady=5)
        self.dl_repo = ctk.CTkEntry(grid, width=300)
        self.dl_repo.grid(row=0, column=1, padx=5, pady=5)

        ctk.CTkLabel(grid, text=tr("lbl_filename")).grid(row=1, column=0, sticky="e", padx=5, pady=5)
        self.dl_filename = ctk.CTkEntry(grid, width=300)
        self.dl_filename.grid(row=1, column=1, padx=5, pady=5)

        self.dl_status = ctk.CTkLabel(frame, text="", text_color="#EAB308")
        self.dl_status.pack(pady=5)

        ctk.CTkButton(frame, text=tr("btn_download"), command=self.start_download).pack(pady=20)

        # Popular Vision Models Section
        ctk.CTkLabel(frame, text=tr("lbl_popular_models"), font=ctk.CTkFont(size=16, weight="bold")).pack(pady=(20, 10))
        preset_frame = ctk.CTkScrollableFrame(frame, height=200, label_text=tr("lbl_click_to_fill"))
        preset_frame.pack(fill="x", padx=10, pady=5)

        presets = [
            ("Qwen 2.5 VL 7B (Q4)", "Qwen/Qwen2.5-VL-7B-Instruct-GGUF", "Qwen2.5-VL-7B-Instruct-Q4_K_M.gguf"),
            ("LLaVA 1.5 7B", "mys/ggml_llava-1.5-7b-Q4_0", "ggml-model-q4_0.gguf"),
            ("LLaVA 1.5 13B", "mys/ggml_llava-1.5-13b-Q4_0", "ggml-model-q4_0.gguf"),
            ("MobileVLM 3B", "mtgv/MobileVLM-3B-GGUF", "MobileVLM-3B.Q4_K_M.gguf"),
            ("LLaVA NeXT 110B", "mys/ggml_llava-v1.5-13b-Q4_0", "ggml-model-q4_0.gguf"),
        ]

        for name, repo, file in presets:
            btn = ctk.CTkButton(preset_frame, text=name,
                                command=lambda r=repo, f=file: self.fill_download(r, f),
                                fg_color="transparent", border_width=1, text_color=("gray10", "gray90"))
            btn.pack(fill="x", pady=2)

        ctk.CTkLabel(frame, text=tr("lbl_download_note"), text_color="gray").pack(side="bottom", pady=20)

    def fill_download(self, repo, filename):
        self.dl_repo.delete(0, "end")
        self.dl_repo.insert(0, repo)
        self.dl_filename.delete(0, "end")
        self.dl_filename.insert(0, filename)
        self.dl_status.configure(text=f"Selected: {filename}")

    def start_download(self):
        repo = self.dl_repo.get().strip()
        filename = self.dl_filename.get().strip()

        if not repo or not filename:
            self.dl_status.configure(text=self.app.tr("msg_fill_fields"))
            return

        self.dl_status.configure(text=self.app.tr("status_download_progress"))
        threading.Thread(target=self._download_worker, args=(repo, filename), daemon=True).start()

    def _download_worker(self, repo, filename):
        try:
            from huggingface_hub import hf_hub_download
            dest_dir = Path(self.model_dir_var.get())
            dest_dir.mkdir(parents=True, exist_ok=True)
            path = hf_hub_download(repo_id=repo, filename=filename, local_dir=dest_dir, local_dir_use_symlinks=False)
            self.after(0, lambda: self.dl_status.configure(text=self.app.tr("status_download_done").format(Path(path).name)))
            self.after(0, lambda: messagebox.showinfo("Download Complete", self.app.tr("msg_download_complete").format(filename)))
            self.after(0, self.refresh_models)
        except Exception as e:
            self.after(0, lambda: self.dl_status.configure(text=self.app.tr("status_download_error").format(str(e))))

    def destroy(self):
        self.stop_camera()
        super().destroy()
