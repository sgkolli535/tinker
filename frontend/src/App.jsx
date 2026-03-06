import { useEffect, useMemo, useState } from "react";
import { createRun, getRun, getReport } from "./lib/api";

const STEP_ORDER = [
  "upload",
  "vision_analysis",
  "component_lookup",
  "physics_validation",
  "tradeoff_analyzer",
  "alternative_suggester",
  "report_generator",
];

function stepIndex(node) {
  const idx = STEP_ORDER.indexOf(node || "upload");
  return idx === -1 ? 0 : idx;
}

function HandUnderline({ w = 180 }) {
  return (
    <svg width={w} height="6" viewBox={`0 0 ${w} 6`}>
      <path d={`M0 4 Q${w * 0.2} 1, ${w * 0.4} 3 T${w * 0.7} 2 T${w} 4`} fill="none" stroke="var(--blue)" strokeWidth="1.5" strokeLinecap="round" />
    </svg>
  );
}

function Header({ title, sub }) {
  return (
    <div className="section-header">
      <h2>{title}</h2>
      <HandUnderline w={Math.min(240, title.length * 12)} />
      <p>{sub}</p>
    </div>
  );
}

function StatusBadge({ status }) {
  const label = status === "pass" ? "PASS" : status === "warn" ? "WARN" : "FAIL";
  return <span className={`badge badge--${status}`}>{label}</span>;
}

