# run_nep_scaling.py -- runs the original single-query script once per NEP query, in a fresh process.
import subprocess, sys, time

SCRIPT = "main_cmd.py"                     # ADAPT: your single-query script (the one that reads sys.argv[1])
QIDS = [f"NEP{k}" for k in range(1, 11)]
TIMEOUT = 3600                             # seconds per query

summary = []
for qid in QIDS:
    print(f"=== {qid} ===", flush=True)
    t0 = time.time()
    try:
        p = subprocess.run([sys.executable, SCRIPT, qid],
                           capture_output=True, text=True, timeout=TIMEOUT)
        status = "ok" if p.returncode == 0 else f"exit {p.returncode}"
        out = p.stdout + ("\n--- STDERR ---\n" + p.stderr if p.stderr else "")
    except subprocess.TimeoutExpired as e:
        status, out = "timeout", (e.stdout or b"").decode(errors="ignore") if isinstance(e.stdout, bytes) else (e.stdout or "")
    wall = time.time() - t0
    with open(f"{qid}.log", "w") as f:      # full output, including the PRISM time profile
        f.write(out)
    summary.append((qid, status, wall))
    print(f"{qid}: {status}, {wall:.1f}s (log: {qid}.log)", flush=True)

print("\nqid,status,wall_seconds")
for qid, status, wall in summary:
    print(f"{qid},{status},{wall:.1f}")