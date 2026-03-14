"use client";

import { useEffect, useState } from "react";
import AppShell from "@/components/AppShell";
import { fetchJson } from "@/lib/webBridge";
import { useApp } from "@/context/AppContext";

type OmniTransferState = {
  installed: boolean;
  running: boolean;
};

export default function OmniTransferPage() {
  const { translations } = useApp();
  const [state, setState] = useState<OmniTransferState | null>(null);
  const [logs, setLogs] = useState<string[]>([]);

  const refresh = async () => {
    const data = await fetchJson<OmniTransferState>("/modules/omni_transfer/state");
    setState(data);
  };

  const refreshLogs = async () => {
    const data = await fetchJson<{ lines: string[] }>("/modules/omni_transfer/logs");
    setLogs(data.lines);
  };

  const clearLogs = async () => {
    await fetchJson("/modules/omni_transfer/clear_logs", { method: "POST" });
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
    await fetchJson("/modules/omni_transfer/install", { method: "POST" });
    refresh();
  };

  const uninstall = async () => {
    await fetchJson("/modules/omni_transfer/uninstall", { method: "POST" });
    refresh();
  };

  return (
    <AppShell>
      <div className="page-header">
        <div className="eyebrow">{translations.omni_transfer_title || "OmniTransfer"}</div>
        <h1>{translations.omni_transfer_title || "OmniTransfer"}</h1>
        <p>{translations.omni_transfer_subtitle || "All-in-one framework for spatio-temporal video transfer."}</p>
        <p>{translations.omni_transfer_plain || "Transfers style and motion between videos."}</p>
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
                {translations.omni_transfer_btn_install || "Install backend"}
              </button>
            )}
            {state?.installed && (
              <button className="ghost" onClick={uninstall}>
                {translations.omni_transfer_btn_uninstall || "Uninstall backend"}
              </button>
            )}
            <a className="ghost" href="https://github.com/PangzeCheung/OmniTransfer" target="_blank">
              {translations.omni_transfer_btn_open_repo || "Open repo"}
            </a>
            <a className="ghost" href="https://pangzecheung.github.io/OmniTransfer/" target="_blank">
              {translations.omni_transfer_btn_open_project || "Open project page"}
            </a>
            <a className="ghost" href="https://arxiv.org/abs/2601.14250" target="_blank">
              {translations.omni_transfer_btn_open_paper || "Open paper"}
            </a>
          </div>
          <p style={{ marginTop: "0.8rem" }}>
            {translations.omni_transfer_note || "Note: academic project, check repo for code status."}
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
