from __future__ import annotations

import base64
import hashlib
import struct
import unittest

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

from lease_tracker.wecom_callback import WeComCallbackCrypto, extract_text_message


def encrypt_payload(key: bytes, xml_text: str, corp_id: str) -> str:
    raw = b"0123456789abcdef" + struct.pack(">I", len(xml_text.encode("utf-8")))
    raw += xml_text.encode("utf-8") + corp_id.encode("utf-8")
    pad = 32 - (len(raw) % 32)
    raw += bytes([pad]) * pad
    cipher = Cipher(algorithms.AES(key), modes.CBC(key[:16]))
    encryptor = cipher.encryptor()
    return base64.b64encode(encryptor.update(raw) + encryptor.finalize()).decode("ascii")


def signature(token: str, timestamp: str, nonce: str, encrypted: str) -> str:
    return hashlib.sha1("".join(sorted([token, timestamp, nonce, encrypted])).encode("utf-8")).hexdigest()


class WeComCallbackTest(unittest.TestCase):
    def test_decrypt_xml_and_extract_text(self) -> None:
        token = "query-token"
        corp_id = "ww-test-corp"
        key = bytes(range(32))
        encoding_key = base64.b64encode(key).decode("ascii").rstrip("=")
        message_xml = (
            "<xml>"
            "<FromUserName>user-a</FromUserName>"
            "<CreateTime>1782260000</CreateTime>"
            "<MsgType>text</MsgType>"
            "<Content>South Loop Tracker Arrive Lex现在有多少available lease</Content>"
            "</xml>"
        )
        encrypted = encrypt_payload(key, message_xml, corp_id)
        timestamp = "1782260001"
        nonce = "nonce"
        envelope = f"<xml><Encrypt>{encrypted}</Encrypt></xml>".encode("utf-8")

        crypto = WeComCallbackCrypto(token, encoding_key, corp_id)
        decrypted = crypto.decrypt_xml(signature(token, timestamp, nonce, encrypted), timestamp, nonce, envelope)
        parsed = extract_text_message(decrypted)

        self.assertEqual(parsed.sender, "user-a")
        self.assertEqual(parsed.msg_type, "text")
        self.assertIn("South Loop Tracker", parsed.content)

    def test_rejects_bad_signature(self) -> None:
        token = "query-token"
        corp_id = "ww-test-corp"
        key = bytes(range(32))
        encoding_key = base64.b64encode(key).decode("ascii").rstrip("=")
        encrypted = encrypt_payload(key, "<xml><MsgType>text</MsgType></xml>", corp_id)
        envelope = f"<xml><Encrypt>{encrypted}</Encrypt></xml>".encode("utf-8")

        crypto = WeComCallbackCrypto(token, encoding_key, corp_id)
        with self.assertRaises(ValueError):
            crypto.decrypt_xml("bad-signature", "1", "n", envelope)

    def test_allows_empty_receive_id_for_internal_intelligent_robot(self) -> None:
        token = "query-token"
        key = bytes(range(32))
        encoding_key = base64.b64encode(key).decode("ascii").rstrip("=")
        encrypted = encrypt_payload(key, "<xml><MsgType>text</MsgType></xml>", "")
        timestamp = "1782260001"
        nonce = "nonce"
        envelope = f"<xml><Encrypt>{encrypted}</Encrypt></xml>".encode("utf-8")

        crypto = WeComCallbackCrypto(token, encoding_key)
        decrypted = crypto.decrypt_xml(signature(token, timestamp, nonce, encrypted), timestamp, nonce, envelope)

        self.assertIn("<MsgType>text</MsgType>", decrypted)


if __name__ == "__main__":
    unittest.main()
