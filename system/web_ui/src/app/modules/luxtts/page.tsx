"use client";

import { useEffect, useState } from "react";
import AppShell from "@/components/AppShell";
import { fetchJson } from "@/lib/webBridge";
import { useApp } from "@/context/AppContext";

type LuxTTSState = {
  installed: boolean;
  output_dir: string;
  running: boolean;
};

export default function LuxTTSPage() {
  const { translations } = useApp();
  const [state, setState] = useState<LuxTTSState | null>(null);
  const [logs, setLogs] = useState<string[]>([]);
  const [text, setText] = useState("");
  const [promptAudio, setPromptAudio] = useState("");
  const [modelId, setModelId] = useState("YatharthS/LuxTTS");
  const [device, setDevice] = useState("auto");
  const [threads, setThreads] = useState("2");
  const [rms, setRms] = useState("0.01");
  const [tShift, setTShift] = useState("0.9");
  const [numSteps, setNumSteps] = useState("4");
  const [speed, setSpeed] = useState("1.0");
  const [returnSmooth, setReturnSmooth] = useState(false);
  const [outputDir, setOutputDir] = useState("");

  const refresh = async () => {
    const data = await fetchJson<LuxTTSState>("/modules/luxtts/state");
    setState(data);
    if (!outputDir) {
      setOutputDir(data.output_dir);
    }
  };

  const refreshLogs = async () => {
    const data = await fetchJson<{ lines: string[] }>("/modules/luxtts/logs");
    setLogs(data.lines);
  };

  const clearLogs = async () => {
    await fetchJson("/modules/luxtts/clear_logs", { method: "POST" });
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
    await fetchJson("/modules/luxtts/install", { method: "POST" });
    refresh();
  };

  const uninstall = async () => {
    await fetchJson("/modules/luxtts/uninstall", { method: "POST" });
    refresh();
  };

  const installDeps = async () => {
    await fetchJson("/modules/luxtts/deps", { method: "POST" });
  };

  const run = async () => {
    await fetchJson("/modules/luxtts/run", {
      method: "POST",
      body: JSON.stringify({
        text,
        prompt_audio: promptAudio,
        model_id: modelId,
        device,
        threads: Number(threads),
        rms: Number(rms),
        t_shift: Number(tShift),
        num_steps: Number(numSteps),
        speed: Number(speed),
        return_smooth: returnSmooth,
        output_dir: outputDir,
      }),
    });
  };

  const openOutput = async () => {
    await fetchJson("/modules/luxtts/open_output", {
      method: "POST",
      body: JSON.stringify({ path: outputDir || state?.output_dir }),
    });
  };

  return (
    <AppShell>
      <div className="page-header">
        <div className="eyebrow">{translations.luxtts_title || "LuxTTS"}</div>
        <h1>{translations.luxtts_title || "LuxTTS"}</h1>
        <p>{translations.luxtts_subtitle || "Lightweight ZipVoice TTS for 48khz voice cloning."}</p>
        <p>{translations.luxtts_plain || "Creates audio with a voice similar to a reference."}</p>
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
                {translations.luxtts_btn_install || "Install backend"}
              </button>
            )}
            {state?.installed && (
              <>
                <button className="ghost" onClick={uninstall}>
                  {translations.luxtts_btn_uninstall || "Uninstall backend"}
                </button>
                <button className="ghost" onClick={installDeps}>
                  {translations.luxtts_btn_deps || "Install dependencies"}
                </button>
                <button className="ghost" onClick={openOutput}>
                  {translations.luxtts_btn_open_output || "Open output"}
                </button>
              </>
            )}
            <a className="ghost" href="https://github.com/ysharma3501/LuxTTS" target="_blank">
              {translations.luxtts_btn_open_repo || "Open repo"}
            </a>
            <a className="ghost" href="https://huggingface.co/YatharthS/LuxTTS" target="_blank">
              {translations.luxtts_btn_open_model || "Open model"}
            </a>
            <a className="ghost" href="https://huggingface.co/spaces/YatharthS/LuxTTS" target="_blank">
              {translations.luxtts_btn_open_demo || "Open demo"}
            </a>
          </div>
          <p style={{ marginTop: "0.8rem" }}>
            {translations.luxtts_note || "Note: requires dependencies and a 3s+ reference audio."}
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
              {translations.luxtts_text_label || "Text"}
              <textarea value={text} onChange={(event) => setText(event.target.value)} />
            </label>
            <label>
              {translations.luxtts_prompt_label || "Reference audio"}
              <input value={promptAudio} onChange={(event) => setPromptAudio(event.target.value)} />
            </label>
            <label>
              {translations.luxtts_model_label || "Model"}
              <input value={modelId} onChange={(event) => setModelId(event.target.value)} />
            </label>
            <label>
              {translations.luxtts_device_label || "Device"}
              <select value={device} onChange={(event) => setDevice(event.target.value)}>
                <option value="auto">auto</option>
                <option value="cuda">cuda</option>
                <option value="cpu">cpu</option>
              </select>
            </label>
            <label>
              {translations.luxtts_threads_label || "Threads"}
              <input value={threads} onChange={(event) => setThreads(event.target.value)} />
            </label>
            <label>
              {translations.luxtts_rms_label || "RMS"}
              <input value={rms} onChange={(event) => setRms(event.target.value)} />
            </label>
            <label>
              {translations.luxtts_t_shift_label || "t_shift"}
              <input value={tShift} onChange={(event) => setTShift(event.target.value)} />
            </label>
            <label>
              {translations.luxtts_steps_label || "Steps"}
              <input value={numSteps} onChange={(event) => setNumSteps(event.target.value)} />
            </label>
            <label>
              {translations.luxtts_speed_label || "Speed"}
              <input value={speed} onChange={(event) => setSpeed(event.target.value)} />
            </label>
            <label>
              <span>{translations.luxtts_smooth_label || "Return smooth"}</span>
              <input
                type="checkbox"
                checked={returnSmooth}
                onChange={(event) => setReturnSmooth(event.target.checked)}
              />
            </label>
            <label>
              {translations.luxtts_output_label || "Output"}
              <input value={outputDir} onChange={(event) => setOutputDir(event.target.value)} />
            </label>
          </div>
          <div className="list-actions" style={{ marginTop: "1rem" }}>
            <button className="primary" onClick={run} disabled={!state?.installed || state?.running}>
              {translations.luxtts_btn_run || "Generate"}
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
