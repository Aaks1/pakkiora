# Generated for performance optimization
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('doctors', '0024_remove_doctor_profile_picture'),
    ]

    operations = [
        # Add indexes for frequently queried fields
        migrations.RunSQL(
            "CREATE INDEX IF NOT EXISTS idx_doctors_is_active ON doctors_doctor(is_active);",
            reverse_sql="DROP INDEX IF EXISTS idx_doctors_is_active;"
        ),
        migrations.RunSQL(
            "CREATE INDEX IF NOT EXISTS idx_doctors_specialization ON doctors_doctor(specialization);",
            reverse_sql="DROP INDEX IF EXISTS idx_doctors_specialization;"
        ),
        migrations.RunSQL(
            "CREATE INDEX IF NOT EXISTS idx_doctors_created_at ON doctors_doctor(created_at);",
            reverse_sql="DROP INDEX IF EXISTS idx_doctors_created_at;"
        ),
        migrations.RunSQL(
            "CREATE INDEX IF NOT EXISTS idx_doctors_name_search ON doctors_doctor(first_name, last_name);",
            reverse_sql="DROP INDEX IF EXISTS idx_doctors_name_search;"
        ),
        
        # User table indexes
        migrations.RunSQL(
            "CREATE INDEX IF NOT EXISTS idx_auth_user_is_staff ON auth_user(is_staff);",
            reverse_sql="DROP INDEX IF EXISTS idx_auth_user_is_staff;"
        ),
        migrations.RunSQL(
            "CREATE INDEX IF NOT EXISTS idx_auth_user_date_joined ON auth_user(date_joined);",
            reverse_sql="DROP INDEX IF EXISTS idx_auth_user_date_joined;"
        ),
        
        # Patient table indexes
        migrations.RunSQL(
            "CREATE INDEX IF NOT EXISTS idx_doctors_patient_user_id ON doctors_patient(user_id);",
            reverse_sql="DROP INDEX IF EXISTS idx_doctors_patient_user_id;"
        ),
        
        # Appointment table indexes
        migrations.RunSQL(
            "CREATE INDEX IF NOT EXISTS idx_appointments_patient_id ON appointments_appointment(patient_id);",
            reverse_sql="DROP INDEX IF EXISTS idx_appointments_patient_id;"
        ),
        migrations.RunSQL(
            "CREATE INDEX IF NOT EXISTS idx_appointments_doctor_id ON appointments_appointment(doctor_id);",
            reverse_sql="DROP INDEX IF EXISTS idx_appointments_doctor_id;"
        ),
        migrations.RunSQL(
            "CREATE INDEX IF NOT EXISTS idx_appointments_date ON appointments_appointment(date);",
            reverse_sql="DROP INDEX IF EXISTS idx_appointments_date;"
        ),
        migrations.RunSQL(
            "CREATE INDEX IF NOT EXISTS idx_appointments_status ON appointments_appointment(status);",
            reverse_sql="DROP INDEX IF EXISTS idx_appointments_status;"
        ),
    ]
