"use client";

import Link from "next/link";
import AppShell from "@/components/AppShell";
import { fetchJson } from "@/lib/webBridge";
import { useApp } from "@/context/AppContext";
import { useEffect, useState } from "react";

type MonitorData = {
  system: {
    cpu_name: string;
    cpu_threads: number;
    ram_gb: number;
    ram_used_gb?: number;
    ram_available_gb?: number;
    ram_percent?: number;
    cpu_percent?: number;
    cpu_temp_c?: number | null;
    cuda_available: boolean;
    gpu_names: string[];
    vram_gb: number[];
    gpu_util?: number | null;
    gpu_temp_c?: number | null;
    gpu_mem_used_gb?: number | null;
    gpu_mem_total_gb?: number | null;
  };
};

type HardwareSnapshot = {
  cpu_name?: string;
  cpu_threads?: number;
  ram_gb?: number;
  gpu_name?: string;
  gpu_vram_gb?: number;
};

type MonitorMetrics = {
  cpu_percent?: number;
  cpu_temp_c?: number | null;
  ram_used_gb?: number;
  ram_available_gb?: number;
  ram_percent?: number;
  gpu_util?: number | null;
  gpu_temp_c?: number | null;
  gpu_mem_used_gb?: number | null;
  gpu_mem_total_gb?: number | null;
};

const HARDWARE_SNAPSHOT_KEY = "unlz_hw_snapshot";

const rankGpu = (name: string, vram: number) => {
  const lowered = name.toLowerCase();
  let score = vram || 0;
  if (lowered.includes("nvidia")) score += 1000;
  if (lowered.includes("amd") || lowered.includes("radeon")) score += 500;
  if (lowered.includes("intel")) score += 200;
  if (lowered.includes("virtual") || lowered.includes("microsoft") || lowered.includes("basic render")) {
    score -= 1000;
  }
  return score;
};

const pickGpu = (names: string[] = [], vram: number[] = []) => {
  if (!names.length) {
    return { name: "", vram: 0 };
  }
  const pairs = names.map((name, idx) => ({ name, vram: vram[idx] || 0 }));
  pairs.sort((a, b) => rankGpu(b.name, b.vram) - rankGpu(a.name, a.vram));
  return pairs[0];
};

const mergeSnapshot = (current: HardwareSnapshot | null, detected: HardwareSnapshot) => {
  const next: HardwareSnapshot = { ...(current || {}) };
  if (detected.cpu_name) next.cpu_name = detected.cpu_name;
  if (typeof detected.cpu_threads === "number") next.cpu_threads = detected.cpu_threads;
  if (typeof detected.ram_gb === "number") next.ram_gb = detected.ram_gb;
  if (detected.gpu_name) next.gpu_name = detected.gpu_name;
  if (typeof detected.gpu_vram_gb === "number" && detected.gpu_vram_gb > 0) next.gpu_vram_gb = detected.gpu_vram_gb;
  return next;
};

const hasSnapshotChanged = (current: HardwareSnapshot | null, next: HardwareSnapshot) => {
  const fields: (keyof HardwareSnapshot)[] = ["cpu_name", "cpu_threads", "ram_gb", "gpu_name", "gpu_vram_gb"];
  return fields.some((field) => current?.[field] !== next[field]);
};

