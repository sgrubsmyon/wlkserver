"""Adapter module for the TSE (Technical Security Equipment).

The TSE in use is a cryptovision/D-Trust SEAPI device. The vendor provides
only Java and C APIs. This module isolates all TSE access behind a clean
Python interface and wraps the C library (libse-api-c.so) with ctypes when it
is available. The transaction/export methods are still stubs: fully porting
the Java TSE workflow (process data formatting, transaction life-cycle,
export/delete orchestration) requires a connected device and is tracked as
remaining Phase 5 work.
"""

import ctypes
import os

_LIB_PATHS = [
    os.getenv("TSE_LIB_PATH"),
    os.path.join(os.path.dirname(__file__), "..", "..", "assets", "SE-API-C", "bin", "libse-api-c.so"),
    "libse-api-c.so",
]


def _load_library():
    for path in _LIB_PATHS:
        if not path:
            continue
        try:
            lib = ctypes.CDLL(path)
            lib.se_getApiVersionString.restype = ctypes.c_char_p
            return lib
        except OSError:
            continue
    return None


class TSEClient:
    def __init__(self):
        self.lib = _load_library()
        self.initialized = False
        self.device_path = os.getenv("TSE_DEVICE_PATH")

    def status(self):
        result = {
            "initialized": self.initialized,
            "library_loaded": self.lib is not None,
            "api_version": None,
            "serial": None,
            "transaction_counter": 0,
        }
        if self.lib is not None:
            try:
                result["api_version"] = self.lib.se_getApiVersionString().decode("utf-8", "replace")
            except Exception:
                pass
        return result

    def init(self):
        if self.lib is None:
            self.initialized = True
            return {"status": "initialized (stub: no C library)"}
        # Opening a real device requires TSE_DEVICE_PATH and is device-specific.
        self.initialized = True
        return {"status": "initialized (C library loaded; device open not yet wired)"}

    def create_transaction(self, process_type, process_data, training=False):
        # Full transaction life-cycle porting is remaining Phase 5 work.
        return {
            "transaction_number": 1,
            "signature_counter": 1,
            "signature_base64": "DUMMY_SIGNATURE",
            "transaction_start": "2026-01-01T00:00:00.000+01:00",
            "transaction_end": "2026-01-01T00:00:00.000+01:00",
            "tse_error": None,
        }

    def export_full(self):
        return b""

    def export_partial(self, **kwargs):
        return b""

    def export_and_delete(self, **kwargs):
        return b""


# Module-level singleton used by the router.
tse_client = TSEClient()
