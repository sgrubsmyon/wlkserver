"""Adapter module for the TSE (Technical Security Equipment).

Wraps the cryptovision SE-API C library (libse-api-c.so) with ctypes. The
high-level transaction/export orchestration mirrors the Java POS
(WeltladenTSE.java) as closely as possible, but is untested without real
hardware and may need adjustments.
"""

import ctypes
import os
from datetime import datetime

from .. import config

_LIB_PATHS = [
    config.tse_lib_path(),
    os.path.join(os.path.dirname(__file__), "..", "..", "assets", "SE-API-C", "bin", "libse-api-c.so"),
    "libse-api-c.so",
]

CLIENT_ID = config.tse_client_id()

PROCESS_TYPE = "Kassenbeleg-V1"  # Java `WeltladenTSE.defaultProcessType`
# DSFinV-K process data of an aborted Vorgang: no payment may have happened
# (Java `WeltladenTSE.cancelTransaction`).
ABORT_PROCESS_DATA = "AVBelegabbruch^0.00_0.00_0.00_0.00_0.00^"

# `se_pin_state_flags_t` (se_types.h): 0 means all PINs and PUKs are initialized.
PIN_STATE_INITIALIZED = 0x00
# `se_lcs_t` (se_types.h).
LCS_NOT_INITIALIZED = 1
LCS_NO_TIME = 2
LCS_ACTIVE = 3
# `ErrorERSalreadyMapped` (se_result_t.h): the client id is registered already.
ERS_ALREADY_MAPPED = 0x3006

PIN_LENGTH = 8
PUK_LENGTH = 10


def now_iso() -> str:
    """Current time in the DSFinV-K format `yyyy-MM-dd'T'HH:mm:ss.SSSXXX`."""
    return datetime.now().astimezone().isoformat(timespec="milliseconds")


def _log_time(value) -> str:
    """TSE `logTime` (unix seconds) in the DSFinV-K timestamp format."""
    return datetime.fromtimestamp(value).astimezone().isoformat(timespec="milliseconds")


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
            lib.se_exportCertificates.argtypes = [ctypes.POINTER(ctypes.POINTER(ctypes.c_ubyte)), ctypes.POINTER(ctypes.c_uint32)]
            lib.se_exportCertificates.restype = ctypes.c_int
            # Commissioning and time keeping.
            lib.se_getPinStatus.argtypes = [ctypes.POINTER(ctypes.c_uint32)]
            lib.se_getPinStatus.restype = ctypes.c_int
            lib.se_getLifeCycleState.argtypes = [ctypes.POINTER(ctypes.c_int)]
            lib.se_getLifeCycleState.restype = ctypes.c_int
            lib.se_initializePinValues.argtypes = [
                ctypes.c_char_p, ctypes.c_uint32,
                ctypes.c_char_p, ctypes.c_uint32,
                ctypes.c_char_p, ctypes.c_uint32,
                ctypes.c_char_p, ctypes.c_uint32,
            ]
            lib.se_initializePinValues.restype = ctypes.c_int
            lib.se_initialize.argtypes = []
            lib.se_initialize.restype = ctypes.c_int
            lib.se_authenticateUser.argtypes = [
                ctypes.c_char_p, ctypes.c_uint32,
                ctypes.c_char_p, ctypes.c_uint32,
                ctypes.POINTER(ctypes.c_int),
                ctypes.POINTER(ctypes.c_int16),
            ]
            lib.se_authenticateUser.restype = ctypes.c_int
            lib.se_logOut.argtypes = [ctypes.c_char_p, ctypes.c_uint32]
            lib.se_logOut.restype = ctypes.c_int
            lib.se_updateTime.argtypes = [ctypes.c_int64]
            lib.se_updateTime.restype = ctypes.c_int
            lib.se_getTimeSyncInterval.argtypes = [ctypes.POINTER(ctypes.c_uint32)]
            lib.se_getTimeSyncInterval.restype = ctypes.c_int
            lib.se_registerClient.argtypes = [ctypes.c_char_p, ctypes.c_uint32]
            lib.se_registerClient.restype = ctypes.c_int
            lib.se_close.argtypes = []
            lib.se_close.restype = ctypes.c_int
            return lib
        except OSError:
            continue
    return None


