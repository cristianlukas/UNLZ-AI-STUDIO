"use client";

import { useEffect, useRef, useState } from "react";
import AppShell from "@/components/AppShell";
import { fetchJson } from "@/lib/webBridge";
import { useApp } from "@/context/AppContext";

type MLSharpState = {
  installed: boolean;
  deps_installed: boolean;
  output_dir: string;
  running: boolean;
  scenes: Scene[];
  last_output: string | null;
  torch_installed: boolean;
  torch_cuda: boolean;
};

type Scene = {
  name: string;
  path: string;
  has_viewer: boolean;
  renamable?: boolean;
};

export default function MLSharpPage() {
  const { translations } = useApp();
  const [state, setState] = useState<MLSharpState | null>(null);
  const [logs, setLogs] = useState<string[]>([]);
  const [inputPath, setInputPath] = useState("");
  const [outputDir, setOutputDir] = useState("");
  const [device, setDevice] = useState("default");
  const [render, setRender] = useState(false);
  const outputTouchedRef = useRef(false);
  const settingsKey = "mlsharp_form_settings";

  const refresh = async () => {
    const data = await fetchJson<MLSharpState>("/modules/ml_sharp/state");
    setState(data);
    if (!outputTouchedRef.current && data.output_dir) {
      setOutputDir(data.output_dir);
    }
  };

  const refreshLogs = async () => {
    const data = await fetchJson<{ lines: string[] }>("/modules/ml_sharp/logs");
    setLogs(data.lines);
  };

  const clearLogs = async () => {
    await fetchJson("/modules/ml_sharp/clear_logs", { method: "POST" });
    setLogs([]);
  };

  useEffect(() => {
    if (typeof window !== "undefined") {
      try {
        const saved = window.localStorage.getItem(settingsKey);
        if (saved) {
          const data = JSON.parse(saved) as {
            inputPath?: string;
            outputDir?: string;
            device?: string;
            render?: boolean;
          };
          if (data.inputPath) setInputPath(data.inputPath);
          if (data.outputDir) {
            outputTouchedRef.current = true;
            setOutputDir(data.outputDir);
          }
          if (data.device) setDevice(data.device);
          if (typeof data.render === "boolean") setRender(data.render);
        }
      } catch {
        // Ignore invalid persisted data.
      }
    }
    refresh();
    refreshLogs();
    const id = setInterval(() => {
      refresh();
      refreshLogs();
    }, 4000);
    return () => clearInterval(id);
  }, []);

  useEffect(() => {
    if (typeof window === "undefined") return;
    const payload = {
      inputPath,
      outputDir,
      device,
      render,
    };
    try {
      window.localStorage.setItem(settingsKey, JSON.stringify(payload));
    } catch {
      // Ignore storage failures.
    }
  }, [inputPath, outputDir, device, render]);

  const installDeps = async () => {
    await fetchJson("/modules/ml_sharp/deps", { method: "POST" });
  };

  const installTorch = async (variant: "cpu" | "cu121") => {
    await fetchJson("/modules/ml_sharp/install_torch", {
      method: "POST",
      body: JSON.stringify({ variant }),
    });
  };

  const browseInputFile = async () => {
    const data = await fetchJson<{ path?: string; paths?: string[] }>("/ui/pick_file", {
      method: "POST",
      body: JSON.stringify({
        title: translations.mlsharp_dialog_input || "Select image",
      }),
    });
    const selected = data.paths?.[0] || data.path;
    if (selected) {
      setInputPath(selected);
    }
  };

  const browseInputFolder = async () => {
    const data = await fetchJson<{ path: string }>("/ui/pick_folder", {
      method: "POST",
      body: JSON.stringify({
        title: translations.mlsharp_dialog_input_folder || "Select folder",
      }),
    });
    if (data.path) {
      setInputPath(data.path);
    }
  };

  const browseOutputFolder = async () => {
    const data = await fetchJson<{ path: string }>("/ui/pick_folder", {
      method: "POST",
      body: JSON.stringify({
        title: translations.mlsharp_dialog_output || "Select output",
        initial_dir: outputDir || state?.output_dir || null,
      }),
    });
    if (data.path) {
      outputTouchedRef.current = true;
      setOutputDir(data.path);
    }
  };

  const runPredict = async () => {
    await fetchJson("/modules/ml_sharp/run", {
      method: "POST",
      body: JSON.stringify({
        input_path: inputPath,
        output_dir: outputDir || null,
        device,
        render,
      }),
    });
  };

  const openOutput = async () => {
    await fetchJson("/modules/ml_sharp/open_output", {
      method: "POST",
      body: JSON.stringify({ path: outputDir || state?.output_dir }),
    });
  };

  const viewOutput = async () => {
    const target = outputDir || state?.last_output || state?.output_dir;
    if (!target) {
      return;
    }
    const data = await fetchJson<{ url: string }>("/modules/ml_sharp/view_scene", {
      method: "POST",
      body: JSON.stringify({ path: target }),
    });
    if (data.url) {
      window.open(data.url, "_blank");
    }
  };

  const openScene = async (scene: Scene) => {
    await fetchJson("/modules/ml_sharp/open_scene", {
      method: "POST",
      body: JSON.stringify({ path: scene.path }),
    });
  };

  const viewScene = async (scene: Scene) => {
    const data = await fetchJson<{ url: string }>("/modules/ml_sharp/view_scene", {
      method: "POST",
      body: JSON.stringify({ path: scene.path }),
    });
    if (data.url) {
      window.open(data.url, "_blank");
    }
  };

  const renameScene = async (scene: Scene) => {
    const current = scene.name || "";
    const nextName = window.prompt(translations.mlsharp_rename_prompt || "Nuevo nombre", current);
    if (!nextName) {
      return;
    }
    await fetchJson("/modules/ml_sharp/rename_scene", {
      method: "POST",
      body: JSON.stringify({ path: scene.path, name: nextName }),
    });
    refresh();
  };

  return (
    <AppShell>
      <div className="page-header">
        <div className="eyebrow">{translations.mlsharp_title || "ML-SHARP"}</div>
        <h1>{translations.mlsharp_title || "ML-SHARP"}</h1>
        <p>{translations.mlsharp_subtitle || "Sharp view synthesis with Gaussian splats."}</p>
        <p>{translations.mlsharp_plain || "Turns photos into a 3D scene you can explore."}</p>
      </div>
      {state?.running && <div className="banner">{translations.status_in_progress || "En progreso"}</div>}

      <section className="panel">
        <div className="panel-header">
          <h2>{translations.mlsharp_setup_title || "Setup"}</h2>
          <span className="pill">
            {state?.deps_installed
              ? translations.mlsharp_deps_ok || "Deps OK"
              : translations.mlsharp_deps_missing || "Deps missing"}
          </span>
        </div>
        <div className="panel-body">
          <div className="list-actions">
            <button className="ghost" onClick={installDeps} disabled={!state?.installed}>
              {state?.deps_installed
                ? translations.mlsharp_btn_deps_installed || "Dependencies installed"
                : translations.mlsharp_btn_deps || "Install dependencies"}
            </button>
            <button className="ghost" onClick={() => installTorch("cpu")} disabled={!state?.installed}>
              {translations.mlsharp_btn_torch_cpu || "Install Torch CPU"}
            </button>
            <button className="ghost" onClick={() => installTorch("cu121")} disabled={!state?.installed}>
              {translations.mlsharp_btn_torch_cuda || "Install Torch CUDA"}
            </button>
            <a className="ghost" href="https://github.com/apple/ml-sharp" target="_blank">
              {translations.mlsharp_btn_open_repo || "Open repo"}
            </a>
          </div>
          <div className="list-meta" style={{ marginTop: "0.6rem" }}>
            {state?.torch_installed
              ? state?.torch_cuda
                ? translations.mlsharp_torch_status_cuda || "Torch CUDA ready"
                : translations.mlsharp_torch_status_cpu || "Torch CPU only"
              : translations.mlsharp_torch_status_missing || "Torch not installed"}
          </div>
        </div>
      </section>

      <section className="panel">
        <div className="panel-header">
          <h2>{translations.mlsharp_input_label || "Input"}</h2>
        </div>
        <div className="panel-body">
          <div className="form">
            <label title={translations.mlsharp_input_help || "Path to an image or image folder."}>
              {translations.mlsharp_input_label || "Input"}
              <input
                value={inputPath}
                onChange={(event) => setInputPath(event.target.value)}
                placeholder={translations.mlsharp_input_placeholder || "Select input"}
              />
              <div className="form-row">
                <button className="ghost" type="button" onClick={browseInputFile} disabled={!state?.installed}>
                  {translations.mlsharp_btn_browse_file || "File"}
                </button>
                <button className="ghost" type="button" onClick={browseInputFolder} disabled={!state?.installed}>
                  {translations.mlsharp_btn_browse_folder || "Folder"}
                </button>
              </div>
            </label>
            <label title={translations.mlsharp_output_help || "Folder where the output will be saved."}>
              {translations.mlsharp_output_label || "Output"}
              <input
                value={outputDir}
                onChange={(event) => {
                  outputTouchedRef.current = true;
                  setOutputDir(event.target.value);
                }}
              />
              <div className="form-row">
                <button className="ghost" type="button" onClick={browseOutputFolder} disabled={!state?.installed}>
                  {translations.mlsharp_btn_browse_output || "Browse"}
                </button>
              </div>
            </label>
            <label title={translations.mlsharp_device_help || "Compute device used for inference."}>
              {translations.mlsharp_device_label || "Device"}
              <select value={device} onChange={(event) => setDevice(event.target.value)}>
                <option value="default">{translations.mlsharp_device_default || "default"}</option>
                <option value="cpu">{translations.mlsharp_device_cpu || "cpu"}</option>
                <option value="cuda">{translations.mlsharp_device_cuda || "cuda"}</option>
                <option value="mps">{translations.mlsharp_device_mps || "mps"}</option>
              </select>
            </label>
            <label title={translations.mlsharp_render_help || "When enabled, renders a CUDA camera trajectory."}>
              {translations.mlsharp_render_label || "Render path"}
              <select value={render ? "yes" : "no"} onChange={(event) => setRender(event.target.value === "yes")}>
                <option value="no">No</option>
                <option value="yes">Yes</option>
              </select>
            </label>
          </div>
          <div className="list-actions" style={{ marginTop: "1rem" }}>
            <button className="primary" onClick={runPredict} disabled={!state?.installed}>
              {translations.mlsharp_btn_run || "Run"}
            </button>
            <button className="ghost" onClick={openOutput}>
              {translations.mlsharp_btn_open_output || "Open output"}
            </button>
            <button className="ghost" onClick={viewOutput}>
              {translations.mlsharp_btn_view_output || "View output"}
            </button>
          </div>
        </div>
      </section>

      <section className="panel">
        <div className="panel-header">
          <h2>{translations.mlsharp_scene_library || "Scene Library"}</h2>
          <span className="pill">
            {translations.mlsharp_scene_count
              ? translations.mlsharp_scene_count.replace("{0}", String(state?.scenes?.length || 0))
              : `${state?.scenes?.length || 0} scenes`}
          </span>
        </div>
        <div className="panel-body">
          {!state?.scenes?.length ? (
            <div className="empty">No scenes found.</div>
          ) : (
            <div className="list">
              {state.scenes.map((scene) => (
                <div key={scene.path} className="list-row">
                  <div>
                    <div className="list-title">{scene.name}</div>
                    <div className="list-meta">
                      {scene.has_viewer
                        ? translations.mlsharp_viewer_ready || "Viewer ready"
                        : translations.mlsharp_viewer_pending || "Viewer pending"}
                    </div>
                  </div>
                  <div className="list-actions">
                    {scene.renamable ? (
                      <button className="ghost" onClick={() => renameScene(scene)}>
                        {translations.mlsharp_btn_rename || "Renombrar"}
                      </button>
                    ) : null}
                    <button className="ghost" onClick={() => openScene(scene)} disabled={!scene.has_viewer}>
                      {translations.mlsharp_btn_open_folder_scene || "Open folder"}
                    </button>
                    <button className="primary" onClick={() => viewScene(scene)} disabled={!scene.has_viewer}>
                      {translations.mlsharp_btn_view_scene || "View"}
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
          <h2>{translations.mlsharp_log_label || "Log"}</h2>
          <button className="ghost" onClick={clearLogs}>
            {translations.log_clear_btn || "Clear log"}
          </button>
        </div>
        <div className="panel-body">
          <pre className="empty log-view">
            {logs.length ? logs.join("\n") : translations.mlsharp_log_empty || "No logs yet."}
          </pre>
        </div>
      </section>
    </AppShell>
  );
}
