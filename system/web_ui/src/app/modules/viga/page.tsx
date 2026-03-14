"use client";

import { useEffect, useState } from "react";
import AppShell from "@/components/AppShell";
import { fetchJson } from "@/lib/webBridge";
import { useApp } from "@/context/AppContext";

type VigaState = {
  installed: boolean;
  output_dir: string;
  running: boolean;
  sam_downloaded: boolean;
};

export default function VigaPage() {
  const { translations } = useApp();
  const [state, setState] = useState<VigaState | null>(null);
  const [logs, setLogs] = useState<string[]>([]);
  const [depsTarget, setDepsTarget] = useState("agent");
  const [runner, setRunner] = useState("dynamic_scene");
  const [datasetPath, setDatasetPath] = useState("data/dynamic_scene");
  const [outputDir, setOutputDir] = useState("");
  const [task, setTask] = useState("artist");
  const [model, setModel] = useState("gpt-5");
  const [maxRounds, setMaxRounds] = useState("100");

  const refresh = async () => {
    const data = await fetchJson<VigaState>("/modules/viga/state");
    setState(data);
    if (!outputDir) {
      setOutputDir(data.output_dir);
    }
  };

  const refreshLogs = async () => {
    const data = await fetchJson<{ lines: string[] }>("/modules/viga/logs");
    setLogs(data.lines);
  };

  const clearLogs = async () => {
    await fetchJson("/modules/viga/clear_logs", { method: "POST" });
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

  useEffect(() => {
    const nextDefault = runner === "dynamic_scene" ? "data/dynamic_scene" : "data/static_scene";
    setDatasetPath((prev) => {
      if (!prev || prev === "data/dynamic_scene" || prev === "data/static_scene") {
        return nextDefault;
      }
      return prev;
    });
  }, [runner]);

  const install = async () => {
    await fetchJson("/modules/viga/install", { method: "POST" });
    refresh();
  };

  const uninstall = async () => {
    await fetchJson("/modules/viga/uninstall", { method: "POST" });
    refresh();
  };

  const installDeps = async () => {
    await fetchJson("/modules/viga/deps", {
      method: "POST",
      body: JSON.stringify({ target: depsTarget }),
    });
  };

  const downloadSam = async () => {
    await fetchJson("/modules/viga/download_sam", { method: "POST" });
  };

  const run = async () => {
    await fetchJson("/modules/viga/run", {
      method: "POST",
      body: JSON.stringify({
        runner,
        task,
        model,
        dataset_path: datasetPath,
        output_dir: outputDir,
        max_rounds: maxRounds ? Number(maxRounds) : null,
      }),
    });
  };

  const openOutput = async () => {
    await fetchJson("/modules/viga/open_output", {
      method: "POST",
      body: JSON.stringify({ path: outputDir || state?.output_dir }),
    });
  };

  return (
    <AppShell>
      <div className="page-header">
        <div className="eyebrow">{translations.viga_title || "VIGA"}</div>
        <h1>{translations.viga_title || "VIGA"}</h1>
        <p>
          {translations.viga_subtitle ||
            "Vision-as-Inverse-Graphics Agent for programmatic visual reconstruction."}
        </p>
        <p>{translations.viga_plain || "Separates objects and enhances images automatically."}</p>
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
                {translations.viga_btn_install || "Install backend"}
              </button>
            )}
            {state?.installed && (
              <>
                <button className="ghost" onClick={uninstall}>
                  {translations.viga_btn_uninstall || "Uninstall backend"}
                </button>
                <label>
                  {translations.viga_deps_label || "Dependencies"}
                  <select value={depsTarget} onChange={(event) => setDepsTarget(event.target.value)}>
                    <option value="agent">{translations.viga_deps_agent || "Agent"}</option>
                    <option value="blender">{translations.viga_deps_blender || "Blender"}</option>
                    <option value="sam">{translations.viga_deps_sam || "SAM"}</option>
                  </select>
                </label>
                <button className="ghost" onClick={installDeps}>
                  {translations.viga_btn_deps || "Install dependencies"}
                </button>
                <button className="ghost" onClick={downloadSam}>
                  {translations.viga_btn_download_sam || "Download SAM weights"}
                </button>
                <button className="ghost" onClick={openOutput}>
                  {translations.viga_btn_open_output || "Open output"}
                </button>
              </>
            )}
            <a className="ghost" href="https://github.com/Fugtemypt123/VIGA" target="_blank">
              {translations.viga_btn_open_repo || "Open repo"}
            </a>
            <a className="ghost" href="https://fugtemypt123.github.io/VIGA-website/" target="_blank">
              {translations.viga_btn_open_project || "Open project page"}
            </a>
            <a className="ghost" href="https://arxiv.org/abs/2601.11109" target="_blank">
              {translations.viga_btn_open_docs || "Open docs"}
            </a>
          </div>
          <div className="list-actions" style={{ marginTop: "0.8rem" }}>
            <span className="pill">
              {state?.sam_downloaded
                ? translations.viga_sam_ready || "SAM OK"
                : translations.viga_sam_missing || "SAM missing"}
            </span>
          </div>
        </div>
      </section>

      <section className="panel">
        <div className="panel-header">
          <h2>{translations.viga_runner_label || "Runner"}</h2>
        </div>
        <div className="panel-body">
          <div className="form">
            <label>
              {translations.viga_runner_label || "Runner"}
              <select value={runner} onChange={(event) => setRunner(event.target.value)}>
                <option value="dynamic_scene">{translations.viga_runner_dynamic || "Dynamic scene"}</option>
                <option value="static_scene">{translations.viga_runner_static || "Static scene"}</option>
              </select>
            </label>
            <label>
              {translations.viga_dataset_label || "Dataset"}
              <input
                value={datasetPath}
                onChange={(event) => setDatasetPath(event.target.value)}
                placeholder={translations.viga_dataset_placeholder || "data/dynamic_scene"}
              />
            </label>
            <label>
              {translations.viga_task_label || "Task"}
              <input
                value={task}
                onChange={(event) => setTask(event.target.value)}
                placeholder={translations.viga_task_placeholder || "artist"}
              />
            </label>
            <label>
              {translations.viga_model_label || "Model"}
              <input
                value={model}
                onChange={(event) => setModel(event.target.value)}
                placeholder={translations.viga_model_placeholder || "gpt-5"}
              />
            </label>
            <label>
              {translations.viga_max_rounds_label || "Max rounds"}
              <input value={maxRounds} onChange={(event) => setMaxRounds(event.target.value)} />
            </label>
            <label>
              {translations.viga_output_label || "Output"}
              <input
                value={outputDir}
                onChange={(event) => setOutputDir(event.target.value)}
                placeholder={translations.viga_output_placeholder || "Output folder"}
              />
            </label>
          </div>
          <div className="list-actions" style={{ marginTop: "1rem" }}>
            <button className="primary" onClick={run} disabled={!state?.installed || state?.running}>
              {translations.viga_btn_run || "Run"}
            </button>
            <span className="pill">{state?.running ? "Running" : "Idle"}</span>
          </div>
          <p style={{ marginTop: "0.8rem" }}>
            {translations.viga_note ||
              "Note: VIGA recommends conda with multiple envs. Use these actions as a guide."}
          </p>
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
