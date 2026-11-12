from python.utils import tse_client as tse_module
from python.utils.tse_client import _first_serial_number, _oid_from_asn1

# ASN.1 dump of a cryptovision TSE (TSEUntar.java:89): algorithm=ecdsa-plain-SHA256.
_SHA256_OID_TLV = bytes.fromhex("060a04007f00070101040103")
_SHA256_OID_CONTENT = bytes.fromhex("04007f00070101040103")


def test_oid_from_asn1_full_tlv():
    assert _oid_from_asn1(_SHA256_OID_TLV) == "0.4.0.127.0.7.1.1.4.1.3"


def test_oid_from_asn1_raw_content():
    assert _oid_from_asn1(_SHA256_OID_CONTENT) == "0.4.0.127.0.7.1.1.4.1.3"


def test_oid_from_asn1_empty():
    assert _oid_from_asn1(b"") is None


def test_first_serial_number_offset():
    # Mirrors the vendor test / Java offset: 04 20 <32 bytes> at index 4/6.
    serial = bytes(range(32))
    data = bytes([0x30, 0x24, 0x00, 0x00, 0x04, 0x20]) + serial
    assert _first_serial_number(data) == serial


def test_first_serial_number_rejects_other_encoding():
    assert _first_serial_number(bytes([0x30, 5, 0x04, 0x01, 1, 2, 3])) is None


def test_commissioning_uses_v3_puk_and_unblock(monkeypatch):
    """SE-API v3.1 first boot: `se_initializePuk` + `se_unblockUser` per user.

    `se_initializePinValues` is deprecated in v3.1 (communication timeouts), so
    it must not be used for a brand-new TSE.
    """
    calls = []

    class FakeLib:
        def se_initializePuk(self, user, user_len, puk, puk_len):
            calls.append(("initializePuk", user, puk))
            return 0

        def se_unblockUser(self, user, user_len, puk, puk_len, pin, pin_len, result):
            calls.append(("unblockUser", user, puk, pin))
            result._obj.value = 0
            return 0

        def se_authenticateUser(self, user, user_len, pin, pin_len, result, retries):
            result._obj.value = 0
            return 0

        def se_initialize(self):
            return 0

        def se_updateTime(self, now):
            return 0

        def se_getTimeSyncInterval(self, interval):
            interval._obj.value = 0
            return 0

        def se_registerClient(self, client_id, client_id_len):
            return 0

        def se_logOut(self, user, user_len):
            return 0

    client = tse_module.tse_client
    monkeypatch.setattr(client, "lib", FakeLib())
    monkeypatch.setattr(client, "_open", lambda: True)
    monkeypatch.setattr(client, "status", lambda: {})
    # all four PIN/PUK flags set (transport state), then initialized
    states = iter([0x0F, 0])
    monkeypatch.setattr(client, "pin_state", lambda: next(states))
    monkeypatch.setattr(client, "life_cycle_state", lambda: tse_module.LCS_NOT_INITIALIZED)

    result = client.initialize(
        b"12345678", b"1234567890", b"87654321", b"0987654321"
    )

    assert result["status"] == "initialized"
    assert calls == [
        ("initializePuk", b"Admin", b"1234567890"),
        ("unblockUser", b"Admin", b"1234567890", b"12345678"),
        ("initializePuk", b"TimeAdmin", b"0987654321"),
        ("unblockUser", b"TimeAdmin", b"0987654321", b"87654321"),
    ]
