"use client";

import { useEffect, useState } from "react";
import AppShell from "@/components/AppShell";
import { fetchJson } from "@/lib/webBridge";
import { useApp } from "@/context/AppContext";

type VibeVoiceState = {
  installed: boolean;
  output_dir: string;
  running: boolean;
};

export default function VibeVoiceASRPage() {
  const { translations } = useApp();
  const [state, setState] = useState<VibeVoiceState | null>(null);
  const [logs, setLogs] = useState<string[]>([]);
  const [modelPath, setModelPath] = useState("microsoft/VibeVoice-ASR");
  const [audioFile, setAudioFile] = useState("");
  const [device, setDevice] = useState("auto");
  const [maxTokens, setMaxTokens] = useState("32768");
  const [temperature, setTemperature] = useState("0.0");
  const [topP, setTopP] = useState("1.0");
  const [numBeams, setNumBeams] = useState("1");
  const [attnImpl, setAttnImpl] = useState("flash_attention_2");
  const [outputDir, setOutputDir] = useState("");

  const refresh = async () => {
    const data = await fetchJson<VibeVoiceState>("/modules/vibevoice_asr/state");
    setState(data);
    if (!outputDir) {
      setOutputDir(data.output_dir);
    }
  };

  const refreshLogs = async () => {
    const data = await fetchJson<{ lines: string[] }>("/modules/vibevoice_asr/logs");
    setLogs(data.lines);
  };

  const clearLogs = async () => {
    await fetchJson("/modules/vibevoice_asr/clear_logs", { method: "POST" });
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
    await fetchJson("/modules/vibevoice_asr/install", { method: "POST" });
    refresh();
  };

  const uninstall = async () => {
    await fetchJson("/modules/vibevoice_asr/uninstall", { method: "POST" });
    refresh();
  };

  const installDeps = async () => {
    await fetchJson("/modules/vibevoice_asr/deps", { method: "POST" });
  };

  const run = async () => {
    await fetchJson("/modules/vibevoice_asr/run", {
      method: "POST",
      body: JSON.stringify({
        model_path: modelPath,
        audio_file: audioFile,
        device,
        max_new_tokens: Number(maxTokens),
        temperature: Number(temperature),
        top_p: Number(topP),
        num_beams: Number(numBeams),
        attn_implementation: attnImpl,
        output_dir: outputDir,
      }),
    });
  };

  const openOutput = async () => {
    await fetchJson("/modules/vibevoice_asr/open_output", {
      method: "POST",
      body: JSON.stringify({ path: outputDir || state?.output_dir }),
    });
  };

  return (
    <AppShell>
      <div className="page-header">
        <div className="eyebrow">{translations.vibevoice_asr_title || "VibeVoice ASR"}</div>
        <h1>{translations.vibevoice_asr_title || "VibeVoice ASR"}</h1>
        <p>
          {translations.vibevoice_asr_subtitle ||
            "Long-form ASR with diarization (who/when/what) in one pass."}
        </p>
        <p>{translations.vibevoice_asr_plain || "Turns long audio into text and indicates who speaks."}</p>
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
                {translations.vibevoice_asr_btn_install || "Install backend"}
              </button>
            )}
            {state?.installed && (
              <>
                <button className="ghost" onClick={uninstall}>
                  {translations.vibevoice_asr_btn_uninstall || "Uninstall backend"}
                </button>
                <button className="ghost" onClick={installDeps}>
                  {translations.vibevoice_asr_btn_deps || "Install dependencies"}
                </button>
                <button className="ghost" onClick={openOutput}>
                  {translations.vibevoice_asr_btn_open_output || "Open output"}
                </button>
              </>
            )}
            <a className="ghost" href="https://github.com/microsoft/VibeVoice" target="_blank">
              {translations.vibevoice_asr_btn_open_repo || "Open repo"}
            </a>
            <a className="ghost" href="https://huggingface.co/microsoft/VibeVoice-ASR" target="_blank">
              {translations.vibevoice_asr_btn_open_project || "Open project page"}
            </a>
            <a className="ghost" href="https://aka.ms/vibevoice-asr" target="_blank">
              {translations.vibevoice_asr_btn_open_demo || "Open demo"}
            </a>
          </div>
          <p style={{ marginTop: "0.8rem" }}>
            {translations.vibevoice_asr_note || "Note: requires dependencies and may need ffmpeg."}
          </p>
        </div>
      </section>

      <section className="panel">
        <div className="panel-header">
          <h2>Transcription</h2>
        </div>
        <div className="panel-body">
          <div className="form">
            <label>
              {translations.vibevoice_asr_model_label || "Model"}
              <input value={modelPath} onChange={(event) => setModelPath(event.target.value)} />
            </label>
            <label>
              {translations.vibevoice_asr_audio_label || "Audio"}
              <input value={audioFile} onChange={(event) => setAudioFile(event.target.value)} />
            </label>
            <label>
              {translations.vibevoice_asr_device_label || "Device"}
              <select value={device} onChange={(event) => setDevice(event.target.value)}>
                <option value="auto">auto</option>
                <option value="cuda">cuda</option>
                <option value="cpu">cpu</option>
              </select>
            </label>
            <label>
              {translations.vibevoice_asr_max_tokens_label || "Max tokens"}
              <input value={maxTokens} onChange={(event) => setMaxTokens(event.target.value)} />
            </label>
            <label>
              {translations.vibevoice_asr_temp_label || "Temperature"}
              <input value={temperature} onChange={(event) => setTemperature(event.target.value)} />
            </label>
            <label>
              {translations.vibevoice_asr_top_p_label || "Top-p"}
              <input value={topP} onChange={(event) => setTopP(event.target.value)} />
            </label>
            <label>
              {translations.vibevoice_asr_beams_label || "Num beams"}
              <input value={numBeams} onChange={(event) => setNumBeams(event.target.value)} />
            </label>
            <label>
              {translations.vibevoice_asr_attn_label || "Attn implementation"}
              <input value={attnImpl} onChange={(event) => setAttnImpl(event.target.value)} />
            </label>
            <label>
              {translations.vibevoice_asr_output_label || "Output"}
              <input value={outputDir} onChange={(event) => setOutputDir(event.target.value)} />
            </label>
          </div>
          <div className="list-actions" style={{ marginTop: "1rem" }}>
            <button className="primary" onClick={run} disabled={!state?.installed || state?.running}>
              {translations.vibevoice_asr_btn_run || "Transcribe"}
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
