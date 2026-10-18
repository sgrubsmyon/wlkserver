"""Adapter module for the TSE (Technical Security Equipment).

There is no Python TSE library for the cryptovision/D-Trust SEAPI TSE used
by the Java POS; the vendor only provides Java and C APIs. This module
isolates all TSE access behind a clean Python interface. The current
implementation is a stub that keeps the API usable (and testable) without
the actual TSE hardware/C library. Replace the method bodies with ctypes/cffi
calls to the vendor C library when deploying on real hardware.
"""


class TSEClient:
    def __init__(self):
        self.initialized = False

    def status(self):
        return {
            "initialized": self.initialized,
            "serial": None,
            "transaction_counter": 0,
        }

    def init(self):
        self.initialized = True
        return {"status": "initialized"}

    def create_transaction(self, process_type, process_data, training=False):
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
