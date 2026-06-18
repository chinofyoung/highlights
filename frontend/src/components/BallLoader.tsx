export function BallLoader() {
  return (
    <div className="flex justify-center py-2 overflow-x-hidden">
      <div className="relative w-56 h-10" aria-hidden="true">
        {/* ground shadow */}
        <div className="ball-rally-shadow absolute bottom-0 left-0 w-10 h-10" />
        {/* ball */}
        <div className="ball-rally absolute bottom-0 left-0 h-10 w-10 rounded-full bg-[var(--accent)]" />
      </div>
    </div>
  );
}
