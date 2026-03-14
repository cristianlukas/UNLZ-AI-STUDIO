"use client";

import { useEffect, useState } from "react";
import Image from "next/image";
import AppShell from "@/components/AppShell";
import { fetchJson } from "@/lib/webBridge";
import { useApp } from "@/context/AppContext";

const MAX_IMAGE_SIDE = 1024;
const JPEG_QUALITY = 0.86;

function errorMessage(err: unknown): string {
  if (err instanceof Error) {
    return err.message;
  }
  return "Unknown error";
}

async function fileToOptimizedDataUrl(file: File): Promise<string> {
  return await new Promise<string>((resolve, reject) => {
    const url = URL.createObjectURL(file);
    const image = new window.Image();
    image.onload = () => {
      try {
        const width = image.naturalWidth || image.width;
        const height = image.naturalHeight || image.height;
        const largest = Math.max(width, height);
        const scale = largest > MAX_IMAGE_SIDE ? MAX_IMAGE_SIDE / largest : 1;
        const targetWidth = Math.max(1, Math.round(width * scale));
        const targetHeight = Math.max(1, Math.round(height * scale));

        const canvas = document.createElement("canvas");
        canvas.width = targetWidth;
        canvas.height = targetHeight;
        const ctx = canvas.getContext("2d");
        if (!ctx) {
          reject(new Error("Canvas 2D context unavailable"));
          return;
        }

        // Encode as JPEG to keep visual token count and payload size manageable.
        ctx.drawImage(image, 0, 0, targetWidth, targetHeight);
        const optimized = canvas.toDataURL("image/jpeg", JPEG_QUALITY);
        resolve(optimized);
      } catch (err) {
        reject(err instanceof Error ? err : new Error("Failed to optimize image"));
      } finally {
        URL.revokeObjectURL(url);
      }
    };
    image.onerror = () => {
      URL.revokeObjectURL(url);
      reject(new Error("Failed to load image file"));
    };
    image.src = url;
  });
}

type ModelEntry = {
  label: string;
  path: string;
  recommended: boolean;
};

type VLMState = {
  running: boolean;
  model_dir: string;
  models: ModelEntry[];
};

const PRESETS = [
  {
    name: "Qwen 2.5 VL 7B Instruct (Q4)",
    repo: "unsloth/Qwen2.5-VL-7B-Instruct-GGUF",
    file: "Qwen2.5-VL-7B-Instruct-Q4_K_M.gguf",
  },
  {
    name: "Qwen 2.5 VL mmproj (F16)",
    repo: "unsloth/Qwen2.5-VL-7B-Instruct-GGUF",
    file: "mmproj-F16.gguf",
  },
  {
    name: "Qwen 2.5 VL mmproj (BF16)",
    repo: "unsloth/Qwen2.5-VL-7B-Instruct-GGUF",
    file: "mmproj-BF16.gguf",
  },
];

