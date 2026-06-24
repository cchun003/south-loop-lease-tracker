from __future__ import annotations

import base64
import hashlib
import struct
import xml.etree.ElementTree as ET
from dataclasses import dataclass

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes


@dataclass
class WeComTextMessage:
    sender: str
    content: str
    msg_type: str
    create_time: str


class WeComCallbackCrypto:
    def __init__(self, token: str, encoding_aes_key: str, receive_id: str = ""):
        if len(encoding_aes_key) != 43:
            raise ValueError("WECOM_CALLBACK_ENCODING_AES_KEY must be 43 characters.")
        self.token = token
        # WeCom internal intelligent robots use an empty ReceiveId.
        self.receive_id = receive_id
        self.key = base64.b64decode(encoding_aes_key + "=")
        if len(self.key) != 32:
            raise ValueError("Invalid WeCom callback AES key.")

    def verify_signature(self, signature: str, timestamp: str, nonce: str, encrypted: str) -> None:
        pieces = sorted([self.token, timestamp, nonce, encrypted])
        expected = hashlib.sha1("".join(pieces).encode("utf-8")).hexdigest()
        if expected != signature:
            raise ValueError("Invalid WeCom callback signature.")

    def decrypt_echo(self, signature: str, timestamp: str, nonce: str, echostr: str) -> str:
        self.verify_signature(signature, timestamp, nonce, echostr)
        return self.decrypt_payload(echostr)

    def decrypt_xml(self, signature: str, timestamp: str, nonce: str, body: bytes) -> str:
        root = ET.fromstring(body)
        encrypted = root.findtext("Encrypt") or ""
        self.verify_signature(signature, timestamp, nonce, encrypted)
        return self.decrypt_payload(encrypted)

    def decrypt_payload(self, encrypted: str) -> str:
        ciphertext = base64.b64decode(encrypted)
        cipher = Cipher(algorithms.AES(self.key), modes.CBC(self.key[:16]))
        decryptor = cipher.decryptor()
        padded = decryptor.update(ciphertext) + decryptor.finalize()
        plain = remove_pkcs7_padding(padded)
        msg_len = struct.unpack(">I", plain[16:20])[0]
        msg = plain[20 : 20 + msg_len]
        receive_id = plain[20 + msg_len :].decode("utf-8")
        if self.receive_id and receive_id != self.receive_id:
            raise ValueError("WeCom ReceiveId mismatch.")
        return msg.decode("utf-8")


def extract_text_message(xml_text: str) -> WeComTextMessage:
    root = ET.fromstring(xml_text.encode("utf-8"))
    return WeComTextMessage(
        sender=root.findtext("FromUserName") or "",
        content=root.findtext("Content") or "",
        msg_type=root.findtext("MsgType") or "",
        create_time=root.findtext("CreateTime") or "",
    )


def remove_pkcs7_padding(data: bytes) -> bytes:
    if not data:
        raise ValueError("Empty encrypted payload.")
    pad = data[-1]
    if pad < 1 or pad > 32:
        raise ValueError("Invalid PKCS7 padding.")
    return data[:-pad]
