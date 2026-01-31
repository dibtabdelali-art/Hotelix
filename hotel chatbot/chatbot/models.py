from django.db import models
import uuid


class ChatSession(models.Model):
    """Store chat conversations"""
    session_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    email = models.EmailField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Session {str(self.session_id)[:8]}... ({self.created_at})"


class Message(models.Model):
    """Chat messages between user and bot"""
    SENDER_CHOICES = [('user', 'User'), ('bot', 'Bot')]

    session = models.ForeignKey(ChatSession, on_delete=models.CASCADE, related_name='messages')
    sender = models.CharField(max_length=10, choices=SENDER_CHOICES)
    text = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    intent = models.CharField(max_length=50, null=True, blank=True)

    class Meta:
        ordering = ['timestamp']

    def __str__(self):
        return f"{self.sender.upper()}: {self.text[:50]}"


class UserSearchPreference(models.Model):
    """Cache user preferences for recommendations"""
    session = models.OneToOneField(ChatSession, on_delete=models.CASCADE, related_name='preferences')
    location = models.CharField(max_length=255, blank=True)
    check_in = models.DateField(null=True, blank=True)
    check_out = models.DateField(null=True, blank=True)
    guests = models.IntegerField(default=1)
    budget_min = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    budget_max = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    room_type = models.CharField(max_length=50, blank=True)
    preferences = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "User Search Preferences"

    def __str__(self):
        return f"{self.location} - {self.check_in}"


class HotelRecommendation(models.Model):
    """Hotel recommendations sent to user"""
    session = models.ForeignKey(ChatSession, on_delete=models.CASCADE, related_name='recommendations')
    booking_id = models.CharField(max_length=100, null=True, blank=True)
    name = models.CharField(max_length=255, null=True, blank=True, default='')
    location = models.CharField(max_length=255, null=True, blank=True, default='')
    price_per_night = models.DecimalField(max_digits=8, decimal_places=2)
    rating = models.FloatField(null=True, blank=True)
    total_rating_count = models.IntegerField(default=0)
    image_url = models.URLField(null=True, blank=True)
    affiliate_url = models.URLField()
    description = models.TextField(blank=True)
    amenities = models.JSONField(default=list)
    score = models.FloatField(default=0)
    sent_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-sent_at']

    def __str__(self):
        return f"{self.name} ({self.location})"


class RecommendationClick(models.Model):
    """Track which recommendations users clicked (for analytics)"""
    recommendation = models.ForeignKey(HotelRecommendation, on_delete=models.CASCADE, related_name='clicks')
    session = models.ForeignKey(ChatSession, on_delete=models.CASCADE)
    clicked_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('recommendation', 'session')
        verbose_name_plural = "Recommendation Clicks"

    def __str__(self):
        return f"{self.recommendation.name} clicked at {self.clicked_at}"
