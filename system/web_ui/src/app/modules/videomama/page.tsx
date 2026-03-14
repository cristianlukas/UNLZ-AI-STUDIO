"use client";

import { useEffect, useState } from "react";
import AppShell from "@/components/AppShell";
import { fetchJson } from "@/lib/webBridge";
import { useApp } from "@/context/AppContext";

type VideoMamaState = {
  installed: boolean;
  output_dir: string;
  running: boolean;
};

export default function VideoMamaPage() {
  const { translations } = useApp();
  const [state, setState] = useState<VideoMamaState | null>(null);
  const [logs, setLogs] = useState<string[]>([]);
  const [baseModelPath, setBaseModelPath] = useState("checkpoints/stable-video-diffusion-img2vid-xt");
  const [unetPath, setUnetPath] = useState("checkpoints/VideoMaMa");
  const [imageRoot, setImageRoot] = useState("assets/example/image");
  const [maskRoot, setMaskRoot] = useState("assets/example/mask");
  const [outputDir, setOutputDir] = useState("");
  const [keepAspect, setKeepAspect] = useState(false);

  const refresh = async () => {
    const data = await fetchJson<VideoMamaState>("/modules/videomama/state");
    setState(data);
    if (!outputDir) {
      setOutputDir(data.output_dir);
    }
  };

  const refreshLogs = async () => {
    const data = await fetchJson<{ lines: string[] }>("/modules/videomama/logs");
    setLogs(data.lines);
  };

  const clearLogs = async () => {
    await fetchJson("/modules/videomama/clear_logs", { method: "POST" });
    setLogs([]);
  };

  useEffect(() => {
    refresh();
    refreshLogs();
    const id = setInterval(() => {
      refresh();
      refreshLogs();
    }, 4000);
    return () => clearInterval(id);
  }, []);

  const install = async () => {
    await fetchJson("/modules/videomama/install", { method: "POST" });
    refresh();
  };

  const uninstall = async () => {
    await fetchJson("/modules/videomama/uninstall", { method: "POST" });
    refresh();
  };

  const installDeps = async () => {
    await fetchJson("/modules/videomama/deps", { method: "POST" });
  };

  const run = async () => {
    await fetchJson("/modules/videomama/run", {
      method: "POST",
      body: JSON.stringify({
        base_model_path: baseModelPath,
        unet_checkpoint_path: unetPath,
        image_root_path: imageRoot,
        mask_root_path: maskRoot,
        output_dir: outputDir,
        keep_aspect_ratio: keepAspect,
      }),
    });
  };

  const openOutput = async () => {
    await fetchJson("/modules/videomama/open_output", {
      method: "POST",
      body: JSON.stringify({ path: outputDir || state?.output_dir }),
    });
  };

  return (
    <AppShell>
      <div className="page-header">
        <div className="eyebrow">{translations.videomama_title || "VideoMaMa"}</div>
        <h1>{translations.videomama_title || "VideoMaMa"}</h1>
        <p>{translations.videomama_subtitle || "Mask-guided video matting via generative prior."}</p>
        <p>{translations.videomama_plain || "Cuts out people or objects from videos."}</p>
      </div>
      {state?.running && <div className="banner">{translations.status_in_progress || "En progreso"}</div>}

      <section className="panel">
        <div className="panel-header">
          <h2>Setup</h2>
          <span className="pill">{state?.installed ? "Instalado" : "No instalado"}</span>
        </div>
        <div className="panel-body">
          <div className="list-actions">
            {!state?.installed && (
              <button className="primary" onClick={install}>
                {translations.videomama_btn_install || "Install backend"}
              </button>
            )}
            {state?.installed && (
              <>
                <button className="ghost" onClick={uninstall}>
                  {translations.videomama_btn_uninstall || "Uninstall backend"}
                </button>
                <button className="ghost" onClick={installDeps}>
                  {translations.videomama_btn_deps || "Install dependencies"}
                </button>
                <button className="ghost" onClick={openOutput}>
                  {translations.videomama_btn_open_output || "Open output"}
                </button>
              </>
            )}
            <a className="ghost" href="https://github.com/cvlab-kaist/VideoMaMa" target="_blank">
              {translations.videomama_btn_open_repo || "Open repo"}
            </a>
            <a className="ghost" href="https://cvlab-kaist.github.io/VideoMaMa/" target="_blank">
              {translations.videomama_btn_open_project || "Open project page"}
            </a>
            <a className="ghost" href="https://huggingface.co/spaces/SammyLim/VideoMaMa" target="_blank">
              {translations.videomama_btn_open_demo || "Open demo"}
            </a>
          </div>
          <p style={{ marginTop: "0.8rem" }}>
            {translations.videomama_note ||
              "Note: run scripts/setup.sh and configure the conda environment."}
          </p>
        </div>
      </section>

      <section className="panel">
        <div className="panel-header">
          <h2>Inference</h2>
        </div>
        <div className="panel-body">
          <div className="form">
            <label>
              {translations.videomama_base_model_label || "Base model path"}
              <input value={baseModelPath} onChange={(event) => setBaseModelPath(event.target.value)} />
            </label>
            <label>
              {translations.videomama_unet_label || "UNet checkpoint path"}
              <input value={unetPath} onChange={(event) => setUnetPath(event.target.value)} />
            </label>
            <label>
              {translations.videomama_image_label || "Image root path"}
              <input value={imageRoot} onChange={(event) => setImageRoot(event.target.value)} />
            </label>
            <label>
              {translations.videomama_mask_label || "Mask root path"}
              <input value={maskRoot} onChange={(event) => setMaskRoot(event.target.value)} />
            </label>
            <label>
              {translations.videomama_output_label || "Output"}
              <input value={outputDir} onChange={(event) => setOutputDir(event.target.value)} />
            </label>
            <label>
              <span>{translations.videomama_keep_aspect || "Keep aspect ratio"}</span>
              <input
                type="checkbox"
                checked={keepAspect}
                onChange={(event) => setKeepAspect(event.target.checked)}
              />
            </label>
          </div>
          <div className="list-actions" style={{ marginTop: "1rem" }}>
            <button className="primary" onClick={run} disabled={!state?.installed || state?.running}>
              {translations.videomama_btn_run || "Run"}
            </button>
            <span className="pill">{state?.running ? "Running" : "Idle"}</span>
          </div>
        </div>
      </section>

      <section className="panel">
        <div className="panel-header">
          <h2>Logs</h2>
          <button className="ghost" onClick={clearLogs}>
            {translations.log_clear_btn || "Clear log"}
          </button>
        </div>
        <div className="panel-body">
          <pre className="empty log-view">{logs.length ? logs.join("\n") : "No logs yet."}</pre>
        </div>
      </section>
    </AppShell>
  );
}
