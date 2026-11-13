"""Adapter module for the TSE (Technical Security Equipment).

Wraps the cryptovision SE-API C library (libse-api-c.so) with ctypes. The
high-level transaction/export orchestration mirrors the Java POS
(WeltladenTSE.java) as closely as possible, but is untested without real
hardware and may need adjustments.
"""

import ctypes
import logging
import os
from base64 import b64encode
from datetime import datetime
from io import BytesIO
from tarfile import open as tarfile_open

from .. import config

logger = logging.getLogger(__name__)

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

# `se_sync_variants_t` (se_types.h).
TIME_SYNC_VARIANTS = {0: "noInput", 1: "utcTime", 2: "generalizedTime", 3: "unixTime"}
# BSI TR-03151 signature algorithm OIDs (Java `WeltladenTSE.getSignatureAlgorithm`).
SIGNATURE_ALGORITHMS = {
    "0.4.0.127.0.7.1.1.4.1.1": "ecdsa-plain-SHA1",
    "0.4.0.127.0.7.1.1.4.1.2": "ecdsa-plain-SHA224",
    "0.4.0.127.0.7.1.1.4.1.3": "ecdsa-plain-SHA256",
    "0.4.0.127.0.7.1.1.4.1.4": "ecdsa-plain-SHA384",
    "0.4.0.127.0.7.1.1.4.1.5": "ecdsa-plain-SHA512",
    "0.4.0.127.0.7.1.1.4.1.6": "ecdsa-plain-RIPEMD160",
    "0.4.0.127.0.7.3.7.1.1": "id-SE-API-transaction-log",
    "0.4.0.127.0.7.3.7.1.2": "id-SE-API-system-log",
    "0.4.0.127.0.7.3.7.1.3": "id-SE-API-SE-audit-log",
}


