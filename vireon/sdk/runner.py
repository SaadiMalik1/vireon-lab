import subprocess
import os

def run_sandboxed(cmd: list, cwd: str = None, input_data: str = None) -> subprocess.CompletedProcess:
    """
    Executes a command inside a lightweight sandbox using bubblewrap (bwrap) to prevent 
    unauthorized filesystem and network access by the spawned process.
    """
    bwrap_cmd = [
        "bwrap",
        "--unshare-all",          # Unshare all namespaces (network, pid, ipc, etc.)
        "--share-net",            # Allow network if needed for loopback sockets
        "--ro-bind", "/", "/",    # Read-only root filesystem
        "--proc", "/proc",        # Mount proc
        "--dev", "/dev",          # Mount dev
        "--tmpfs", "/tmp",        # Temporary /tmp
        "--bind", cwd if cwd else os.getcwd(), cwd if cwd else os.getcwd(),  # Allow writing only to CWD
    ]
    bwrap_cmd.extend(cmd)
    
    return subprocess.run(
        bwrap_cmd,
        cwd=cwd,
        input=input_data,
        capture_output=True,
        text=True
    )

def popen_sandboxed(cmd: list, cwd: str = None, stdout=None, stderr=None) -> subprocess.Popen:
    """
    Spawns a process asynchronously inside a lightweight sandbox using bubblewrap.
    """
    bwrap_cmd = [
        "bwrap",
        "--unshare-all",
        "--share-net",            # Need network for QEMU TCP sockets
        "--ro-bind", "/", "/",
        "--proc", "/proc",
        "--dev", "/dev",
        "--tmpfs", "/tmp",
        "--bind", cwd if cwd else os.getcwd(), cwd if cwd else os.getcwd(),
    ]
    bwrap_cmd.extend(cmd)
    
    return subprocess.Popen(
        bwrap_cmd,
        cwd=cwd,
        stdout=stdout,
        stderr=stderr
    )
