import unittest
from mywa.models import Contact
from mywa.segmenter import segment, deduplicate

class TestSegmenter(unittest.TestCase):
    def setUp(self):
        self.c1 = Contact(name="Alice", numbers=["0241234567"], msg_count=60, groups=["Client"])
        self.c2 = Contact(name="Alice", numbers=["0241234567"], msg_count=10, groups=["Prospect"])
        self.c3 = Contact(name="Bob", numbers=["0501234567"], msg_count=0)

    def test_deduplicate(self):
        contacts = [self.c1, self.c2]
        deduped = deduplicate(contacts, "GH")
        self.assertEqual(len(deduped), 1)
        self.assertEqual(deduped[0].msg_count, 70)

    def test_segment(self):
        contacts = [self.c1, self.c3]
        segmented = segment(contacts, "GH", opportunity_keywords=["Client"])
        self.assertEqual(len(segmented), 2)
        # Alice is hot because msg_count > 50
        self.assertEqual(segmented[0].activity, "hot")
        self.assertTrue("Client" in segmented[0].group_tags)
        # Bob is cold
        self.assertEqual(segmented[1].activity, "cold")
