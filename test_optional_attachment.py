#!/usr/bin/env python
"""
Test script to verify that qualifications can be created without file attachments.
This script tests the changes made to make file uploads optional.
"""

import os
import sys
import django
from django.test import TestCase
from datetime import date

# Add the project directory to Python path
sys.path.insert(0, '/Users/lukasbisdorf/Dev/JF-Manager')

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'jf_manager_backend.settings')
django.setup()

from qualifications.models import Qualification, QualificationType
from members.models import Attachment
from users.models import CustomUser
from django.contrib.contenttypes.models import ContentType


def test_qualification_without_attachment():
    """Test creating a qualification without file attachment"""
    
    print("Testing qualification creation without file attachment...")
    
    try:
        # Create a qualification type if none exists
        qual_type, created = QualificationType.objects.get_or_create(
            name="Test Qualification",
            defaults={
                'description': 'Test qualification for optional attachment test',
                'expires': False
            }
        )
        
        if created:
            print(f"✓ Created qualification type: {qual_type.name}")
        else:
            print(f"✓ Using existing qualification type: {qual_type.name}")
        
        # Create a test user if none exists
        test_user, created = CustomUser.objects.get_or_create(
            username="testuser_attach",
            defaults={
                'email': 'testuser@example.com',
                'first_name': 'Test',
                'last_name': 'User'
            }
        )
        
        if created:
            print(f"✓ Created test user: {test_user.username}")
        else:
            print(f"✓ Using existing test user: {test_user.username}")
        
        # Create qualification without attachment
        qualification = Qualification.objects.create(
            type=qual_type,
            user=test_user,
            date_acquired=date.today(),
            issued_by="Test Department",
            note="Test qualification created without attachment"
        )
        
        print(f"✓ Successfully created qualification ID {qualification.id} without attachment")
        
        # Verify no attachments are associated
        content_type = ContentType.objects.get_for_model(Qualification)
        attachments = Attachment.objects.filter(
            content_type=content_type,
            object_id=qualification.id
        )
        
        if attachments.count() == 0:
            print("✓ Confirmed: No attachments associated with the qualification")
        else:
            print(f"⚠ Warning: {attachments.count()} attachments found (unexpected)")
        
        # Test attachment model with empty file
        try:
            attachment = Attachment(
                content_type=content_type,
                object_id=qualification.id,
                name="Test Attachment Without File",
                description="Testing optional file field",
                uploaded_by=test_user
            )
            attachment.save()
            print(f"✓ Successfully created attachment ID {attachment.id} without file")
            
            # Clean up
            attachment.delete()
            print("✓ Cleaned up test attachment")
            
        except Exception as e:
            print(f"✗ Failed to create attachment without file: {e}")
            return False
        
        # Clean up qualification
        qualification.delete()
        print("✓ Cleaned up test qualification")
        
        print("\n🎉 All tests passed! File upload is now optional for qualifications.")
        return True
        
    except Exception as e:
        print(f"✗ Test failed: {e}")
        return False


if __name__ == "__main__":
    success = test_qualification_without_attachment()
    sys.exit(0 if success else 1)