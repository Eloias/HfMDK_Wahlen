"""
Standalone test for email processing logic
"""

import re


def process_email_file(content):
    """
    Process the email file content and convert to Helios format.
    
    Input format: vorname.nachname@students.hfmdk-frankfurt.de (comma-separated)
    Output format: password,Vorname,vorname.nachname@students.hfmdk-frankfurt.de,Vorname Nachname
    """
    # Split content by commas and clean up
    emails = [email.strip() for email in content.replace('\n', ',').split(',')]
    emails = [email for email in emails if email]  # Remove empty strings
    
    converted_lines = []
    
    for email in emails:
        email = email.strip()
        if not email:
            continue
            
        # Validate email format
        if not email.endswith('@students.hfmdk-frankfurt.de'):
            continue
            
        # Extract the local part (before @)
        local_part = email.split('@')[0]
        
        # Check if it contains a dot (vorname.nachname format)
        if '.' not in local_part:
            continue
            
        # Split into vorname and nachname
        parts = local_part.split('.')
        if len(parts) != 2:
            continue
            
        vorname, nachname = parts
        
        # Capitalize for display names
        vorname_cap = vorname.capitalize()
        nachname_cap = nachname.capitalize()
        
        # Create the converted line
        # Format: password,Vorname,vorname.nachname@students.hfmdk-frankfurt.de,Vorname Nachname
        converted_line = f"password,{vorname_cap},{email},{vorname_cap} {nachname_cap}"
        converted_lines.append(converted_line)
    
    return '\n'.join(converted_lines)


def test_email_processing():
    """Run tests for email processing logic"""
    tests_passed = 0
    tests_failed = 0
    
    # Test 1: Single email
    print("Test 1: Single email")
    input_text = "max.mustermann@students.hfmdk-frankfurt.de"
    expected = "password,Max,max.mustermann@students.hfmdk-frankfurt.de,Max Mustermann"
    result = process_email_file(input_text)
    if result == expected:
        print("✓ PASSED")
        tests_passed += 1
    else:
        print(f"✗ FAILED\nExpected: {expected}\nGot: {result}")
        tests_failed += 1
    
    # Test 2: Multiple emails
    print("\nTest 2: Multiple emails")
    input_text = "max.mustermann@students.hfmdk-frankfurt.de, anna.schmidt@students.hfmdk-frankfurt.de"
    expected = """password,Max,max.mustermann@students.hfmdk-frankfurt.de,Max Mustermann
password,Anna,anna.schmidt@students.hfmdk-frankfurt.de,Anna Schmidt"""
    result = process_email_file(input_text)
    if result == expected:
        print("✓ PASSED")
        tests_passed += 1
    else:
        print(f"✗ FAILED\nExpected: {expected}\nGot: {result}")
        tests_failed += 1
    
    # Test 3: Invalid domain
    print("\nTest 3: Invalid domain should be ignored")
    input_text = "max.mustermann@other-domain.de, anna.schmidt@students.hfmdk-frankfurt.de"
    expected = "password,Anna,anna.schmidt@students.hfmdk-frankfurt.de,Anna Schmidt"
    result = process_email_file(input_text)
    if result == expected:
        print("✓ PASSED")
        tests_passed += 1
    else:
        print(f"✗ FAILED\nExpected: {expected}\nGot: {result}")
        tests_failed += 1
    
    # Test 4: No dot in local part
    print("\nTest 4: No dot in local part should be ignored")
    input_text = "maxmustermann@students.hfmdk-frankfurt.de, anna.schmidt@students.hfmdk-frankfurt.de"
    expected = "password,Anna,anna.schmidt@students.hfmdk-frankfurt.de,Anna Schmidt"
    result = process_email_file(input_text)
    if result == expected:
        print("✓ PASSED")
        tests_passed += 1
    else:
        print(f"✗ FAILED\nExpected: {expected}\nGot: {result}")
        tests_failed += 1
    
    # Test 5: Multiple dots in local part
    print("\nTest 5: Multiple dots in local part should be ignored")
    input_text = "max.von.mustermann@students.hfmdk-frankfurt.de, anna.schmidt@students.hfmdk-frankfurt.de"
    expected = "password,Anna,anna.schmidt@students.hfmdk-frankfurt.de,Anna Schmidt"
    result = process_email_file(input_text)
    if result == expected:
        print("✓ PASSED")
        tests_passed += 1
    else:
        print(f"✗ FAILED\nExpected: {expected}\nGot: {result}")
        tests_failed += 1
    
    # Test 6: Whitespace handling
    print("\nTest 6: Whitespace handling")
    input_text = "  max.mustermann@students.hfmdk-frankfurt.de  ,   anna.schmidt@students.hfmdk-frankfurt.de   "
    expected = """password,Max,max.mustermann@students.hfmdk-frankfurt.de,Max Mustermann
password,Anna,anna.schmidt@students.hfmdk-frankfurt.de,Anna Schmidt"""
    result = process_email_file(input_text)
    if result == expected:
        print("✓ PASSED")
        tests_passed += 1
    else:
        print(f"✗ FAILED\nExpected: {expected}\nGot: {result}")
        tests_failed += 1
    
    print(f"\n\nTest Results: {tests_passed} passed, {tests_failed} failed")
    return tests_failed == 0


if __name__ == '__main__':
    success = test_email_processing()
    if success:
        print("All tests passed! ✓")
    else:
        print("Some tests failed! ✗")
        exit(1)