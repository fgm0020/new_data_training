#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import csv
import os
import sys
import time
import textwrap
import subprocess
from pathlib import Path
from typing import List, Tuple

DEFAULT_PREFIX = """\
You are assisting in curating AI-for-Science (AI4S) papers from three top conferences.
Goal:
- Given multiple CSV snippets (file name, header row, and a few sample rows),
  identify entries that are AI4S-related from the specified venues.
- Standardize and deduplicate entries across files (same title+authors => one record).
- Output only the final aggregated table in CSV format.

Constraints and instructions:
- Conferences of interest (exact match in venue or inferred from context): NeurIPS, ICLR, ICML.
- Treat variations like "NeurIPS 2024" or "Neural Information Processing Systems (NeurIPS)" as NeurIPS.
- If the venue is unknown in the snippet, infer when reasonable from title/venue columns if present.
- Remove duplicate rows across all snippets using a normalized key: lowercased title stripped of punctuation + first author lowercased.
- If fields are missing in samples, leave empty.
- Final output format (CSV header, in this exact order):
  title,authors,year,venue,track,keywords,doi,url,notes,file_source
- Only output the CSV (no explanations, no code fences around the final CSV). If unsure, still output best-effort CSV rows.

Now I will provide multiple CSV snippets. Each snippet is structured as:
- A heading that indicates the file path.
- A CSV code block with the header row and up to N sample rows.

Please aggregate them following the rules above.
"""

def parse_args():
    p = argparse.ArgumentParser(description="Batch-feed CSV context to Copilot with pacing.")
    p.add_argument("--source-dir", required=True, help="Directory containing small CSV chunk files.")
    p.add_argument("--pattern", default="**/*.csv", help="Glob pattern relative to source-dir (default: **/*.csv)")
    p.add_argument("--out-dir", default="copilot_batches", help="Directory to store generated prompt/response files.")
    p.add_argument("--batch-size", type=int, default=50, help="Max files per batch (default: 50)")
    p.add_argument("--interval-seconds", type=int, default=180, help="Interval between batches in seconds (default: 180)")
    p.add_argument("--rows-per-file", type=int, default=3, help="Sample rows per file to include (default: 3)")
    p.add_argument("--max-prompt-bytes", type=int, default=60000, help="Max prompt size in bytes; script will auto-trim if exceeded.")
    p.add_argument("--shuffle", action="store_true", help="Shuffle file order before batching.")
    p.add_argument("--prompt-prefix-file", default="", help="Path to a custom prompt prefix (Markdown).")
    p.add_argument("--use-cli", action="store_true", help="Try to send each prompt to Copilot chat in the terminal and save the response.")
    p.add_argument("--dry-run", action="store_true", help="Only generate prompt files; do not send to Copilot.")
    p.add_argument("--state-file", default=".copilot_feed_state.json", help="State file for resumable progress.")
    return p.parse_args()

def read_prefix(prefix_path: str) -> str:
    if prefix_path:
        p = Path(prefix_path)
        if p.exists():
            return p.read_text(encoding="utf-8")
        else:
            print(f"[WARN] prompt-prefix-file not found: {p}. Using default prefix.", file=sys.stderr)
    return DEFAULT_PREFIX

def list_csv_files(source_dir: Path, pattern: str, shuffle: bool) -> List[Path]:
    files = sorted(source_dir.glob(pattern))
    files = [p for p in files if p.is_file()]
    if shuffle:
        import random
        random.shuffle(files)
    return files

def read_csv_head(p: Path, rows: int) -> Tuple[List[str], List[List[str]], int]:
    """Read header and up to `rows` rows, plus try to estimate total rows (best-effort)."""
    header = []
    samples: List[List[str]] = []
    total = 0
    try:
        with p.open("r", encoding="utf-8", newline="") as f:
            reader = csv.reader(f)
            for r_idx, row in enumerate(reader):
                if r_idx == 0:
                    header = row
                else:
                    if len(samples) < rows:
                        samples.append(row)
                total += 1
                # If file is huge, we still count total in this pass (linear). Acceptable for small chunks.
    except UnicodeDecodeError:
        # Fallback with latin-1 to avoid crashing
        with p.open("r", encoding="latin-1", newline="") as f:
            reader = csv.reader(f)
            for r_idx, row in enumerate(reader):
                if r_idx == 0:
                    header = row
                else:
                    if len(samples) < rows:
                        samples.append(row)
                total += 1
    except Exception as e:
        # If any error, return minimal info
        header = []
        samples = []
        total = -1
    return header, samples, total

def csv_block(header: List[str], rows: List[List[str]]) -> str:
    def esc(v: str) -> str:
        return v.replace('"', '""')
    parts = []
    if header:
        parts.append(",".join([f'"{esc(x)}"' if ("," in x or '"' in x) else x for x in header]))
    for r in rows:
        parts.append(",".join([f'"{esc(x)}"' if ("," in x or '"' in x) else x for x in r]))
    return "\n".join(parts)

