"""Inter-Prozess-Dateilocks (Windows msvcrt / POSIX flock).

Vom Audit-Logger und vom Excel-Writer benutzt, um Schreiboperationen
mehrerer Workstations auf demselben SMB-Share zu serialisieren. Die Locks
hängen am File-Descriptor und werden vom Betriebssystem freigegeben, wenn
der Prozess endet — verwaiste Locks gibt es nicht.
"""

from __future__ import annotations

import os
import sys
import time


if sys.platform == "win32":
    import msvcrt

    def acquire_lock(fd: int, timeout: float) -> bool:
        """Versucht das Lock bis zur Deadline zu bekommen. True = Erfolg."""
        deadline = time.monotonic() + timeout
        os.lseek(fd, 0, os.SEEK_SET)
        while True:
            try:
                # LK_NBLCK = non-blocking — wir machen den Retry selbst.
                msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
                return True
            except OSError:
                if time.monotonic() >= deadline:
                    return False
                time.sleep(0.05)

    def release_lock(fd: int) -> None:
        try:
            os.lseek(fd, 0, os.SEEK_SET)
            msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
        except OSError:
            pass

else:
    import fcntl

    def acquire_lock(fd: int, timeout: float) -> bool:
        deadline = time.monotonic() + timeout
        while True:
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                return True
            except OSError:
                if time.monotonic() >= deadline:
                    return False
                time.sleep(0.05)

    def release_lock(fd: int) -> None:
        try:
            fcntl.flock(fd, fcntl.LOCK_UN)
        except OSError:
            pass
