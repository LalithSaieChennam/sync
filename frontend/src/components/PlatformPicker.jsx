const PLATFORMS = [
  { id: 'tiktok', label: 'TikTok' },
  { id: 'reels', label: 'Reels' },
  { id: 'shorts', label: 'Shorts' },
  { id: 'general', label: 'General' },
]

export default function PlatformPicker({ platform, onPlatformChange }) {
  return (
    <div>
      <p className="section-label">Platform</p>
      <div className="platform-row">
        {PLATFORMS.map((p) => (
          <button
            key={p.id}
            className={`plat-btn ${platform === p.id ? 'active' : ''}`}
            onClick={() => onPlatformChange(p.id)}
          >
            {p.label}
          </button>
        ))}
      </div>

      <style>{`
        .platform-row {
          display: flex;
          gap: 6px;
        }
        .plat-btn {
          flex: 1;
          padding: 9px 4px;
          border: 1px solid var(--border);
          border-radius: 8px;
          background: transparent;
          color: var(--text-2);
          font-size: 13px;
          font-weight: 500;
          font-family: 'Inter', sans-serif;
          cursor: pointer;
          transition: all 0.15s;
        }
        .plat-btn:hover {
          border-color: var(--text-3);
          color: var(--text);
        }
        .plat-btn.active {
          border-color: var(--accent);
          background: var(--accent-dim);
          color: var(--text);
        }
      `}</style>
    </div>
  )
}
