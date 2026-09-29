import React, { useCallback, useEffect, useState } from 'react';
import { AlertTriangle, Database, HardDrive, RefreshCw } from 'lucide-react';
import { getUsage, type UsageMeter, type UsageRes } from '../utils/api';
import { isCompressionEnabled, setCompressionEnabled } from '../utils/imageUpload';

const formatMB = (bytes: number) => `${(bytes / (1024 * 1024)).toFixed(bytes < 100 * 1024 * 1024 ? 1 : 0)} MB`;

function useUsage() {
  const [usage, setUsage] = useState<UsageRes | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setUsage(await getUsage());
    } catch (e: any) {
      setError(e?.message || 'Failed to load usage');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { void refresh(); }, [refresh]);
  return { usage, loading, error, refresh };
}

/** Home-page warning, rendered only once database or storage passes the warn threshold. */
export const UsageBanner: React.FC = () => {
  const { usage } = useUsage();
  if (usage?.restricted) {
    return (
      <div className="rounded-xl border px-4 py-3 flex items-start gap-3 bg-red-50 border-red-200 text-red-800">
        <AlertTriangle className="w-5 h-5 flex-shrink-0 mt-0.5" />
        <div className="text-sm">
          <p className="font-semibold">Supabase project restricted</p>
          <p className="mt-0.5">{usage.message}</p>
        </div>
      </div>
    );
  }
  if (!usage?.available || !usage.database || !usage.storage) return null;

  const warnAt = usage.warn_percent ?? 80;
  const full = [
    { label: 'Database', meter: usage.database },
    { label: 'Image storage', meter: usage.storage },
  ].filter(x => x.meter.percent >= warnAt);
  if (full.length === 0) return null;

  const critical = full.some(x => x.meter.percent >= 95);
  return (
    <div className={`rounded-xl border px-4 py-3 flex items-start gap-3 ${
      critical ? 'bg-red-50 border-red-200 text-red-800' : 'bg-amber-50 border-amber-200 text-amber-800'
    }`}>
      <AlertTriangle className="w-5 h-5 flex-shrink-0 mt-0.5" />
      <div className="text-sm">
        <p className="font-semibold">Running low on free Supabase space</p>
        <p className="mt-0.5">
          {full.map(x => `${x.label} is ${Math.round(x.meter.percent)}% full (${formatMB(x.meter.used_bytes)} of ${formatMB(x.meter.limit_bytes)})`).join('. ')}.
          {' '}Delete old assessments you no longer need to free up space. Going over a limit can get the whole project restricted.
        </p>
      </div>
    </div>
  );
};

const MeterBar: React.FC<{ icon: React.ReactNode; label: string; meter: UsageMeter; warnAt: number; extra?: string }> = ({ icon, label, meter, warnAt, extra }) => {
  const pct = Math.min(100, meter.percent);
  const color = meter.percent >= 95 ? 'bg-red-500' : meter.percent >= warnAt ? 'bg-amber-500' : 'bg-blue-500';
  return (
    <div>
      <div className="flex items-center justify-between text-sm mb-1">
        <span className="flex items-center gap-2 font-medium text-slate-700">{icon}{label}</span>
        <span className="text-slate-600">
          {formatMB(meter.used_bytes)} of {formatMB(meter.limit_bytes)} ({meter.percent.toFixed(1)}%)
        </span>
      </div>
      <div className="h-2.5 rounded-full bg-slate-100 overflow-hidden">
        <div className={`h-full ${color} transition-all`} style={{ width: `${pct}%` }} />
      </div>
      {extra && <p className="text-xs text-slate-500 mt-1">{extra}</p>}
    </div>
  );
};

/** Settings-page panel: usage meters plus the upload compression toggle. */
export const UsagePanel: React.FC = () => {
  const { usage, loading, error, refresh } = useUsage();
  const [compress, setCompress] = useState(isCompressionEnabled);
  const warnAt = usage?.warn_percent ?? 80;

  return (
    <div className="space-y-6">
      <div className="bg-white rounded-lg border border-slate-200 p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold">Supabase Usage</h3>
          <button
            onClick={() => void refresh()}
            disabled={loading}
            className="px-3 py-1.5 text-sm bg-slate-100 hover:bg-slate-200 rounded-md flex items-center gap-2 disabled:opacity-50"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </button>
        </div>

        {error && <p className="text-sm text-red-600">{error}</p>}
        {usage && !usage.available && <p className="text-sm text-amber-700">{usage.message}</p>}
        {usage?.available && usage.database && usage.storage && (
          <div className="space-y-5">
            <MeterBar icon={<Database className="w-4 h-4" />} label="Database" meter={usage.database} warnAt={warnAt} />
            <MeterBar
              icon={<HardDrive className="w-4 h-4" />}
              label="Image storage"
              meter={usage.storage}
              warnAt={warnAt}
              extra={`${usage.storage.objects.toLocaleString()} files`}
            />
            <p className="text-xs text-slate-500">
              A warning appears on the dashboard at {warnAt}%. Monthly data transfer (egress) isn't shown here;
              check it on the Supabase dashboard's Usage page.
            </p>
          </div>
        )}
      </div>

      <div className="bg-white rounded-lg border border-slate-200 p-6">
        <h3 className="text-lg font-semibold mb-2">Image Uploads</h3>
        <label className="flex items-start gap-3 cursor-pointer">
          <input
            type="checkbox"
            className="mt-1"
            checked={compress}
            onChange={e => { setCompress(e.target.checked); setCompressionEnabled(e.target.checked); }}
          />
          <span className="text-sm text-slate-700">
            <span className="font-medium">Compress images before upload</span>
            <span className="block text-slate-500 mt-0.5">
              Large images are resized to 2000px on the long side and saved as JPEG, typically cutting them to a
              third of their size. Text stays readable, but turn this off if you need models graded on the exact
              original files.
            </span>
          </span>
        </label>
      </div>
    </div>
  );
};
