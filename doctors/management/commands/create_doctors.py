from django.core.management.base import BaseCommand
from django.db import transaction
from datetime import date
from doctors.models import Doctor


class Command(BaseCommand):
    help = 'Create sample doctors through ORM with all active status and filled details'

    def handle(self, *args, **options):
        """Create sample doctors through ORM"""
        
        doctors_data = [
            {
                'first_name': 'John',
                'last_name': 'Smith',
                'email': 'john.smith@pakkiora.com',
                'phone': '+12345678901',
                'date_of_birth': date(1980, 5, 15),
                'gender': 'M',
                'blood_group': 'O+',
                'address': '123 Medical Center Dr, Suite 100, New York, NY 10001',
                'specialization': 'Cardiology',
                'qualification': 'MD, FACC',
                'experience_years': 15,
                'license_number': 'NYMED123456',
                'department': 'Cardiology Department',
                'bio': 'Dr. John Smith is a board-certified cardiologist with over 15 years of experience in treating heart conditions. He specializes in interventional cardiology and preventive heart care.',
                'is_active': True
            },
            {
                'first_name': 'Sarah',
                'last_name': 'Johnson',
                'email': 'sarah.johnson@pakkiora.com',
                'phone': '+12345678902',
                'date_of_birth': date(1982, 8, 22),
                'gender': 'F',
                'blood_group': 'A+',
                'address': '456 Health Plaza, Floor 3, Boston, MA 02108',
                'specialization': 'Pediatrics',
                'qualification': 'MD, FAAP',
                'experience_years': 12,
                'license_number': 'MAMED789012',
                'department': 'Pediatrics Department',
                'bio': 'Dr. Sarah Johnson is a dedicated pediatrician with 12 years of experience in child healthcare. She specializes in pediatric emergency medicine and childhood development.',
                'is_active': True
            },
            {
                'first_name': 'Michael',
                'last_name': 'Chen',
                'email': 'michael.chen@pakkiora.com',
                'phone': '+12345678903',
                'date_of_birth': date(1978, 3, 10),
                'gender': 'M',
                'blood_group': 'B+',
                'address': '789 Wellness Ave, Unit 200, San Francisco, CA 94102',
                'specialization': 'Orthopedics',
                'qualification': 'MD, FAAOS',
                'experience_years': 18,
                'license_number': 'CAMED345678',
                'department': 'Orthopedics Department',
                'bio': 'Dr. Michael Chen is an experienced orthopedic surgeon specializing in sports medicine and joint replacement surgery. He has 18 years of experience in treating musculoskeletal conditions.',
                'is_active': True
            },
            {
                'first_name': 'Emily',
                'last_name': 'Williams',
                'email': 'emily.williams@pakkiora.com',
                'phone': '+12345678904',
                'date_of_birth': date(1985, 11, 30),
                'gender': 'F',
                'blood_group': 'AB+',
                'address': '321 Neurology Center, Wing B, Chicago, IL 60611',
                'specialization': 'Neurology',
                'qualification': 'MD, FAAN',
                'experience_years': 10,
                'license_number': 'ILMED901234',
                'department': 'Neurology Department',
                'bio': 'Dr. Emily Williams is a neurologist with expertise in stroke treatment and epilepsy management. She has 10 years of experience in diagnosing and treating neurological disorders.',
                'is_active': True
            },
            {
                'first_name': 'Robert',
                'last_name': 'Taylor',
                'email': 'robert.taylor@pakkiora.com',
                'phone': '+12345678905',
                'date_of_birth': date(1976, 7, 18),
                'gender': 'M',
                'blood_group': 'O-',
                'address': '654 Mental Health Blvd, Suite 300, Los Angeles, CA 90028',
                'specialization': 'Psychiatry',
                'qualification': 'MD, FAPA',
                'experience_years': 20,
                'license_number': 'CAMED567890',
                'department': 'Psychiatry Department',
                'bio': 'Dr. Robert Taylor is a board-certified psychiatrist with 20 years of experience in mental health. He specializes in anxiety disorders, depression treatment, and cognitive behavioral therapy.',
                'is_active': True
            },
            {
                'first_name': 'Lisa',
                'last_name': 'Anderson',
                'email': 'lisa.anderson@pakkiora.com',
                'phone': '+12345678906',
                'date_of_birth': date(1983, 9, 25),
                'gender': 'F',
                'blood_group': 'A-',
                'address': '987 Radiology Institute, Imaging Center, Houston, TX 77002',
                'specialization': 'Radiology',
                'qualification': 'MD, FACR',
                'experience_years': 14,
                'license_number': 'TXMED234567',
                'department': 'Radiology Department',
                'bio': 'Dr. Lisa Anderson is a diagnostic radiologist with 14 years of experience in medical imaging. She specializes in MRI interpretation, CT scans, and interventional radiology procedures.',
                'is_active': True
            },
            {
                'first_name': 'David',
                'last_name': 'Martinez',
                'email': 'david.martinez@pakkiora.com',
                'phone': '+12345678907',
                'date_of_birth': date(1979, 4, 12),
                'gender': 'M',
                'blood_group': 'B-',
                'address': '246 Surgery Center, OR Floor 5, Phoenix, AZ 85001',
                'specialization': 'Surgery',
                'qualification': 'MD, FACS',
                'experience_years': 16,
                'license_number': 'AZMED890123',
                'department': 'Surgery Department',
                'bio': 'Dr. David Martinez is a general surgeon with 16 years of experience in various surgical procedures. He specializes in minimally invasive surgery and trauma care.',
                'is_active': True
            },
            {
                'first_name': 'Jennifer',
                'last_name': 'Brown',
                'email': 'jennifer.brown@pakkiora.com',
                'phone': '+12345678908',
                'date_of_birth': date(1984, 2, 14),
                'gender': 'F',
                'blood_group': 'O+',
                'address': '135 Primary Care Center, Main Office, Seattle, WA 98101',
                'specialization': 'General Practice',
                'qualification': 'MD, FAAFP',
                'experience_years': 11,
                'license_number': 'WAMED456789',
                'department': 'Primary Care Department',
                'bio': 'Dr. Jennifer Brown is a family medicine physician with 11 years of experience in comprehensive primary care. She focuses on preventive medicine, chronic disease management, and patient education.',
                'is_active': True
            },
            {
                'first_name': 'William',
                'last_name': 'Garcia',
                'email': 'william.garcia@pakkiora.com',
                'phone': '+12345678909',
                'date_of_birth': date(1977, 6, 8),
                'gender': 'M',
                'blood_group': 'A+',
                'address': '567 Dermatology Clinic, Suite 400, Miami, FL 33101',
                'specialization': 'Dermatology',
                'qualification': 'MD, FAAD',
                'experience_years': 13,
                'license_number': 'FLMED678901',
                'department': 'Dermatology Department',
                'bio': 'Dr. William Garcia is a dermatologist with 13 years of experience in skin health. He specializes in medical dermatology, cosmetic procedures, and skin cancer screening.',
                'is_active': True
            },
            {
                'first_name': 'Margaret',
                'last_name': 'Thompson',
                'email': 'margaret.thompson@pakkiora.com',
                'phone': '+12345678910',
                'date_of_birth': date(1981, 10, 5),
                'gender': 'F',
                'blood_group': 'AB-',
                'address': '890 Women\'s Health Center, Floor 2, Denver, CO 80202',
                'specialization': 'Obstetrics & Gynecology',
                'qualification': 'MD, FACOG',
                'experience_years': 17,
                'license_number': 'COMED123456',
                'department': 'Women\'s Health Department',
                'bio': 'Dr. Margaret Thompson is an OB/GYN with 17 years of experience in women\'s health. She specializes in high-risk pregnancies, minimally invasive gynecology, and reproductive health.',
                'is_active': True
            }
        ]
        
        self.stdout.write(f"Creating {len(doctors_data)} doctors...")
        
        with transaction.atomic():
            created_doctors = []
            for i, doctor_data in enumerate(doctors_data, 1):
                try:
                    doctor = Doctor.objects.create(**doctor_data)
                    created_doctors.append(doctor)
                    self.stdout.write(self.style.SUCCESS(f"Created doctor {i}: Dr. {doctor.first_name} {doctor.last_name} - {doctor.specialization}"))
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"Error creating doctor {i}: {e}"))
                    continue
        
        self.stdout.write(self.style.SUCCESS(f"\nSuccessfully created {len(created_doctors)} doctors!"))
        self.stdout.write(self.style.SUCCESS("All doctors are active with complete details filled."))
        
        # Verify all doctors are active
        active_count = Doctor.objects.filter(is_active=True).count()
        total_count = Doctor.objects.count()
        self.stdout.write(self.style.SUCCESS(f"Verification: {active_count}/{total_count} doctors are active"))
