export interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  createdAt: string
}

export interface ChatResponse {
  response: string
  conversation_id: string
}

export interface StatusResponse {
  status: string
  detail: string
  errors: string[]
  updated_at: string
  backend_healthy: boolean
}

export interface VoiceTranscriptionResponse {
  text: string
}

declare global {
  interface Window {
    janeAPI?: {
      backendUrl: string
      platform: string
    }
  }
}

export {}