export default function VLMFrontendPage() {
  const { translations } = useApp();
  const [state, setState] = useState<VLMState | null>(null);
  const [selectedModel, setSelectedModel] = useState("");
  const [prompt, setPrompt] = useState("");
  const [answer, setAnswer] = useState("");
  const [busy, setBusy] = useState(false);
  const [repoId, setRepoId] = useState("");
  const [filename, setFilename] = useState("");
  const [imageDataUrl, setImageDataUrl] = useState("");
  const [statusMessage, setStatusMessage] = useState("");

  const refresh = async () => {
    const data = await fetchJson<VLMState>("/modules/vlm_frontend/state");
    setState(data);
    if (!selectedModel && data.models.length) {
      setSelectedModel(data.models[0].path);
    }
  };

  useEffect(() => {
    refresh();
    const id = setInterval(refresh, 4000);
    return () => clearInterval(id);
  }, []);

  const onImageSelected = async (file: File | null) => {
    if (!file) {
      setImageDataUrl("");
      return;
    }
    try {
      setStatusMessage("Optimizing image...");
      const dataUrl = await fileToOptimizedDataUrl(file);
      setImageDataUrl(dataUrl);
      setStatusMessage("Image ready");
    } catch (err) {
      setStatusMessage(errorMessage(err));
      setImageDataUrl("");
    }
  };

  const startServer = async () => {
    if (!selectedModel) return;
    setBusy(true);
    setStatusMessage("");
    try {
      await fetchJson("/modules/vlm_frontend/start", {
        method: "POST",
        body: JSON.stringify({ model_path: selectedModel }),
      });
      await refresh();
    } catch (err) {
      setStatusMessage(errorMessage(err));
    } finally {
      setBusy(false);
    }
  };

  const stopServer = async () => {
    setBusy(true);
    setStatusMessage("");
    try {
      await fetchJson("/modules/vlm_frontend/stop", { method: "POST" });
      await refresh();
    } catch (err) {
      setStatusMessage(errorMessage(err));
    } finally {
      setBusy(false);
    }
  };

  const analyze = async () => {
    if (!prompt.trim() || !imageDataUrl) return;
    setBusy(true);
    setStatusMessage("");
    try {
      const data = await fetchJson<{ answer: string }>("/modules/vlm_frontend/analyze", {
        method: "POST",
        body: JSON.stringify({
          prompt: prompt.trim(),
          image_data_url: imageDataUrl,
        }),
      });
      setAnswer(data.answer || "");
    } catch (err) {
      const message = errorMessage(err);
      setAnswer(message);
      setStatusMessage(message);
    } finally {
      setBusy(false);
    }
  };

  const deleteModel = async (path: string) => {
    try {
      await fetchJson("/modules/vlm_frontend/delete", {
        method: "POST",
        body: JSON.stringify({ path }),
      });
      await refresh();
    } catch (err) {
      setStatusMessage(errorMessage(err));
    }
  };

  const downloadModel = async () => {
    if (!repoId || !filename) return;
    setBusy(true);
    setStatusMessage("");
    try {
      await fetchJson("/modules/vlm_frontend/download", {
        method: "POST",
        body: JSON.stringify({ repo_id: repoId, filename }),
      });
      await refresh();
    } catch (err) {
      setStatusMessage(errorMessage(err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <AppShell>
      <div className="page-header">
        <div className="eyebrow">{translations.mod_vlm_title || "Vision AI"}</div>
        <h1>{translations.mod_vlm_title || "Vision AI"}</h1>
        <p>{translations.mod_vlm_desc || "Analyze images with local VLM models."}</p>
      </div>

      <section className="panel">
        <div className="panel-header">
          <h2>{translations.tab_vision || "Vision"}</h2>
          <span className="pill">{state?.running ? "Running" : "Stopped"}</span>
        </div>
        <div className="panel-body">
          <div className="form">
            <label>
              {translations.lbl_active_model || "Active model"}
              <select value={selectedModel} onChange={(event) => setSelectedModel(event.target.value)}>
                {state?.models?.length ? (
                  state.models.map((model) => (
                    <option key={model.path} value={model.path}>
                      {model.label}
                    </option>
                  ))
                ) : (
                  <option value="">{translations.placeholder_select_model || "Select model"}</option>
                )}
              </select>
            </label>
          </div>

          <div className="list-actions" style={{ marginTop: "1rem" }}>
            <button className="primary" onClick={startServer} disabled={busy || state?.running || !selectedModel}>
              {translations.btn_load || "Load"}
            </button>
            <button className="ghost" onClick={stopServer} disabled={busy || !state?.running}>
              {translations.btn_stop || "Stop"}
            </button>
          </div>

          <div className="form" style={{ marginTop: "1rem" }}>
            <label>
              {translations.lbl_image || "Image"}
              <input
                type="file"
                accept="image/*"
                onChange={(event) => onImageSelected(event.target.files?.[0] || null)}
              />
            </label>
            <label>
              {translations.lbl_prompt || "Prompt"}
              <input
                value={prompt}
                onChange={(event) => setPrompt(event.target.value)}
                placeholder={translations.vision_prompt_placeholder || "What should I analyze?"}
              />
            </label>
          </div>

          {imageDataUrl ? (
            <div style={{ marginTop: "1rem" }}>
              <Image
                src={imageDataUrl}
                alt="VLM input"
                width={1024}
                height={320}
                unoptimized
                style={{ maxWidth: "100%", maxHeight: 320, borderRadius: 12, border: "1px solid #2b3240" }}
              />
            </div>
          ) : (
            <div className="empty" style={{ marginTop: "1rem" }}>
              {translations.placeholder_no_image || "No image loaded"}
            </div>
          )}

          <div className="list-actions" style={{ marginTop: "1rem" }}>
            <button
              className="primary"
              onClick={analyze}
              disabled={busy || !state?.running || !prompt.trim() || !imageDataUrl}
            >
              {translations.btn_analyze || "Analyze"}
            </button>
            <button
              className="ghost"
              onClick={() => {
                setAnswer("");
                setPrompt("");
              }}
              disabled={busy}
            >
              {translations.btn_clear_response || "Clear response"}
            </button>
          </div>

          <div className="panel-body" style={{ marginTop: "1rem" }}>
            <div className="list-title">{translations.lbl_response || "Response"}</div>
            <div className="list-meta" style={{ whiteSpace: "pre-wrap" }}>
              {answer || translations.status_ready || "Ready"}
            </div>
            {statusMessage && (
              <div className="list-meta" style={{ marginTop: "0.6rem" }}>
                {statusMessage}
              </div>
            )}
          </div>
        </div>
      </section>

      <section className="panel">
        <div className="panel-header">
          <h2>{translations.tab_models || "Models"}</h2>
          <span className="pill">{state?.models?.length || 0}</span>
        </div>
        <div className="panel-body">
          {!state?.models?.length ? (
            <div className="empty">{translations.msg_no_models || "No models found."}</div>
          ) : (
            <div className="list">
              {state.models.map((model) => (
                <div key={model.path} className="list-row">
                  <div>
                    <div className="list-title">{model.label}</div>
                    <div className="list-meta">{model.path}</div>
                  </div>
                  <div className="list-actions">
                    <button className="ghost" onClick={() => deleteModel(model.path)}>
                      {translations.btn_delete || "Delete"}
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </section>

      <section className="panel">
        <div className="panel-header">
          <h2>{translations.tab_download || "Downloads"}</h2>
        </div>
        <div className="panel-body">
          <div className="form">
            <label>
              {translations.lbl_repo_id || "Repo ID"}
              <input value={repoId} onChange={(event) => setRepoId(event.target.value)} />
            </label>
            <label>
              {translations.lbl_filename || "Filename"}
              <input value={filename} onChange={(event) => setFilename(event.target.value)} />
            </label>
          </div>
          <div className="list-actions" style={{ marginTop: "0.8rem" }}>
            <button className="primary" onClick={downloadModel} disabled={busy}>
              {translations.btn_download || "Download"}
            </button>
          </div>
          <div className="list" style={{ marginTop: "1rem" }}>
            {PRESETS.map((preset) => (
              <div key={preset.file} className="list-row">
                <div>
                  <div className="list-title">{preset.name}</div>
                  <div className="list-meta">{preset.repo}</div>
                </div>
                <div className="list-actions">
                  <button
                    className="ghost"
                    onClick={() => {
                      setRepoId(preset.repo);
                      setFilename(preset.file);
                    }}
                  >
                    {translations.lbl_click_to_fill || "Use"}
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>
    </AppShell>
  );
}
