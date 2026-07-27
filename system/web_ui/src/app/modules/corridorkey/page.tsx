"use client";

import { useEffect, useState } from "react";
import AppShell from "@/components/AppShell";
import { fetchJson } from "@/lib/webBridge";

type State = {
  installed: boolean;
  deps_installed: boolean;
  running: boolean;
  backend_dir: string;
  output_dir: string;
  uv_available: boolean;
};

export default function CorridorKeyPage() {
  const [state, setState] = useState<State | null>(null);
  const [logs, setLogs] = useState<string[]>([]);
  const [inputPath, setInputPath] = useState("");
  const [alphaPath, setAlphaPath] = useState("");
  const [jobName, setJobName] = useState("shot");
  const [device, setDevice] = useState("auto");
  const [screenColor, setScreenColor] = useState("auto");
  const [colorspace, setColorspace] = useState("srgb");
  const [imageSize, setImageSize] = useState(2048);
  const [despill, setDespill] = useState(5);
  const [despeckle, setDespeckle] = useState(true);
  const [error, setError] = useState("");

  const refresh = async () => {
    try {
      setState(await fetchJson<State>("/modules/corridorkey/state"));
      const data = await fetchJson<{ lines: string[] }>("/modules/corridorkey/logs");
      setLogs(data.lines);
      setError("");
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  };

  useEffect(() => {
    refresh();
    const id = setInterval(refresh, 3500);
    return () => clearInterval(id);
  }, []);

  const action = async (path: string, body?: unknown) => {
    try {
      setError("");
      await fetchJson(path, {
        method: "POST",
        ...(body === undefined ? {} : { body: JSON.stringify(body) }),
      });
      refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  };

  return (
    <AppShell>
      <div className="page-header">
        <div className="eyebrow">Visión · VFX</div>
        <h1>CorridorKey</h1>
        <p>Extracción neural de pantalla verde o azul con foreground y alpha lineal.</p>
      </div>
      <div className="banner">
        Backend externo bajo CC BY-NC-SA 4.0 con condiciones adicionales. UNLZ AI Studio lo descarga desde el repositorio oficial.
      </div>
      {error && <div className="banner">{error}</div>}

      <section className="panel">
        <div className="panel-header">
          <h2>Preparación</h2>
          <span className="pill">{state?.running ? "En ejecución" : state?.deps_installed ? "Listo" : state?.installed ? "Backend instalado" : "No instalado"}</span>
        </div>
        <div className="panel-body">
          <div className="list-actions">
            {!state?.installed && <button className="primary" disabled={state?.running} onClick={() => action("/modules/corridorkey/install")}>Instalar backend</button>}
            {state?.installed && <button className="ghost" disabled={state?.running} onClick={() => action("/modules/corridorkey/deps", { device })}>Preparar entorno</button>}
            <a className="ghost" href="https://github.com/nikopueringer/CorridorKey" target="_blank" rel="noreferrer">Repositorio oficial</a>
            {!state?.uv_available && <span className="pill">uv se instalará automáticamente</span>}
          </div>
        </div>
      </section>

      <section className="panel">
        <div className="panel-header"><h2>Procesar material</h2></div>
        <div className="panel-body">
          <div className="form">
            <label>Video o carpeta de secuencia<input value={inputPath} onChange={(e) => setInputPath(e.target.value)} placeholder="C:\material\plano.mp4" /></label>
            <label>Alpha Hint (video o carpeta)<input value={alphaPath} onChange={(e) => setAlphaPath(e.target.value)} placeholder="C:\material\alpha.mp4" /></label>
            <label>Nombre del trabajo<input value={jobName} onChange={(e) => setJobName(e.target.value)} /></label>
            <label>Dispositivo<select value={device} onChange={(e) => setDevice(e.target.value)}><option value="auto">Auto</option><option value="cuda">CUDA</option><option value="cpu">CPU</option></select></label>
            <label>Color de pantalla<select value={screenColor} onChange={(e) => setScreenColor(e.target.value)}><option value="auto">Auto</option><option value="green">Verde</option><option value="blue">Azul</option></select></label>
            <label>Espacio de entrada<select value={colorspace} onChange={(e) => setColorspace(e.target.value)}><option value="srgb">sRGB / Rec.709</option><option value="linear">Lineal</option></select></label>
            <label>Resolución de inferencia<select value={imageSize} onChange={(e) => setImageSize(Number(e.target.value))}><option value={512}>512</option><option value={1024}>1024</option><option value={2048}>2048</option></select></label>
            <label>Despill (0–10)<input type="number" min={0} max={10} value={despill} onChange={(e) => setDespill(Number(e.target.value))} /></label>
            <label><input type="checkbox" checked={despeckle} onChange={(e) => setDespeckle(e.target.checked)} /> Limpieza automática de puntos</label>
          </div>
          <div className="list-actions" style={{ marginTop: "1rem" }}>
            <button className="primary" disabled={!state?.deps_installed || state?.running || !inputPath || !alphaPath} onClick={() => action("/modules/corridorkey/run", {
              input_path: inputPath, alpha_path: alphaPath, job_name: jobName, device, screen_color: screenColor,
              colorspace, image_size: imageSize, despill, despeckle, despeckle_size: 400, refiner: 1.0,
            })}>Procesar</button>
            {state?.running && <button className="ghost" onClick={() => action("/modules/corridorkey/stop")}>Detener</button>}
            <button className="ghost" onClick={() => action("/modules/corridorkey/open_output", { path: jobName })}>Abrir resultados</button>
          </div>
        </div>
      </section>

      <section className="panel">
        <div className="panel-header"><h2>Logs</h2></div>
        <div className="panel-body"><pre className="empty">{logs.length ? logs.join("\n") : "Sin actividad."}</pre></div>
      </section>
    </AppShell>
  );
}
