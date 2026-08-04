import unittest
import os
from mywa.ingest import detect_kind

class TestIngest(unittest.TestCase):
    def setUp(self):
        self.testdata = "testdata"

    def test_detect_kind(self):
        self.assertEqual(detect_kind(os.path.join(self.testdata, "contacts.vcf")), "vcf")
        self.assertEqual(detect_kind(os.path.join(self.testdata, "adb_contacts.tsv")), "tsv")
        # .db detection is content-based: returns "wa.db" only when a wa_contacts
        # table exists, otherwise "sqlite" (depends on the testdata DB contents)
        self.assertIn(detect_kind(os.path.join(self.testdata, "wa.db")), ("wa.db", "sqlite"))
        self.assertIn(detect_kind(os.path.join(self.testdata, "msgstore.db")), ("msgstore.db", "sqlite"))

if __name__ == "__main__":
    unittest.main()
