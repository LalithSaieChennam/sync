import { useState } from 'react'

export default function VideoPreview({ originalUrl, scoredUrl }) {
  const [showOriginal, setShowOriginal] = useState(false)

  return (
    <div className="preview">
      <div className="preview-tabs">
        <button
          className={`preview-tab ${!showOriginal ? 'active' : ''}`}
          onClick={() => setShowOriginal(false)}
        >
          Scored
        </button>
        <button
          className={`preview-tab ${showOriginal ? 'active' : ''}`}
          onClick={() => setShowOriginal(true)}
        >
          Original
        </button>
      </div>
      <video
        key={showOriginal ? 'o' : 's'}
        controls
        autoPlay
        className="preview-video"
        src={showOriginal ? originalUrl : scoredUrl}
      />

      <style>{`
        .preview {
          border: 1px solid var(--border);
          border-radius: 12px;
          overflow: hidden;
          background: var(--surface);
        }
        .preview-tabs {
          display: flex;
          border-bottom: 1px solid var(--border);
        }
        .preview-tab {
          flex: 1;
          padding: 10px;
          border: none;
          background: transparent;
          color: var(--text-3);
          font-size: 13px;
          font-weight: 500;
          font-family: 'Inter', sans-serif;
          cursor: pointer;
          transition: color 0.15s;
        }
        .preview-tab:first-child {
          border-right: 1px solid var(--border);
        }
        .preview-tab:hover {
          color: var(--text-2);
        }
        .preview-tab.active {
          color: var(--text);
          background: var(--surface-2);
        }
        .preview-video {
          width: 100%;
          display: block;
          max-height: 420px;
          background: #000;
        }
      `}</style>
    </div>
  )
}
