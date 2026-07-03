import { useEffect, useRef } from 'react'
import type { ChatMessage } from '../types'
import { Message } from './Message'

interface ChatWindowProps {
  messages: ChatMessage[]
  isSending: boolean
}

export function ChatWindow({ messages, isSending }: ChatWindowProps) {
  const bottomRef = useRef<HTMLDivElement | null>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isSending])

  return (
    <div className="flex min-h-0 flex-1 flex-col overflow-hidden rounded-2xl border border-white/10 bg-[#0f1016]">
      <div className="border-b border-white/10 px-4 py-3 text-left">
        <h2 className="text-sm font-semibold text-white">Conversation</h2>
        <p className="text-xs text-slate-400">Chat, memory retrieval, and desktop actions</p>
      </div>

      <div className="flex-1 space-y-4 overflow-y-auto px-4 py-4">
        {messages.length === 0 ? (
          <div className="flex h-full items-center justify-center px-6 text-center">
            <div>
              <p className="text-lg font-medium text-white">JaneAI is ready</p>
              <p className="mt-2 text-sm text-slate-400">
                Ask a question, request a memory lookup, or tell Jane to inspect your screen.
              </p>
            </div>
          </div>
        ) : (
          messages.map((message) => <Message key={message.id} message={message} />)
        )}

        {isSending ? (
          <div className="flex justify-start">
            <div className="rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-sm text-slate-300">
              Jane is thinking...
            </div>
          </div>
        ) : null}

        <div ref={bottomRef} />
      </div>
    </div>
  )
}
