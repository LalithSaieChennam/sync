import { useState } from 'react'
import VideoUploader from './components/VideoUploader'
import VibeSelector from './components/VibeSelector'
import PlatformPicker from './components/PlatformPicker'
import ProgressTracker from './components/ProgressTracker'
import VideoPreview from './components/VideoPreview'
import DownloadPanel from './components/DownloadPanel'
import './App.css'

const API = ''  // Vite proxy handles /api -> backend

function App() {
  const [file, setFile] = useState(null)
  const [vibe, setVibe] = useState('')
  const [platform, setPlatform] = useState('general')
  const [jobId, setJobId] = useState(null)
  const [status, setStatus] = useState(null)
  const [error, setError] = useState(null)
  const [polling, setPolling] = useState(false)

  const handleScore = async () => {
    if (!file) return
    setError(null)
    setStatus(null)

    const formData = new FormData()
    formData.append('video', file)
    formData.append('vibe', vibe)
    formData.append('platform', platform)
    formData.append('vocals', 'false')

    try {
      const res = await fetch(`${API}/api/score`, { method: 'POST', body: formData })
      if (!res.ok) {
        const err = await res.json()
        throw new Error(err.detail || 'Upload failed')
      }
      const { job_id } = await res.json()
      setJobId(job_id)
      setPolling(true)
      pollStatus(job_id)
    } catch (e) {
      setError(e.message)
    }
  }

  const pollStatus = async (id) => {
    const poll = async () => {
      try {
        const res = await fetch(`${API}/api/status/${id}`)
        const data = await res.json()
        setStatus(data)
        if (data.stage === 'complete' || data.stage === 'error') {
          setPolling(false)
          if (data.stage === 'error') setError(data.message)
          return
        }
        setTimeout(poll, 2000)
      } catch {
        setTimeout(poll, 3000)
      }
    }
    poll()
  }

  const isComplete = status?.stage === 'complete'
  const isProcessing = polling && !isComplete

  return (
    <div className="app">
      <header className="header">
        <h1 className="logo">sync</h1>
        <p className="tagline">Drop a video. Get a soundtrack. Frame-perfect.</p>
      </header>

      <main className="main">
        {!isProcessing && !isComplete && (
          <div className="setup">
            <VideoUploader file={file} onFileChange={setFile} />
            {file && (
              <>
                <VibeSelector vibe={vibe} onVibeChange={setVibe} />
                <PlatformPicker platform={platform} onPlatformChange={setPlatform} />
                <button className="score-btn" onClick={handleScore}>
                  Score My Video
                </button>
              </>
            )}
            {error && <p className="error">{error}</p>}
          </div>
        )}

        {isProcessing && status && (
          <ProgressTracker status={status} />
        )}

        {isComplete && (
          <div className="results">
            <VideoPreview
              originalUrl={file ? URL.createObjectURL(file) : null}
              scoredUrl={`${API}${status.scored_video_url}`}
            />
            <DownloadPanel
              scoredUrl={`${API}${status.scored_video_url}`}
              musicUrl={`${API}${status.music_only_url}`}
            />
            <button className="score-btn reset-btn" onClick={() => {
              setFile(null)
              setJobId(null)
              setStatus(null)
              setError(null)
            }}>
              Score Another Video
            </button>
          </div>
        )}
      </main>
    </div>
  )
}

export default App
