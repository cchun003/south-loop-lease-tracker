from __future__ import annotations

import unittest

from lease_tracker.query_setup import generate_query_secrets, valid_encoding_key_shape
from lease_tracker.wecom_callback import WeComCallbackCrypto


class QuerySetupTest(unittest.TestCase):
    def test_generate_query_secrets_have_valid_shapes(self) -> None:
        generated = generate_query_secrets()

        self.assertTrue(generated.query_gateway_token)
        self.assertTrue(generated.wecom_callback_token)
        self.assertTrue(valid_encoding_key_shape(generated.wecom_callback_encoding_aes_key))
        self.assertEqual(len(generated.env_lines()), 3)

    def test_generated_encoding_key_initializes_callback_crypto(self) -> None:
        generated = generate_query_secrets()
        crypto = WeComCallbackCrypto(
            generated.wecom_callback_token,
            generated.wecom_callback_encoding_aes_key,
        )

        self.assertEqual(crypto.receive_id, "")


if __name__ == "__main__":
    unittest.main()
