from django.db import connection

def check_doctor_tables():
    """Check existing doctor-related tables"""
    with connection.cursor() as cursor:
        cursor.execute("SELECT tablename FROM pg_tables WHERE tablename LIKE '%doctor%'")
        tables = cursor.fetchall()
        print("Doctor-related tables:")
        for table in tables:
            print(f"  {table[0]}")
        return tables

if __name__ == '__main__':
    check_doctor_tables()
