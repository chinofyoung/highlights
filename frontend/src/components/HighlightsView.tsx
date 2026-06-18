import { useEffect, useState } from "react";
import { Trash2 } from "lucide-react";
import { listOutput, outputUrl, deleteClip, clearOutput } from "../api";

interface Listing {
  clips: string[];
  stitched: string | null;
}

export function HighlightsView({ videoId }: { videoId: string }) {
  const [listing, setListing] = useState<Listing>({ clips: [], stitched: null });
  const [version, setVersion] = useState(0);
  const [fetchError, setFetchError] = useState<string | null>(null);

  useEffect(() => {
    setFetchError(null);
    listOutput(videoId)
      .then(setListing)
      .catch((e: unknown) => {
        setFetchError(e instanceof Error ? e.message : "Couldn't load highlights.");
      });
  }, [videoId]);

  async function handleDeleteClip(name: string) {
    const updated = await deleteClip(videoId, name);
    setListing(updated);
    setVersion((v) => v + 1);
  }

  async function handleClearAll() {
    const updated = await clearOutput(videoId);
    setListing(updated);
    setVersion((v) => v + 1);
  }

  const isEmpty = listing.clips.length === 0 && listing.stitched === null;

  return (
    <div className="flex flex-col gap-6">
      {fetchError && (
        <p className="text-sm text-[var(--danger)]">{fetchError}</p>
      )}
      <div className="flex items-center justify-between">
        <h2 className="font-display text-xl font-bold tracking-tight text-[var(--ink)]">
          Highlights
        </h2>
        {!isEmpty && (
          <button
            onClick={handleClearAll}
            className="rounded border border-[var(--line)] px-3 py-1.5 text-sm
                       text-[var(--muted)] hover:text-[var(--ink)] hover:border-[var(--ink)]
                       transition-colors"
          >
            Clear all
          </button>
        )}
      </div>

      {isEmpty && (
        <p className="text-sm text-[var(--muted)]">
          No highlights yet — export some rallies.
        </p>
      )}

      {listing.stitched !== null && (
        <div className="flex flex-col gap-2">
          <p className="text-sm font-medium text-[var(--ink)]">Combined reel</p>
          <video
            controls
            src={outputUrl(videoId, "highlights.mp4") + "?v=" + version}
            className="w-full rounded-lg border border-[var(--line)] bg-[var(--surface)]"
          />
        </div>
      )}

      {listing.clips.length > 0 && (
        <div className="flex flex-col gap-3">
          <p className="text-sm font-medium text-[var(--ink)]">
            Clips ({listing.clips.length})
          </p>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            {listing.clips.map((name) => (
              <div
                key={name}
                className="flex flex-col gap-2 rounded-lg border border-[var(--line)]
                           bg-[var(--surface)] p-3"
              >
                <video
                  controls
                  src={outputUrl(videoId, name)}
                  className="w-full rounded border border-[var(--line)]"
                />
                <div className="flex items-center justify-between gap-2">
                  <span className="font-mono text-xs text-[var(--muted)] truncate">
                    {name}
                  </span>
                  <button
                    onClick={() => handleDeleteClip(name)}
                    aria-label={`Delete ${name}`}
                    className="shrink-0 rounded p-1 text-[var(--muted)] hover:text-[var(--danger)]
                               transition-colors focus-visible:outline-2 focus-visible:outline-[var(--teal)]"
                  >
                    <Trash2 size={14} />
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
