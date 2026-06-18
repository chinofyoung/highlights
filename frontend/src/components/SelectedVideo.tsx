import { useEffect, useState } from "react";

export function SelectedVideo({
  file,
  onAnalyze,
  onReset,
  analyzing,
}: {
  file: File;
  onAnalyze: () => void;
  onReset: () => void;
  analyzing: boolean;
}) {
  const [objectUrl, setObjectUrl] = useState<string | null>(null);

  useEffect(() => {
    const url = URL.createObjectURL(file);
    setObjectUrl(url);
    return () => { URL.revokeObjectURL(url); };
  }, [file]);

  const sizeMB = (file.size / (1024 * 1024)).toFixed(1);

  return (
    <div className="flex flex-col items-center gap-6 py-8">
      <div className="text-center">
        <h2 className="font-display text-2xl font-extrabold tracking-tight text-[var(--ink)]">
          Ready to analyze
        </h2>
        <p className="mt-2 font-mono text-sm text-[var(--muted)]">
          {file.name}
          <span className="ml-2 text-[var(--muted)]">· {sizeMB} MB</span>
        </p>
      </div>

      {objectUrl && (
        <video
          controls
          src={objectUrl}
          className="w-full max-w-xl rounded-lg border border-[var(--line)] bg-black"
        />
      )}

      <div className="flex flex-col items-center gap-3 sm:flex-row">
        <button
          onClick={onAnalyze}
          disabled={analyzing}
          className="flex items-center gap-2 rounded bg-[var(--accent)] px-6 py-2.5 text-sm font-semibold
                     text-[var(--accent-ink)] transition-colors duration-150
                     hover:brightness-95
                     disabled:opacity-50 disabled:cursor-not-allowed
                     focus-visible:outline-2 focus-visible:outline-[var(--teal)] focus-visible:outline-offset-2"
        >
          {analyzing ? "Uploading…" : "Analyze video"}
        </button>

        <button
          onClick={onReset}
          disabled={analyzing}
          className="rounded px-4 py-2.5 text-sm font-medium text-[var(--muted)]
                     hover:text-[var(--ink)] transition-colors duration-150
                     disabled:opacity-50 disabled:cursor-not-allowed
                     focus-visible:outline-2 focus-visible:outline-[var(--teal)] focus-visible:outline-offset-2"
        >
          Choose a different video
        </button>
      </div>
    </div>
  );
}
