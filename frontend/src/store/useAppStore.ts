import { create } from 'zustand'
import type { ChatMessage } from '../types'

interface AppState {
  conversationId: string | null
  messages: ChatMessage[]
  status: string
  statusDetail: string
  errors: string[]
  isSending: boolean
  isListening: boolean
  backendHealthy: boolean
  setConversationId: (id: string | null) => void
  addMessage: (message: ChatMessage) => void
  setStatus: (status: string, detail?: string) => void
  setErrors: (errors: string[]) => void
  setIsSending: (value: boolean) => void
  setIsListening: (value: boolean) => void
  setBackendHealthy: (value: boolean) => void
  clearMessages: () => void
}

export const useAppStore = create<AppState>((set) => ({
  conversationId: null,
  messages: [],
  status: 'Connecting',
  statusDetail: 'Waiting for backend',
  errors: [],
  isSending: false,
  isListening: false,
  backendHealthy: false,
  setConversationId: (conversationId) => set({ conversationId }),
  addMessage: (message) =>
    set((state) => ({
      messages: [...state.messages, message],
    })),
  setStatus: (status, statusDetail = '') => set({ status, statusDetail }),
  setErrors: (errors) => set({ errors }),
  setIsSending: (isSending) => set({ isSending }),
  setIsListening: (isListening) => set({ isListening }),
  setBackendHealthy: (backendHealthy) => set({ backendHealthy }),
  clearMessages: () => set({ messages: [], conversationId: null }),
}))
