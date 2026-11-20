"""Shared bounded subprocess execution; unavailable enforcement fails closed."""

import ctypes
import os
import subprocess
import sys
import uuid
from ctypes import wintypes
from dataclasses import dataclass
from typing import Any

from loometric.planning.validation import PlanningError, integer


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


def _resume_windows_child(pid: int) -> None:
    """Resume the sole primary thread after attaching the suspended launcher."""

    class ThreadEntry(ctypes.Structure):
        _fields_ = [
            (name, wintypes.DWORD) for name in ("size", "usage", "thread_id", "owner_pid")
        ] + [
            ("base_priority", wintypes.LONG),
            ("delta_priority", wintypes.LONG),
            ("flags", wintypes.DWORD),
        ]

    api = ctypes.WinDLL("kernel32", use_last_error=True)
    api.CreateToolhelp32Snapshot.argtypes = [wintypes.DWORD, wintypes.DWORD]
    api.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
    api.Thread32First.argtypes = [wintypes.HANDLE, ctypes.POINTER(ThreadEntry)]
    api.Thread32First.restype = wintypes.BOOL
    api.Thread32Next.argtypes = [wintypes.HANDLE, ctypes.POINTER(ThreadEntry)]
    api.Thread32Next.restype = wintypes.BOOL
    api.OpenThread.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    api.OpenThread.restype = wintypes.HANDLE
    api.ResumeThread.argtypes = [wintypes.HANDLE]
    api.ResumeThread.restype = wintypes.DWORD
    api.CloseHandle.argtypes = [wintypes.HANDLE]
    snapshot = api.CreateToolhelp32Snapshot(4, 0)  # TH32CS_SNAPTHREAD
    if snapshot == wintypes.HANDLE(-1).value:
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        entry = ThreadEntry()
        entry.size = ctypes.sizeof(entry)
        found = api.Thread32First(snapshot, ctypes.byref(entry))
        while found:
            if entry.owner_pid == pid:
                thread = api.OpenThread(2, False, entry.thread_id)  # THREAD_SUSPEND_RESUME
                if not thread:
                    raise ctypes.WinError(ctypes.get_last_error())
                try:
                    if api.ResumeThread(thread) != 1:
                        raise OSError("Suspended child did not have exactly one suspension.")
                    return
                finally:
                    api.CloseHandle(thread)
            found = api.Thread32Next(snapshot, ctypes.byref(entry))
        raise OSError("Suspended child primary thread was not found.")
    finally:
        api.CloseHandle(snapshot)


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
        self.name = f"Loometric-M03C-{uuid.uuid4().hex}"
        self.handle = self.api.CreateJobObjectW(None, self.name)
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


def apply_child_memory_limit(memory_bytes: int, windows_job_name: str | None = None) -> str:
    if os.name == "nt":
        api = ctypes.WinDLL("kernel32", use_last_error=True)
        api.QueryInformationJobObject.argtypes = [
            wintypes.HANDLE,
            ctypes.c_int,
            ctypes.c_void_p,
            wintypes.DWORD,
            ctypes.c_void_p,
        ]
        api.QueryInformationJobObject.restype = wintypes.BOOL
        if not windows_job_name:
            raise OSError("No parent resource job identity was supplied.")
        api.OpenJobObjectW.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.LPCWSTR]
        api.OpenJobObjectW.restype = wintypes.HANDLE
        api.IsProcessInJob.argtypes = [
            wintypes.HANDLE,
            wintypes.HANDLE,
            ctypes.POINTER(wintypes.BOOL),
        ]
        api.IsProcessInJob.restype = wintypes.BOOL
        api.CloseHandle.argtypes = [wintypes.HANDLE]
        job = api.OpenJobObjectW(4, False, windows_job_name)
        if not job:
            raise ctypes.WinError(ctypes.get_last_error())
        try:
            info = _ExtendedLimits()
            member = wintypes.BOOL()
            if (
                not api.IsProcessInJob(wintypes.HANDLE(-1), job, ctypes.byref(member))
                or not member.value
                or not api.QueryInformationJobObject(
                    job, 9, ctypes.byref(info), ctypes.sizeof(info), None
                )
                or not info.basic.flags & 0x200
                or info.job_memory != memory_bytes
            ):
                raise OSError("Worker is not inside the requested hard memory-limited Job Object.")
        finally:
            api.CloseHandle(job)
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
    request: str,
    memory_mib: int,
    timeout: float,
    *,
    worker_module: str = "loometric.benchmarks.worker",
) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    """Start waiting stdlib-only child, enforce limits, then release one request."""
    import json
    from time import perf_counter

    if worker_module not in (
        "loometric.benchmarks.worker",
        "loometric.scenarios.worker",
        "loometric.api.worker",
    ):
        raise ValueError("Unsupported bounded worker module.")
    started = perf_counter()
    process = subprocess.Popen(
        [sys.executable, "-m", worker_module],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        creationflags=0x4 | 0x08000000 if os.name == "nt" else 0,
    )
    job = None
    measurements: dict[str, Any] = {"peak_committed_bytes": None}
    try:
        if os.name == "nt":
            job = WindowsJob(process.pid, memory_mib * 1024**2)
            _resume_windows_child(process.pid)
            request = json.dumps({**json.loads(request), "windows_job_name": job.name})
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


@dataclass(frozen=True)
class ResourceLimits:
    max_operations: int = 300
    max_alternatives: int = 20000
    max_variables: int = 25000
    max_constraints: int = 90000
    process_memory_mib: int = 768
    process_wall_seconds: int = 60
    batch_wall_seconds: int = 2400

    def __post_init__(self) -> None:
        for name in self.__dataclass_fields__:
            integer(getattr(self, name), name, minimum=1)
        if self.process_memory_mib > 2048 or self.process_wall_seconds > 120:
            raise PlanningError("INVALID_BENCHMARK", "Child limits exceed local audit safeguards.")
        if self.batch_wall_seconds > 7200:
            raise PlanningError("INVALID_BENCHMARK", "Batch limit exceeds two hours.")

    def rejection(self, dimensions: dict[str, Any]) -> str | None:
        for metric, ceiling in (
            ("operations", self.max_operations),
            ("eligible_fragment_upper_bound", self.max_alternatives),
            ("eligible_alternatives", self.max_alternatives),
            ("model_variables", self.max_variables),
            ("model_constraints", self.max_constraints),
        ):
            if dimensions.get(metric, 0) > ceiling:
                return f"{metric}={dimensions[metric]} exceeds declared limit {ceiling}"
        return None
