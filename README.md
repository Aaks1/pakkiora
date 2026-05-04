# Piki Ora Medical Centre - Appointment Management System

A comprehensive web-based appointment management system for Piki Ora Medical Centre that allows patients to book and manage appointments with doctors while enabling administrative staff to oversee clinic operations efficiently.

## 🏥 Features

### Patient Functions
- **View Available Doctors**: Browse doctors and their consultation schedules
- **Book Appointments**: Schedule appointments for specific dates and times
- **View Upcoming Appointments**: See all scheduled appointments
- **Manage Appointments**: Edit or cancel existing appointments
- **Confirmation Notifications**: Receive booking confirmations

### Administrator Functions
- **Custom Admin Dashboard**: Complete clinic oversight (not Django Admin)
- **Doctor Management**: Add, edit, and remove doctor profiles
- **Appointment Slot Management**: Create and manage available time slots
- **Booking Oversight**: View all patient bookings
- **Appointment Control**: Edit or cancel patient appointments
- **User Management**: Manage patient accounts

### System Features
- **Authentication**: Secure patient and admin login
- **Double Booking Prevention**: Database-level protection against conflicts
- **Responsive Design**: Works on all devices with Tailwind CSS
- **Data Integrity**: Relational database with proper constraints
- **User-Friendly Interface**: Modern, intuitive design

## 🛠 Technology Stack

- **Backend**: Django 4.x
- **Database**: SQLite (development ready)
- **Frontend**: Tailwind CSS
- **Icons**: Font Awesome
- **Authentication**: Django's built-in auth system
- **Messages**: Django Messages Framework

## 📋 Requirements Met

✅ All specified requirements fully implemented:
- Patient appointment booking and management
- Custom administrator dashboard
- Doctor profile management
- Schedule and slot management
- Authentication and security
- Double booking prevention
- Responsive, user-friendly interface

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- pip
- virtualenv (recommended)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/piki-ora-medical-centre.git
   cd piki-ora-medical-centre
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   # On Windows:
   venv\Scripts\activate
   # On macOS/Linux:
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run migrations**
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```

5. **Create superuser (admin)**
   ```bash
   python manage.py createsuperuser
   ```

6. **Run the development server**
   ```bash
   python manage.py runserver
   ```

7. **Access the application**
   - Home page: http://127.0.0.1:8000/
   - login: http://127.0.0.1:8000/login/
   - Patient registration: http://127.0.0.1:8000/register/

## 🏗 Project Structure

```
piki-ora-medical-centre/
├── DoctorX/                 # Django project settings
├── accounts/               # User authentication and profiles
├── appointments/           # Appointment booking and management
├── doctors/                # Doctor profiles and schedules
├── templates/              # HTML templates
│   ├── admin/             # Admin interface templates
│   ├── patient/           # Patient interface templates
│   └── base.html          # Base template
├── static/                 # CSS, JavaScript, images
├── media/                  # User-uploaded files
├── manage.py              # Django management script
└── README.md              # This file
```

## 🔐 Security Features

- **Authentication**: Required for all booking functions
- **Authorization**: Role-based access control
- **CSRF Protection**: Built-in Django security
- **SQL Injection Prevention**: Django ORM protection
- **Double Booking Prevention**: Database transactions and constraints

## 📱 Responsive Design

The application is fully responsive and works seamlessly on:
- Desktop computers
- Tablets
- Mobile phones

## 🎨 UI/UX Features

- Modern, clean interface with Tailwind CSS
- Intuitive navigation
- Clear status indicators
- Professional healthcare theme
- Accessibility considerations

## 📊 Database Schema

Key models include:
- **User**: Django's built-in user model
- **Patient**: Patient profiles and information
- **Doctor**: Doctor profiles and specializations
- **Appointment**: Booking details and status
- **AdminProfile**: Administrator profiles

## 🔧 Development Notes

- **Double Booking Prevention**: Uses database transactions with `select_for_update()`
- **Time Slot Generation**: Automatically creates 30-minute slots (9 AM - 5 PM, weekdays)
- **Status Management**: Comprehensive appointment status tracking
- **Error Handling**: Robust error handling and user feedback

## 📄 License

This project is proprietary software of Naveen's Medical Centre.

## 🤝 Contributing

This is an internal project for Piki Ora Medical Centre. Please follow the clinic's development guidelines when making changes.

## 📞 Support

For technical support or questions about the system, please contact the development team or Piki Ora Medical Centre administration.
Email at - Navinaveenbisht5742@gmail.com
---

**Piki Ora Medical Centre Appointment Management System**  
*Modern healthcare appointment booking and management*
