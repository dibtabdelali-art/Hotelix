import os
import logging
from typing import List, Dict, Optional
import requests
import re

logger = logging.getLogger(__name__)


class MakcorpsClient:
    """Client for Makcorps hotel APIs (city/hotel/mapping).

    Uses query-param `api_key` as shown in Makcorps docs and the
    documented endpoints: `/mapping`, `/city`, `/hotel`, `/booking`, `/expedia`.
    """

    def __init__(self, base_url: Optional[str] = None, api_key: Optional[str] = None, timeout: int = 10):
        self.base_url = (base_url or os.getenv('MAKCORPS_BASE_URL', 'https://api.makcorps.com')).rstrip('/')
        self.api_key = api_key or os.getenv('MAKCORPS_API_KEY')
        self.timeout = timeout

    def _get(self, path: str, params: Dict = None) -> Optional[object]:
        params = params.copy() if params else {}
        params['api_key'] = self.api_key
        url = f"{self.base_url}/{path.lstrip('/')}"
        try:
            resp = requests.get(url, params=params, timeout=self.timeout)
            # don't raise; capture body for better diagnostics
            if resp.status_code != 200:
                body = None
                try:
                    body = resp.text
                except Exception:
                    body = '<unreadable body>'
                logger.error('Makcorps request failed: %s %s %s', url, resp.status_code, body)
                # also print to stdout so interactive REPL shows it
                try:
                    print(f"Makcorps request failed: {url} {resp.status_code} {body}")
                except Exception:
                    pass
                return None
            return resp.json()
        except requests.RequestException as e:
            logger.error('Makcorps request failed: %s %s', url, e)
            try:
                print(f"Makcorps request failed: {url} {e}")
            except Exception:
                pass
            return None

    def mapping(self, name: str) -> List[Dict]:
        """Call mapping API to resolve city/hotel names to Makcorps IDs."""
        data = self._get('/mapping', {'name': name})
        if not data:
            return []
        return data if isinstance(data, list) else []

    def _choose_id_from_mapping(self, name: str) -> Optional[int]:
        items = self.mapping(name)
        if not items:
            return None
        # Prefer GEO (city) then HOTEL then any value field
        for it in items:
            if it.get('type') == 'GEO' or it.get('data_type') == 'LOCATION':
                return it.get('value') or it.get('document_id')
        for it in items:
            if it.get('type') == 'HOTEL':
                return it.get('value') or it.get('document_id')
        first = items[0]
        return first.get('value') or first.get('document_id')

    def search_by_city_id(self, cityid: int, checkin: str, checkout: str, adults: int = 2, rooms: int = 1, currency: str = 'EUR', pagination: int = 0) -> List[Dict]:
        params = {
            'cityid': cityid,
            'checkin': checkin,
            'checkout': checkout,
            'adults': adults,
            'rooms': rooms,
            'cur': currency,
            'pagination': pagination,
        }
        data = self._get('/city', params)
        if not data:
            return []

        normalized = []
        for item in data:
            # Some Makcorps responses include trailing metadata as a list
            # (e.g. pagination info). Skip any non-dict entries.
            if not isinstance(item, dict):
                continue
            # extract cheapest price from vendor/price pairs
            price = None
            for i in range(1, 11):
                p = item.get(f'price{i}')
                if p:
                    price = p
                    break

            rating = None
            reviews = item.get('reviews') or {}
            rating = reviews.get('rating') if isinstance(reviews, dict) else None

            # normalize price into numeric value (EUR) when possible
            price_value = None
            if price:
                # remove currency symbols and non-digit characters except dot and comma
                p = str(price)
                # replace comma with dot for decimals if present
                p_clean = re.sub(r"[^0-9,\.]", "", p).replace(',', '.')
                try:
                    price_value = float(p_clean)
                except Exception:
                    price_value = None

            normalized.append({
                'vendor_name': item.get('name'),
                'hotel_id': item.get('hotelId') or item.get('value') or item.get('document_id'),
                'price_str': price,
                'price': price_value,
                'total_price': None,
                'rating': rating,
                'rating_raw': rating,
                'location': item.get('parent_name') or item.get('location') or None,
                'telephone': item.get('telephone'),
                'affiliate_url': None,
                'raw': item,
            })
        return normalized

    def search_by_hotel_id(self, hotelid: int, checkin: str, checkout: str, adults: int = 2, rooms: int = 1, currency: str = 'EUR') -> List[Dict]:
        params = {
            'hotelid': hotelid,
            'checkin': checkin,
            'checkout': checkout,
            'adults': adults,
            'rooms': rooms,
            'currency': currency,
        }
        data = self._get('/hotel', params)
        if not data:
            return []

        # data likely contains comparison list with vendor price entries
        results = []
        comparison = data.get('comparison') if isinstance(data, dict) else None
        if comparison and len(comparison) > 0:
            # first element is an array of vendor objects with vendorN/priceN keys
            vendors = comparison[0]
            for v in vendors:
                # find the first price key and its corresponding vendor key
                price = None
                vendor_name = None
                for i in range(1, 21):
                    price_key = f'price{i}'
                    vendor_key = f'vendor{i}'
                    if price_key in v and v.get(price_key):
                        price = v.get(price_key)
                        vendor_name = v.get(vendor_key) or vendor_name
                        break
                # fallback: some responses may include 'price' or 'vendor' directly
                if not price:
                    # try generic keys
                    for k, val in v.items():
                        if k.lower().startswith('price') and val:
                            price = val
                            break
                if not vendor_name:
                    for k, val in v.items():
                        if k.lower().startswith('vendor') and isinstance(val, str):
                            vendor_name = val
                            break

                results.append({'vendor': vendor_name, 'price': price, 'raw': v})

        # Map to normalized structure (single hotel)
        normalized = []
        for r in results:
            normalized.append({
                'vendor_name': r.get('vendor'),
                'hotel_id': hotelid,
                'price': r.get('price'),
                'total_price': None,
                'rating': None,
                'location': None,
                'affiliate_url': None,
                'raw': r.get('raw'),
            })
        return normalized

    def booking(self, country: str, hotelid: str, checkin: str, checkout: str, currency: str = 'EUR', kids: int = 0, adults: int = 1, rooms: int = 1) -> Optional[object]:
        params = {
            'country': country,
            'hotelid': hotelid,
            'checkin': checkin,
            'checkout': checkout,
            'currency': currency,
            'kids': kids,
            'adults': adults,
            'rooms': rooms,
        }
        return self._get('/booking', params)

    def roomtype(self, hotelid: str, checkin: str, checkout: str, adults: int = 2, rooms: int = 1) -> Optional[object]:
        params = {
            'hotelid': hotelid,
            'adults': adults,
            'rooms': rooms,
            'checkin': checkin,
            'checkout': checkout,
        }
        return self._get('/roomtype', params)

    def expedia(self, hotelid: str, checkin: str, checkout: str, currency: str = 'EUR', adults: int = 2, rooms: int = 1) -> Optional[object]:
        params = {
            'hotelid': hotelid,
            'checkin': checkin,
            'checkout': checkout,
            'currency': currency,
            'adults': adults,
            'rooms': rooms,
        }
        return self._get('/expedia', params)

    def search_hotels(self, location: str, check_in: str, check_out: str, guests: int = 1, max_price: Optional[int] = None, amenities: Optional[List[str]] = None) -> List[Dict]:
        # If location looks like an integer id, use hotel or city endpoint heuristically
        try:
            val = int(location)
            # prefer city search by id
            return self.search_by_city_id(val, check_in, check_out, adults=guests)
        except Exception:
            pass

        # Try to resolve city id via mapping
        city_id = self._choose_id_from_mapping(location)
        if city_id:
            return self.search_by_city_id(city_id, check_in, check_out, adults=guests, currency='EUR')

        # As fallback, try hotel endpoint with name slug (some endpoints accept hotelid as slug)
        data = self._get('/booking', {'country': '', 'hotelid': location, 'checkin': check_in, 'checkout': check_out, 'currency': 'EUR', 'adults': guests, 'rooms': 1})
        if data:
            # booking endpoint returns room options; map to simple hotels
            normalized = []
            if isinstance(data, list) and len(data) > 0:
                rooms = data[0] if isinstance(data[0], list) else []
                hotel_meta = data[1] if len(data) > 1 else {}
                for room in rooms:
                    normalized.append({
                        'vendor_name': hotel_meta.get('name') or location,
                        'hotel_id': hotel_meta.get('hotelid') or None,
                        'price': room.get('price'),
                        'total_price': None,
                        'rating': None,
                        'location': hotel_meta.get('address'),
                        'affiliate_url': None,
                        'raw': room,
                    })
            return normalized

        return []


def default_client() -> MakcorpsClient:
    return MakcorpsClient()
