import unittest

from src.GUI.Utils.file_list import _legacy_drt_warning_message


class LegacyDrtWarningTests(unittest.TestCase):
    def test_message_aggregates_duplicate_files_and_explains_remediation(self):
        message = _legacy_drt_warning_message(
            ["sample-a.xlsx", "sample-a.xlsx", "sample-b.xlsx"]
        )

        self.assertEqual(message.count("sample-a.xlsx"), 1)
        self.assertEqual(message.count("sample-b.xlsx"), 1)
        self.assertIn("Bode", message)
        self.assertIn("Nyquist", message)
        self.assertIn("DRT", message)
        self.assertIn("reprocess", message.lower())
        self.assertIn("save", message.lower())


if __name__ == "__main__":
    unittest.main()
