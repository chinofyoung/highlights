export function BallLoader() {
  return (
    <div className="flex justify-center py-2 overflow-x-hidden">
      <div className="relative w-56 h-12" aria-hidden="true">
        {/* ground shadow */}
        <div className="ball-rally-shadow absolute bottom-0 left-0 w-6 h-6" />
        {/* ball */}
        <div className="ball-rally absolute bottom-0 left-0 h-6 w-6 rounded-full bg-[var(--accent)]" />
      </div>
    </div>
  );
}
