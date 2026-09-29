import unittest
from unittest.mock import patch

from src.GUI.Utils.file_list import (
    _legacy_drt_warning_message,
    _show_legacy_drt_warning,
)


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

    def test_popup_is_shown_once_for_aggregated_files_and_skipped_when_empty(self):
        with patch("src.GUI.Utils.progress_modal.show_warning_dialog") as show_dialog:
            _show_legacy_drt_warning(["sample-a.xlsx", "sample-a.xlsx", "sample-b.xlsx"])
            _show_legacy_drt_warning([])

        show_dialog.assert_called_once()
        title, message = show_dialog.call_args.args
        self.assertIn("Legacy Frequency", title)
        self.assertEqual(message.count("sample-a.xlsx"), 1)
        self.assertEqual(message.count("sample-b.xlsx"), 1)


if __name__ == "__main__":
    unittest.main()
