from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from lease_tracker.query_setup import GeneratedQuerySecrets, write_generated_secrets_to_env


class QuerySetupEnvTest(unittest.TestCase):
    def test_write_generated_secrets_to_env_preserves_other_values(self) -> None:
        generated = GeneratedQuerySecrets("gateway-token", "callback-token", "A" * 43)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "tracker.env"
            path.write_text(
                "GOOGLE_SHEET_ID=sheet-id\n"
                "QUERY_GATEWAY_TOKEN=\n"
                "WECOM_CALLBACK_TOKEN=\n"
                "WECOM_CALLBACK_ENCODING_AES_KEY=\n"
                "WECOM_CORP_ID=\n",
                encoding="utf-8",
            )

            write_generated_secrets_to_env(path, generated)

            text = path.read_text(encoding="utf-8")
            self.assertIn("GOOGLE_SHEET_ID=sheet-id", text)
            self.assertIn("QUERY_GATEWAY_TOKEN=gateway-token", text)
            self.assertIn("WECOM_CALLBACK_TOKEN=callback-token", text)
            self.assertIn("WECOM_CALLBACK_ENCODING_AES_KEY=" + "A" * 43, text)
            self.assertIn("WECOM_CORP_ID=", text)


if __name__ == "__main__":
    unittest.main()
