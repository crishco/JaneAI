import axios, { AxiosError } from 'axios'
import type {
  ChatResponse,
  StatusResponse,
  VoiceTranscriptionResponse,
} from '../types'

const DEFAULT_BACKEND = 'http://127.0.0.1:8765'

function resolveBaseUrl(): string {
  if (import.meta.env.VITE_API_URL) {
    return import.meta.env.VITE_API_URL
  }
  if (window.janeAPI?.backendUrl) {
    return window.janeAPI.backendUrl
  }
  if (import.meta.env.DEV) {
    return '/api'
  }
  return DEFAULT_BACKEND
}

export const api = axios.create({
  baseURL: resolveBaseUrl(),
  timeout: 120_000,
})

function extractErrorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const axiosError = error as AxiosError<{ detail?: string | { msg?: string }[] }>
    const detail = axiosError.response?.data?.detail
    if (typeof detail === 'string') {
      return detail
    }
    if (Array.isArray(detail) && detail.length > 0) {
      return detail.map((item) => item.msg ?? 'Request failed').join(', ')
    }
    if (axiosError.code === 'ECONNABORTED') {
      return 'Request timed out. The model may still be loading.'
    }
    if (!axiosError.response) {
      return `Cannot reach JaneAI backend at ${resolveBaseUrl()}. Is it running?`
    }
    return axiosError.message
  }
  if (error instanceof Error) {
    return error.message
  }
  return 'An unexpected error occurred'
}

export async function sendChatMessage(
  message: string,
  conversationId?: string | null,
): Promise<ChatResponse> {
  try {
    const { data } = await api.post<ChatResponse>('/chat', {
      message,
      conversation_id: conversationId,
    })
    return data
  } catch (error) {
    throw new Error(extractErrorMessage(error))
  }
}

export async function fetchStatus(): Promise<StatusResponse> {
  try {
    const { data } = await api.get<StatusResponse>('/status')
    return data
  } catch (error) {
    throw new Error(extractErrorMessage(error))
  }
}

export async function transcribeAudio(blob: Blob, filename = 'recording.webm'): Promise<string> {
  const formData = new FormData()
  formData.append('audio', blob, filename)

  try {
    const { data } = await api.post<VoiceTranscriptionResponse>('/voice/transcribe', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    return data.text
  } catch (error) {
    throw new Error(extractErrorMessage(error))
  }
}

export async function synthesizeSpeech(text: string): Promise<Blob> {
  try {
    const { data } = await api.post<ArrayBuffer>(
      '/voice/speak',
      { text },
      { responseType: 'arraybuffer' },
    )
    return new Blob([data], { type: 'audio/wav' })
  } catch (error) {
    throw new Error(extractErrorMessage(error))
  }
}

export async function checkBackendHealth(): Promise<boolean> {
  try {
    const { data } = await api.get<{ status: string }>('/health')
    return data.status === 'healthy' || data.status === 'degraded'
  } catch {
    return false
  }
}
