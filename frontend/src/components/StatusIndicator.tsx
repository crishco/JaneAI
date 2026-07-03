import clsx from 'clsx'

interface StatusIndicatorProps {
  status: string
  detail: string
  healthy: boolean
  errors: string[]
}

const STATUS_COLORS: Record<string, string> = {
  Idle: 'bg-emerald-500',
  Thinking: 'bg-amber-400',
  Listening: 'bg-sky-400',
  'Searching memory': 'bg-violet-400',
  'Looking at screen': 'bg-orange-400',
  'Controlling desktop': 'bg-orange-500',
  Error: 'bg-red-500',
  Degraded: 'bg-yellow-500',
  Connecting: 'bg-slate-400',
  Starting: 'bg-slate-400',
}

export function StatusIndicator({ status, detail, healthy, errors }: StatusIndicatorProps) {
  const dotClass = STATUS_COLORS[status] ?? 'bg-slate-400'

  return (
    <div className="rounded-xl border border-white/10 bg-white/5 px-4 py-3">
      <div className="flex items-center gap-3">
        <span className={clsx('h-2.5 w-2.5 rounded-full', dotClass, !healthy && 'animate-pulse')} />
        <div className="min-w-0 text-left">
          <p className="text-sm font-medium text-white">{status}</p>
          {detail ? <p className="truncate text-xs text-slate-300">{detail}</p> : null}
        </div>
      </div>
      {errors.length > 0 ? (
        <div className="mt-3 space-y-1 text-left">
          {errors.slice(-3).map((error) => (
            <p key={error} className="text-xs text-red-300">
              {error}
            </p>
          ))}
        </div>
      ) : null}
    </div>
  )
}
