import { Mic, SendHorizonal } from 'lucide-react'
import { useState } from 'react'
import clsx from 'clsx'

interface MessageInputProps {
  disabled: boolean
  isListening: boolean
  onSend: (message: string) => Promise<void>
  onToggleVoice: () => void
}

export function MessageInput({
  disabled,
  isListening,
  onSend,
  onToggleVoice,
}: MessageInputProps) {
  const [value, setValue] = useState('')

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault()
    const trimmed = value.trim()
    if (!trimmed || disabled) {
      return
    }
    setValue('')
    await onSend(trimmed)
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="flex items-end gap-3 rounded-2xl border border-white/10 bg-[#12131a] p-3"
    >
      <button
        type="button"
        onClick={onToggleVoice}
        disabled={disabled}
        className={clsx(
          'inline-flex h-11 w-11 shrink-0 items-center justify-center rounded-xl transition',
          isListening
            ? 'bg-red-500 text-white animate-pulse'
            : 'bg-white/10 text-white hover:bg-white/15',
          disabled && 'cursor-not-allowed opacity-50',
        )}
        aria-label={isListening ? 'Stop listening' : 'Start voice input'}
      >
        <Mic className="h-5 w-5" />
      </button>

      <textarea
        value={value}
        onChange={(event) => setValue(event.target.value)}
        placeholder="Ask Jane anything..."
        rows={1}
        disabled={disabled}
        className="max-h-40 min-h-[44px] flex-1 resize-none bg-transparent px-1 py-2 text-sm text-white outline-none placeholder:text-slate-500 disabled:opacity-50"
        onKeyDown={(event) => {
          if (event.key === 'Enter' && !event.shiftKey) {
            event.preventDefault()
            void handleSubmit(event)
          }
        }}
      />

      <button
        type="submit"
        disabled={disabled || !value.trim()}
        className="inline-flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-violet-600 text-white transition hover:bg-violet-500 disabled:cursor-not-allowed disabled:opacity-50"
        aria-label="Send message"
      >
        <SendHorizonal className="h-5 w-5" />
      </button>
    </form>
  )
}
