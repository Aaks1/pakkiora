from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.utils import timezone
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from datetime import timedelta
from .models import Doctor, DoctorAvailability

def is_admin(user):
    return user.is_authenticated and user.is_staff


class DoctorListView(ListView):
    """List all doctors"""
    model = Doctor
    template_name = 'admin/doctors/list.html'
    context_object_name = 'doctors'
    paginate_by = 20
    
    def get_queryset(self):
        return Doctor.objects.all().order_by('first_name', 'last_name')



            
