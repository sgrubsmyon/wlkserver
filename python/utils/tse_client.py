"""Adapter module for the TSE (Technical Security Equipment).

Wraps the cryptovision SE-API C library (libse-api-c.so) with ctypes. The
high-level transaction/export orchestration mirrors the Java POS
(WeltladenTSE.java) as closely as possible, but is untested without real
hardware and may need adjustments.
"""

import ctypes
import os

_LIB_PATHS = [
    os.getenv("TSE_LIB_PATH"),
    os.path.join(os.path.dirname(__file__), "..", "..", "assets", "SE-API-C", "bin", "libse-api-c.so"),
    "libse-api-c.so",
]

CLIENT_ID = os.getenv("TSE_CLIENT_ID", "WeltladenKasse").encode("utf-8")


class SeStartTransactionResult(ctypes.Structure):
    _fields_ = [
        ("logTime", ctypes.c_int64),
        ("serialNumber", ctypes.POINTER(ctypes.c_ubyte)),
        ("serialNumberLength", ctypes.c_uint32),
        ("signatureCounter", ctypes.c_uint32),
        ("signatureValue", ctypes.POINTER(ctypes.c_ubyte)),
        ("signatureValueLength", ctypes.c_uint32),
        ("transactionNumber", ctypes.c_uint32),
    ]


class SeFinishTransactionResult(ctypes.Structure):
    _fields_ = [
        ("logTime", ctypes.c_int64),
        ("serialNumber", ctypes.POINTER(ctypes.c_ubyte)),
        ("serialNumberLength", ctypes.c_uint32),
        ("signatureCounter", ctypes.c_uint32),
        ("signatureValue", ctypes.POINTER(ctypes.c_ubyte)),
        ("signatureValueLength", ctypes.c_uint32),
    ]


def _load_library():
    for path in _LIB_PATHS:
        if not path:
            continue
        try:
            lib = ctypes.CDLL(path)
            lib.se_getApiVersionString.restype = ctypes.c_char_p
            # prototypes
            lib.se_openDirect.argtypes = [ctypes.c_char_p, ctypes.c_uint32]
            lib.se_openDirect.restype = ctypes.c_int
            lib.se_initialize.argtypes = []
            lib.se_initialize.restype = ctypes.c_int
            lib.se_startTransaction.argtypes = [
                ctypes.c_char_p, ctypes.c_uint32,
                ctypes.c_char_p, ctypes.c_uint32,
                ctypes.c_char_p, ctypes.c_uint32,
                ctypes.c_char_p, ctypes.c_uint32,
                ctypes.POINTER(SeStartTransactionResult),
            ]
            lib.se_startTransaction.restype = ctypes.c_int
            lib.se_finishTransaction.argtypes = [
                ctypes.c_char_p, ctypes.c_uint32,
                ctypes.c_uint32,
                ctypes.c_char_p, ctypes.c_uint32,
                ctypes.c_char_p, ctypes.c_uint32,
                ctypes.c_char_p, ctypes.c_uint32,
                ctypes.POINTER(SeFinishTransactionResult),
            ]
            lib.se_finishTransaction.restype = ctypes.c_int
            lib.se_exportData.argtypes = [
                ctypes.c_char_p, ctypes.c_uint32,
                ctypes.c_uint32, ctypes.c_uint32, ctypes.c_uint32,
                ctypes.c_int64, ctypes.c_int64,
                ctypes.c_int32,
                ctypes.POINTER(ctypes.POINTER(ctypes.c_ubyte)),
                ctypes.POINTER(ctypes.c_uint32),
            ]
            lib.se_exportData.restype = ctypes.c_int
            lib.se_exportMoreData.argtypes = [
                ctypes.POINTER(ctypes.c_ubyte), ctypes.c_uint32,
                ctypes.c_uint32, ctypes.c_int32,
                ctypes.POINTER(ctypes.POINTER(ctypes.c_ubyte)),
                ctypes.POINTER(ctypes.c_uint32),
            ]
            lib.se_exportMoreData.restype = ctypes.c_int
            lib.se_deleteStoredDataUpTo.argtypes = [
                ctypes.POINTER(ctypes.c_ubyte), ctypes.c_uint32,
                ctypes.c_uint32,
            ]
            lib.se_deleteStoredDataUpTo.restype = ctypes.c_int
            lib.se_free.argtypes = [ctypes.c_void_p]
            lib.se_free.restype = None
            lib.se_getSignatureCounter1.argtypes = [ctypes.POINTER(ctypes.c_uint32)]
            lib.se_getSignatureCounter1.restype = ctypes.c_int
            return lib
        except OSError:
            continue
    return None


