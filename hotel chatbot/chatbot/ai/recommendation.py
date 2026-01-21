from typing import List, Dict, Any


class RecommendationEngine:
    """Score and rank hotels based on user preferences."""

    def rank_hotels(self, hotels: List[Dict[str, Any]], user_prefs: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Score hotels and return a ranked list.

        Scoring factors (weights):
        - Price vs budget (30)
        - Rating (25)
        - Amenities match (20)
        - Review count (15)
        - Quality bonus (10)
        """

        def _to_float(value, default=0.0):
            try:
                return float(value)
            except (TypeError, ValueError):
                return default

        def calculate_score(hotel: Dict[str, Any]) -> float:
            score = 0.0

            # Price scoring (30)
            budget = _to_float(user_prefs.get('budget_max'))
            price = _to_float(hotel.get('price') or hotel.get('price_per_night'))
            if budget > 0:
                if price <= budget:
                    # More points the lower the price relative to budget
                    score += 30 * (1 - (price / budget))
                else:
                    # Small penalty if over budget
                    score -= 5
            else:
                score += 15  # neutral baseline when no budget provided

            # Rating scoring (25)
            # Makcorps ratings are on a 0-5 scale; convert to 0-10 for scoring
            rating_raw = _to_float(hotel.get('rating') or hotel.get('rating_raw'))
            rating10 = max(0.0, min(rating_raw * 2.0, 10.0))
            score += rating10 * 2.5

            # Amenities scoring (20)
            hotel_amenities = set(hotel.get('amenities') or [])
            pref_amenities = set(user_prefs.get('preferences') or [])
            if pref_amenities and hotel_amenities:
                match_count = len(hotel_amenities & pref_amenities)
                total_wanted = len(pref_amenities)
                score += (match_count / total_wanted) * 20
            else:
                score += 10

            # Review count bonus (15)
            review_count = int(hotel.get('rating_count') or hotel.get('total_rating_count') or 0)
            if review_count > 100:
                score += 15
            elif review_count > 50:
                score += 10
            else:
                score += 5

            # Quality bonus (10)
                if rating10 >= 9.0:
                    score += 10
                elif rating10 >= 8.5:
                    score += 7
                elif rating10 >= 8.0:
                    score += 3

            return score

        scored_hotels: List[Dict[str, Any]] = []
        for hotel in hotels:
            # avoid mutating original dict if caller relies on it
            h = dict(hotel)
            h['score'] = calculate_score(h)
            scored_hotels.append(h)

        # Sort by score descending
        return sorted(scored_hotels, key=lambda h: h.get('score', 0.0), reverse=True)
