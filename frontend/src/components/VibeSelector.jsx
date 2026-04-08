const PRESETS = [
  { id: 'cinematic', label: 'Cinematic' },
  { id: 'lo-fi', label: 'Lo-fi' },
  { id: 'hype', label: 'Hype' },
  { id: 'emotional', label: 'Emotional' },
  { id: 'corporate', label: 'Corporate' },
  { id: 'dreamy', label: 'Dreamy' },
]

export default function VibeSelector({ vibe, onVibeChange }) {
  const isCustom = vibe && !PRESETS.find(p => p.id === vibe)

  return (
    <div>
      <p className="section-label">Vibe</p>
      <div className="vibe-pills">
        {PRESETS.map((preset) => (
          <button
            key={preset.id}
            className={`pill ${vibe === preset.id ? 'active' : ''}`}
            onClick={() => onVibeChange(vibe === preset.id ? '' : preset.id)}
          >
            {preset.label}
          </button>
        ))}
      </div>
      <input
        type="text"
        className="vibe-input"
        placeholder='Or type a custom vibe...'
        value={isCustom ? vibe : ''}
        onChange={(e) => onVibeChange(e.target.value)}
        onFocus={() => { if (!isCustom) onVibeChange('') }}
      />

      <style>{`
        .vibe-pills {
          display: flex;
          flex-wrap: wrap;
          gap: 6px;
          margin-bottom: 10px;
        }
        .pill {
          padding: 7px 16px;
          border: 1px solid var(--border);
          border-radius: 100px;
          background: transparent;
          color: var(--text-2);
          font-size: 13px;
          font-weight: 500;
          font-family: 'Inter', sans-serif;
          cursor: pointer;
          transition: all 0.15s;
        }
        .pill:hover {
          border-color: var(--text-3);
          color: var(--text);
        }
        .pill.active {
          border-color: var(--accent);
          background: var(--accent-dim);
          color: var(--text);
        }
        .vibe-input {
          width: 100%;
          padding: 10px 14px;
          border: 1px solid var(--border);
          border-radius: 8px;
          font-size: 13px;
          font-family: 'Inter', sans-serif;
          background: transparent;
          color: var(--text);
          transition: border-color 0.15s;
        }
        .vibe-input::placeholder { color: var(--text-3); }
        .vibe-input:focus {
          outline: none;
          border-color: var(--accent);
        }
      `}</style>
    </div>
  )
}