class TSEClient:
    def __init__(self):
        self.lib = _load_library()
        self.initialized = False
        self.opened = False
        self.device_path = os.getenv("TSE_DEVICE_PATH")

    def _ensure_open(self):
        if self.opened:
            return True
        if self.lib is None or not self.device_path:
            return False
        try:
            rc = self.lib.se_openDirect(self.device_path.encode(), 5000)
            if rc != 0:
                return False
            rc = self.lib.se_initialize()
            self.opened = (rc == 0)
            self.initialized = self.opened
            return self.opened
        except Exception:
            return False

    def status(self):
        result = {
            "initialized": self.initialized,
            "opened": self.opened,
            "library_loaded": self.lib is not None,
            "api_version": None,
            "device_path": self.device_path,
        }
        if self.lib is not None:
            try:
                result["api_version"] = self.lib.se_getApiVersionString().decode("utf-8", "replace")
            except Exception:
                pass
        return result

    def init(self):
        if self._ensure_open():
            return {"status": "initialized"}
        if self.lib is None:
            self.initialized = True
            return {"status": "initialized (stub: no C library)"}
        return {"status": "failed: device not available", "device_path": self.device_path}

    def create_transaction(self, process_type, process_data, training=False):
        if not self._ensure_open():
            return {
                "transaction_number": 1,
                "signature_counter": 1,
                "signature_base64": "DUMMY_SIGNATURE",
                "transaction_start": "2026-01-01T00:00:00.000+01:00",
                "transaction_end": "2026-01-01T00:00:00.000+01:00",
                "tse_error": "device not available (stub)",
            }
        # Start transaction
        start_res = SeStartTransactionResult()
        client_id = CLIENT_ID
        rc = self.lib.se_startTransaction(
            client_id, len(client_id),
            None, 0,
            None, 0,
            None, 0,
            ctypes.byref(start_res),
        )
        if rc != 0:
            return {
                "transaction_number": None,
                "signature_counter": None,
                "signature_base64": None,
                "transaction_start": None,
                "transaction_end": None,
                "tse_error": f"startTransaction failed: {rc}",
            }
        tx_number = start_res.transactionNumber
        start_time = start_res.logTime

        # Finish transaction
        proc_bytes = (process_data or "").encode("utf-8")
        ptype = (process_type or "").encode("utf-8")
        finish_res = SeFinishTransactionResult()
        rc = self.lib.se_finishTransaction(
            client_id, len(client_id),
            tx_number,
            proc_bytes, len(proc_bytes),
            ptype, len(ptype),
            None, 0,
            ctypes.byref(finish_res),
        )
        if rc != 0:
            return {
                "transaction_number": tx_number,
                "signature_counter": start_res.signatureCounter,
                "signature_base64": None,
                "transaction_start": str(start_time),
                "transaction_end": None,
                "tse_error": f"finishTransaction failed: {rc}",
            }
        sig_b64 = ""
        if finish_res.signatureValue and finish_res.signatureValueLength:
            import base64
            raw = bytes(finish_res.signatureValue[:finish_res.signatureValueLength])
            sig_b64 = base64.b64encode(raw).decode("ascii")
            self.lib.se_free(finish_res.signatureValue)
            self.lib.se_free(finish_res.serialNumber)
        self.lib.se_free(start_res.signatureValue)
        self.lib.se_free(start_res.serialNumber)
        return {
            "transaction_number": tx_number,
            "signature_counter": finish_res.signatureCounter,
            "signature_base64": sig_b64,
            "transaction_start": str(start_time),
            "transaction_end": str(finish_res.logTime),
            "tse_error": None,
        }

    def _export_bytes(self, client_id_bytes, transaction_number=None, start_tx=None, end_tx=None,
                      start_date=0, end_date=0, max_records=0, previous_sig_counter=0, max_records2=0,
                      use_more=False):
        if not self._ensure_open():
            return b""
        if not use_more:
            exported = ctypes.POINTER(ctypes.c_ubyte)()
            length = ctypes.c_uint32(0)
            rc = self.lib.se_exportData(
                client_id_bytes, len(client_id_bytes),
                transaction_number or 0,
                start_tx or 0,
                end_tx or 0,
                start_date, end_date,
                max_records,
                ctypes.byref(exported),
                ctypes.byref(length),
            )
            if rc != 0 or not exported or length.value == 0:
                return b""
            data = bytes(exported[:length.value])
            self.lib.se_free(exported)
            return data
        else:
            exported = ctypes.POINTER(ctypes.c_ubyte)()
            length = ctypes.c_uint32(0)
            serial_key = None
            rc = self.lib.se_exportMoreData(
                serial_key, 0,
                previous_sig_counter,
                max_records2,
                ctypes.byref(exported),
                ctypes.byref(length),
            )
            if rc != 0 or not exported or length.value == 0:
                return b""
            data = bytes(exported[:length.value])
            self.lib.se_free(exported)
            return data

    def export_full(self):
        data = self._export_bytes(CLIENT_ID, max_records=0)
        return data

    def export_partial(self, **kwargs):
        # Prefer exportMoreData by signature counter if provided
        prev = kwargs.get("last_excluded_signature_counter", 0) or 0
        maxr = kwargs.get("max_records", 0) or 0
        if kwargs.get("start_tx_number") or kwargs.get("end_tx_number"):
            return self._export_bytes(
                CLIENT_ID,
                start_tx=kwargs.get("start_tx_number", 0),
                end_tx=kwargs.get("end_tx_number", 0),
                max_records=kwargs.get("max_records", 0) or 0,
            )
        if kwargs.get("start_date") or kwargs.get("end_date"):
            def _to_epoch(s):
                if not s:
                    return 0
                try:
                    from datetime import datetime, timezone
                    dt = datetime.fromisoformat(s)
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=timezone.utc)
                    return int(dt.timestamp())
                except Exception:
                    return 0
            sd = _to_epoch(kwargs.get("start_date"))
            ed = _to_epoch(kwargs.get("end_date"))
            return self._export_bytes(CLIENT_ID, start_date=sd, end_date=ed, max_records=kwargs.get("max_records", 0) or 0)
        return self._export_bytes(CLIENT_ID, use_more=True, previous_sig_counter=prev, max_records2=maxr)

    def get_signature_counter(self):
        if not self._ensure_open():
            return None
        counter = ctypes.c_uint32(0)
        try:
            rc = self.lib.se_getSignatureCounter1(ctypes.byref(counter))
            if rc == 0:
                return counter.value
        except Exception:
            pass
        return None

    def export_and_delete(self, **kwargs):
        prev = kwargs.get("last_excluded_signature_counter", 0) or 0
        data = self.export_partial(last_excluded_signature_counter=prev, max_records=kwargs.get("max_records", 0))
        if not data:
            return b""
        # Delete stored TSE data up to the current signature counter.
        counter = self.get_signature_counter()
        if counter is not None and self.lib is not None and self.opened:
            try:
                self.lib.se_deleteStoredDataUpTo(CLIENT_ID, len(CLIENT_ID), counter)
            except Exception:
                pass
        return data


# Module-level singleton used by the router.
tse_client = TSEClient()