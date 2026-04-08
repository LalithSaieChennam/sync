const STAGES = [
  { id: 'uploading', label: 'Uploading' },
  { id: 'analyzing', label: 'Analyzing scenes' },
  { id: 'composing', label: 'Composing prompt' },
  { id: 'generating', label: 'Generating music' },
  { id: 'assembling', label: 'Mixing audio' },
  { id: 'complete', label: 'Complete' },
]

function getStageIndex(stage) {
  const idx = STAGES.findIndex(s => s.id === stage)
  return idx >= 0 ? idx : 1
}

export default function ProgressTracker({ status }) {
  const currentIdx = getStageIndex(status.stage)

  return (
    <div className="tracker">
      <p className="tracker-msg">{status.message}</p>

      <div className="tracker-bar">
        <div className="tracker-fill" style={{ width: `${status.progress}%` }} />
      </div>

      <div className="tracker-stages">
        {STAGES.map((stage, i) => {
          const state = i < currentIdx ? 'done' : i === currentIdx ? 'active' : 'waiting'
          return (
            <div key={stage.id} className={`tracker-step ${state}`}>
              <div className="step-marker">
                {state === 'done' ? (
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3"><polyline points="20 6 9 17 4 12"/></svg>
                ) : state === 'active' ? (
                  <div className="step-pulse" />
                ) : (
                  <div className="step-empty" />
                )}
              </div>
              <span className="step-label">{stage.label}</span>
            </div>
          )
        })}
      </div>

      <style>{`
        .tracker {
          border: 1px solid var(--border);
          border-radius: 12px;
          padding: 28px 24px;
          background: var(--surface);
        }
        .tracker-msg {
          font-size: 15px;
          font-weight: 600;
          color: var(--text);
          margin-bottom: 16px;
        }
        .tracker-bar {
          height: 3px;
          background: var(--surface-3);
          border-radius: 2px;
          overflow: hidden;
          margin-bottom: 24px;
        }
        .tracker-fill {
          height: 100%;
          background: var(--accent);
          border-radius: 2px;
          transition: width 0.6s ease;
        }
        .tracker-stages {
          display: flex;
          flex-direction: column;
          gap: 8px;
        }
        .tracker-step {
          display: flex;
          align-items: center;
          gap: 10px;
          font-size: 13px;
        }
        .step-marker {
          width: 20px;
          height: 20px;
          display: flex;
          align-items: center;
          justify-content: center;
          flex-shrink: 0;
        }
        .step-empty {
          width: 6px;
          height: 6px;
          border-radius: 50%;
          background: var(--surface-3);
        }
        .step-pulse {
          width: 8px;
          height: 8px;
          border-radius: 50%;
          background: var(--accent);
          animation: pulse 1.5s ease-in-out infinite;
        }
        @keyframes pulse {
          0%, 100% { opacity: 1; transform: scale(1); }
          50% { opacity: 0.5; transform: scale(0.8); }
        }
        .tracker-step.done { color: var(--green); }
        .tracker-step.active {
          color: var(--text);
          font-weight: 500;
        }
        .tracker-step.waiting { color: var(--text-3); }
      `}</style>
    </div>
  )
}
