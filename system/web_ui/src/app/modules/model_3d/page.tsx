"use client";

import { useEffect, useMemo, useState } from "react";
import Script from "next/script";
import AppShell from "@/components/AppShell";
import { fetchJson, WEB_BRIDGE_URL } from "@/lib/webBridge";
import { useApp } from "@/context/AppContext";

type WeightOption = {
  key: string;
  label: string;
  repo_id: string;
  local_dir: string;
};

type Model3DState = {
  backend: string;
  weights: WeightOption[];
  installed: boolean;
  weights_installed: boolean;
  running: boolean;
  output_base: string;
  last_output_dir?: string;
  hf_token_saved: boolean;
};

type Model3DHistoryItem = {
  name: string;
  rel_path: string;
  folder: string;
  size_mb?: number;
  modified?: number;
};

type Model3DPrereqs = {
  pybind11_ok: boolean;
  compiler_ok: boolean;
  nvcc_version: string;
  torch_cuda: string;
  torch_version?: string;
  cuda_match: boolean;
};

const BACKENDS = [
  { key: "hunyuan3d2", labelKey: "model3d_backend_hunyuan" },
  { key: "reconv", labelKey: "model3d_backend_reconv" },
  { key: "sam3d", labelKey: "model3d_backend_sam3d" },
  { key: "stepx1", labelKey: "model3d_backend_stepx1" },
];

const INPUT_MODES = [
  { key: "single", labelKey: "model3d_input_mode_single" },
  { key: "multi", labelKey: "model3d_input_mode_multi" },
  { key: "video", labelKey: "model3d_input_mode_video" },
];

