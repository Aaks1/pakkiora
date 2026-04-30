"""
Fix schedule service with correct table names
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'DoctorX.settings')
django.setup()

from django.db import connection

def check_table_names():
    """Check exact table names"""
    with connection.cursor() as cursor:
        cursor.execute("SELECT tablename FROM pg_tables WHERE tablename LIKE '%doctor%' ORDER BY tablename")
        tables = cursor.fetchall()
        print("Doctor-related tables:")
        for table in tables:
            print(f"  {table[0]}")
        return tables

if __name__ == '__main__':
    check_table_names()