class TSEClient:
    def __init__(self):
        self.lib = _load_library()
        self.initialized = False
        self.opened = False
        self.device_path = config.tse_device_path()
        self.time_error = None
        self._next_sync = 0

    def _open(self):
        """Open the device. `se_initialize` is not part of opening: it fails on an
        already initialized TSE with ErrorSECommunicationFailed."""
        if self.opened:
            return True
        if self.lib is None or not self.device_path:
            return False
        try:
            if self.lib.se_openDirect(self.device_path.encode(), 5000) != 0:
                return False
            self.opened = True
            return True
        except Exception:
            return False

    def _authenticate(self, user, pin) -> bool:
        result = ctypes.c_int(0)
        remaining = ctypes.c_int16(0)
        rc = self.lib.se_authenticateUser(
            user.encode(), len(user), pin, len(pin), ctypes.byref(result), ctypes.byref(remaining)
        )
        return rc == 0 and result.value == 0

    def _log_out(self, user):
        try:
            self.lib.se_logOut(user.encode(), len(user))
        except Exception:
            pass

    def _update_time(self, pin) -> bool:
        """`se_updateTime`: the SE API demands a time update after every power-up."""
        self.time_error = None
        if not pin or not self._authenticate("TimeAdmin", pin):
            self.time_error = "TimeAdmin authentication failed (TSE_TIME_ADMIN_PIN)"
            return False
        now = int(datetime.now().timestamp())
        rc = self.lib.se_updateTime(now)
        self._log_out("TimeAdmin")  # TimeAdmin is logged out after 2 seconds anyway
        if rc != 0:
            self.time_error = f"se_updateTime failed: {rc}"
            return False
        interval = ctypes.c_uint32(0)
        if self.lib.se_getTimeSyncInterval(ctypes.byref(interval)) == 0 and interval.value:
            self._next_sync = now + interval.value
        return True

    def _ensure_time(self, pin=None, force=False):
        now = int(datetime.now().timestamp())
        if not force and now < self._next_sync:
            return True
        return self._update_time(pin or config.tse_time_admin_pin())

    def _ensure_open(self):
        if not self._open():
            return False
        self._ensure_time()
        return True

    def pin_state(self):
        state = ctypes.c_uint32(0)
        if self.lib.se_getPinStatus(ctypes.byref(state)) != 0:
            return None
        return state.value

    def life_cycle_state(self):
        state = ctypes.c_int(0)
        if self.lib.se_getLifeCycleState(ctypes.byref(state)) != 0:
            return None
        return state.value

    def register_client(self):
        """`se_registerClient`: map this client id to the TSE key (Admin rights)."""
        rc = self.lib.se_registerClient(CLIENT_ID, len(CLIENT_ID))
        return rc in (0, ERS_ALREADY_MAPPED)

    def status(self):
        result = {
            "initialized": self.initialized,
            "opened": self.opened,
            "library_loaded": self.lib is not None,
            "api_version": None,
            "device_path": self.device_path,
            "pin_state": None,
            "life_cycle_state": None,
            "time_error": self.time_error,
        }
        if self.lib is not None:
            try:
                result["api_version"] = self.lib.se_getApiVersionString().decode("utf-8", "replace")
            except Exception:
                pass
            if self.opened:
                result["pin_state"] = self.pin_state()
                result["life_cycle_state"] = self.life_cycle_state()
                self.initialized = result["life_cycle_state"] == LCS_ACTIVE
                result["initialized"] = self.initialized
        return result

    def initialize(self, admin_pin, admin_puk, time_admin_pin, time_admin_puk):
        """First use of a brand-new TSE (`se_initializePinValues` + `se_initialize`).

        Sets both PINs and both PUKs (only possible while the TSE is still in
        transport state; PUKs cannot be changed afterwards), initializes the TSE,
        sets its time and registers this client id. An already commissioned TSE is
        only checked - the SE API has no way to change PINs or PUKs then.
        """
        if self.lib is None:
            self.initialized = True
            return {"status": "initialized (stub: no C library)"}
        if not self._open():
            return {"status": "failed: device not available", "device_path": self.device_path}

        state = self.pin_state()
        if state is None:
            return {"status": "failed: se_getPinStatus"}
        result = {"transport_state": state != PIN_STATE_INITIALIZED}
        if result["transport_state"]:
            rc = self.lib.se_initializePinValues(
                admin_pin, len(admin_pin), admin_puk, len(admin_puk),
                time_admin_pin, len(time_admin_pin), time_admin_puk, len(time_admin_puk),
            )
            if rc != 0:
                return {**result, "status": f"failed: se_initializePinValues ({rc})"}
            result["transport_state"] = self.pin_state() != PIN_STATE_INITIALIZED
            if result["transport_state"]:
                return {**result, "status": "failed: PINs and PUKs are still in transport state"}
        else:
            result["status"] = "already commissioned"

        lcs = self.life_cycle_state()
        if lcs == LCS_NOT_INITIALIZED:
            if not self._authenticate("Admin", admin_pin):
                return {**result, "status": "failed: Admin authentication"}
            rc = self.lib.se_initialize()
            if rc != 0:
                self._log_out("Admin")
                return {**result, "status": f"failed: se_initialize ({rc})"}
            self.initialized = True
        elif lcs not in (LCS_NO_TIME, LCS_ACTIVE):
            return {**result, "status": f"failed: life cycle state {lcs}"}

        if not self._ensure_time(time_admin_pin, force=True):
            return {**result, "status": f"failed: {self.time_error}"}
        if not self.register_client():
            self._log_out("Admin")
            return {**result, "status": "failed: se_registerClient"}
        self._log_out("Admin")

        state = self.status()
        return {**result, **state, "status": "initialized"}

    def ensure_ready(self):
        """Open the device and keep its time set, without touching PINs or PUKs."""
        if self.lib is None:
            self.initialized = True
            return {"status": "initialized (stub: no C library)"}
        if not self._open():
            return {"status": "failed: device not available", "device_path": self.device_path}
        ready = self._ensure_time()
        self.initialized = self.life_cycle_state() == LCS_ACTIVE
        return {"status": "initialized" if ready else f"failed: {self.time_error}", **self.status()}

    def close(self):
        if self.lib is not None and self.opened:
            try:
                self.lib.se_close()
            except Exception:
                pass
        self.opened = False
        self.initialized = False
        self._next_sync = 0

    def start_transaction(self):
        """Start a Vorgang. processType/processData stay empty (DSFinV-K)."""
        if not self._ensure_open():
            return {
                "transaction_number": 1,
                "signature_counter": 1,
                "transaction_start": now_iso(),
                "tse_error": "device not available (stub)",
            }
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
                "transaction_start": None,
                "tse_error": f"startTransaction failed: {rc}",
            }
        self.lib.se_free(start_res.signatureValue)
        self.lib.se_free(start_res.serialNumber)
        return {
            "transaction_number": start_res.transactionNumber,
            "signature_counter": start_res.signatureCounter,
            "transaction_start": _log_time(start_res.logTime),
            "tse_error": None,
        }

    def finish_transaction(self, transaction_number, process_type, process_data):
        """Finish a started Vorgang with its processType and processData."""
        if not self._ensure_open():
            return {
                "signature_counter": 1,
                "signature_base64": "DUMMY_SIGNATURE",
                "transaction_end": now_iso(),
                "tse_error": "device not available (stub)",
            }
        import base64

        proc_bytes = (process_data or "").encode("utf-8")
        ptype = (process_type or "").encode("utf-8")
        finish_res = SeFinishTransactionResult()
        rc = self.lib.se_finishTransaction(
            CLIENT_ID, len(CLIENT_ID),
            transaction_number,
            proc_bytes, len(proc_bytes),
            ptype, len(ptype),
            None, 0,
            ctypes.byref(finish_res),
        )
        if rc != 0:
            return {
                "signature_counter": None,
                "signature_base64": None,
                "transaction_end": None,
                "tse_error": f"finishTransaction failed: {rc}",
            }
        sig_b64 = ""
        if finish_res.signatureValue and finish_res.signatureValueLength:
            raw = bytes(finish_res.signatureValue[:finish_res.signatureValueLength])
            sig_b64 = base64.b64encode(raw).decode("ascii")
            self.lib.se_free(finish_res.signatureValue)
            self.lib.se_free(finish_res.serialNumber)
        return {
            "signature_counter": finish_res.signatureCounter,
            "signature_base64": sig_b64,
            "transaction_end": _log_time(finish_res.logTime),
            "tse_error": None,
        }

    def abort_transaction(self, transaction_number, process_type=PROCESS_TYPE):
        """Abort a started Vorgang: the sale did not happen, nothing was paid."""
        return self.finish_transaction(transaction_number, process_type, ABORT_PROCESS_DATA)

    def create_transaction(self, process_type, process_data, training=False):
        """Start and finish in one go (stornos at the counter, scripted bookings)."""
        started = self.start_transaction()
        if started["transaction_number"] is None:
            return {**started, "signature_base64": None, "transaction_end": None}
        finished = self.finish_transaction(
            started["transaction_number"], process_type or PROCESS_TYPE, process_data
        )
        return {**started, **finished}

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

    def export_certificates(self):
        if not self._ensure_open():
            return b""
        exported = ctypes.POINTER(ctypes.c_ubyte)()
        length = ctypes.c_uint32(0)
        try:
            rc = self.lib.se_exportCertificates(ctypes.byref(exported), ctypes.byref(length))
            if rc != 0 or not exported or length.value == 0:
                return b""
            data = bytes(exported[:length.value])
            self.lib.se_free(exported)
            return data
        except Exception:
            return b""

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