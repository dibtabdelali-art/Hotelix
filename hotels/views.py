from django.shortcuts import render
from rest_framework import viewsets
from .models import Hotel, HotelAvailability

# Create your views here.


class HotelViewSet(viewsets.ModelViewSet):
    """ViewSet for hotel listings."""
    queryset = Hotel.objects.all()
    # TODO: Add serializer and permissions
