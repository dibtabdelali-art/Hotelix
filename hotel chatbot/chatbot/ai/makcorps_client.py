import os
import logging
from typing import List, Dict, Optional
import requests
import re

logger = logging.getLogger(__name__)


def _parse_price(price_val):
    if price_val is None:
        return None
    try:
        p = str(price_val)
        p_clean = re.sub(r"[^0-9,\.]", "", p).replace(',', '.')
        return float(p_clean)
    except Exception:
        return None


class MakcorpsClient:
    """Client for Makcorps hotel APIs (city/hotel/mapping).

    Uses query-param `api_key` as shown in Makcorps docs and the
    documented endpoints: `/mapping`, `/city`, `/hotel`, `/booking`, `/expedia`.
    """

    def __init__(self, base_url: Optional[str] = None, api_key: Optional[str] = None, timeout: int = 30):
        self.base_url = (base_url or os.getenv('MAKCORPS_BASE_URL', 'https://api.makcorps.com')).rstrip('/')
        self.api_key = api_key or os.getenv('MAKCORPS_API_KEY')
        self.timeout = timeout

    def _get(self, path: str, params: Dict = None) -> Optional[object]:
        params = params.copy() if params else {}
        params['api_key'] = self.api_key
        url = f"{self.base_url}/{path.lstrip('/')}"
        try:
            resp = requests.get(url, params=params, timeout=self.timeout)
            # raise on non-200 so callers can handle errors explicitly
            if resp.status_code != 200:
                body = None
                try:
                    body = resp.text
                except Exception:
                    body = '<unreadable body>'
                logger.error('Makcorps request failed: %s %s %s', url, resp.status_code, body)
                try:
                    print(f"Makcorps request failed: {url} {resp.status_code} {body}")
                except Exception:
                    pass
                # raise a descriptive exception so higher layers can surface it to users
                raise MakcorpsAPIError(url=url, status=resp.status_code, body=body)
            try:
                return resp.json()
            except ValueError:
                return resp.text
        except requests.RequestException as e:
            logger.error('Makcorps request failed: %s %s', url, e)
            try:
                print(f"Makcorps request failed: {url} {e}")
            except Exception:
                pass
            raise MakcorpsAPIError(url=url, status=None, body=str(e))

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
                'id': item.get('hotelId') or item.get('value') or item.get('document_id'),
                'booking_id': item.get('hotelId') or item.get('value') or item.get('document_id'),
                'name': item.get('name') or item.get('hotel_name') or item.get('vendor'),
                'vendor_name': item.get('name'),
                'hotel_id': item.get('hotelId') or item.get('value') or item.get('document_id'),
                'price_str': price,
                'price': price_value,
                'price_per_night': price_value,
                'total_price': None,
                'rating': rating,
                'rating_raw': rating,
                'rating_count': (item.get('reviews') or {}).get('count') if isinstance(item.get('reviews'), dict) else None,
                'location': item.get('parent_name') or item.get('location') or None,
                'telephone': item.get('telephone'),
                'affiliate_url': None,
                'raw': item,
            })
        # attempt to enrich items missing a numeric price by querying hotel offers
        for h in normalized:
            if (h.get('price') is None or h.get('price_per_night') is None) and h.get('hotel_id'):
                try:
                    offer = self.get_best_offer_for_hotel(h.get('hotel_id'), checkin, checkout, adults)
                    if offer:
                        h['price'] = offer.get('price')
                        h['price_per_night'] = offer.get('price')
                        h['price_str'] = offer.get('price_str') or h.get('price_str')
                        # prefer vendor name from offer
                        if offer.get('vendor'):
                            h['vendor_name'] = offer.get('vendor')
                            if not h.get('name'):
                                h['name'] = offer.get('vendor')
                        if offer.get('affiliate_url'):
                            h['affiliate_url'] = offer.get('affiliate_url')
                except Exception:
                    # don't fail the whole search if enrichment fails
                    logger.debug('Failed to enrich hotel %s with offers', h.get('hotel_id'))
                    pass

        # ensure string fields are not None
        for h in normalized:
            for k in ('name', 'vendor_name', 'location', 'affiliate_url'):
                if h.get(k) is None:
                    h[k] = ''

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
                'id': hotelid,
                'booking_id': hotelid,
                'name': r.get('vendor') or r.get('name') or '',
                'vendor_name': r.get('vendor') or '',
                'hotel_id': hotelid,
                'price': None if r.get('price') is None else _parse_price(r.get('price')),
                'price_per_night': None if r.get('price') is None else _parse_price(r.get('price')),
                'total_price': None,
                'rating': None,
                'rating_count': None,
                'location': None,
                'affiliate_url': None,
                'raw': r.get('raw'),
            })
        return normalized

    def get_best_offer_for_hotel(self, hotelid: int, checkin: str, checkout: str, adults: int = 2) -> Optional[Dict]:
        """Query the hotel comparison endpoint and return the cheapest vendor offer.

        Returns dict: { 'price': float, 'price_str': str, 'vendor': str, 'affiliate_url': str }
        """
        try:
            offers = self.search_by_hotel_id(hotelid, checkin, checkout, adults=adults)
            best = None
            for o in offers:
                p = o.get('price')
                if p is None:
                    continue
                if best is None or (p < best.get('price')):
                    best = {'price': p, 'price_str': f"€{int(round(p))}", 'vendor': o.get('vendor_name') or o.get('name') or '', 'affiliate_url': o.get('affiliate_url') or ''}
            return best
        except Exception:
            return None

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
        try:
            city_id = self._choose_id_from_mapping(location)
            if city_id:
                logger.info(f"Resolved {location} to city ID {city_id}")
                return self.search_by_city_id(city_id, check_in, check_out, adults=guests, currency='EUR')
        except MakcorpsAPIError as e:
            logger.error(f"Mapping API failed for {location}: {e}")
            # Mapping failed - raise with helpful message
            raise MakcorpsAPIError(
                url=e.url, 
                status=e.status, 
                body=f"Unable to find city '{location}'. The Makcorps mapping service is unavailable. Please contact support or try again later."
            )
        except Exception as e:
            logger.exception(f"Unexpected error during mapping lookup for {location}")
            raise

        # Fallback: try calling city endpoint directly by name (some Makcorps deployments support this)
        try:
            params = {
                'name': location,
                'checkin': check_in,
                'checkout': check_out,
                'adults': guests,
                'cur': 'EUR'
            }
            data = self._get('/city', params)
            if data and isinstance(data, list):
                # reuse the same normalization as search_by_city_id
                normalized = []
                for item in data:
                    if not isinstance(item, dict):
                        continue
                    price = None
                    for i in range(1, 11):
                        p = item.get(f'price{i}')
                        if p:
                            price = p
                            break

                    rating = None
                    reviews = item.get('reviews') or {}
                    rating = reviews.get('rating') if isinstance(reviews, dict) else None

                    price_value = None
                    if price:
                        p = str(price)
                        p_clean = re.sub(r"[^0-9,\.]", "", p).replace(',', '.')
                        try:
                            price_value = float(p_clean)
                        except Exception:
                            price_value = None

                    normalized.append({
                        'id': item.get('hotelId') or item.get('value') or item.get('document_id'),
                        'booking_id': item.get('hotelId') or item.get('value') or item.get('document_id'),
                        'name': item.get('name') or item.get('hotel_name') or item.get('vendor'),
                        'vendor_name': item.get('name'),
                        'hotel_id': item.get('hotelId') or item.get('value') or item.get('document_id'),
                        'price_str': price,
                        'price': price_value,
                        'price_per_night': price_value,
                        'total_price': None,
                        'rating': rating,
                        'rating_raw': rating,
                        'rating_count': (item.get('reviews') or {}).get('count') if isinstance(item.get('reviews'), dict) else None,
                        'location': item.get('parent_name') or item.get('location') or None,
                        'telephone': item.get('telephone'),
                        'affiliate_url': None,
                        'raw': item,
                    })
                return normalized
        except Exception:
            pass

        # As fallback, try hotel endpoint with name slug (some endpoints accept hotelid as slug)
        data = self._get('/booking', {'country': '', 'hotelid': location, 'checkin': check_in, 'checkout': check_out, 'currency': 'EUR', 'adults': guests, 'rooms': 1})
        if data:
            # booking endpoint returns room options; map to simple hotels
            normalized = []
            if isinstance(data, list) and len(data) > 0:
                rooms = data[0] if isinstance(data[0], list) else []
                hotel_meta = data[1] if len(data) > 1 else {}
                for room in rooms:
                    price_val = room.get('price')
                    pv = _parse_price(price_val)
                    normalized.append({
                        'id': hotel_meta.get('hotelid') or None,
                        'booking_id': hotel_meta.get('hotelid') or None,
                        'name': hotel_meta.get('name') or location,
                        'vendor_name': hotel_meta.get('name') or location,
                        'hotel_id': hotel_meta.get('hotelid') or None,
                        'price': pv,
                        'price_per_night': pv,
                        'total_price': None,
                        'rating': None,
                        'rating_count': None,
                        'location': hotel_meta.get('address'),
                        'affiliate_url': None,
                        'raw': room,
                    })
            return normalized

        return []


def default_client() -> MakcorpsClient:
    return MakcorpsClient()


class MakcorpsAPIError(Exception):
    def __init__(self, url: str = '', status: Optional[int] = None, body: Optional[str] = None):
        self.url = url
        self.status = status
        self.body = body
        msg = f"Makcorps API error {status} for {url}: {body}"
        super().__init__(msg)
