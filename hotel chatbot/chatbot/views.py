from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from .models import ChatSession, Message, UserSearchPreference, HotelRecommendation
from .serializers import MessageSerializer, ChatSessionSerializer
from .ai.llm_engine import ChatbotAIEngine
from .ai.recommendation import RecommendationEngine
from hotels.booking_api import BookingSearchClient
import uuid
import logging

logger = logging.getLogger(__name__)


class ChatbotViewSet(viewsets.ViewSet):
    """Hotel recommendation chatbot endpoint"""

    permission_classes = [AllowAny]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ai_engine = ChatbotAIEngine()
        self.rec_engine = RecommendationEngine()
        self.booking_client = BookingSearchClient()

    @action(detail=False, methods=['POST'])
    def start_session(self, request):
        """Start new chat session"""
        email = request.data.get('email', '')
        session_id = str(uuid.uuid4())
        try:
            session = ChatSession.objects.create(
                session_id=session_id,
                email=email
            )
            # Create preferences
            UserSearchPreference.objects.create(session=session)

            # Welcome message
            welcome_msg = Message.objects.create(
                session=session,
                sender='bot',
                text=(
                    "Bienvenue! Je suis votre assistant de recommandation d'hôtels. "
                    "Aidez-moi à trouver les meilleurs hôtels pour vous!\n\n"
                    "Dites-moi: où voulez-vous aller, quand, et quel est votre budget?"
                )
            )
            logger.info("New session created: %s", session_id)
            return Response({
                'session_id': session_id,
                'message': welcome_msg.text
            }, status=status.HTTP_201_CREATED)
        except Exception as e:
            logger.exception("Session creation error")
            return Response({'error': 'Failed to create session'}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['POST'])
    def send_message(self, request):
        """Send message and get recommendations"""
        session_id = request.data.get('session_id')
        user_text = request.data.get('message', '').strip()
        if not user_text:
            return Response({'error': 'Message cannot be empty'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            session = ChatSession.objects.get(session_id=session_id)
        except ChatSession.DoesNotExist:
            return Response({'error': 'Session not found'}, status=404)

        try:
            # Save user message
            Message.objects.create(session=session, sender='user', text=user_text)

            # Parse intent
            intent_data = self.ai_engine.parse_user_intent(user_text)
            intent = intent_data.get('intent', 'help')

            # Update user preferences (if present)
            prefs = session.preferences
            if intent_data.get('location'):
                prefs.location = intent_data['location']
            if intent_data.get('check_in'):
                prefs.check_in = intent_data['check_in']
            if intent_data.get('check_out'):
                prefs.check_out = intent_data['check_out']
            if intent_data.get('guests'):
                try:
                    prefs.guests = int(intent_data['guests'])
                except (ValueError, TypeError):
                    pass
            if intent_data.get('budget_max') is not None:
                try:
                    prefs.budget_max = float(intent_data['budget_max'])
                except (ValueError, TypeError):
                    prefs.budget_max = None
            if intent_data.get('preferences'):
                prefs.preferences = intent_data['preferences']
            prefs.save()

            # Get recommendations
            recommendations = []
            bot_response = ""

            if intent == 'search' and prefs.location and prefs.check_in and prefs.check_out:
                try:
                    hotels = self.booking_client.search_hotels(
                        location=prefs.location,
                        check_in=str(prefs.check_in),
                        check_out=str(prefs.check_out),
                        guests=prefs.guests
                    )
                    if hotels:
                        prefs_dict = {
                            'budget_max': float(prefs.budget_max) if prefs.budget_max else None,
                            'preferences': prefs.preferences or []
                        }
                        ranked = self.rec_engine.rank_hotels(hotels, prefs_dict)

                        # Save top 10 recommendations
                        for hotel in ranked[:10]:
                            HotelRecommendation.objects.create(
                                session=session,
                                booking_id=hotel.get('id') or hotel.get('booking_id'),
                                name=hotel.get('name'),
                                location=hotel.get('location'),
                                price_per_night=hotel.get('price') or hotel.get('price_per_night') or 0,
                                rating=hotel.get('rating'),
                                total_rating_count=int(hotel.get('rating_count') or hotel.get('total_rating_count') or 0),
                                image_url=hotel.get('image_url'),
                                affiliate_url=hotel.get('affiliate_url') or hotel.get('url') or '',
                                description=hotel.get('description', ''),
                                amenities=hotel.get('amenities', []),
                                score=hotel.get('score', 0)
                            )
                        recommendations = ranked[:5]
                except Exception as e:
                    logger.exception("Hotel search error")
                    bot_response = f"Erreur lors de la recherche d'hôtels. {str(e)}"

            # Generate response
            if not bot_response:
                bot_response = self.ai_engine.generate_response(intent, recommendations)

            # Save bot response
            Message.objects.create(session=session, sender='bot', text=bot_response, intent=intent)

            # Prepare response payload
            payload_recs = []
            for h in recommendations:
                payload_recs.append({
                    'id': h.get('id') or h.get('booking_id'),
                    'name': h.get('name'),
                    'location': h.get('location'),
                    'price': float(h.get('price') or h.get('price_per_night') or 0),
                    'rating': float(h.get('rating')) if h.get('rating') is not None else None,
                    'amenities': h.get('amenities', []),
                    'image_url': h.get('image_url'),
                    'affiliate_url': h.get('affiliate_url') or h.get('url') or '',
                    'score': float(h.get('score', 0))
                })

            return Response({'bot_response': bot_response, 'intent': intent, 'recommendations': payload_recs}, status=status.HTTP_200_OK)
        except Exception as e:
            logger.exception("Message processing error")
            return Response({'error': 'Failed to process message'}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['GET'])
    def get_conversation(self, request):
        """Get full conversation history"""
        session_id = request.query_params.get('session_id')
        try:
            session = ChatSession.objects.get(session_id=session_id)
            messages = Message.objects.filter(session=session)
            serializer = MessageSerializer(messages, many=True)
            return Response(serializer.data)
        except ChatSession.DoesNotExist:
            return Response({'error': 'Session not found'}, status=404)

    @action(detail=False, methods=['GET'])
    def get_recommendations(self, request):
        """Get previous recommendations in session"""
        session_id = request.query_params.get('session_id')
        try:
            session = ChatSession.objects.get(session_id=session_id)
            recs = HotelRecommendation.objects.filter(session=session).order_by('-sent_at')
            return Response([
                {
                    'id': r.id,
                    'name': r.name,
                    'location': r.location,
                    'price': str(r.price_per_night),
                    'rating': r.rating,
                    'amenities': r.amenities,
                    'image_url': r.image_url,
                    'affiliate_url': r.affiliate_url,
                    'score': r.score,
                    'sent_at': r.sent_at
                }
                for r in recs
            ])
        except ChatSession.DoesNotExist:
            return Response({'error': 'Session not found'}, status=404)
