"use client";

import { useEffect, useState } from "react";
import AppShell from "@/components/AppShell";
import { fetchJson } from "@/lib/webBridge";

type State = {
  installed: boolean;
  running: boolean;
  backend_dir: string;
  output_dir: string;
};

export default function Img2ThreeJSPage() {
  const [state, setState] = useState<State | null>(null);
  const [logs, setLogs] = useState<string[]>([]);
  const [inputPath, setInputPath] = useState("");
  const [name, setName] = useState("");
  const [outputDir, setOutputDir] = useState("");
  const [error, setError] = useState("");

  const refresh = async () => {
    try {
      const next = await fetchJson<State>("/modules/img2threejs/state");
      setState(next);
      setOutputDir((current) => current || next.output_dir);
      const logData = await fetchJson<{ lines: string[] }>("/modules/img2threejs/logs");
      setLogs(logData.lines);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : String(cause));
    }
  };

  useEffect(() => {
    refresh();
    const timer = setInterval(refresh, 3500);
    return () => clearInterval(timer);
  }, []);

  const action = async (path: string, body?: object) => {
    setError("");
    try {
      await fetchJson(path, {
        method: "POST",
        body: body ? JSON.stringify(body) : undefined,
      });
      await refresh();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : String(cause));
    }
  };

  return (
    <AppShell>
      <div className="page-header">
        <div className="eyebrow">Imagen → código 3D</div>
        <h1>img2threejs</h1>
        <p>Reconstruye un objeto como código procedural Three.js, con especificación, pases y controles de calidad.</p>
      </div>
      {error && <div className="banner">{error}</div>}
      {state?.running && <div className="banner">Proceso en ejecución. Consultá el registro para ver el avance.</div>}

      <section className="panel">
        <div className="panel-header">
          <h2>Backend</h2>
          <span className="pill">{state?.installed ? "Instalado" : "No instalado"}</span>
        </div>
        <div className="panel-body">
          <div className="list-actions">
            {!state?.installed && <button className="primary" onClick={() => action("/modules/img2threejs/install")}>Instalar</button>}
            {state?.installed && <button className="ghost" onClick={() => action("/modules/img2threejs/update")}>Actualizar</button>}
            <button className="ghost" onClick={() => action("/modules/img2threejs/open_output", { path: outputDir || state?.output_dir })}>Abrir resultados</button>
            <a className="ghost" href="https://github.com/img2threejs/img2threejs" target="_blank" rel="noreferrer">Repositorio oficial</a>
          </div>
        </div>
      </section>

      <section className="panel">
        <div className="panel-header"><h2>Nuevo proyecto</h2></div>
        <div className="panel-body">
          <div className="form">
            <label>Ruta de la imagen<input value={inputPath} onChange={(event) => setInputPath(event.target.value)} placeholder="C:\imagenes\objeto.png" /></label>
            <label>Nombre del objeto<input value={name} onChange={(event) => setName(event.target.value)} placeholder="Mi objeto" /></label>
            <label>Carpeta de salida<input value={outputDir} onChange={(event) => setOutputDir(event.target.value)} /></label>
          </div>
          <div className="list-actions" style={{ marginTop: "1rem" }}>
            <button className="primary" disabled={!state?.installed || state?.running || !inputPath} onClick={() => action("/modules/img2threejs/run", { input_path: inputPath, name: name || null, output_dir: outputDir || null })}>
              Preparar proyecto y generar base
            </button>
          </div>
          <p style={{ marginTop: "0.9rem" }}>La salida debe pasar por revisión visual antes de completar todos los pases. Las caras ocultas se reconstruyen por inferencia.</p>
        </div>
      </section>

      <section className="panel">
        <div className="panel-header"><h2>Registro</h2></div>
        <div className="panel-body"><pre className="empty">{logs.length ? logs.join("\n") : "Todavía no hay actividad."}</pre></div>
      </section>
    </AppShell>
  );
}
