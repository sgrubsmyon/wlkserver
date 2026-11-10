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
