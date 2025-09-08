#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import base64
import glob
import json
import os
import random
import signal
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import requests


API_BASE = "https://api.github.com"


class GracefulKiller:
    def __init__(self):
        self.kill_now = False
        try:
            signal.signal(signal.SIGINT, self.exit_gracefully)
            signal.signal(signal.SIGTERM, self.exit_gracefully)
        except Exception:
            pass

    def exit_gracefully(self, *_):
        self.kill_now = True


def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)


def github_request(
    method: str,
    url: str,
    token: str,
    json_body: Optional[dict] = None,
    extra_headers: Optional[dict] = None,
    expected: Optional[List[int]] = None,
    max_retries: int = 3,
    backoff_sec: float = 2.0,
):
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "User-Agent": "csv-batch-uploader/1.0",
    }
    if extra_headers:
        headers.update(extra_headers)

    for attempt in range(1, max_retries + 1):
        resp = requests.request(method, url, headers=headers, json=json_body)
        rl_rem = resp.headers.get("X-RateLimit-Remaining")
        rl_reset = resp.headers.get("X-RateLimit-Reset")

        if resp.status_code == 403 and rl_rem is not None and rl_reset is not None:
            # Hit rate limit; wait until reset
            try:
                remaining = int(rl_rem)
                reset_at = int(rl_reset)
            except Exception:
                remaining, reset_at = 0, int(time.time()) + 60
            if remaining == 0:
                wait = max(0, reset_at - int(time.time()) + 5)
                eprint(f"[RateLimit] Waiting {wait}s until reset...")
                time.sleep(wait)
                continue

        if expected is None:
            expected = [200, 201]

        if resp.status_code in expected:
            if resp.text:
                try:
                    return resp.json(), resp
                except ValueError:
                    return resp.text, resp
            return None, resp

        # Retry on 5xx
        if 500 <= resp.status_code < 600 and attempt < max_retries:
            eprint(f"[Retryable] {method} {url} => {resp.status_code}, retrying in {backoff_sec}s...")
            time.sleep(backoff_sec)
            backoff_sec *= 2
            continue

        # Give up
        try:
            err = resp.json()
        except ValueError:
            err = resp.text
        raise RuntimeError(f"GitHub API error {resp.status_code} for {method} {url}: {err}")


def get_repo(token: str, owner: str, repo: str) -> dict:
    url = f"{API_BASE}/repos/{owner}/{repo}"
    data, _ = github_request("GET", url, token)
    return data


def get_branch_head(token: str, owner: str, repo: str, branch: str) -> Tuple[str, str]:
    # returns (ref, commit_sha)
    url = f"{API_BASE}/repos/{owner}/{repo}/git/ref/heads/{branch}"
    data, _ = github_request("GET", url, token, expected=[200])
    return data["ref"], data["object"]["sha"]


def create_blob(token: str, owner: str, repo: str, content_bytes: bytes) -> str:
    b64 = base64.b64encode(content_bytes).decode("ascii")
    url = f"{API_BASE}/repos/{owner}/{repo}/git/blobs"
    body = {"content": b64, "encoding": "base64"}
    data, _ = github_request("POST", url, token, json_body=body, expected=[201])
    return data["sha"]


def create_tree(
    token: str,
    owner: str,
    repo: str,
    base_tree_sha: str,
    tree_entries: List[dict],
) -> str:
    url = f"{API_BASE}/repos/{owner}/{repo}/git/trees"
    body = {"base_tree": base_tree_sha, "tree": tree_entries}
    data, _ = github_request("POST", url, token, json_body=body, expected=[201])
    return data["sha"]


def create_commit(
    token: str,
    owner: str,
    repo: str,
    message: str,
    tree_sha: str,
    parents: List[str],
) -> str:
    url = f"{API_BASE}/repos/{owner}/{repo}/git/commits"
    body = {"message": message, "tree": tree_sha, "parents": parents}
    data, _ = github_request("POST", url, token, json_body=body, expected=[201])
    return data["sha"]


def update_ref(
    token: str,
    owner: str,
    repo: str,
    branch: str,
    commit_sha: str,
    force: bool = False,
):
    url = f"{API_BASE}/repos/{owner}/{repo}/git/refs/heads/{branch}"
    body = {"sha": commit_sha, "force": force}
    _, _ = github_request("PATCH", url, token, json_body=body, expected=[200])


def load_state(path: Path) -> Dict:
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"uploaded": [], "batch_index": 0}


def save_state(path: Path, state: Dict):
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


def chunked(lst: List[str], size: int) -> List[List[str]]:
    return [lst[i : i + size] for i in range(0, len(lst), size)]


def relative_to_dir(files: List[Path], base: Path) -> List[str]:
    out = []
    for f in files:
        try:
            out.append(str(f.relative_to(base)))
        except Exception:
            out.append(f.name)
    return out


def build_tree_entries_for_batch(
    token: str,
    owner: str,
    repo: str,
    batch_files: List[Path],
    source_dir: Path,
    dest_dir_in_repo: str,
) -> Tuple[List[dict], List[str]]:
    entries = []
    dest_paths = []
    for f in batch_files:
        content = f.read_bytes()
        blob_sha = create_blob(token, owner, repo, content)
        rel = f.relative_to(source_dir)
        # Preserve subdirectory structure under dest_dir_in_repo
        dest_path = str(Path(dest_dir_in_repo) / rel)
        entries.append(
            {
                "path": dest_path.replace("\\", "/"),
                "mode": "100644",
                "type": "blob",
                "sha": blob_sha,
            }
        )
        dest_paths.append(dest_path.replace("\\", "/"))
    return entries, dest_paths


