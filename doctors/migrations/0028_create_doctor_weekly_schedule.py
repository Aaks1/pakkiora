# Generated migration for DoctorWeeklySchedule model
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('doctors', '0027_add_simple_schedule_fields'),
    ]

    operations = [
        # Create DoctorWeeklySchedule model
        migrations.CreateModel(
            name='DoctorWeeklySchedule',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('weekday', models.PositiveSmallIntegerField(choices=[(0, 'Monday'), (1, 'Tuesday'), (2, 'Wednesday'), (3, 'Thursday'), (4, 'Friday'), (5, 'Saturday'), (6, 'Sunday')])),
                ('start_time', models.TimeField(default='09:00')),
                ('end_time', models.TimeField(default='17:00')),
                ('is_active', models.BooleanField(default=True)),
                ('doctor', models.ForeignKey(on_delete=models.CASCADE, related_name='weekly_schedules', to='doctors.doctor')),
            ],
            options={
                'verbose_name': 'Doctor Weekly Schedule',
                'verbose_name_plural': 'Doctor Weekly Schedules',
                'unique_together': [('doctor', 'weekday')],
            },
        ),
    ]
