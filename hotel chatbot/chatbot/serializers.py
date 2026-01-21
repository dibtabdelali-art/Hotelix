from rest_framework import serializers
from .models import Message, ChatSession, HotelRecommendation


class MessageSerializer(serializers.ModelSerializer):
	class Meta:
		model = Message
		fields = ['id', 'sender', 'text', 'timestamp', 'intent']
		read_only_fields = ['id', 'timestamp']


class ChatSessionSerializer(serializers.ModelSerializer):
	messages = MessageSerializer(many=True, read_only=True)

	class Meta:
		model = ChatSession
		fields = ['session_id', 'email', 'created_at', 'updated_at', 'messages']
		read_only_fields = ['session_id', 'created_at', 'updated_at']


class HotelRecommendationSerializer(serializers.ModelSerializer):
	class Meta:
		model = HotelRecommendation
		fields = [
			'id', 'name', 'location', 'price_per_night',
			'rating', 'image_url', 'affiliate_url', 'amenities',
			'description', 'score', 'sent_at'
		]
		read_only_fields = ['id', 'sent_at']
