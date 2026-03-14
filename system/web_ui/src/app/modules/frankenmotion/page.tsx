"use client";

import { useEffect, useState } from "react";
import AppShell from "@/components/AppShell";
import { fetchJson } from "@/lib/webBridge";
import { useApp } from "@/context/AppContext";

type FrankenMotionState = {
  installed: boolean;
  running: boolean;
};

export default function FrankenMotionPage() {
  const { translations } = useApp();
  const [state, setState] = useState<FrankenMotionState | null>(null);
  const [logs, setLogs] = useState<string[]>([]);

  const refresh = async () => {
    const data = await fetchJson<FrankenMotionState>("/modules/frankenmotion/state");
    setState(data);
  };

  const refreshLogs = async () => {
    const data = await fetchJson<{ lines: string[] }>("/modules/frankenmotion/logs");
    setLogs(data.lines);
  };

  const clearLogs = async () => {
    await fetchJson("/modules/frankenmotion/clear_logs", { method: "POST" });
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
    await fetchJson("/modules/frankenmotion/install", { method: "POST" });
    refresh();
  };

  const uninstall = async () => {
    await fetchJson("/modules/frankenmotion/uninstall", { method: "POST" });
    refresh();
  };

  return (
    <AppShell>
      <div className="page-header">
        <div className="eyebrow">{translations.frankenmotion_title || "FrankenMotion"}</div>
        <h1>{translations.frankenmotion_title || "FrankenMotion"}</h1>
        <p>{translations.frankenmotion_subtitle || "Part-level human motion generation and composition."}</p>
        <p>{translations.frankenmotion_plain || "Combines motion parts to create new animations."}</p>
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
                {translations.frankenmotion_btn_install || "Install backend"}
              </button>
            )}
            {state?.installed && (
              <button className="ghost" onClick={uninstall}>
                {translations.frankenmotion_btn_uninstall || "Uninstall backend"}
              </button>
            )}
            <a className="ghost" href="https://github.com/Coral79/FrankenMotion-Code" target="_blank">
              {translations.frankenmotion_btn_open_repo || "Open repo"}
            </a>
            <a className="ghost" href="https://coral79.github.io/frankenmotion/" target="_blank">
              {translations.frankenmotion_btn_open_project || "Open project page"}
            </a>
            <a className="ghost" href="https://arxiv.org/abs/2601.10909" target="_blank">
              {translations.frankenmotion_btn_open_paper || "Open paper"}
            </a>
          </div>
          <p style={{ marginTop: "0.8rem" }}>
            {translations.frankenmotion_coming_soon || "Code and weights are pending release."}
          </p>
          <p>{translations.frankenmotion_note || "Note: the repo announces a future full pipeline release."}</p>
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
