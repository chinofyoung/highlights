import { useState } from "react";
import { Upload } from "lucide-react";

export function UploadView({ onFile, error }: { onFile: (f: File) => void; error: string | null }) {
  const [dragActive, setDragActive] = useState(false);

  function handleDragOver(e: React.DragEvent<HTMLLabelElement>) {
    e.preventDefault();
    setDragActive(true);
  }

  function handleDragLeave() {
    setDragActive(false);
  }

  function handleDrop(e: React.DragEvent<HTMLLabelElement>) {
    e.preventDefault();
    setDragActive(false);
    const file = e.dataTransfer.files[0];
    if (file) onFile(file);
  }

  return (
    <div className="flex flex-col items-center gap-6 py-8">
      <div className="text-center">
        <h2 className="font-display text-3xl font-extrabold tracking-tight text-[var(--ink)] sm:text-4xl">
          Find the rallies.<br />Skip the standing around.
        </h2>
        <p className="mt-3 text-[var(--muted)] max-w-md mx-auto">
          Drop in a match recorded from one fixed angle. We'll spot every rally
          so you can cut a highlight reel in minutes.
        </p>
      </div>

      <label
        className={[
          "flex w-full max-w-md cursor-pointer flex-col items-center gap-4 rounded-lg",
          "border-2 border-dashed px-10 py-14",
          "transition-colors duration-150",
          "focus-within:outline-2 focus-within:outline-[var(--teal)] focus-within:outline-offset-2",
          dragActive
            ? "border-[var(--teal)] bg-[var(--accent)]/10"
            : "border-[var(--line)] hover:border-[var(--teal)] hover:bg-[var(--teal)]/5",
        ].join(" ")}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
      >
        <Upload className="h-9 w-9 text-[var(--teal)]" />
        <span className="text-base font-medium text-[var(--ink)]">
          Drop a match video or click to choose
        </span>
        <span className="text-sm text-[var(--muted)]">
          MP4, MOV, or any format your browser supports
        </span>
        <input
          type="file"
          accept="video/*"
          className="sr-only"
          onChange={(e) => e.target.files?.[0] && onFile(e.target.files[0])}
        />
      </label>

      {error && (
        <p className="text-sm text-[var(--danger)]">{error}</p>
      )}
    </div>
  );
}
