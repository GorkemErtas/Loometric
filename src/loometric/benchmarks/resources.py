"""Hard subprocess resource boundaries; unavailable enforcement fails closed."""

import ctypes
import os
import subprocess
import sys
from ctypes import wintypes
from typing import Any


class _BasicLimits(ctypes.Structure):
    _fields_ = [
        ("process_time", ctypes.c_longlong),
        ("job_time", ctypes.c_longlong),
        ("flags", wintypes.DWORD),
        ("minimum_working_set", ctypes.c_size_t),
        ("maximum_working_set", ctypes.c_size_t),
        ("active_processes", wintypes.DWORD),
        ("affinity", ctypes.c_size_t),
        ("priority", wintypes.DWORD),
        ("scheduling", wintypes.DWORD),
    ]


class _ExtendedLimits(ctypes.Structure):
    _fields_ = [
        ("basic", _BasicLimits),
        ("io", ctypes.c_ulonglong * 6),
        ("process_memory", ctypes.c_size_t),
        ("job_memory", ctypes.c_size_t),
        ("peak_process_memory", ctypes.c_size_t),
        ("peak_job_memory", ctypes.c_size_t),
    ]


class WindowsJob:
    """One child per job. No child benchmark work starts until assignment succeeds."""

    def __init__(self, pid: int, memory_bytes: int):
        self.api = ctypes.WinDLL("kernel32", use_last_error=True)
        self.api.CreateJobObjectW.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR]
        self.api.CreateJobObjectW.restype = wintypes.HANDLE
        self.api.SetInformationJobObject.argtypes = [
            wintypes.HANDLE,
            ctypes.c_int,
            ctypes.c_void_p,
            wintypes.DWORD,
        ]
        self.api.SetInformationJobObject.restype = wintypes.BOOL
        self.api.QueryInformationJobObject.argtypes = [
            wintypes.HANDLE,
            ctypes.c_int,
            ctypes.c_void_p,
            wintypes.DWORD,
            ctypes.c_void_p,
        ]
        self.api.QueryInformationJobObject.restype = wintypes.BOOL
        self.api.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        self.api.OpenProcess.restype = wintypes.HANDLE
        self.api.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
        self.api.AssignProcessToJobObject.restype = wintypes.BOOL
        self.api.CloseHandle.argtypes = [wintypes.HANDLE]
        self.api.CloseHandle.restype = wintypes.BOOL
        self.handle = self.api.CreateJobObjectW(None, None)
        if not self.handle:
            raise ctypes.WinError(ctypes.get_last_error())
        child = None
        try:
            info = _ExtendedLimits()
            # PROCESS_MEMORY | JOB_MEMORY | ACTIVE_PROCESS | KILL_ON_JOB_CLOSE.
            # Windows venv's launcher creates one underlying interpreter process.
            info.basic.flags = 0x100 | 0x200 | 0x8 | 0x2000
            info.basic.active_processes = 2
            info.process_memory = memory_bytes
            info.job_memory = memory_bytes
            if not self.api.SetInformationJobObject(
                self.handle, 9, ctypes.byref(info), ctypes.sizeof(info)
            ):
                raise ctypes.WinError(ctypes.get_last_error())
            child = self.api.OpenProcess(0x100 | 0x1, False, pid)  # SET_QUOTA | TERMINATE
            if not child or not self.api.AssignProcessToJobObject(self.handle, child):
                raise ctypes.WinError(ctypes.get_last_error())
        except BaseException:
            self.close()
            raise
        finally:
            if child:
                self.api.CloseHandle(child)

    def peak_committed_bytes(self) -> int:
        info = _ExtendedLimits()
        if not self.api.QueryInformationJobObject(
            self.handle, 9, ctypes.byref(info), ctypes.sizeof(info), None
        ):
            raise ctypes.WinError(ctypes.get_last_error())
        return info.peak_job_memory

    def close(self) -> None:
        if self.handle:
            self.api.CloseHandle(self.handle)
            self.handle = None