export default function Model3DPage() {
  const { translations } = useApp();
  const [state, setState] = useState<Model3DState | null>(null);
  const [backend, setBackend] = useState("hunyuan3d2");
  const [inputMode, setInputMode] = useState("single");
  const [inputPaths, setInputPaths] = useState("");
  const [outputDir, setOutputDir] = useState("");
  const [weightKey, setWeightKey] = useState("");
  const [hfToken, setHfToken] = useState("");
  const [logs, setLogs] = useState<string[]>([]);
  const [history, setHistory] = useState<Model3DHistoryItem[]>([]);
  const [previewRel, setPreviewRel] = useState<string>("");
  const [prereqs, setPrereqs] = useState<Model3DPrereqs | null>(null);
  const [prereqAlert, setPrereqAlert] = useState<string>("");

  const refresh = async () => {
    const data = await fetchJson<Model3DState>("/modules/model_3d/state");
    setState(data);
    setBackend(data.backend);
    if (!outputDir) {
      setOutputDir(data.last_output_dir || data.output_base);
    }
    if (data.weights.length) {
      setWeightKey(data.weights[0].key);
    }
  };

  const refreshLogs = async () => {
    const data = await fetchJson<{ lines: string[] }>("/modules/model_3d/logs");
    setLogs(data.lines);
  };

  const refreshPrereqs = async () => {
    const data = await fetchJson<Model3DPrereqs>("/modules/model_3d/prereqs");
    setPrereqs(data);
  };

  const refreshHistory = async () => {
    const data = await fetchJson<{ items: Model3DHistoryItem[] }>("/modules/model_3d/history");
    const items = data.items || [];
    setHistory(items);
    if (!previewRel && items.length) {
      setPreviewRel(items[0].rel_path);
    }
  };

  const clearLogs = async () => {
    await fetchJson("/modules/model_3d/clear_logs", { method: "POST" });
    setLogs([]);
  };

  useEffect(() => {
    refresh();
    refreshLogs();
    refreshHistory();
    refreshPrereqs();
    const id = setInterval(() => {
      refresh();
      refreshLogs();
      refreshHistory();
      refreshPrereqs();
    }, 4000);
    return () => clearInterval(id);
  }, []);

  const backendLabel = useMemo(() => {
    const match = BACKENDS.find((item) => item.key === backend);
    return match ? translations[match.labelKey] || match.key : backend;
  }, [backend, translations]);

  const updateBackend = async (value: string) => {
    setBackend(value);
    await fetchJson("/modules/model_3d/set_backend", {
      method: "POST",
      body: JSON.stringify({ backend_key: value }),
    });
    refresh();
  };

  const installBackend = async () => {
    await fetchJson("/modules/model_3d/install_backend", {
      method: "POST",
      body: JSON.stringify({ backend_key: backend }),
    });
    refresh();
  };

  const uninstallBackend = async () => {
    await fetchJson("/modules/model_3d/uninstall_backend", {
      method: "POST",
      body: JSON.stringify({ backend_key: backend }),
    });
    refresh();
  };

  const installWeights = async () => {
    await fetchJson("/modules/model_3d/install_weights", {
      method: "POST",
      body: JSON.stringify({ backend_key: backend, weight_key: weightKey }),
    });
    refresh();
  };

  const uninstallWeights = async () => {
    await fetchJson("/modules/model_3d/uninstall_weights", {
      method: "POST",
      body: JSON.stringify({ backend_key: backend, weight_key: weightKey }),
    });
    refresh();
  };

  const reinstallWeights = async () => {
    await fetchJson("/modules/model_3d/reinstall_weights", {
      method: "POST",
      body: JSON.stringify({ backend_key: backend, weight_key: weightKey }),
    });
    refresh();
  };

  const runGeneration = async () => {
    const paths = inputPaths
      .split("\n")
      .map((line) => line.trim())
      .filter(Boolean);
    await fetchJson("/modules/model_3d/run", {
      method: "POST",
      body: JSON.stringify({
        backend_key: backend,
        input_paths: paths,
        input_mode: inputMode,
        output_dir: outputDir || null,
      }),
    });
  };

  const updateDeps = async () => {
    const res = await fetchJson<{ needs_manual?: boolean; reason?: string }>("/modules/model_3d/update_deps", {
      method: "POST",
    });
    if (res?.needs_manual) {
      if (res.reason === "compiler") {
        setPrereqAlert(
          translations.model3d_prereq_alert_compiler ||
            "Falta el compilador C++. Instala Visual Studio Build Tools (Desktop development with C++)."
        );
      } else if (res.reason === "cuda") {
        setPrereqAlert(
          translations.model3d_prereq_alert_cuda ||
            "CUDA del sistema no coincide con PyTorch. Instala CUDA 12.1 o usa un PyTorch compatible."
        );
      } else if (res.reason === "torch") {
        setPrereqAlert(
          translations.model3d_prereq_alert_torch ||
            "No se pudo actualizar PyTorch a 2.6. Revisa el registro para mas detalles."
        );
      } else {
        setPrereqAlert(translations.model3d_prereq_alert_generic || "Faltan prerequisitos para compilar.");
      }
    } else {
      setPrereqAlert("");
    }
    refreshPrereqs();
  };

  const openCudaNeeded = async () => {
    await fetchJson("/modules/model_3d/open_cuda_needed", { method: "POST" });
  };

  const restartRun = async () => {
    await fetchJson("/modules/model_3d/restart", { method: "POST" });
    refresh();
  };

  const stopRun = async () => {
    await fetchJson("/modules/model_3d/stop", { method: "POST" });
    refresh();
  };

  const openOutput = async () => {
    await fetchJson("/modules/model_3d/open_output", {
      method: "POST",
      body: JSON.stringify({ path: outputDir || state?.last_output_dir || state?.output_base }),
    });
  };

  const openHistoryFolder = async (path: string) => {
    await fetchJson("/modules/model_3d/open_output", {
      method: "POST",
      body: JSON.stringify({ path }),
    });
  };

  const saveToken = async () => {
    if (!hfToken) return;
    await fetchJson("/modules/model_3d/save_hf", {
      method: "POST",
      body: JSON.stringify({ token: hfToken }),
    });
    setHfToken("");
    refresh();
  };

  const deleteToken = async () => {
    await fetchJson("/modules/model_3d/delete_hf", { method: "POST" });
    refresh();
  };

  const appendPath = (path: string) => {
    if (!path) return;
    setInputPaths((prev) => (prev ? `${prev}\n${path}` : path));
  };

  const pickFile = async () => {
    const res = await fetchJson<{ path?: string; paths?: string[] }>("/ui/pick_file", {
      method: "POST",
      body: JSON.stringify({ title: translations.model3d_input_label || "Input paths", initial_dir: "" }),
    });
    if (res.paths?.length) {
      res.paths.forEach((path) => appendPath(path));
    } else if (res.path) {
      appendPath(res.path);
    }
  };

  const pickFolder = async () => {
    const res = await fetchJson<{ path: string }>("/ui/pick_folder", {
      method: "POST",
      body: JSON.stringify({ title: translations.model3d_input_label || "Input paths", initial_dir: "" }),
    });
    appendPath(res.path);
  };

  const previewItem = useMemo(() => {
    if (!history.length) return null;
    return history.find((item) => item.rel_path === previewRel) || history[0];
  }, [history, previewRel]);

  const previewUrl = useMemo(() => {
    if (!previewItem) return "";
    return `${WEB_BRIDGE_URL}/modules/model_3d/preview?path=${encodeURIComponent(previewItem.rel_path)}`;
  }, [previewItem]);

  return (
    <AppShell>
      <Script
        src="https://unpkg.com/@google/model-viewer/dist/model-viewer.min.js"
        strategy="afterInteractive"
      />
      <div className="page-header">
        <div className="eyebrow">{translations.model3d_title || "3D Models"}</div>
        <h1>{translations.model3d_title || "3D Model Generation"}</h1>
        <p>{translations.model3d_subtitle || "Generate 3D assets with multiple backends."}</p>
        <p>{translations.model3d_plain || "Creates a 3D model from one or more images."}</p>
      </div>
      {state?.running && <div className="banner">{translations.status_in_progress || "En progreso"}</div>}

      <section className="panel">
        <div className="panel-header">
          <h2>{translations.model3d_backend_label || "Backend"}</h2>
          <span className="pill">{backendLabel}</span>
        </div>
        <div className="panel-body">
          <div className="form">
            <label>
              {translations.model3d_backend_label || "Backend"}
              <select value={backend} onChange={(event) => updateBackend(event.target.value)}>
                {BACKENDS.map((item) => (
                  <option key={item.key} value={item.key}>
                    {translations[item.labelKey] || item.key}
                  </option>
                ))}
              </select>
            </label>
            <label>
              {translations.model3d_input_mode_label || "Input mode"}
              <select value={inputMode} onChange={(event) => setInputMode(event.target.value)}>
                {INPUT_MODES.map((item) => (
                  <option key={item.key} value={item.key}>
                    {translations[item.labelKey] || item.key}
                  </option>
                ))}
              </select>
            </label>
            <label>
              {translations.model3d_input_label || "Input paths"}
              <textarea
                value={inputPaths}
                onChange={(event) => setInputPaths(event.target.value)}
                placeholder={translations.model3d_input_placeholder || "Paste one path per line"}
              />
            </label>
            <div className="list-actions">
              <button className="ghost" onClick={pickFile}>
                {translations.model3d_btn_select_files || "Select files"}
              </button>
              <button className="ghost" onClick={pickFolder}>
                {translations.model3d_btn_select_folder || "Select folder"}
              </button>
            </div>
            <label>
              {translations.model3d_output_label || "Output"}
              <input value={outputDir} onChange={(event) => setOutputDir(event.target.value)} />
            </label>
          </div>
          <div className="list-actions" style={{ marginTop: "1rem" }}>
            <button className="primary" onClick={runGeneration} disabled={!state?.installed || state?.running}>
              {translations.model3d_btn_generate || "Generate"}
            </button>
            <button className="ghost" onClick={openOutput}>
              {translations.model3d_btn_open_output || "Open output"}
            </button>
          </div>
          <div className="list-actions" style={{ marginTop: "0.6rem" }}>
            <button className="ghost" onClick={updateDeps}>
              {translations.model3d_btn_update_deps || "Update dependencies"}
            </button>
            <button className="ghost" onClick={stopRun} disabled={!state?.running}>
              {translations.model3d_btn_stop || "Stop"}
            </button>
            <button className="ghost" onClick={restartRun} disabled={!state?.running}>
              {translations.model3d_btn_restart || "Restart"}
            </button>
          </div>
        </div>
      </section>

      <section className="panel">
        <div className="panel-header">
          <h2>{translations.model3d_actions_label || "Actions"}</h2>
        </div>
        <div className="panel-body">
          <div className="list-actions">
            {!state?.installed && (
              <button className="primary" onClick={installBackend}>
                {translations.model3d_btn_install_backend || "Install backend"}
              </button>
            )}
            {state?.installed && (
              <button className="ghost" onClick={uninstallBackend}>
                {translations.model3d_btn_uninstall_backend || "Uninstall backend"}
              </button>
            )}
            <button className="ghost" onClick={installWeights}>
              {translations.model3d_btn_install_weights || "Install weights"}
            </button>
            <button className="ghost" onClick={reinstallWeights}>
              {translations.model3d_btn_reinstall_weights || "Reinstall weights"}
            </button>
            <button className="ghost" onClick={uninstallWeights}>
              {translations.model3d_btn_uninstall_weights || "Uninstall weights"}
            </button>
          </div>
          <div className="form" style={{ marginTop: "1rem" }}>
            <label>
              {translations.model3d_weights_label || "Weights"}
              <select value={weightKey} onChange={(event) => setWeightKey(event.target.value)}>
                {state?.weights?.length ? (
                  state.weights.map((opt) => (
                    <option key={opt.key} value={opt.key}>
                      {opt.label}
                    </option>
                  ))
                ) : (
                  <option value="">{translations.model3d_weights_none || "No weights"}</option>
                )}
              </select>
            </label>
          </div>
        </div>
      </section>

      <section className="panel">
        <div className="panel-header">
          <h2>{translations.model3d_prereq_title || "Prerequisites"}</h2>
        </div>
        <div className="panel-body">
          {prereqAlert && <div className="banner">{prereqAlert}</div>}
          <div className="list-actions" style={{ flexWrap: "wrap" }}>
            {prereqs?.torch_version ? (
              <span className="pill">Torch: {prereqs.torch_version}</span>
            ) : null}
            <span className="pill">
              {translations.model3d_prereq_pybind11 || "pybind11"}:{" "}
              {prereqs?.pybind11_ok ? "OK" : "Falta"}
            </span>
            <span className="pill">
              {translations.model3d_prereq_compiler || "Compiler"}:{" "}
              {prereqs?.compiler_ok ? "OK" : "Falta"}
            </span>
            <span className="pill">
              CUDA NVCC: {prereqs?.nvcc_version || "N/A"}
            </span>
            <span className="pill">
              Torch CUDA: {prereqs?.torch_cuda || "N/A"}
            </span>
            <span className="pill">
              {translations.model3d_prereq_cuda_match || "CUDA compatible"}:{" "}
              {prereqs?.cuda_match ? "OK" : "No"}
            </span>
          </div>
          <div className="list-actions" style={{ marginTop: "0.8rem" }}>
            <button className="ghost" onClick={openCudaNeeded}>
              {translations.model3d_btn_open_cuda_needed || "Instalar CUDA necesario"}
            </button>
          </div>
        </div>
      </section>

      <section className="panel">
        <div className="panel-header">
          <h2>Hugging Face</h2>
          <span className="pill">{state?.hf_token_saved ? "Token saved" : "No token"}</span>
        </div>
        <div className="panel-body">
          {state?.hf_token_saved ? (
            <div className="list-actions">
              <button className="ghost" onClick={deleteToken}>
                {translations.model3d_btn_delete_hf || "Delete token"}
              </button>
            </div>
          ) : (
            <div className="form">
              <label>
                {translations.model3d_hf_token_label || "HF Token"}
                <input
                  type="password"
                  value={hfToken}
                  onChange={(event) => setHfToken(event.target.value)}
                />
              </label>
              <div className="list-actions" style={{ marginTop: "0.8rem" }}>
                <button className="primary" onClick={saveToken}>
                  {translations.model3d_btn_save_hf || "Save token"}
                </button>
                <a className="ghost" href="https://huggingface.co/settings/tokens" target="_blank">
                  {translations.model3d_btn_open_hf_tokens || "Open HF tokens"}
                </a>
              </div>
            </div>
          )}
        </div>
      </section>

      <section className="panel">
        <div className="panel-header">
          <h2>{translations.model3d_preview_title || "Preview"}</h2>
        </div>
        <div className="panel-body">
          {previewUrl ? (
            <div style={{ display: "grid", gap: "0.8rem" }}>
              <model-viewer
                src={previewUrl}
                style={{ width: "100%", height: "360px", background: "var(--panel-soft)" }}
                camera-controls
                auto-rotate
                exposure="0.9"
                shadow-intensity="1"
              />
              {previewItem?.name && <div className="list-meta">{previewItem.name}</div>}
            </div>
          ) : (
            <div className="empty">{translations.model3d_preview_empty || "No preview available yet."}</div>
          )}
        </div>
      </section>

      <section className="panel">
        <div className="panel-header">
          <h2>{translations.model3d_history_title || "History"}</h2>
        </div>
        <div className="panel-body">
          {history.length ? (
            <div className="list">
              {history.map((item) => (
                <div key={item.rel_path} className="list-row">
                  <div>
                    <div className="list-title">{item.name}</div>
                    {item.size_mb ? <div className="list-meta">{item.size_mb} MB</div> : null}
                  </div>
                  <div className="list-actions">
                    <button className="ghost" onClick={() => setPreviewRel(item.rel_path)}>
                      {translations.model3d_btn_preview || "Ver"}
                    </button>
                    <button className="ghost" onClick={() => openHistoryFolder(item.folder)}>
                      {translations.model3d_btn_open_folder || "Abrir carpeta"}
                    </button>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="empty">{translations.model3d_history_empty || "No outputs yet."}</div>
          )}
        </div>
      </section>

      <section className="panel">
        <div className="panel-header">
          <h2>{translations.model3d_log_label || "Log"}</h2>
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