export default function Home() {
  const { translations, modules, favorites, refresh } = useApp();
  const installed = modules.filter((mod) => mod.installed);
  const [hardwareSnapshot, setHardwareSnapshot] = useState<HardwareSnapshot | null>(null);
  const [metrics, setMetrics] = useState<MonitorMetrics | null>(null);

  useEffect(() => {
    let active = true;
    if (typeof window !== "undefined") {
      try {
        const savedSnapshot = window.localStorage.getItem(HARDWARE_SNAPSHOT_KEY);
        if (savedSnapshot) {
          setHardwareSnapshot(JSON.parse(savedSnapshot) as HardwareSnapshot);
        }
      } catch {
        // Ignore invalid cached data.
      }
    }

    const refreshMonitor = async () => {
      try {
        const data = await fetchJson<MonitorData>("/monitor");
        if (active) {
          const gpu = pickGpu(data.system.gpu_names, data.system.vram_gb);
          const detectedSnapshot: HardwareSnapshot = {
            cpu_name: data.system.cpu_name,
            cpu_threads: data.system.cpu_threads,
            ram_gb: data.system.ram_gb,
            gpu_name: gpu.name || undefined,
            gpu_vram_gb: gpu.vram || undefined,
          };

          setHardwareSnapshot((current) => {
            const next = mergeSnapshot(current, detectedSnapshot);
            if (!hasSnapshotChanged(current, next)) {
              return current;
            }
            try {
              window.localStorage.setItem(HARDWARE_SNAPSHOT_KEY, JSON.stringify(next));
            } catch {
              // Ignore storage failures.
            }
            return next;
          });

          setMetrics({
            cpu_percent: data.system.cpu_percent,
            cpu_temp_c: data.system.cpu_temp_c ?? null,
            ram_used_gb: data.system.ram_used_gb,
            ram_available_gb: data.system.ram_available_gb,
            ram_percent: data.system.ram_percent,
            gpu_util: data.system.gpu_util ?? null,
            gpu_temp_c: data.system.gpu_temp_c ?? null,
            gpu_mem_used_gb: data.system.gpu_mem_used_gb ?? null,
            gpu_mem_total_gb: data.system.gpu_mem_total_gb ?? null,
          });
        }
      } catch {
        // Keep the last known snapshot/metrics when monitor isn't reachable.
      }
    };

    refreshMonitor();
    const id = setInterval(refreshMonitor, 5000);
    return () => {
      active = false;
      clearInterval(id);
    };
  }, []);

  return (
    <AppShell>
      <section className="hero">
        <div>
          <div className="eyebrow">{translations.hero_badge || "AI POWERED STUDIO"}</div>
          <h1>{translations.hero_title || "Create, Analyze, Innovate"}</h1>
          <p>
            {translations.hero_subtitle ||
              "The comprehensive AI platform for UNLZ. Run language, vision, and audio models locally."}
          </p>
        </div>
        <div className="hero-card">
          <div className="hero-title">{translations.sidebar_installed || "Installed"}</div>
          <div className="hero-value">{installed.length} modulos activos</div>
          <div className="hero-meta">
            {modules.length} disponibles en la tienda de modulos.
          </div>
          <div className="hero-meta">
            <Link className="ghost" href="/modules">
              {translations.btn_explore || "Explore Modules"}
            </Link>
          </div>
        </div>
      </section>

      <section className="stats">
        <div className="stat-card">
          <div className="stat-label">{translations.feat_perf_title || "High Performance"}</div>
          <div className="stat-value">GPU/CPU</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">{translations.feat_sec_title || "Secure Environment"}</div>
          <div className="stat-value">Local</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">{translations.feat_mod_title || "Modular Design"}</div>
          <div className="stat-value">{modules.length}</div>
        </div>
      </section>

      <section className="stats">
        <div className="stat-card">
          <div className="stat-label">CPU</div>
          <div className="stat-value">
            {hardwareSnapshot?.cpu_name
              ? `${hardwareSnapshot.cpu_name} (${hardwareSnapshot.cpu_threads || 0} Threads)`
              : "Detectando..."}
          </div>
          <div className="list-meta">
            {metrics?.cpu_percent !== undefined ? `Uso ${metrics.cpu_percent.toFixed(0)}%` : ""}
            {metrics?.cpu_temp_c !== null && metrics?.cpu_temp_c !== undefined
              ? ` - Temp ${metrics.cpu_temp_c.toFixed(0)} C`
              : ""}
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-label">RAM</div>
          <div className="stat-value">{hardwareSnapshot?.ram_gb ? `${hardwareSnapshot.ram_gb} GB` : "Detectando..."}</div>
          <div className="list-meta">
            {metrics?.ram_used_gb !== undefined ? `Usada ${metrics.ram_used_gb} GB` : ""}
            {metrics?.ram_available_gb !== undefined ? ` - Libre ${metrics.ram_available_gb} GB` : ""}
            {metrics?.ram_percent !== undefined ? ` - ${metrics.ram_percent.toFixed(0)}%` : ""}
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-label">GPU</div>
          <div className="stat-value">
            {hardwareSnapshot?.gpu_name
              ? `${hardwareSnapshot.gpu_name} (${hardwareSnapshot.gpu_vram_gb || 0} GB)`
              : "Detectando..."}
          </div>
          <div className="list-meta">
            {metrics?.gpu_util !== null && metrics?.gpu_util !== undefined ? `Uso ${metrics.gpu_util.toFixed(0)}%` : ""}
            {metrics?.gpu_temp_c !== null && metrics?.gpu_temp_c !== undefined
              ? ` - Temp ${metrics.gpu_temp_c.toFixed(0)} C`
              : ""}
            {metrics?.gpu_mem_used_gb !== null && metrics?.gpu_mem_used_gb !== undefined
              ? ` - VRAM ${metrics.gpu_mem_used_gb.toFixed(1)}/${(metrics.gpu_mem_total_gb || 0).toFixed(1)} GB`
              : ""}
          </div>
        </div>
      </section>

    </AppShell>
  );
}