def apply_child_memory_limit(memory_bytes: int) -> str:
    if os.name == "nt":
        # Assigned by the parent before it sends the request. This is not a self-asserted limit.
        return "windows-job-aggregate-commit"
    if sys.platform.startswith("linux"):
        import resource

        _, hard = resource.getrlimit(resource.RLIMIT_AS)
        ceiling = memory_bytes if hard == resource.RLIM_INFINITY else min(hard, memory_bytes)
        resource.setrlimit(resource.RLIMIT_AS, (ceiling, ceiling))
        return "linux-rlimit-as"
    raise OSError("Hard memory enforcement is implemented only for Windows and Linux.")


def peak_working_set_bytes() -> int | None:
    if os.name == "nt":

        class Counters(ctypes.Structure):
            _fields_ = [("size", wintypes.DWORD), ("faults", wintypes.DWORD)] + [
                (name, ctypes.c_size_t)
                for name in (
                    "peak_working_set",
                    "working_set",
                    "peak_paged",
                    "paged",
                    "peak_nonpaged",
                    "nonpaged",
                    "pagefile",
                    "peak_pagefile",
                    "private",
                )
            ]

        counters = Counters()
        counters.size = ctypes.sizeof(counters)
        api = ctypes.WinDLL("psapi", use_last_error=True)
        api.GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.c_void_p, wintypes.DWORD]
        api.GetProcessMemoryInfo.restype = wintypes.BOOL
        # The documented pseudo handle for the current process; no handle to close.
        if api.GetProcessMemoryInfo(wintypes.HANDLE(-1), ctypes.byref(counters), counters.size):
            return counters.peak_working_set
        return None
    if sys.platform.startswith("linux"):
        import resource

        return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024
    return None


def guarded_child(
    request: str, memory_mib: int, timeout: float
) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    """Start waiting stdlib-only child, enforce limits, then release one request."""
    import json
    from time import perf_counter

    started = perf_counter()
    process = subprocess.Popen(
        [sys.executable, "-m", "loometric.benchmarks.worker"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    job = None
    measurements: dict[str, Any] = {"peak_committed_bytes": None}
    try:
        if os.name == "nt":
            job = WindowsJob(process.pid, memory_mib * 1024**2)
        elif not sys.platform.startswith("linux"):
            raise OSError("Hard memory limits unavailable on this platform.")
        try:
            stdout, stderr = process.communicate(request, timeout=timeout)
        except subprocess.TimeoutExpired:
            if job:
                measurements["peak_committed_bytes"] = job.peak_committed_bytes()
                job.close()  # Kill the launcher AND its interpreter before draining pipes.
                job = None
            if process.poll() is None:
                process.kill()
            stdout, stderr = process.communicate()
            measurements.update(
                status="TERMINATED_RESOURCE_LIMIT", reason="Whole-child wall watchdog exceeded."
            )
            return None, measurements
        measurements["returncode"] = process.returncode
        if process.returncode != 0:
            measurements.update(
                status="WORKER_FAILED", reason=stderr[-2000:] or "Worker exited without a report."
            )
            return None, measurements
        try:
            payload = json.loads(stdout)
        except (json.JSONDecodeError, ValueError):
            measurements.update(status="WORKER_FAILED", reason="Malformed worker JSON.")
            return None, measurements
        return payload, measurements
    except OSError as exc:
        measurements.update(
            status="SKIPPED_RESOURCE_LIMIT", reason=f"Hard memory guard unavailable: {exc}"
        )
        return None, measurements
    finally:
        if process.poll() is None:
            if job:
                measurements["peak_committed_bytes"] = job.peak_committed_bytes()
                job.close()
                job = None
            process.kill()
            process.communicate()
        if job:
            try:
                measurements["peak_committed_bytes"] = job.peak_committed_bytes()
            except OSError:
                measurements["peak_committed_bytes"] = None
            finally:
                job.close()
        measurements["whole_child_wall_seconds"] = perf_counter() - started
