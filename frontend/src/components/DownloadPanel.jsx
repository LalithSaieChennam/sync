export default function DownloadPanel({ scoredUrl, musicUrl }) {
  return (
    <div className="downloads">
      <a href={scoredUrl} download className="dl dl-main">
        <span>Download scored video</span>
        <span className="dl-format">MP4</span>
      </a>
      <a href={musicUrl} download className="dl dl-alt">
        <span>Download music only</span>
        <span className="dl-format">MP3</span>
      </a>

      <style>{`
        .downloads {
          display: flex;
          gap: 8px;
        }
        .dl {
          flex: 1;
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 8px;
          padding: 12px;
          border-radius: 10px;
          text-decoration: none;
          font-size: 13px;
          font-weight: 600;
          font-family: 'Inter', sans-serif;
          transition: all 0.15s;
        }
        .dl-main {
          background: var(--accent);
          color: #fff;
        }
        .dl-main:hover { background: #7c4fe0; }
        .dl-alt {
          background: var(--surface-2);
          color: var(--text-2);
          border: 1px solid var(--border);
        }
        .dl-alt:hover {
          color: var(--text);
          border-color: var(--text-3);
        }
        .dl-format {
          font-size: 10px;
          font-weight: 700;
          letter-spacing: 0.5px;
          padding: 2px 6px;
          border-radius: 4px;
          background: rgba(255,255,255,0.15);
        }
        .dl-alt .dl-format {
          background: var(--surface-3);
        }
      `}</style>
    </div>
  )
}
