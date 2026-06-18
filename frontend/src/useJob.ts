import { useEffect, useState } from "react";
import { getJob } from "./api";
import type { JobRecord } from "./types";

const IDLE: JobRecord = { status: "running", progress: 0, result: null, error: null };

export function useJob(jobId: string | null): JobRecord {
  const [rec, setRec] = useState<JobRecord>(IDLE);

  useEffect(() => {
    if (!jobId) { setRec(IDLE); return; }
    setRec(IDLE);
    let active = true;

    const tick = async () => {
      try {
        const next = await getJob(jobId);
        if (!active) return;
        setRec(next);
        if (next.status !== "running") clearInterval(id);
      } catch (e) {
        if (!active) return;
        setRec({ status: "error", progress: 0, result: null, error: String(e) });
        clearInterval(id);
      }
    };

    const id = setInterval(tick, 500);
    tick();
    return () => { active = false; clearInterval(id); };
  }, [jobId]);

  return rec;
}
