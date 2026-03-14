"use client";

import AppShell from "@/components/AppShell";
import { useApp } from "@/context/AppContext";

export default function FlowActR1Page() {
  const { translations } = useApp();

  return (
    <AppShell>
      <div className="page-header">
        <div className="eyebrow">{translations.flowact_r1_title || "FlowAct-R1"}</div>
        <h1>{translations.flowact_r1_title || "FlowAct-R1"}</h1>
        <p>{translations.flowact_r1_subtitle || "Flow-guided human motion with reasoning."}</p>
        <p>{translations.flowact_r1_plain || "Research on generating more natural motion."}</p>
      </div>

      <section className="panel">
        <div className="panel-header">
          <h2>Enlaces</h2>
        </div>
        <div className="panel-body">
          <div className="list-actions">
            <a className="ghost" href="https://grisoon.github.io/FlowAct-R1/" target="_blank">
              {translations.flowact_r1_btn_open_project || "Open project page"}
            </a>
            <a className="ghost" href="https://arxiv.org/pdf/2601.10103" target="_blank">
              {translations.flowact_r1_btn_open_paper || "Open paper"}
            </a>
          </div>
          <p style={{ marginTop: "0.8rem" }}>
            {translations.flowact_r1_note || "Note: public page with paper/results. Code not linked."}
          </p>
        </div>
      </section>
    </AppShell>
  );
}
