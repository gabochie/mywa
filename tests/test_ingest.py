import unittest
import os
from mywa.ingest import detect_kind

class TestIngest(unittest.TestCase):
    def setUp(self):
        self.testdata = "testdata"

    def test_detect_kind(self):
        self.assertEqual(detect_kind(os.path.join(self.testdata, "contacts.vcf")), "vcf")
        self.assertEqual(detect_kind(os.path.join(self.testdata, "adb_contacts.tsv")), "tsv")
        # wa.db and msgstore.db might depend on sqlite, let's just check if detection returns expected type
        self.assertEqual(detect_kind(os.path.join(self.testdata, "wa.db")), "wa.db")
        self.assertEqual(detect_kind(os.path.join(self.testdata, "msgstore.db")), "msgstore.db")

if __name__ == "__main__":
    unittest.main()
