"use client";

import AppShell from "@/components/AppShell";
import { useApp } from "@/context/AppContext";

const SCENEMA_URL =
  "https://www.reddit.com/r/StableDiffusion/comments/1tbzgi3/scenema_audio_zeroshot_expressive_voice_cloning/";

export default function ScenemaAudioPage() {
  const { translations } = useApp();

  return (
    <AppShell>
      <div className="page-header">
        <div className="eyebrow">{translations.scenema_title || "Scenema Audio"}</div>
        <h1>{translations.scenema_title || "Scenema Audio"}</h1>
        <p>{translations.scenema_subtitle || "Reference module for zero-shot expressive voice cloning."}</p>
      </div>

      <section className="panel">
        <div className="panel-header">
          <h2>{translations.scenema_notice_title || "Integrated source"}</h2>
        </div>
        <div className="panel-body">
          <p>
            {translations.scenema_notice_desc ||
              "This module adds a direct link to the shared post for exploration and follow-up."}
          </p>
          <div className="list-actions" style={{ marginTop: "1rem" }}>
            <a className="ghost" href={SCENEMA_URL} target="_blank">
              {translations.scenema_btn_open_source || "Open source"}
            </a>
          </div>
        </div>
      </section>
    </AppShell>
  );
}