def _oid_from_asn1(data: bytes) -> str | None:
    """Dotted OID from the ASN.1 OBJECT IDENTIFIER the TSE returns.

    Accepts both the full TLV (tag 0x06 + length + content) and the raw content
    octets (base-128, first byte combines the first two arcs).
    """
    if len(data) >= 3 and data[0] == 0x06 and data[1] == len(data) - 2:  # TLV wrapper
        data = data[2:]
    if not data:
        return None
    arcs = [str(data[0] // 40), str(data[0] % 40)]
    value = 0
    for byte in data[1:]:
        value = (value << 7) | (byte & 0x7F)
        if not byte & 0x80:
            arcs.append(str(value))
            value = 0
    return ".".join(arcs)


def _first_serial_number(data: bytes) -> bytes | None:
    """First key serial (32-byte OCTET STRING) of the TR-03151 export.

    Layout `30 <len> 04 20 <32 bytes>` as assumed by the vendor test and Java
    `WeltladenTSE.updateTSEStatusValues` (`Arrays.copyOfRange(data, 6, 6+32)`).
    """
    if len(data) >= 38 and data[4] == 0x04 and data[5] == 0x20:
        return bytes(data[6:38])
    return None


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
            # v3.1 order: processData before processType (se_api.h:748).
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
            # v3.1 first boot: initializePuk + unblockUser instead of the
            # deprecated initializePinValues (four writes can time out, se_api.h:414).
            lib.se_initializePuk.argtypes = [
                ctypes.c_char_p, ctypes.c_uint32, ctypes.c_char_p, ctypes.c_uint32,
            ]
            lib.se_initializePuk.restype = ctypes.c_int
            lib.se_unblockUser.argtypes = [
                ctypes.c_char_p, ctypes.c_uint32, ctypes.c_char_p, ctypes.c_uint32,
                ctypes.c_char_p, ctypes.c_uint32, ctypes.POINTER(ctypes.c_int),
            ]
            lib.se_unblockUser.restype = ctypes.c_int
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
            # Status getters (TSE identification for `abrechnung_tag_tse` / DSFinV-K tse.csv).
            lib.se_getUniqueId.argtypes = [ctypes.POINTER(ctypes.c_uint32)]
            lib.se_getUniqueId.restype = ctypes.c_void_p
            lib.se_getCertificationId.argtypes = [
                ctypes.POINTER(ctypes.c_char_p), ctypes.POINTER(ctypes.c_uint32),
            ]
            lib.se_getCertificationId.restype = ctypes.c_int
            lib.se_getFirmwareId.argtypes = []
            lib.se_getFirmwareId.restype = ctypes.c_char_p
            lib.se_getCertificateExpirationDate.argtypes = [
                ctypes.POINTER(ctypes.c_ubyte), ctypes.c_uint32,
                ctypes.POINTER(ctypes.c_int64),
            ]
            lib.se_getCertificateExpirationDate.restype = ctypes.c_int
            lib.se_exportSerialNumbers.argtypes = [
                ctypes.POINTER(ctypes.POINTER(ctypes.c_ubyte)), ctypes.POINTER(ctypes.c_uint32),
            ]
            lib.se_exportSerialNumbers.restype = ctypes.c_int
            lib.se_exportPublicKey.argtypes = [
                ctypes.c_char_p, ctypes.c_uint32,
                ctypes.POINTER(ctypes.POINTER(ctypes.c_ubyte)), ctypes.POINTER(ctypes.c_uint32),
            ]
            lib.se_exportPublicKey.restype = ctypes.c_int
            lib.se_getSignatureAlgorithm.argtypes = [
                ctypes.POINTER(ctypes.POINTER(ctypes.c_ubyte)), ctypes.POINTER(ctypes.c_uint32),
            ]
            lib.se_getSignatureAlgorithm.restype = ctypes.c_int
            lib.se_getTimeSyncVariant.argtypes = [ctypes.POINTER(ctypes.c_int)]
            lib.se_getTimeSyncVariant.restype = ctypes.c_int
            lib.se_getTransactionCounter.argtypes = [ctypes.POINTER(ctypes.c_uint32)]
            lib.se_getTransactionCounter.restype = ctypes.c_int
            lib.se_getWearIndicator.argtypes = [ctypes.POINTER(ctypes.c_uint32)]
            lib.se_getWearIndicator.restype = ctypes.c_int
            lib.se_getTotalLogMemory.argtypes = [ctypes.POINTER(ctypes.c_uint64)]
            lib.se_getTotalLogMemory.restype = ctypes.c_int
            lib.se_getAvailableLogMemory.argtypes = [ctypes.POINTER(ctypes.c_uint64)]
            lib.se_getAvailableLogMemory.restype = ctypes.c_int
            lib.se_getMaxNumberOfClients.argtypes = [ctypes.POINTER(ctypes.c_uint32)]
            lib.se_getMaxNumberOfClients.restype = ctypes.c_int
            lib.se_getCurrentNumberOfClients.argtypes = [ctypes.POINTER(ctypes.c_uint32)]
            lib.se_getCurrentNumberOfClients.restype = ctypes.c_int
            lib.se_getMaxNumberOfTransactions.argtypes = [ctypes.POINTER(ctypes.c_uint32)]
            lib.se_getMaxNumberOfTransactions.restype = ctypes.c_int
            lib.se_getCurrentNumberOfTransactions.argtypes = [ctypes.POINTER(ctypes.c_uint32)]
            lib.se_getCurrentNumberOfTransactions.restype = ctypes.c_int
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
        # Never authenticate TimeAdmin on a TSE that is not commissioned yet: a
        # failed attempt would burn PIN retries before the PINs are even set.
        pin_state = self.pin_state()
        lcs = self.life_cycle_state()
        if pin_state != PIN_STATE_INITIALIZED or lcs not in (LCS_NO_TIME, LCS_ACTIVE):
            self.time_error = (
                f"TSE not ready for a time update (pin_state={pin_state}, lcs={lcs})"
            )
            return False
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
                result["tse"] = self.status_values()
        return result

    def status_values(self):
        """TSE identification values (Java `WeltladenTSE.updateTSEStatusValues`).

        Returns None when the TSE is not available; a dict with None entries
        where a single read failed. The settlement stores NULLs like Java does
        when the TSE is not operational.
        """
        if not self._open():
            return None
        values = {
            "unique_id": None,
            "certification_id": None,
            "firmware_id": None,
            "serial_number": None,
            "public_key": None,
            "signature_algorithm": None,
            "time_sync_variant": None,
            "certificate": None,
            "certificate_expiration": None,
            "transaction_counter": None,
            "signature_counter": None,
            "total_log_memory": None,
            "available_log_memory": None,
            "wear_indicator": None,
            "max_clients": None,
            "current_clients": None,
            "max_transactions": None,
            "current_transactions": None,
        }
        try:
            length = ctypes.c_uint32(0)
            raw_id = self.lib.se_getUniqueId(ctypes.byref(length))
            if raw_id:
                values["unique_id"] = ctypes.string_at(raw_id, length.value).hex()
            # not null terminated (se_api.h): read exactly `cert_id_len` bytes
            cert_id = ctypes.c_char_p()
            cert_id_len = ctypes.c_uint32(0)
            if self.lib.se_getCertificationId(
                ctypes.byref(cert_id), ctypes.byref(cert_id_len)
            ) == 0 and cert_id:
                values["certification_id"] = ctypes.string_at(
                    cert_id, cert_id_len.value
                ).decode("utf-8", "replace")
                self.lib.se_free(cert_id)
            firmware = self.lib.se_getFirmwareId()
            if firmware:
                values["firmware_id"] = firmware.decode("utf-8", "replace")

            serials = ctypes.POINTER(ctypes.c_ubyte)()
            serials_len = ctypes.c_uint32(0)
            if self.lib.se_exportSerialNumbers(
                ctypes.byref(serials), ctypes.byref(serials_len)
            ) == 0 and serials:
                serial = _first_serial_number(bytes(serials[:serials_len.value]))
                self.lib.se_free(serials)
                if serial is not None:
                    values["serial_number"] = serial.hex()
                    public_key = ctypes.POINTER(ctypes.c_ubyte)()
                    public_key_len = ctypes.c_uint32(0)
                    if self.lib.se_exportPublicKey(
                        serial, len(serial),
                        ctypes.byref(public_key), ctypes.byref(public_key_len),
                    ) == 0 and public_key:
                        values["public_key"] = b64encode(
                            bytes(public_key[:public_key_len.value])
                        ).decode("ascii")
                        self.lib.se_free(public_key)
                    values["certificate"] = self._certificate_for(serial)
                    # certificate expiration of that key (Java uses the serial too)
                    expiration = ctypes.c_int64(0)
                    if self.lib.se_getCertificateExpirationDate(
                        serial, len(serial), ctypes.byref(expiration)
                    ) == 0:
                        values["certificate_expiration"] = expiration.value
                else:
                    values["tse_error"] = "unexpected serial number encoding"

            algorithm = ctypes.POINTER(ctypes.c_ubyte)()
            algorithm_len = ctypes.c_uint32(0)
            if self.lib.se_getSignatureAlgorithm(
                ctypes.byref(algorithm), ctypes.byref(algorithm_len)
            ) == 0 and algorithm:
                oid = _oid_from_asn1(bytes(algorithm[:algorithm_len.value]))
                self.lib.se_free(algorithm)
                values["signature_algorithm"] = SIGNATURE_ALGORITHMS.get(oid, "unknown")

            variant = ctypes.c_int(0)
            if self.lib.se_getTimeSyncVariant(ctypes.byref(variant)) == 0:
                values["time_sync_variant"] = TIME_SYNC_VARIANTS.get(
                    variant.value, str(variant.value)
                )

            values["signature_counter"] = self.get_signature_counter()
            counter = ctypes.c_uint32(0)
            if self.lib.se_getTransactionCounter(ctypes.byref(counter)) == 0:
                values["transaction_counter"] = counter.value
            if self.lib.se_getWearIndicator(ctypes.byref(counter)) == 0:
                values["wear_indicator"] = counter.value
            if self.lib.se_getMaxNumberOfClients(ctypes.byref(counter)) == 0:
                values["max_clients"] = counter.value
            if self.lib.se_getCurrentNumberOfClients(ctypes.byref(counter)) == 0:
                values["current_clients"] = counter.value
            if self.lib.se_getMaxNumberOfTransactions(ctypes.byref(counter)) == 0:
                values["max_transactions"] = counter.value
            if self.lib.se_getCurrentNumberOfTransactions(ctypes.byref(counter)) == 0:
                values["current_transactions"] = counter.value
            memory = ctypes.c_uint64(0)
            if self.lib.se_getTotalLogMemory(ctypes.byref(memory)) == 0:
                values["total_log_memory"] = memory.value
            if self.lib.se_getAvailableLogMemory(ctypes.byref(memory)) == 0:
                values["available_log_memory"] = memory.value
        except Exception:
            logger.exception("Reading TSE status values failed")
        return values

    def _certificate_for(self, serial: bytes) -> str | None:
        """Certificate for a key serial from the certificate export tar.

        Java `TSEUntar.exportCertificate`: the tar entry name starts with the
        hex serial number.
        """
        data = self.export_certificates()
        if not data:
            return None
        try:
            prefix = serial.hex()
            with tarfile_open(fileobj=BytesIO(data)) as tf:
                for member in tf.getmembers():
                    if member.name.startswith(prefix):
                        file = tf.extractfile(member)
                        if file is not None:
                            return b64encode(file.read()).decode("ascii")
        except Exception:
            logger.exception("Extracting the TSE certificate failed")
        return None

    def initialize(self, admin_pin, admin_puk, time_admin_pin, time_admin_puk):
        """First use of a brand-new TSE (SE-API v3.1 `firstBootTest` sequence).

        Sets both PUKs (`se_initializePuk`) and both PINs (`se_unblockUser`)
        while the TSE is still in transport state (`se_initializePinValues` is
        deprecated in v3.1), initializes the TSE, sets its time and registers
        this client id. PUKs cannot be changed once set.
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
            # `se_pin_state_flags_t`: Admin PIN 0x01 / PUK 0x02,
            # TimeAdmin PIN 0x04 / PUK 0x08. PUKs and PINs are set per user so
            # a partially commissioned TSE is handled too.
            for user, puk, pin, pin_bit, puk_bit in (
                ("Admin", admin_puk, admin_pin, 0x01, 0x02),
                ("TimeAdmin", time_admin_puk, time_admin_pin, 0x04, 0x08),
            ):
                if state & puk_bit:
                    rc = self.lib.se_initializePuk(
                        user.encode(), len(user), puk, len(puk)
                    )
                    if rc != 0:
                        return {**result, "status": f"failed: se_initializePuk ({user}, {rc})"}
                if state & pin_bit:
                    unblock = ctypes.c_int(0)
                    rc = self.lib.se_unblockUser(
                        user.encode(), len(user), puk, len(puk), pin, len(pin),
                        ctypes.byref(unblock),
                    )
                    if rc != 0 or unblock.value != 0:
                        return {**result, "status": f"failed: se_unblockUser ({user}, {rc})"}
            result["transport_state"] = self.pin_state() != PIN_STATE_INITIALIZED
            if result["transport_state"]:
                return {**result, "status": "failed: PINs and PUKs are still in transport state"}
        else:
            result["status"] = "already commissioned"

        lcs = self.life_cycle_state()
        if state == PIN_STATE_INITIALIZED and lcs in (LCS_NO_TIME, LCS_ACTIVE):
            # Commissioning is one-shot; a re-run would only authenticate
            # TimeAdmin with the request PIN and burn retries (gap G4).
            return {
                **result,
                "status": "failed: already commissioned, use POST /tse/init without a body to refresh the time",
            }
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
        # Delete stored TSE data up to the current signature counter, on the
        # primary key (NULL key) like the export above.
        counter = self.get_signature_counter()
        if counter is not None and self.lib is not None and self.opened:
            try:
                self.lib.se_deleteStoredDataUpTo(None, 0, counter)
            except Exception:
                pass
        return data


# Module-level singleton used by the router.
tse_client = TSEClient()