export default function App() {
  const [files, setFiles] = useState([]);
  const [userContext, setUserContext] = useState("");
  const [runId, setRunId] = useState("");
  const [run, setRun] = useState(null);
  const [report, setReport] = useState("");
  const [error, setError] = useState("");

  const currentNode = run?.status?.current_node || "upload";
  const activeIdx = stepIndex(currentNode);

  useEffect(() => {
    if (!runId) return;
    let stopped = false;

    const tick = async () => {
      try {
        const data = await getRun(runId);
        if (stopped) return;
        setRun(data);
        if (data.status.status === "completed") {
          const rep = await getReport(runId);
          if (!stopped) setReport(rep.report_markdown);
          return;
        }
        if (data.status.status !== "failed") {
          setTimeout(tick, 1200);
        }
      } catch (e) {
        if (!stopped) setError(String(e.message || e));
      }
    };

    tick();
    return () => {
      stopped = true;
    };
  }, [runId]);

  const classification = run?.state?.system_classification || {};
  const components = run?.state?.matched_components || [];
  const validation = run?.state?.physics_validation || {};
  const tradeoffs = run?.state?.tradeoff_analysis || [];
  const suggestions = run?.state?.suggestions || [];

  const metrics = useMemo(
    () => [
      { label: "Total Current", value: `${validation.estimated_total_current_mA ?? "-"} mA` },
      { label: "Control Latency", value: `${validation.estimated_control_latency_ms ?? "-"} ms` },
      { label: "Line Out", value: `${validation.estimated_line_out_headroom_dBu ?? "-"} dBu` },
      { label: "Bottlenecks", value: `${(validation.bottlenecks || []).length}` },
    ],
    [validation]
  );

  async function onRun() {
    setError("");
    setReport("");
    setRun(null);
    if (!files.length) {
      setError("Select at least one image.");
      return;
    }
    try {
      const created = await createRun(files, userContext);
      setRunId(created.run_id);
    } catch (e) {
      setError(String(e.message || e));
    }
  }

  return (
    <div className="app">
      <link href="https://fonts.googleapis.com/css2?family=Titillium+Web:wght@400;600;700&family=IBM+Plex+Mono:ital,wght@0,400;0,500;0,700;1,400&family=Caveat:wght@400;500&display=swap" rel="stylesheet" />

      <div className="topbar">
        <div>
          <span className="title">tinker</span>
          <span className="subtitle">reverse-engineer synths and MIDI controllers from photos</span>
        </div>
        <div className="meta">domain: synth_midi · v0.1</div>
      </div>

      <div className="pipeline">
        {STEP_ORDER.map((step, i) => (
          <div key={step} className={`step ${i === activeIdx ? "active" : ""} ${i < activeIdx ? "done" : ""}`}>
            {step.replaceAll("_", " ")}
          </div>
        ))}
      </div>

      <main className="page">
        <div className="margin-line" />
        <section>
          <Header title="Photo Input" sub="NODE 1 — vision_analysis" />
          <div className="upload-card">
            <label className="file-input">
              <input type="file" multiple accept="image/*" onChange={(e) => setFiles(Array.from(e.target.files || []))} />
              <span className="file-input-label">Choose photos...</span>
              {files.length > 0 ? <span className="file-input-count">{files.length} file{files.length > 1 ? "s" : ""} selected</span> : null}
            </label>
            <textarea value={userContext} onChange={(e) => setUserContext(e.target.value)} placeholder="Optional context, e.g. bus-powered MIDI controller" />
            <button onClick={onRun}>Run Analysis</button>
            {runId ? <div className="mono">run_id: {runId}</div> : null}
          </div>
          {error ? <div className="error">{error}</div> : null}
        </section>

        {activeIdx >= 1 ? (
          <section>
            <Header title="System Classification" sub="NODE 1 — pass 1" />
            <div className="grid2 mono">
              <div>category: <strong>{classification.category || "-"}</strong></div>
              <div>form factor: <strong>{classification.form_factor || "-"}</strong></div>
              <div>power: <strong>{classification.power_input || "-"}</strong></div>
              <div>use case: <strong>{classification.apparent_use_case || "-"}</strong></div>
            </div>
          </section>
        ) : null}

        {activeIdx >= 2 ? (
          <section>
            <Header title="Component Match" sub="NODE 2 — component_lookup" />
            <div className="stack mono">
              {components.map((c, i) => (
                <div key={`${c.best_match}-${i}`} className="row">
                  <span>{c.role}</span>
                  <span>{c.best_match}</span>
                  <span>{c.confidence}</span>
                  <span>x{c.count}</span>
                </div>
              ))}
            </div>
          </section>
        ) : null}

        {activeIdx >= 3 ? (
          <section>
            <Header title="Physics Validation" sub="NODE 3 — physics_validation" />
            <div className="metrics">
              {metrics.map((m) => (
                <div className="metric" key={m.label}>
                  <div className="k">{m.label}</div>
                  <div className="v">{m.value}</div>
                </div>
              ))}
            </div>
            <div className="stack mono">
              {(validation.checks || []).map((c, i) => (
                <div key={`${c.name}-${i}`} className="row">
                  <StatusBadge status={c.status || "warn"} />
                  <span>{c.name}</span>
                  <span>{c.value}</span>
                  <span>{c.note}</span>
                </div>
              ))}
            </div>
          </section>
        ) : null}

        {activeIdx >= 4 ? (
          <section>
            <Header title="Trade-off Analysis" sub="NODE 4 — tradeoff_analyzer" />
            <div className="stack mono">
              {tradeoffs.map((t, i) => (
                <div key={i} className="tradeoff">
                  <strong>{i + 1}. {t.choice}</strong>
                  <div>optimized: {t.optimized}</div>
                  <div>sacrificed: {t.sacrificed}</div>
                  <div>{t.verdict}</div>
                </div>
              ))}
            </div>
          </section>
        ) : null}

        {activeIdx >= 5 ? (
          <section>
            <Header title="Alternative Configurations" sub="NODE 5 — alternative_suggester" />
            <div className="stack mono">
              {suggestions.map((s, i) => (
                <div className="tradeoff" key={i}>
                  <strong>{s.change}</strong>
                  {s.validated ? <StatusBadge status="pass" /> : null}
                  <div>improves: {s.improves}</div>
                  <div>improvement: {s.improvement}</div>
                  <div>cost: {s.cost}</div>
                  {s.new_usb_headroom_mA != null ? <div>new USB headroom: {s.new_usb_headroom_mA} mA</div> : null}
                  {s.new_estimated_total_current_mA != null ? <div>new total current: {s.new_estimated_total_current_mA} mA</div> : null}
                </div>
              ))}
            </div>
          </section>
        ) : null}

        {report ? (
          <section>
            <Header title="Final Report" sub="NODE 6 — report_generator" />
            <pre className="report">{report}</pre>
          </section>
        ) : null}
      </main>
    </div>
  );
}
