"use client";

import { useEffect, useState } from "react";
import AppShell from "@/components/AppShell";
import { fetchJson } from "@/lib/webBridge";
import { useApp } from "@/context/AppContext";

type PersonaPlexState = {
  installed: boolean;
  output_dir: string;
  running: boolean;
};

export default function PersonaPlexPage() {
  const { translations } = useApp();
  const [state, setState] = useState<PersonaPlexState | null>(null);
  const [logs, setLogs] = useState<string[]>([]);
  const [hfToken, setHfToken] = useState("");
  const [voicePrompt, setVoicePrompt] = useState("NATF2.pt");
  const [inputWav, setInputWav] = useState("");
  const [textPrompt, setTextPrompt] = useState("");
  const [seed, setSeed] = useState("42424242");
  const [cpuOffload, setCpuOffload] = useState(false);
  const [outputDir, setOutputDir] = useState("");

  const refresh = async () => {
    const data = await fetchJson<PersonaPlexState>("/modules/personaplex/state");
    setState(data);
    if (!outputDir) {
      setOutputDir(data.output_dir);
    }
  };

  const refreshLogs = async () => {
    const data = await fetchJson<{ lines: string[] }>("/modules/personaplex/logs");
    setLogs(data.lines);
  };

  const clearLogs = async () => {
    await fetchJson("/modules/personaplex/clear_logs", { method: "POST" });
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
    await fetchJson("/modules/personaplex/install", { method: "POST" });
    refresh();
  };

  const uninstall = async () => {
    await fetchJson("/modules/personaplex/uninstall", { method: "POST" });
    refresh();
  };

  const installDeps = async () => {
    await fetchJson("/modules/personaplex/deps", { method: "POST" });
  };

  const run = async () => {
    await fetchJson("/modules/personaplex/run", {
      method: "POST",
      body: JSON.stringify({
        input_wav: inputWav,
        voice_prompt: voicePrompt,
        text_prompt: textPrompt || null,
        seed,
        cpu_offload: cpuOffload,
        output_dir: outputDir,
        hf_token: hfToken || null,
      }),
    });
  };

  const openOutput = async () => {
    await fetchJson("/modules/personaplex/open_output", {
      method: "POST",
      body: JSON.stringify({ path: outputDir || state?.output_dir }),
    });
  };

  return (
    <AppShell>
      <div className="page-header">
        <div className="eyebrow">{translations.personaplex_title || "PersonaPlex"}</div>
        <h1>{translations.personaplex_title || "PersonaPlex"}</h1>
        <p>
          {translations.personaplex_subtitle ||
            "Conversacion full-duplex con control de rol y voz."}
        </p>
        <p>{translations.personaplex_plain || "Creates spoken conversations with defined voice and role."}</p>
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
                {translations.personaplex_btn_install || "Install backend"}
              </button>
            )}
            {state?.installed && (
              <>
                <button className="ghost" onClick={uninstall}>
                  {translations.personaplex_btn_uninstall || "Uninstall backend"}
                </button>
                <button className="ghost" onClick={installDeps}>
                  {translations.personaplex_btn_deps || "Install dependencies"}
                </button>
                <button className="ghost" onClick={openOutput}>
                  {translations.personaplex_btn_open_output || "Open output"}
                </button>
              </>
            )}
            <a className="ghost" href="https://github.com/NVIDIA/personaplex" target="_blank">
              {translations.personaplex_btn_open_repo || "Open repo"}
            </a>
            <a className="ghost" href="https://huggingface.co/nvidia/personaplex-7b-v1" target="_blank">
              {translations.personaplex_btn_open_model || "Open model"}
            </a>
            <a className="ghost" href="https://research.nvidia.com/labs/adlr/personaplex/" target="_blank">
              {translations.personaplex_btn_open_demo || "Open demo"}
            </a>
            <a
              className="ghost"
              href="https://research.nvidia.com/labs/adlr/files/personaplex/personaplex_preprint.pdf"
              target="_blank"
            >
              {translations.personaplex_btn_open_paper || "Open paper"}
            </a>
          </div>
          <p style={{ marginTop: "0.8rem" }}>
            {translations.personaplex_note ||
              "Note: accept HF license, set token, and install libopus for realtime audio."}
          </p>
        </div>
      </section>

      <section className="panel">
        <div className="panel-header">
          <h2>Offline</h2>
        </div>
        <div className="panel-body">
          <div className="form">
            <label>
              {translations.personaplex_hf_token_label || "HF token"}
              <input
                type="password"
                value={hfToken}
                onChange={(event) => setHfToken(event.target.value)}
              />
            </label>
            <label>
              {translations.personaplex_voice_label || "Voice prompt"}
              <input value={voicePrompt} onChange={(event) => setVoicePrompt(event.target.value)} />
            </label>
            <label>
              {translations.personaplex_input_label || "Input wav"}
              <input value={inputWav} onChange={(event) => setInputWav(event.target.value)} />
            </label>
            <label>
              {translations.personaplex_prompt_label || "Role prompt"}
              <textarea value={textPrompt} onChange={(event) => setTextPrompt(event.target.value)} />
            </label>
            <label>
              {translations.personaplex_seed_label || "Seed"}
              <input value={seed} onChange={(event) => setSeed(event.target.value)} />
            </label>
            <label>
              {translations.personaplex_output_label || "Output"}
              <input value={outputDir} onChange={(event) => setOutputDir(event.target.value)} />
            </label>
          </div>
          <div className="list-actions" style={{ marginTop: "1rem" }}>
            <label className="checkbox">
              <input
                type="checkbox"
                checked={cpuOffload}
                onChange={(event) => setCpuOffload(event.target.checked)}
              />
              <span>{translations.personaplex_cpu_offload_label || "CPU offload"}</span>
            </label>
            <button className="primary" onClick={run} disabled={!state?.installed || state?.running}>
              {translations.personaplex_btn_run || "Run offline"}
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
