"""
Tests for Email Import Tool
"""

import unittest
from email_import.views import process_email_file


class TestEmailProcessing(unittest.TestCase):
    
    def test_single_email(self):
        """Test processing a single email address"""
        input_text = "max.mustermann@students.hfmdk-frankfurt.de"
        expected = "password,Max,max.mustermann@students.hfmdk-frankfurt.de,Max Mustermann"
        result = process_email_file(input_text)
        self.assertEqual(result, expected)
    
    def test_multiple_emails(self):
        """Test processing multiple email addresses"""
        input_text = "max.mustermann@students.hfmdk-frankfurt.de, anna.schmidt@students.hfmdk-frankfurt.de"
        expected = """password,Max,max.mustermann@students.hfmdk-frankfurt.de,Max Mustermann
password,Anna,anna.schmidt@students.hfmdk-frankfurt.de,Anna Schmidt"""
        result = process_email_file(input_text)
        self.assertEqual(result, expected)
    
    def test_newline_separated_emails(self):
        """Test processing emails separated by newlines"""
        input_text = """max.mustermann@students.hfmdk-frankfurt.de
anna.schmidt@students.hfmdk-frankfurt.de"""
        expected = """password,Max,max.mustermann@students.hfmdk-frankfurt.de,Max Mustermann
password,Anna,anna.schmidt@students.hfmdk-frankfurt.de,Anna Schmidt"""
        result = process_email_file(input_text)
        self.assertEqual(result, expected)
    
    def test_mixed_separators(self):
        """Test processing emails with mixed comma and newline separators"""
        input_text = """max.mustermann@students.hfmdk-frankfurt.de,
anna.schmidt@students.hfmdk-frankfurt.de,
tim.weber@students.hfmdk-frankfurt.de"""
        expected = """password,Max,max.mustermann@students.hfmdk-frankfurt.de,Max Mustermann
password,Anna,anna.schmidt@students.hfmdk-frankfurt.de,Anna Schmidt
password,Tim,tim.weber@students.hfmdk-frankfurt.de,Tim Weber"""
        result = process_email_file(input_text)
        self.assertEqual(result, expected)
    
    def test_invalid_domain(self):
        """Test that emails with wrong domain are ignored"""
        input_text = "max.mustermann@other-domain.de, anna.schmidt@students.hfmdk-frankfurt.de"
        expected = "password,Anna,anna.schmidt@students.hfmdk-frankfurt.de,Anna Schmidt"
        result = process_email_file(input_text)
        self.assertEqual(result, expected)
    
    def test_invalid_format_no_dot(self):
        """Test that emails without dot in local part are ignored"""
        input_text = "maxmustermann@students.hfmdk-frankfurt.de, anna.schmidt@students.hfmdk-frankfurt.de"
        expected = "password,Anna,anna.schmidt@students.hfmdk-frankfurt.de,Anna Schmidt"
        result = process_email_file(input_text)
        self.assertEqual(result, expected)
    
    def test_invalid_format_multiple_dots(self):
        """Test that emails with multiple dots in local part are ignored"""
        input_text = "max.von.mustermann@students.hfmdk-frankfurt.de, anna.schmidt@students.hfmdk-frankfurt.de"
        expected = "password,Anna,anna.schmidt@students.hfmdk-frankfurt.de,Anna Schmidt"
        result = process_email_file(input_text)
        self.assertEqual(result, expected)
    
    def test_empty_input(self):
        """Test processing empty input"""
        result = process_email_file("")
        self.assertEqual(result, "")
    
    def test_whitespace_handling(self):
        """Test that extra whitespace is handled correctly"""
        input_text = "  max.mustermann@students.hfmdk-frankfurt.de  ,   anna.schmidt@students.hfmdk-frankfurt.de   "
        expected = """password,Max,max.mustermann@students.hfmdk-frankfurt.de,Max Mustermann
password,Anna,anna.schmidt@students.hfmdk-frankfurt.de,Anna Schmidt"""
        result = process_email_file(input_text)
        self.assertEqual(result, expected)


if __name__ == '__main__':
    unittest.main()