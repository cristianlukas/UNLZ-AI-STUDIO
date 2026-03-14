"use client";

import { useEffect, useState } from "react";
import AppShell from "@/components/AppShell";
import { fetchJson } from "@/lib/webBridge";
import { useApp } from "@/context/AppContext";

type LightOnOCRState = {
  installed: boolean;
  output_dir: string;
  running: boolean;
};

export default function LightOnOCRPage() {
  const { translations } = useApp();
  const [state, setState] = useState<LightOnOCRState | null>(null);
  const [logs, setLogs] = useState<string[]>([]);
  const [modelId, setModelId] = useState("lightonai/LightOnOCR-2-1B");
  const [inputPath, setInputPath] = useState("");
  const [inputType, setInputType] = useState("auto");
  const [page, setPage] = useState("0");
  const [dpi, setDpi] = useState("200");
  const [device, setDevice] = useState("auto");
  const [dtype, setDtype] = useState("auto");
  const [maxTokens, setMaxTokens] = useState("1024");
  const [temperature, setTemperature] = useState("0.2");
  const [topP, setTopP] = useState("0.9");
  const [outputDir, setOutputDir] = useState("");

  const refresh = async () => {
    const data = await fetchJson<LightOnOCRState>("/modules/lightonocr/state");
    setState(data);
    if (!outputDir) {
      setOutputDir(data.output_dir);
    }
  };

  const refreshLogs = async () => {
    const data = await fetchJson<{ lines: string[] }>("/modules/lightonocr/logs");
    setLogs(data.lines);
  };

  const clearLogs = async () => {
    await fetchJson("/modules/lightonocr/clear_logs", { method: "POST" });
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
    await fetchJson("/modules/lightonocr/install", { method: "POST" });
    refresh();
  };

  const uninstall = async () => {
    await fetchJson("/modules/lightonocr/uninstall", { method: "POST" });
    refresh();
  };

  const installDeps = async () => {
    await fetchJson("/modules/lightonocr/deps", { method: "POST" });
  };

  const run = async () => {
    await fetchJson("/modules/lightonocr/run", {
      method: "POST",
      body: JSON.stringify({
        input_path: inputPath,
        input_type: inputType,
        page: Number(page),
        dpi: Number(dpi),
        model_id: modelId,
        device,
        dtype,
        max_new_tokens: Number(maxTokens),
        temperature: Number(temperature),
        top_p: Number(topP),
        output_dir: outputDir,
      }),
    });
  };

  const openOutput = async () => {
    await fetchJson("/modules/lightonocr/open_output", {
      method: "POST",
      body: JSON.stringify({ path: outputDir || state?.output_dir }),
    });
  };

  return (
    <AppShell>
      <div className="page-header">
        <div className="eyebrow">{translations.lightonocr_title || "LightOnOCR-2-1B"}</div>
        <h1>{translations.lightonocr_title || "LightOnOCR-2-1B"}</h1>
        <p>
          {translations.lightonocr_subtitle ||
            "OCR end-to-end para PDFs e imagenes con salida de texto limpio."}
        </p>
        <p>{translations.lightonocr_plain || "Reads text from images or PDFs and makes it editable."}</p>
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
                {translations.lightonocr_btn_install || "Install backend"}
              </button>
            )}
            {state?.installed && (
              <>
                <button className="ghost" onClick={uninstall}>
                  {translations.lightonocr_btn_uninstall || "Uninstall backend"}
                </button>
                <button className="ghost" onClick={installDeps}>
                  {translations.lightonocr_btn_deps || "Install dependencies"}
                </button>
                <button className="ghost" onClick={openOutput}>
                  {translations.lightonocr_btn_open_output || "Open output"}
                </button>
              </>
            )}
            <a className="ghost" href="https://huggingface.co/lightonai/LightOnOCR-2-1B" target="_blank">
              {translations.lightonocr_btn_open_model || "Open model"}
            </a>
            <a className="ghost" href="https://huggingface.co/spaces/lightonai/LightOnOCR-2-1B-Demo" target="_blank">
              {translations.lightonocr_btn_open_demo || "Open demo"}
            </a>
            <a className="ghost" href="https://huggingface.co/blog/lightonai/lightonocr-2" target="_blank">
              {translations.lightonocr_btn_open_blog || "Open blog"}
            </a>
            <a className="ghost" href="https://arxiv.org/pdf/2601.14251" target="_blank">
              {translations.lightonocr_btn_open_paper || "Open paper"}
            </a>
          </div>
          <p style={{ marginTop: "0.8rem" }}>
            {translations.lightonocr_note || "Note: requires transformers from source plus pillow and pypdfium2."}
          </p>
        </div>
      </section>

      <section className="panel">
        <div className="panel-header">
          <h2>OCR</h2>
        </div>
        <div className="panel-body">
          <div className="form">
            <label>
              {translations.lightonocr_model_label || "Model"}
              <input value={modelId} onChange={(event) => setModelId(event.target.value)} />
            </label>
            <label>
              {translations.lightonocr_input_label || "Input file"}
              <input value={inputPath} onChange={(event) => setInputPath(event.target.value)} />
            </label>
            <label>
              {translations.lightonocr_input_type_label || "Input type"}
              <select value={inputType} onChange={(event) => setInputType(event.target.value)}>
                <option value="auto">{translations.lightonocr_input_type_auto || "Auto"}</option>
                <option value="image">{translations.lightonocr_input_type_image || "Image"}</option>
                <option value="pdf">{translations.lightonocr_input_type_pdf || "PDF"}</option>
              </select>
            </label>
            <label>
              {translations.lightonocr_page_label || "PDF page (0-based)"}
              <input value={page} onChange={(event) => setPage(event.target.value)} />
            </label>
            <label>
              {translations.lightonocr_dpi_label || "PDF DPI"}
              <input value={dpi} onChange={(event) => setDpi(event.target.value)} />
            </label>
            <label>
              {translations.lightonocr_device_label || "Device"}
              <select value={device} onChange={(event) => setDevice(event.target.value)}>
                <option value="auto">auto</option>
                <option value="cuda">cuda</option>
                <option value="cpu">cpu</option>
                <option value="mps">mps</option>
              </select>
            </label>
            <label>
              {translations.lightonocr_dtype_label || "Dtype"}
              <select value={dtype} onChange={(event) => setDtype(event.target.value)}>
                <option value="auto">auto</option>
                <option value="bfloat16">bfloat16</option>
                <option value="float16">float16</option>
                <option value="float32">float32</option>
              </select>
            </label>
            <label>
              {translations.lightonocr_max_tokens_label || "Max tokens"}
              <input value={maxTokens} onChange={(event) => setMaxTokens(event.target.value)} />
            </label>
            <label>
              {translations.lightonocr_temp_label || "Temperature"}
              <input value={temperature} onChange={(event) => setTemperature(event.target.value)} />
            </label>
            <label>
              {translations.lightonocr_top_p_label || "Top-p"}
              <input value={topP} onChange={(event) => setTopP(event.target.value)} />
            </label>
            <label>
              {translations.lightonocr_output_label || "Output"}
              <input value={outputDir} onChange={(event) => setOutputDir(event.target.value)} />
            </label>
          </div>
          <div className="list-actions" style={{ marginTop: "1rem" }}>
            <button className="primary" onClick={run} disabled={!state?.installed || state?.running}>
              {translations.lightonocr_btn_run || "Run OCR"}
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
