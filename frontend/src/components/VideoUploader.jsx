import { useRef, useState } from 'react'

export default function VideoUploader({ file, onFileChange }) {
  const inputRef = useRef(null)
  const [dragOver, setDragOver] = useState(false)

  const handleFile = (f) => {
    if (!f) return
    const ext = f.name.split('.').pop().toLowerCase()
    if (!['mp4', 'mov', 'webm'].includes(ext)) {
      alert('Please upload an MP4, MOV, or WebM file.')
      return
    }
    if (f.size > 100 * 1024 * 1024) {
      alert('File too large. Max 100MB.')
      return
    }
    onFileChange(f)
  }

  return (
    <div
      className={`uploader ${dragOver ? 'drag-over' : ''} ${file ? 'has-file' : ''}`}
      onClick={() => !file && inputRef.current?.click()}
      onDragOver={(e) => { e.preventDefault(); setDragOver(true) }}
      onDragLeave={() => setDragOver(false)}
      onDrop={(e) => {
        e.preventDefault()
        setDragOver(false)
        handleFile(e.dataTransfer.files[0])
      }}
    >
      <input
        ref={inputRef}
        type="file"
        accept="video/mp4,video/quicktime,video/webm,.mp4,.mov,.webm"
        style={{ display: 'none' }}
        onChange={(e) => handleFile(e.target.files[0])}
      />
      {file ? (
        <div className="file-row">
          <div className="file-dot" />
          <div className="file-meta">
            <span className="file-name">{file.name}</span>
            <span className="file-size">{(file.size / 1024 / 1024).toFixed(1)} MB</span>
          </div>
          <button className="file-remove" onClick={(e) => {
            e.stopPropagation()
            onFileChange(null)
          }}>&times;</button>
        </div>
      ) : (
        <div className="upload-empty">
          <p className="upload-title">Drop a video file here, or click to browse</p>
          <p className="upload-meta">MP4, MOV, WebM &middot; up to 120s &middot; 100MB max</p>
        </div>
      )}

      <style>{`
        .uploader {
          border: 1.5px dashed var(--border);
          border-radius: 12px;
          padding: 36px 24px;
          cursor: pointer;
          transition: border-color 0.15s, background 0.15s;
          background: transparent;
        }
        .uploader:hover,
        .uploader.drag-over {
          border-color: var(--accent);
          background: var(--accent-dim);
        }
        .uploader.has-file {
          border-style: solid;
          border-color: var(--border);
          padding: 14px 16px;
          cursor: default;
          background: var(--surface);
        }
        .uploader.has-file:hover {
          border-color: var(--border);
          background: var(--surface);
        }

        .upload-empty { text-align: center; }
        .upload-title {
          color: var(--text-2);
          font-size: 14px;
          font-weight: 500;
        }
        .upload-meta {
          color: var(--text-3);
          font-size: 12px;
          margin-top: 6px;
        }

        .file-row {
          display: flex;
          align-items: center;
          gap: 12px;
        }
        .file-dot {
          width: 8px;
          height: 8px;
          border-radius: 50%;
          background: var(--green);
          flex-shrink: 0;
        }
        .file-meta {
          flex: 1;
          display: flex;
          align-items: baseline;
          gap: 8px;
          min-width: 0;
        }
        .file-name {
          font-weight: 600;
          font-size: 14px;
          color: var(--text);
          white-space: nowrap;
          overflow: hidden;
          text-overflow: ellipsis;
        }
        .file-size {
          font-size: 12px;
          color: var(--text-3);
          flex-shrink: 0;
        }
        .file-remove {
          background: none;
          border: none;
          color: var(--text-3);
          font-size: 20px;
          line-height: 1;
          cursor: pointer;
          padding: 2px 6px;
          border-radius: 4px;
          transition: color 0.15s;
        }
        .file-remove:hover {
          color: var(--red);
        }
      `}</style>
    </div>
  )
}
