import { useCallback, useEffect, useRef } from 'react'
import toast, { Toaster } from 'react-hot-toast'
import { ChatWindow } from './components/ChatWindow'
import { MessageInput } from './components/MessageInput'
import { StatusIndicator } from './components/StatusIndicator'
import {
  checkBackendHealth,
  fetchStatus,
  sendChatMessage,
  synthesizeSpeech,
  transcribeAudio,
} from './services/api'
import { useAppStore } from './store/useAppStore'
import type { ChatMessage } from './types'

function createMessage(role: ChatMessage['role'], content: string): ChatMessage {
  return {
    id: crypto.randomUUID(),
    role,
    content,
    createdAt: new Date().toISOString(),
  }
}

export default function App() {
  const {
    conversationId,
    messages,
    status,
    statusDetail,
    errors,
    isSending,
    isListening,
    backendHealthy,
    addMessage,
    setConversationId,
    setStatus,
    setErrors,
    setIsSending,
    setIsListening,
    setBackendHealthy,
  } = useAppStore()

  const mediaRecorderRef = useRef<MediaRecorder | null>(null)
  const audioChunksRef = useRef<Blob[]>([])

  useEffect(() => {
    let active = true

    async function pollStatus() {
      try {
        const snapshot = await fetchStatus()
        if (!active) {
          return
        }
        setStatus(snapshot.status, snapshot.detail)
        setErrors(snapshot.errors)
        setBackendHealthy(snapshot.backend_healthy)
      } catch (error) {
        if (!active) {
          return
        }
        setBackendHealthy(false)
        setStatus('Error', 'Backend unreachable')
        setErrors([error instanceof Error ? error.message : 'Backend unreachable'])
      }
    }

    void pollStatus()
    const interval = window.setInterval(() => {
      void pollStatus()
    }, 2000)

    return () => {
      active = false
      window.clearInterval(interval)
    }
  }, [setBackendHealthy, setErrors, setStatus])

  useEffect(() => {
    void checkBackendHealth().then(setBackendHealthy)
  }, [setBackendHealthy])

  const handleSend = useCallback(
    async (content: string) => {
      const trimmed = content.trim()
      if (!trimmed || isSending) {
        return
      }

      addMessage(createMessage('user', trimmed))
      setIsSending(true)
      setStatus('Thinking', 'Generating response')

      try {
        const result = await sendChatMessage(trimmed, conversationId)
        setConversationId(result.conversation_id)
        addMessage(createMessage('assistant', result.response))

        try {
          const audioBlob = await synthesizeSpeech(result.response)
          const audioUrl = URL.createObjectURL(audioBlob)
          const audio = new Audio(audioUrl)
          audio.onended = () => URL.revokeObjectURL(audioUrl)
          await audio.play()
        } catch {
          // Piper may be unconfigured; chat still succeeded.
        }
      } catch (error) {
        const message = error instanceof Error ? error.message : 'Failed to send message'
        toast.error(message)
        setStatus('Error', message)
        setErrors([message])
      } finally {
        setIsSending(false)
      }
    },
    [
      addMessage,
      conversationId,
      isSending,
      setConversationId,
      setErrors,
      setIsSending,
      setStatus,
    ],
  )

  const stopRecording = useCallback(async () => {
    const recorder = mediaRecorderRef.current
    if (!recorder) {
      return
    }

    await new Promise<void>((resolve) => {
      recorder.onstop = () => resolve()
      recorder.stop()
    })

    mediaRecorderRef.current = null
    setIsListening(false)
    setStatus('Thinking', 'Transcribing audio')

    const blob = new Blob(audioChunksRef.current, { type: recorder.mimeType || 'audio/webm' })
    audioChunksRef.current = []

    try {
      const text = await transcribeAudio(blob)
      setStatus('Idle', 'Ready')
      await handleSend(text)
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Voice transcription failed'
      toast.error(message)
      setStatus('Error', message)
      setErrors([message])
    }
  }, [handleSend, setErrors, setIsListening, setStatus])

  const startRecording = useCallback(async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      const recorder = new MediaRecorder(stream)
      audioChunksRef.current = []
      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data)
        }
      }
      recorder.onstop = () => {
        stream.getTracks().forEach((track) => track.stop())
      }
      mediaRecorderRef.current = recorder
      recorder.start()
      setIsListening(true)
      setStatus('Listening', 'Recording voice input')
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Microphone access denied'
      toast.error(message)
      setStatus('Error', message)
      setErrors([message])
    }
  }, [setErrors, setIsListening, setStatus])

  const handleToggleVoice = useCallback(async () => {
    if (isListening) {
      await stopRecording()
      return
    }
    await startRecording()
  }, [isListening, startRecording, stopRecording])

  return (
    <div className="flex min-h-screen flex-col bg-[#090a0f] text-white">
      <Toaster position="top-right" toastOptions={{ duration: 5000 }} />

      <header className="border-b border-white/10 px-6 py-5">
        <div className="mx-auto flex max-w-6xl flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <div className="text-left">
            <p className="text-xs uppercase tracking-[0.24em] text-violet-300">JaneAI</p>
            <h1 className="text-2xl font-semibold text-white">Desktop Assistant</h1>
            <p className="mt-1 text-sm text-slate-400">
              Multi-modal agent with memory, voice, and desktop control
            </p>
          </div>
          <div className="w-full max-w-md">
            <StatusIndicator
              status={status}
              detail={statusDetail}
              healthy={backendHealthy}
              errors={errors}
            />
          </div>
        </div>
      </header>

      <main className="mx-auto flex w-full max-w-6xl flex-1 flex-col gap-4 px-6 py-6">
        <ChatWindow messages={messages} isSending={isSending} />
        <MessageInput
          disabled={isSending}
          isListening={isListening}
          onSend={handleSend}
          onToggleVoice={handleToggleVoice}
        />
      </main>
    </div>
  )
}