def parse_args():
    p = argparse.ArgumentParser(description="Batch upload CSV files to GitHub repository at a fixed interval.")
    p.add_argument("--repo", required=True, help="Target repository in form owner/repo")
    p.add_argument("--source-dir", required=True, help="Directory containing small CSV chunks")
    p.add_argument("--dest-dir", default="incoming", help="Destination directory in the repository")
    p.add_argument("--branch", default="main", help="Target branch (default: main)")
    p.add_argument("--batch-size", type=int, default=50, help="Files per batch (default: 50)")
    p.add_argument("--interval-seconds", type=int, default=180, help="Interval between batches in seconds (default: 180)")
    p.add_argument("--include-pattern", default="**/*.csv", help="Glob pattern relative to source-dir (default: **/*.csv)")
    p.add_argument("--shuffle", action="store_true", help="Shuffle file order before batching")
    p.add_argument("--dry-run", action="store_true", help="Do not upload, only print plan")
    p.add_argument("--state-file", default=".upload_state.json", help="Path to state file (default: .upload_state.json)")
    return p.parse_args()


def main():
    args = parse_args()

    token = os.getenv("GITHUB_TOKEN")
    if not token:
        eprint("ERROR: Please set environment variable GITHUB_TOKEN with 'repo' scope.")
        sys.exit(1)

    try:
        owner, repo = args.repo.split("/", 1)
    except ValueError:
        eprint("ERROR: --repo must be in the form owner/repo, e.g., fgm0020/AI_for_Science_paper_collection")
        sys.exit(1)

    source_dir = Path(args.source_dir).resolve()
    if not source_dir.exists():
        eprint(f"ERROR: Source directory not found: {source_dir}")
        sys.exit(1)

    # Collect candidate files
    all_paths = sorted(Path(source_dir).glob(args.include_pattern))
    all_paths = [p for p in all_paths if p.is_file()]
    if not all_paths:
        eprint(f"ERROR: No files matched pattern {args.include_pattern} under {source_dir}")
        sys.exit(1)

    if args.shuffle:
        random.shuffle(all_paths)

    # State
    state_path = Path(args.state_file).resolve()
    state = load_state(state_path)
    uploaded_rel = set(state.get("uploaded", []))
    batch_index = int(state.get("batch_index", 0))

    # Filter out already uploaded by local state
    remaining_files = [p for p in all_paths if str(p.relative_to(source_dir)) not in uploaded_rel]

    if not remaining_files:
        print("All files already uploaded according to local state.")
        sys.exit(0)

    # Preflight GitHub
    repo_info = get_repo(token, owner, repo)
    default_branch = repo_info.get("default_branch", "main")
    branch = args.branch or default_branch
    _, head_commit_sha = get_branch_head(token, owner, repo, branch)
    base_tree_sha = repo_info.get("pushed_at")  # Not used; we will start from head commit tree
    # Fetch head commit to get its tree
    head_commit_url = f"{API_BASE}/repos/{owner}/{repo}/git/commits/{head_commit_sha}"
    head_commit, _ = github_request("GET", head_commit_url, token, expected=[200])
    base_tree_sha = head_commit["tree"]["sha"]

    # Plan batches
    batches = chunked(remaining_files, args.batch_size)
    print(f"Planned {len(batches)} batch(es), total files to upload: {len(remaining_files)}")
    killer = GracefulKiller()

    for i, batch_files in enumerate(batches, start=1):
        if killer.kill_now:
            eprint("Interrupted. Saving state and exiting...")
            break

        current_batch_num = batch_index + i
        rel_names = relative_to_dir(batch_files, source_dir)

        print(f"\n=== Batch #{current_batch_num} ===")
        for name in rel_names:
            print(f"  - {name}")

        if args.dry_run:
            continue

        # Re-fetch head commit and tree each batch to avoid conflicts
        _, head_commit_sha = get_branch_head(token, owner, repo, branch)
        head_commit, _ = github_request("GET", f"{API_BASE}/repos/{owner}/{repo}/git/commits/{head_commit_sha}", token)
        base_tree_sha = head_commit["tree"]["sha"]

        # Build tree entries for this batch
        tree_entries, dest_paths = build_tree_entries_for_batch(
            token, owner, repo, batch_files, source_dir, args.dest_dir
        )

        # Create new tree
        new_tree_sha = create_tree(token, owner, repo, base_tree_sha, tree_entries)

        # Commit message
        msg_title = f"AI4S CSV batch #{current_batch_num} ({len(batch_files)} files) to {args.dest_dir}"
        msg_body = "\n".join([f"- {p}" for p in dest_paths])
        commit_message = f"{msg_title}\n\n{msg_body}"

        # Create commit
        new_commit_sha = create_commit(token, owner, repo, commit_message, new_tree_sha, [head_commit_sha])

        # Update ref
        update_ref(token, owner, repo, branch, new_commit_sha, force=False)

        # Update local state
        uploaded_rel.update(rel_names)
        state["uploaded"] = sorted(list(uploaded_rel))
        state["batch_index"] = current_batch_num
        save_state(state_path, state)
        print(f"Committed batch #{current_batch_num} with {len(batch_files)} files.")

        # Sleep between batches if not last
        if i < len(batches):
            sleep_sec = int(args.interval_seconds)
            print(f"Sleeping {sleep_sec} seconds before next batch...")
            for sec in range(sleep_sec, 0, -1):
                if killer.kill_now:
                    eprint("Interrupted during sleep. Saving state and exiting...")
                    break
                time.sleep(1)
            if killer.kill_now:
                break

    print("\nDone.")


if __name__ == "__main__":
    main()