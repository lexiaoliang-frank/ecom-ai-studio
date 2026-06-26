import { useState, useCallback, useEffect, useRef } from 'react'
import { useAuth } from '../App'

interface GenerationResult {
  task_id: string
  status: string
  progress: number
  result_urls: string[]
  error_message?: string
}

export default function DashboardPage() {
  const { auth, logout } = useAuth()

  // Generation state
  const [requirement, setRequirement] = useState('')
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [previewUrl, setPreviewUrl] = useState<string | null>(null)
  const [generating, setGenerating] = useState(false)
  const [taskId, setTaskId] = useState<string | null>(null)
  const [result, setResult] = useState<GenerationResult | null>(null)
  const [error, setError] = useState<string | null>(null)
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)

  // History
  const [history, setHistory] = useState<Array<{
    requirement: string
    taskId: string
    urls: string[]
    timestamp: number
  }>>([])

  const handleFileChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) {
      setSelectedFile(file)
      const url = URL.createObjectURL(file)
      setPreviewUrl(url)
    }
  }, [])

  const handleGenerate = useCallback(async () => {
    if (!requirement.trim()) return
    setError(null)
    setResult(null)
    setGenerating(true)

    try {
      const token = auth.token
      const res = await fetch('/api/v1/generate/image', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({
          requirement: requirement,
          style: 'lifestyle',
          aspect_ratio: '1:1',
          quality: 'standard',
        }),
      })

      if (!res.ok) {
        throw new Error('Failed to submit generation task')
      }

      const data = await res.json()
      setTaskId(data.task_id)

      // Start polling
      pollRef.current = setInterval(async () => {
        try {
          const statusRes = await fetch(`/api/v1/generate/tasks/${data.task_id}`, {
            headers: { 'Authorization': `Bearer ${token}` },
          })

          if (!statusRes.ok) return

          const statusData: GenerationResult = await statusRes.json()
          setResult(statusData)

          if (statusData.status === 'completed' || statusData.status === 'failed') {
            if (pollRef.current) {
              clearInterval(pollRef.current)
              pollRef.current = null
            }
            setGenerating(false)

            // Add to history
            if (statusData.status === 'completed' && statusData.result_urls.length > 0) {
              setHistory(prev => [{
                requirement,
                taskId: data.task_id,
                urls: statusData.result_urls,
                timestamp: Date.now(),
              }, ...prev].slice(0, 20))
            }
          }
        } catch {
          // Ignore polling errors
        }
      }, 2000)

    } catch (err) {
      setError(err instanceof Error ? err.message : 'Generation failed')
      setGenerating(false)
    }
  }, [requirement, auth.token])

  // Cleanup polling on unmount
  useEffect(() => {
    return () => {
      if (pollRef.current) clearInterval(pollRef.current)
    }
  }, [])

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b shadow-sm">
        <div className="max-w-5xl mx-auto px-6 py-4 flex items-center justify-between">
          <h1 className="text-xl font-bold text-gray-900">E-Commerce AI Studio</h1>
          <div className="flex items-center gap-4">
            <span className="text-sm text-gray-600">{auth.user?.email}</span>
            <button
              onClick={logout}
              className="text-sm text-gray-500 hover:text-gray-700"
            >
              Sign Out
            </button>
          </div>
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-6 py-8">
        {/* Generation Panel */}
        <div className="bg-white rounded-xl shadow-sm border p-6 mb-8">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Generate Product Image</h2>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Upload Area */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Upload Product Photo
              </label>
              <div className="border-2 border-dashed border-gray-300 rounded-xl p-6 text-center hover:border-primary-400 transition-colors">
                {previewUrl ? (
                  <div className="relative">
                    <img
                      src={previewUrl}
                      alt="Preview"
                      className="max-h-64 mx-auto rounded-lg object-contain"
                    />
                    <button
                      onClick={() => { setSelectedFile(null); setPreviewUrl(null) }}
                      className="absolute top-2 right-2 bg-white rounded-full p-1 shadow text-xs"
                    >
                      ✕
                    </button>
                  </div>
                ) : (
                  <>
                    <input
                      type="file"
                      accept="image/*"
                      onChange={handleFileChange}
                      className="hidden"
                      id="file-upload"
                    />
                    <label
                      htmlFor="file-upload"
                      className="cursor-pointer inline-flex flex-col items-center gap-2"
                    >
                      <div className="w-12 h-12 rounded-full bg-primary-50 flex items-center justify-center">
                        <svg className="w-6 h-6 text-primary-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                        </svg>
                      </div>
                      <span className="text-sm text-gray-500">Click to upload product photo</span>
                      <span className="text-xs text-gray-400">PNG, JPG up to 20MB</span>
                    </label>
                  </>
                )}
              </div>
            </div>

            {/* Requirement Input */}
            <div className="flex flex-col">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Describe Your Vision
              </label>
              <textarea
                value={requirement}
                onChange={(e) => setRequirement(e.target.value)}
                placeholder={"e.g. Put this white sneaker on a sunny beach with waves in the background, natural lighting, lifestyle style"}
                rows={4}
                className="flex-1 px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 resize-none text-sm"
              />
              <div className="mt-3 flex items-center justify-between">
                <span className="text-xs text-gray-400">
                  {selectedFile ? '1 image selected' : 'Upload a product photo first'}
                </span>
                <button
                  onClick={handleGenerate}
                  disabled={generating || !requirement.trim()}
                  className="px-6 py-2.5 bg-primary-600 text-white rounded-lg font-medium text-sm hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  {generating ? (
                    <span className="flex items-center gap-2">
                      <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                      Generating...
                    </span>
                  ) : (
                    'Generate'
                  )}
                </button>
              </div>
            </div>
          </div>

          {/* Progress & Results */}
          {result && (
            <div className="mt-6 pt-6 border-t">
              <h3 className="text-sm font-medium text-gray-700 mb-3">
                Status: <span className="capitalize text-primary-600">{result.status}</span>
              </h3>

              {result.status === 'running' && (
                <div className="w-full bg-gray-200 rounded-full h-2 mb-4">
                  <div
                    className="bg-primary-600 h-2 rounded-full transition-all duration-500"
                    style={{ width: `${Math.max(result.progress * 100, 10)}%` }}
                  />
                </div>
              )}

              {result.result_urls.length > 0 && (
                <div className="grid grid-cols-2 gap-4">
                  {result.result_urls.map((url, i) => (
                    <img
                      key={i}
                      src={url}
                      alt={`Generated ${i + 1}`}
                      className="rounded-lg shadow-md object-cover w-full aspect-square"
                    />
                  ))}
                </div>
              )}

              {result.error_message && (
                <p className="text-red-600 text-sm">{result.error_message}</p>
              )}
            </div>
          )}

          {error && (
            <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
              {error}
            </div>
          )}
        </div>

        {/* History */}
        {history.length > 0 && (
          <div className="bg-white rounded-xl shadow-sm border p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Generation History</h2>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              {history.map((item, i) => (
                <div key={i} className="group relative">
                  {item.urls[0] && (
                    <img
                      src={item.urls[0]}
                      alt={item.requirement}
                      className="rounded-lg shadow-sm object-cover w-full aspect-square"
                    />
                  )}
                  <div className="absolute inset-0 bg-black/50 opacity-0 group-hover:opacity-100 transition-opacity rounded-lg flex items-center justify-center p-2">
                    <p className="text-white text-xs line-clamp-3">{item.requirement}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </main>
    </div>
  )
}
