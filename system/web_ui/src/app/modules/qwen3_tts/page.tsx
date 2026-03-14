"use client";

import { useEffect, useState } from "react";
import AppShell from "@/components/AppShell";
import { fetchJson } from "@/lib/webBridge";
import { useApp } from "@/context/AppContext";

type Qwen3TTSState = {
  installed: boolean;
  output_dir: string;
  running: boolean;
};

export default function Qwen3TTSPage() {
  const { translations } = useApp();
  const [state, setState] = useState<Qwen3TTSState | null>(null);
  const [logs, setLogs] = useState<string[]>([]);
  const [mode, setMode] = useState("custom_voice");
  const [modelId, setModelId] = useState("Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice");
  const [text, setText] = useState("");
  const [language, setLanguage] = useState("Auto");
  const [speaker, setSpeaker] = useState("Vivian");
  const [instruct, setInstruct] = useState("");
  const [refAudio, setRefAudio] = useState("");
  const [refText, setRefText] = useState("");
  const [device, setDevice] = useState("auto");
  const [dtype, setDtype] = useState("bfloat16");
  const [attnImpl, setAttnImpl] = useState("flash_attention_2");
  const [outputDir, setOutputDir] = useState("");

  const refresh = async () => {
    const data = await fetchJson<Qwen3TTSState>("/modules/qwen3_tts/state");
    setState(data);
    if (!outputDir) {
      setOutputDir(data.output_dir);
    }
  };

  const refreshLogs = async () => {
    const data = await fetchJson<{ lines: string[] }>("/modules/qwen3_tts/logs");
    setLogs(data.lines);
  };

  const clearLogs = async () => {
    await fetchJson("/modules/qwen3_tts/clear_logs", { method: "POST" });
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
    await fetchJson("/modules/qwen3_tts/install", { method: "POST" });
    refresh();
  };

  const uninstall = async () => {
    await fetchJson("/modules/qwen3_tts/uninstall", { method: "POST" });
    refresh();
  };

  const installDeps = async () => {
    await fetchJson("/modules/qwen3_tts/deps", { method: "POST" });
  };

  const run = async () => {
    await fetchJson("/modules/qwen3_tts/run", {
      method: "POST",
      body: JSON.stringify({
        mode,
        model_id: modelId,
        text,
        language,
        speaker,
        instruct,
        ref_audio: refAudio,
        ref_text: refText,
        device,
        dtype,
        attn_implementation: attnImpl,
        output_dir: outputDir,
      }),
    });
  };

  const openOutput = async () => {
    await fetchJson("/modules/qwen3_tts/open_output", {
      method: "POST",
      body: JSON.stringify({ path: outputDir || state?.output_dir }),
    });
  };

  return (
    <AppShell>
      <div className="page-header">
        <div className="eyebrow">{translations.qwen3_tts_title || "Qwen3-TTS"}</div>
        <h1>{translations.qwen3_tts_title || "Qwen3-TTS"}</h1>
        <p>{translations.qwen3_tts_subtitle || "Multilingual TTS with custom voice and cloning."}</p>
        <p>{translations.qwen3_tts_plain || "Generates speech with style and personality control."}</p>
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
                {translations.qwen3_tts_btn_install || "Install backend"}
              </button>
            )}
            {state?.installed && (
              <>
                <button className="ghost" onClick={uninstall}>
                  {translations.qwen3_tts_btn_uninstall || "Uninstall backend"}
                </button>
                <button className="ghost" onClick={installDeps}>
                  {translations.qwen3_tts_btn_deps || "Install dependencies"}
                </button>
                <button className="ghost" onClick={openOutput}>
                  {translations.qwen3_tts_btn_open_output || "Open output"}
                </button>
              </>
            )}
            <a className="ghost" href="https://github.com/QwenLM/Qwen3-TTS" target="_blank">
              {translations.qwen3_tts_btn_open_repo || "Open repo"}
            </a>
            <a className="ghost" href="https://huggingface.co/collections/Qwen/qwen3-tts" target="_blank">
              {translations.qwen3_tts_btn_open_model || "Open models"}
            </a>
            <a className="ghost" href="https://huggingface.co/spaces/Qwen/Qwen3-TTS" target="_blank">
              {translations.qwen3_tts_btn_open_demo || "Open demo"}
            </a>
            <a className="ghost" href="https://qwen.ai/blog?id=qwen3tts-0115" target="_blank">
              {translations.qwen3_tts_btn_open_blog || "Open blog"}
            </a>
            <a className="ghost" href="https://arxiv.org/abs/2601.15621" target="_blank">
              {translations.qwen3_tts_btn_open_paper || "Open paper"}
            </a>
          </div>
          <p style={{ marginTop: "0.8rem" }}>
            {translations.qwen3_tts_note || "Note: install dependencies and use a compatible model."}
          </p>
        </div>
      </section>

      <section className="panel">
        <div className="panel-header">
          <h2>Generacion</h2>
        </div>
        <div className="panel-body">
          <div className="form">
            <label>
              {translations.qwen3_tts_mode_label || "Mode"}
              <select value={mode} onChange={(event) => setMode(event.target.value)}>
                <option value="custom_voice">{translations.qwen3_tts_mode_custom || "Custom voice"}</option>
                <option value="voice_design">{translations.qwen3_tts_mode_design || "Voice design"}</option>
                <option value="voice_clone">{translations.qwen3_tts_mode_clone || "Voice clone"}</option>
              </select>
            </label>
            <label>
              {translations.qwen3_tts_model_label || "Model"}
              <input value={modelId} onChange={(event) => setModelId(event.target.value)} />
            </label>
            <label>
              {translations.qwen3_tts_text_label || "Text"}
              <textarea value={text} onChange={(event) => setText(event.target.value)} />
            </label>
            <label>
              {translations.qwen3_tts_language_label || "Language"}
              <input value={language} onChange={(event) => setLanguage(event.target.value)} />
            </label>
            <label>
              {translations.qwen3_tts_speaker_label || "Speaker"}
              <input value={speaker} onChange={(event) => setSpeaker(event.target.value)} />
            </label>
            <label>
              {translations.qwen3_tts_instruct_label || "Instruction"}
              <input value={instruct} onChange={(event) => setInstruct(event.target.value)} />
            </label>
            <label>
              {translations.qwen3_tts_ref_audio_label || "Reference audio"}
              <input value={refAudio} onChange={(event) => setRefAudio(event.target.value)} />
            </label>
            <label>
              {translations.qwen3_tts_ref_text_label || "Reference text"}
              <input value={refText} onChange={(event) => setRefText(event.target.value)} />
            </label>
            <label>
              {translations.qwen3_tts_device_label || "Device"}
              <select value={device} onChange={(event) => setDevice(event.target.value)}>
                <option value="auto">auto</option>
                <option value="cuda:0">cuda:0</option>
                <option value="cpu">cpu</option>
              </select>
            </label>
            <label>
              {translations.qwen3_tts_dtype_label || "Dtype"}
              <select value={dtype} onChange={(event) => setDtype(event.target.value)}>
                <option value="bfloat16">bfloat16</option>
                <option value="float16">float16</option>
                <option value="float32">float32</option>
              </select>
            </label>
            <label>
              {translations.qwen3_tts_attn_label || "Attn implementation"}
              <input value={attnImpl} onChange={(event) => setAttnImpl(event.target.value)} />
            </label>
            <label>
              {translations.qwen3_tts_output_label || "Output"}
              <input value={outputDir} onChange={(event) => setOutputDir(event.target.value)} />
            </label>
          </div>
          <div className="list-actions" style={{ marginTop: "1rem" }}>
            <button className="primary" onClick={run} disabled={!state?.installed || state?.running}>
              {translations.qwen3_tts_btn_run || "Generate"}
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
