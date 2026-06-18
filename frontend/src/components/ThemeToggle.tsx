import { Moon, Sun } from "lucide-react";
import { useEffect, useState } from "react";

export function ThemeToggle() {
  const [dark, setDark] = useState(true);
  useEffect(() => {
    document.documentElement.classList.toggle("dark", dark);
  }, [dark]);
  return (
    <button
      onClick={() => setDark((d) => !d)}
      aria-label="Toggle theme"
      className="rounded p-2 text-[var(--muted)] transition-colors duration-150
                 hover:bg-[var(--surface)] hover:text-[var(--ink)]
                 focus-visible:outline-2 focus-visible:outline-[var(--teal)] focus-visible:outline-offset-2"
    >
      {dark ? <Sun className="h-5 w-5" /> : <Moon className="h-5 w-5" />}
    </button>
  );
}
