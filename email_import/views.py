"""
Email Import Tool Views

This module provides views for the email import functionality,
allowing administrators to upload a text file with student email addresses
and convert them to a Helios-compatible format.
"""

import re
from django.http import HttpResponse, HttpResponseRedirect
from django.urls import reverse
from django.conf import settings
from helios.view_utils import render_template
from helios.stats_views import require_admin
from django.shortcuts import render


def email_import_home(request):
    """
    Main page for the email import tool.
    """
    # user = require_admin(request)
    
    if request.method == "GET":
        return render_template(request, 'email_import/home', {
            'error': request.GET.get('e', None)
        })
    
    if request.method == "POST":
        if 'email_file' not in request.FILES:
            return HttpResponseRedirect(
                f"{request.path}?e=no file specified"
            )
        
        email_file = request.FILES['email_file']
        
        # Validate file type
        if not email_file.name.endswith('.txt'):
            return HttpResponseRedirect(
                f"{request.path}?e=please upload a .txt file"
            )
        
        try:
            # Read and process the file
            file_content = email_file.read().decode('utf-8')
            converted_content = process_email_file(file_content)
            
            # Create response with converted file
            response = HttpResponse(converted_content, content_type='text/csv')
            response['Content-Disposition'] = 'attachment; filename="helios_voters.csv"'
            return response
            
        except Exception as e:
            return HttpResponseRedirect(
                f"{request.path}?e=error processing file: {str(e)}"
            )


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