"""
Hotel Booking API Integration

This module handles search and affiliate links to hotel booking platforms.
It searches for hotels based on criteria and provides affiliate links
for commission tracking.
"""

import logging
import requests
import os
from typing import List, Dict, Optional
from django.conf import settings
from chatbot.ai.makcorps_client import default_client
import os

logger = logging.getLogger(__name__)


class BookingAPIClient:
    """Client for interacting with hotel booking APIs."""
    
    def __init__(self):
        """Initialize booking API client."""
        try:
            self.base_url = settings.BOOKING_API_BASE_URL
        except Exception:
            self.base_url = os.getenv('BOOKING_API_BASE_URL', '')
            logger.warning('BOOKING_API_BASE_URL not in Django settings; falling back to env var')

        try:
            self.api_key = settings.BOOKING_API_KEY
        except Exception:
            self.api_key = os.getenv('BOOKING_API_KEY', '')
            logger.warning('BOOKING_API_KEY not in Django settings; falling back to env var')
        self.timeout = 10
    
    def search_hotels(
        self,
        location: str,
        check_in: str,
        check_out: str,
        guests: int = 1,
        max_price: Optional[int] = None,
        amenities: Optional[List[str]] = None
    ) -> List[Dict]:
        """
        Search for available hotels.
        
        Args:
            location: Hotel location (city or area)
            check_in: Check-in date (YYYY-MM-DD)
            check_out: Check-out date (YYYY-MM-DD)
            guests: Number of guests
            max_price: Maximum price per night
            amenities: List of required amenities
            
        Returns:
            List of hotel search results
        """
        try:
            params = {
                'location': location,
                'check_in': check_in,
                'check_out': check_out,
                'guests': guests,
            }
            
            if max_price:
                params['max_price'] = max_price
            
            if amenities:
                params['amenities'] = ','.join(amenities)
            
            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json',
            }
            
            # If Makcorps is configured, use it as a live source
            mak_client = default_client()
            mak_base = mak_client.base_url
            mak_key = mak_client.api_key
            if mak_base and mak_key:
                logger.info('Using Makcorps client for hotel search')
                return mak_client.search_hotels(location, check_in, check_out, guests, max_price, amenities)

            # TODO: Implement other booking provider API calls here
            logger.info(f"Searched hotels in {location} (no external provider configured)")
            return []
            
        except requests.RequestException as e:
            logger.error(f"Error searching hotels: {str(e)}")
            return []
    
    def get_affiliate_link(self, hotel_id: str) -> str:
        """
        Get affiliate link for a hotel.
        
        Args:
            hotel_id: Hotel identifier from booking platform
            
        Returns:
            Affiliate URL for the hotel
        """
        # Generate affiliate link with tracking parameters
        partner_id = 'hotel_chatbot'
        affiliate_link = f"{self.base_url}/hotel/{hotel_id}?partner={partner_id}"
        
        logger.info(f"Generated affiliate link for hotel {hotel_id}")
        return affiliate_link
    
    def get_hotel_details(self, hotel_id: str) -> Optional[Dict]:
        """
        Get detailed information about a specific hotel.
        
        Args:
            hotel_id: Hotel identifier
            
        Returns:
            Hotel details dictionary or None if not found
        """
        try:
            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json',
            }
            
            # TODO: Implement actual API call
            # response = requests.get(
            #     f'{self.base_url}/hotel/{hotel_id}',
            #     headers=headers,
            #     timeout=self.timeout
            # )
            # response.raise_for_status()
            # return response.json()
            
            logger.info(f"Retrieved details for hotel {hotel_id}")
            return None
            
        except requests.RequestException as e:
            logger.error(f"Error getting hotel details: {str(e)}")
            return None


# Compatibility alias used by interactive tools in the project
BookingSearchClient = BookingAPIClient
