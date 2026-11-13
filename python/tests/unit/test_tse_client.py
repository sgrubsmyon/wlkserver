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
    monkeypatch.setattr(client, "_next_sync", 0)
    # all four PIN/PUK flags set (transport state), then initialized
    states = iter([0x0F, 0])
    monkeypatch.setattr(client, "pin_state", lambda: next(states, 0))
    lcs = iter([tse_module.LCS_NOT_INITIALIZED])
    monkeypatch.setattr(client, "life_cycle_state", lambda: next(lcs, tse_module.LCS_NO_TIME))

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


def test_recommissioning_an_initialized_tse_is_refused(monkeypatch):
    """A re-run must not authenticate TimeAdmin with the request PIN (gap G4)."""
    calls = []

    class FakeLib:
        def se_getPinStatus(self, state):
            state._obj.value = tse_module.PIN_STATE_INITIALIZED
            return 0

        def se_getLifeCycleState(self, state):
            state._obj.value = tse_module.LCS_ACTIVE
            return 0

        def se_authenticateUser(self, *args):
            calls.append("authenticateUser")
            return 0

        def se_updateTime(self, now):
            calls.append("updateTime")
            return 0

    client = tse_module.tse_client
    monkeypatch.setattr(client, "lib", FakeLib())
    monkeypatch.setattr(client, "_open", lambda: True)

    result = client.initialize(
        b"12345678", b"1234567890", b"87654321", b"0987654321"
    )

    assert result["status"].startswith("failed: already commissioned")
    assert calls == []


def _time_fake(pin_state, lcs, calls):
    class FakeLib:
        def se_getPinStatus(self, state):
            calls.append("pin_state")
            state._obj.value = pin_state
            return 0

        def se_getLifeCycleState(self, state):
            calls.append("lcs")
            state._obj.value = lcs
            return 0

        def se_authenticateUser(self, user, user_len, pin, pin_len, result, retries):
            calls.append("auth")
            result._obj.value = 0
            return 0

        def se_updateTime(self, now):
            calls.append("updateTime")
            return 0

        def se_getTimeSyncInterval(self, interval):
            interval._obj.value = 0
            return 0

        def se_logOut(self, user, user_len):
            return 0

    return FakeLib()


def test_ensure_time_skips_uncommissioned_tse(monkeypatch):
    """No TimeAdmin authentication before the PINs are set (would burn retries)."""
    calls = []
    client = tse_module.tse_client
    monkeypatch.setattr(
        client,
        "lib",
        _time_fake(0x0F, tse_module.LCS_NOT_INITIALIZED, calls),
    )
    monkeypatch.setattr(client, "_next_sync", 0)
    monkeypatch.setattr(client, "time_error", None)

    assert client._ensure_time(b"12345678") is False
    assert calls == ["pin_state", "lcs"]
    assert "not ready" in client.time_error


def test_ensure_time_updates_commissioned_tse(monkeypatch):
    calls = []
    client = tse_module.tse_client
    monkeypatch.setattr(
        client,
        "lib",
        _time_fake(0, tse_module.LCS_ACTIVE, calls),
    )
    monkeypatch.setattr(client, "_next_sync", 0)

    assert client._ensure_time(b"12345678") is True
    assert calls == ["pin_state", "lcs", "auth", "updateTime"]


def test_ensure_time_does_not_touch_the_tse_before_the_interval(monkeypatch):
    class ExplodingLib:
        def __getattr__(self, name):
            raise AssertionError(f"{name} must not be called before the interval")

    client = tse_module.tse_client
    monkeypatch.setattr(client, "lib", ExplodingLib())
    monkeypatch.setattr(client, "_next_sync", 2**62)

    assert client._ensure_time(b"12345678") is True
