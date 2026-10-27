"""How much memory a final render may use: installed RAM, the histogram budget, the GPU tile budget.

There is deliberately no fixed ceiling (Apophysis capped renders at 2 GB): the default budget is
half of whatever RAM the machine has, and both budgets can be set explicitly in the settings.
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .final_settings import FinalRenderSettings

DEFAULT_GPU_MEMORY_MB = 1024      # RGBA32F tile texture budget when none is set: fine on any discrete GPU
DEFAULT_MEMORY_FRACTION = 0.5     # of physical RAM, when no limit is set


def physical_memory_bytes() -> int:
    """Installed RAM, or 8 GB if the platform does not say."""
    try:
        pages, page_size = os.sysconf("SC_PHYS_PAGES"), os.sysconf("SC_PAGE_SIZE")
        if pages > 0 and page_size > 0:
            return int(pages) * int(page_size)
    except (AttributeError, ValueError, OSError):
        pass
    try:
        import ctypes

        class _Status(ctypes.Structure):
            _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong), ("ullTotalPhys", ctypes.c_ulonglong),
                        ("ullAvailPhys", ctypes.c_ulonglong), ("ullTotalPageFile", ctypes.c_ulonglong),
                        ("ullAvailPageFile", ctypes.c_ulonglong), ("ullTotalVirtual", ctypes.c_ulonglong),
                        ("ullAvailVirtual", ctypes.c_ulonglong), ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]
        status = _Status()
        status.dwLength = ctypes.sizeof(_Status)
        if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):   # type: ignore[attr-defined]
            return int(status.ullTotalPhys)
    except Exception:  # noqa: BLE001 - not Windows, or the call failed
        pass
    return 8 << 30


def memory_budget_bytes(settings: "FinalRenderSettings") -> int:
    """The histogram memory a render may use: the explicit limit, else half of physical RAM (no fixed ceiling)."""
    if settings.memory_limit_mb > 0:
        return int(settings.memory_limit_mb) << 20
    return int(physical_memory_bytes() * DEFAULT_MEMORY_FRACTION)


def gpu_budget_bytes(settings: "FinalRenderSettings") -> int:
    """Texture memory one GPU tile may use."""
    return int(settings.gpu_memory_mb or DEFAULT_GPU_MEMORY_MB) << 20


__all__ = ["physical_memory_bytes", "memory_budget_bytes", "gpu_budget_bytes", "DEFAULT_GPU_MEMORY_MB", "DEFAULT_MEMORY_FRACTION"]