def build_prompt(prefix: str, files: List[Path], source_root: Path, rows_per_file: int, max_bytes: int) -> Tuple[str, int]:
    """Build prompt; if size exceeds max_bytes, progressively reduce rows per file."""
    # Attempt with requested rows_per_file, then with 1, then with 0 (only headers)
    for rpf in [rows_per_file, 1, 0]:
        sections = [prefix.strip(), ""]
        included = 0
        for fp in files:
            header, samples, total = read_csv_head(fp, rpf)
            rel = str(fp.relative_to(source_root))
            meta = f"### File: {rel}\n"
            if total >= 0:
                meta += f"- approx_rows_in_file: {total if total>0 else 0}\n"
            if header:
                meta += f"- columns: {', '.join(header)}\n"
            sections.append(meta)
            body = ""
            if header:
                block = csv_block(header, samples)
                body = f"```csv\n{block}\n```\n"
            else:
                body = "_(Unable to read CSV header; file may be empty or corrupted.)_\n"
            sections.append(body)
            included += 1
        prompt = "\n".join(sections)
        size = len(prompt.encode("utf-8"))
        if size <= max_bytes:
            return prompt, rpf
    # Still too big; truncate hard by cutting tail
    prompt_bytes = prefix.encode("utf-8")
    prompt_trunc = prompt_bytes[: max_bytes]
    return prompt_trunc.decode("utf-8", errors="ignore"), -1

def chunk(lst: List[Path], n: int) -> List[List[Path]]:
    return [lst[i:i+n] for i in range(0, len(lst), n)]

def ensure_dir(p: Path):
    p.mkdir(parents=True, exist_ok=True)

def save_text(p: Path, content: str):
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(content, encoding="utf-8")
    tmp.replace(p)

def try_send_to_cli(prompt_text: str) -> Tuple[int, str, str]:
    """
    Attempt to send prompt to Copilot chat in terminal.
    This uses a best-effort approach:
    1) Try a '-p' style flag if supported (non-interactive).
    2) Fallback: pipe the prompt via stdin to the chat command (may not be supported by all versions).
    Returns (exit_code, stdout, stderr).
    """
    # Approach 1: explicit prompt flag (if supported by your local installation)
    cmd_candidates = [
        # If your local setup supports a non-interactive prompt flag:
        'gh copilot chat -p "$PROMPT_PAYLOAD"',
        # Fallback: try piping stdin into the chat session:
        'printf "%s" "$PROMPT_PAYLOAD" | gh copilot chat',
    ]
    for cmd in cmd_candidates:
        env = os.environ.copy()
        env["PROMPT_PAYLOAD"] = prompt_text
        # Run in a shell to allow quoting
        proc = subprocess.run(cmd, shell=True, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if proc.returncode == 0 and proc.stdout:
            return proc.returncode, proc.stdout.decode("utf-8", errors="ignore"), proc.stderr.decode("utf-8", errors="ignore")
        # If fails, try next candidate
    return 1, "", "Failed to send prompt non-interactively. Please open the prompt file and paste it into Copilot Chat."

def load_state(state_path: Path) -> dict:
    if state_path.exists():
        try:
            import json
            return json.loads(state_path.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"uploaded_rel": [], "batch_index": 0}

def save_state(state_path: Path, state: dict):
    import json
    tmp = state_path.with_suffix(state_path.suffix + ".tmp")
    tmp.write_text(textwrap.dedent(json.dumps(state, ensure_ascii=False, indent=2)), encoding="utf-8")
    tmp.replace(state_path)

def main():
    args = parse_args()
    source_dir = Path(args.source_dir).resolve()
    if not source_dir.exists():
        print(f"[ERROR] source-dir not found: {source_dir}", file=sys.stderr)
        sys.exit(1)

    ensure_dir(Path(args.out_dir))
    state_path = Path(args.state_file).resolve()
    state = load_state(state_path)
    already = set(state.get("uploaded_rel", []))
    batch_index = int(state.get("batch_index", 0))

    files = list_csv_files(source_dir, args.pattern, args.shuffle)
    files = [p for p in files if str(p.relative_to(source_dir)) not in already]
    if not files:
        print("All files already processed according to local state.")
        return

    # Load prefix
    prefix = read_prefix(args.prompt_prefix_file)

    batches = chunk(files, args.batch_size)
    print(f"Planned {len(batches)} batch(es), total files: {len(files)}")

    for i, batch_files in enumerate(batches, start=1):
        current_batch = batch_index + i
        # Build prompt (auto-trim if too large)
        prompt_text, effective_rpf = build_prompt(prefix, batch_files, source_dir, args.rows_per_file, args.max_prompt_bytes)
        prompt_name = f"batch_{current_batch:04d}_prompt.md"
        prompt_path = Path(args.out_dir) / prompt_name
        save_text(prompt_path, prompt_text)
        print(f"[Batch #{current_batch}] Prompt saved: {prompt_path} (rows-per-file used: {effective_rpf if effective_rpf>=0 else 'truncated'})")

        # Optionally send to terminal Copilot
        if args.use_cli and not args.dry_run:
            code, out, err = try_send_to_cli(prompt_text)
            resp_path = Path(args.out_dir) / f"batch_{current_batch:04d}_response.md"
            if out:
                save_text(resp_path, out)
                print(f"[Batch #{current_batch}] Response saved: {resp_path}")
            if code != 0:
                print(f"[Batch #{current_batch}] Send failed: {err.strip()}", file=sys.stderr)
                print("Tip: Open the prompt file and paste it into your Copilot Chat manually.", file=sys.stderr)

        # Update state
        rels = [str(p.relative_to(source_dir)) for p in batch_files]
        already.update(rels)
        state["uploaded_rel"] = sorted(list(already))
        state["batch_index"] = current_batch
        save_state(state_path, state)

        # Sleep between batches (unless it's the last)
        if i < len(batches):
            sleep_sec = int(args.interval_seconds)
            print(f"[Batch #{current_batch}] Sleeping {sleep_sec}s before next batch...")
            try:
                for _ in range(sleep_sec):
                    time.sleep(1)
            except KeyboardInterrupt:
                print("\nInterrupted by user. Progress saved. Exiting.")
                break

    print("Done.")

if __name__ == "__main__":
    main()