"""
deploy_pro_to_vps.py
====================
UPDATED 2026-03-19 — GitHub Auto-Sync Architecture

The VPS now pulls directly from GitHub (SammySid/cti-suite-final) every 5 minutes
via a systemd timer running /home/ubuntu/cooling-tower_pro/auto_sync.sh.

This script: 
  1. Pushes any uncommitted local changes to GitHub
  2. SSH's into the VPS and immediately triggers the auto_sync.sh
     (so you don't have to wait up to 5 minutes for the timer to fire)

Usage:
    python deploy_pro_to_vps.py

Requirements:
    pip install paramiko
    git must be installed and repo must be configured with push access
"""

import os
import sys
import subprocess
import paramiko

# ── Config ────────────────────────────────────────────────────────────────────

VPS_HOST     = "130.162.191.58"
VPS_USER     = "ubuntu"
VPS_PASSWORD = "Stallion316##"
VPS_SYNC_CMD = "/home/ubuntu/cooling-tower_pro/auto_sync.sh"
BRANCH       = "master"

REPO_ROOT = os.path.dirname(os.path.abspath(__file__))


# ── Helpers ───────────────────────────────────────────────────────────────────

def run_local(cmd: list[str], cwd: str = REPO_ROOT) -> str:
    """Run a local shell command and return stdout. Raises on failure."""
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(
            f"Command failed: {' '.join(cmd)}\n"
            f"stderr: {result.stderr.strip()}"
        )
    return result.stdout.strip()


