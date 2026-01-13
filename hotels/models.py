from django.db import models


class Hotel(models.Model):
    """Hotel listing model."""
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    location = models.CharField(max_length=255)
    city = models.CharField(max_length=100)
    country = models.CharField(max_length=100)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    
    rating = models.FloatField(null=True, blank=True)
    review_count = models.IntegerField(default=0)
    
    price_per_night = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='USD')
    
    amenities = models.JSONField(default=list)
    images = models.JSONField(default=list)
    
    booking_affiliate_url = models.URLField(blank=True)
    external_id = models.CharField(max_length=255, null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-rating', '-review_count']
        indexes = [
            models.Index(fields=['city', 'price_per_night']),
            models.Index(fields=['rating']),
        ]
    
    def __str__(self):
        return f"{self.name} - {self.city}"


class HotelAvailability(models.Model):
    """Hotel availability and pricing."""
    hotel = models.ForeignKey(Hotel, on_delete=models.CASCADE, related_name='availability')
    check_in_date = models.DateField()
    check_out_date = models.DateField()
    available_rooms = models.IntegerField()
    price_per_night = models.DecimalField(max_digits=10, decimal_places=2)
    last_updated = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ('hotel', 'check_in_date', 'check_out_date')
    
    def __str__(self):
        return f"{self.hotel.name} - {self.check_in_date} to {self.check_out_date}"
