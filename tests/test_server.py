import json
import os
import tempfile
import threading
import unittest
import urllib.request
from http.server import ThreadingHTTPServer

_TEST_STATE = tempfile.mkdtemp(prefix="mywa_test_state_")
os.environ["MYWA_STATE"] = _TEST_STATE

from mywa.server import DashboardHandler, _parse_multipart, _validate_upload

_BOUNDARY = "----mywa-test-boundary"
_MULTIPART_CT = f"multipart/form-data; boundary={_BOUNDARY}"


def _multipart_body() -> bytes:
    """Hand-built multipart/form-data body with a text field + one file part."""
    parts = [
        b"--" + _BOUNDARY.encode(),
        b'Content-Disposition: form-data; name="country_code"',
        b"",
        b"GH",
        b"--" + _BOUNDARY.encode(),
        b'Content-Disposition: form-data; name="file"; filename="contacts.vcf"',
        b"Content-Type: text/vcard",
        b"",
        b"BEGIN:VCARD",
        b"END:VCARD",
        b"--" + _BOUNDARY.encode() + b"--",
    ]
    return b"\r\n".join(parts)


class TestParseMultipart(unittest.TestCase):
    def test_parses_text_and_file_fields(self):
        parsed = _parse_multipart(_multipart_body(), _MULTIPART_CT)
        self.assertEqual(parsed["country_code"], b"GH")
        self.assertEqual(parsed["file"], b"BEGIN:VCARD\r\nEND:VCARD")
        self.assertEqual(parsed["filename"], "contacts.vcf")

    def test_non_multipart_returns_empty(self):
        self.assertEqual(_parse_multipart(b"name=foo", "application/x-www-form-urlencoded"), {})
        self.assertEqual(_parse_multipart(b"", "multipart/form-data; boundary=x"), {})


class TestValidateUpload(unittest.TestCase):
    def test_accepts_allowed_extensions(self):
        for ext in (".db", ".vcf", ".csv", ".tsv"):
            ok, name = _validate_upload(f"contacts{ext}", 1024)
            self.assertTrue(ok)
            self.assertEqual(name, f"contacts{ext}")

    def test_rejects_disallowed_extension(self):
        ok, reason = _validate_upload("evil.exe", 1024)
        self.assertFalse(ok)
        self.assertIn("unsupported", reason)

    def test_rejects_oversized_file(self):
        ok, reason = _validate_upload("big.db", 50 * 1024 * 1024 + 1)
        self.assertFalse(ok)
        self.assertIn("50 MB", reason)

    def test_strips_path_components(self):
        ok, name = _validate_upload("C:\\Users\\attacker\\..\\..\\contacts.vcf", 1024)
        self.assertTrue(ok)
        self.assertEqual(name, "contacts.vcf")


class TestUploadEndpoint(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.httpd = ThreadingHTTPServer(("127.0.0.1", 0), DashboardHandler)
        cls.port = cls.httpd.server_address[1]
        cls.thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.httpd.server_close()

    def _post_upload(self, path, filename="sample_contacts.vcf"):
        with open(path, "rb") as fh:
            file_bytes = fh.read()
        boundary = "----mywa-upload-test"
        body = (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
            "Content-Type: text/vcard\r\n"
            "\r\n"
        ).encode("utf-8") + file_bytes + f"\r\n--{boundary}--\r\n".encode("utf-8")
        req = urllib.request.Request(
            f"http://127.0.0.1:{self.port}/api/upload",
            data=body,
            headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def test_upload_runs_pipeline_and_reloads_data(self):
        fixture = os.path.join(os.path.dirname(__file__), "fixtures", "sample_contacts.vcf")
        result = self._post_upload(fixture)
        self.assertTrue(result["ok"])
        self.assertGreaterEqual(result["count"], 2)
        self.assertGreaterEqual(len(DashboardHandler.data), 2)
        demo_out = os.path.join(_TEST_STATE, "demo_out")
        self.assertTrue(os.path.exists(os.path.join(demo_out, "contacts.json")))

    def test_upload_rejects_disallowed_extension(self):
        fixture = os.path.join(os.path.dirname(__file__), "fixtures", "evil.exe")
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            self._post_upload(fixture, filename="evil.exe")
        self.assertEqual(ctx.exception.code, 400)


if __name__ == "__main__":
    unittest.main()