def preflight_syntax_check() -> bool:
    """
    Scans all .js files in app/web/js and uses node -c to verify syntax.
    Returns True if passed, False if syntax error found.
    """
    print("\n🔬  Running JS Syntax Pre-flight Check...")
    
    js_dir = os.path.join(REPO_ROOT, "cti_dashboard_pro", "app", "web", "js")
    if not os.path.exists(js_dir):
        print("    ⚠️  JS directory not found. Skipping check.")
        return True
        
    try:
        subprocess.run(["node", "--version"], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("    ⚠️  Node.js not found in PATH. Skipping syntax check.")
        return True

    errors_found = False
    files_checked = 0

    for root, _, files in os.walk(js_dir):
        for file in files:
            if file.endswith(".js"):
                file_path = os.path.join(root, file)
                result = subprocess.run(["node", "-c", file_path], capture_output=True, text=True)
                if result.returncode != 0:
                    rel_path = os.path.relpath(file_path, REPO_ROOT)
                    print(f"    ❌ SYNTAX ERROR in {rel_path}")
                    # Extract the first meaningful error line
                    err_lines = [line.strip() for line in result.stderr.split('\n') if line.strip() and not line.startswith('Node.js')]
                    if err_lines:
                        print(f"       {err_lines[0]}")
                    errors_found = True
                files_checked += 1

    if errors_found:
        print("\n🚫 Pre-flight check failed! Deployment aborted.")
        return False
        
    print(f"    ✅ All {files_checked} JS files passed syntax validation.")
    return True


def preflight_mypy_check() -> bool:
    """
    Runs mypy on the backend directory to catch Python type errors before deployment.
    """
    print("\n🔬  Running Python Type Check (Mypy)...")
    
    backend_dir = os.path.join(REPO_ROOT, "cti_dashboard_pro", "app", "backend")
    if not os.path.exists(backend_dir):
        print("    ⚠️  Backend directory not found. Skipping mypy check.")
        return True
        
    try:
        subprocess.run(["mypy", "--version"], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("    ⚠️  Mypy not found in PATH. Skipping type check. (Run: pip install mypy)")
        return True

    # Run mypy on the backend folder
    # We ignore missing imports because some third-party libs might not have stubs locally
    result = subprocess.run(
        ["mypy", backend_dir, "--ignore-missing-imports"], 
        capture_output=True, 
        text=True
    )
    
    if result.returncode != 0:
        print(f"    ❌ PYTHON TYPE ERROR FOUND")
        print("       " + "\n       ".join(result.stdout.strip().split('\n')[:10]))
        if len(result.stdout.strip().split('\n')) > 10:
            print("       ... (more errors truncated)")
        print("\n🚫 Pre-flight type check failed! Deployment aborted.")
        return False
        
    print(f"    ✅ Python backend passed mypy type validation.")
    return True


def git_push(commit_message: str) -> bool:
    """
    Stage, commit (if anything changed), and push to GitHub.
    Returns True if a push was made, False if already up to date.
    """
    print("\n📦  Checking git status...")
    status = run_local(["git", "status", "--porcelain"])

    if status:
        print(f"    {len(status.splitlines())} changed file(s) — committing...")
        run_local(["git", "add", "-A"])
        run_local(["git", "commit", "-m", commit_message])
        print("    ✅ Committed.")
    else:
        print("    Working tree clean — nothing to commit.")

    # Check if we're ahead of remote
    ahead = run_local(["git", "rev-list", f"origin/{BRANCH}..HEAD", "--count"])
    if ahead == "0":
        print("    Already up to date with remote — no push needed.")
        return False

    print(f"    ⬆️  Pushing {ahead} commit(s) to GitHub ({BRANCH})...")
    run_local(["git", "push", "origin", BRANCH])
    sha = run_local(["git", "rev-parse", "--short", "HEAD"])
    print(f"    ✅ Pushed. Latest SHA: {sha}")
    return True


def trigger_vps_sync():
    """SSH into VPS and run the auto_sync.sh immediately."""
    print(f"\n🔌  Connecting to VPS ({VPS_HOST})...")
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(VPS_HOST, username=VPS_USER, password=VPS_PASSWORD, timeout=30)

    print(f"🚀  Triggering sync on VPS: {VPS_SYNC_CMD}\n")
    print("─" * 60)

    # Stream output line-by-line
    stdin, stdout, stderr = client.exec_command(
        VPS_SYNC_CMD, get_pty=True, timeout=300
    )
    for line in stdout:
        print(f"  VPS | {line.rstrip()}")

    exit_status = stdout.channel.recv_exit_status()
    client.close()

    print("─" * 60)
    if exit_status == 0:
        print("\n✅  VPS sync complete!")
    else:
        err = stderr.read().decode().strip()
        print(f"\n⚠️  Sync exited with code {exit_status}. stderr: {err}")


# ── Main ──────────────────────────────────────────────────────────────────────

def deploy(commit_message: str):
    print("\n" + "=" * 60)
    print("  CTI Dashboard PRO — Deploy to VPS")
    print("  Mode: GitHub auto-sync (push → trigger)")
    print("=" * 60)

    # Step 0: Pre-flight Syntax Check
    if not preflight_syntax_check():
        sys.exit(1)
        
    # Step 0.5: Pre-flight Python Type Check
    if not preflight_mypy_check():
        sys.exit(1)

    # Step 1: Push to GitHub
    try:
        git_push(commit_message)
    except RuntimeError as e:
        print(f"\n⚠️  Git error (continuing anyway): {e}")

    # Step 2: Trigger immediate sync on VPS
    try:
        trigger_vps_sync()
    except Exception as e:
        print(f"\n❌  VPS connection failed: {e}")
        print("\n💡  The VPS timer will still auto-sync within 5 minutes.")
        print(f"    Monitor: ssh {VPS_USER}@{VPS_HOST} 'tail -f /var/log/cti_autosync.log'")
        return

    print(f"\n🌐  Live at: https://ct.ftp.sh")
    print(f"    Logs:    ssh {VPS_USER}@{VPS_HOST} 'docker logs cti-dashboard-pro --tail 30'")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    msg = sys.argv[1] if len(sys.argv) > 1 else "chore: auto-deploy commit from deploy_pro_to_vps.py"
    deploy(msg)
