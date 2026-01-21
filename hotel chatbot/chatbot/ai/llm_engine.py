import json
import logging
from typing import List, Dict, Any, Optional

try:
    import requests
except Exception:
    requests = None
import os

logger = logging.getLogger(__name__)


class ChatbotAIEngine:
    """Uses Groq API (Mixtral) to parse intents and generate responses."""

    def __init__(self) -> None:
        # Read API key from environment variable named GROQ_API_KEY
        self.api_key: Optional[str] = os.getenv("GROQ_API_KEY")
        self.base_url: str = "https://api.groq.com/openai/v1"
        self.model = "llama-3.1-8b-instant"
        self.timeout: int = 15
        # Optional Makcorps (user-provided) settings
        self.makcorps_url: Optional[str] = os.getenv("MAKCORPS_API_URL")
        self.makcorps_key: Optional[str] = os.getenv("MAKCORPS_API_KEY")

        # Sanity / GROQ dataset settings (for data lookup)
        self.sanity_project_id: Optional[str] = os.getenv("SANITY_PROJECT_ID")
        self.sanity_dataset: str = os.getenv("SANITY_DATASET", "production")
        self.sanity_token: Optional[str] = os.getenv("SANITY_TOKEN")

    def parse_user_intent(self, user_message: str) -> Dict[str, Any]:
        """Extract intent using the Groq chat completions endpoint.

        Returns a dict parsed from the LLM JSON response or an error dict.
        """
        system_prompt = (
            "Tu es un assistant de recommandation d'hôtels intelligent.\n"
            "Analyse le message de l'utilisateur et extrais les informations en JSON strict.\n"
            "Intentions possibles: search, refine, help, info\n"
            "Format de réponse JSON:\n"
            "{\n"
            "  \"intent\": \"search|refine|help|info\",\n"
            "  \"location\": \"ville ou null\",\n"
            "  \"check_in\": \"YYYY-MM-DD ou null\",\n"
            "  \"check_out\": \"YYYY-MM-DD ou null\",\n"
            "  \"guests\": nombre ou null,\n"
            "  \"budget_max\": nombre ou null,\n"
            "  \"preferences\": [\"wifi\", \"pool\", ...] ou []\n"
            "}\n"
            "Réponds UNIQUEMENT avec du JSON valide, rien d'autre."
        )

        if not self.api_key:
            logger.error("GROQ_API_KEY is not configured")
            return {'intent': 'help', 'error': 'API key not configured'}

        try:
            resp = requests.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_message},
                    ],
                    "temperature": 0.3,
                    "max_tokens": 500,
                },
                timeout=self.timeout,
            )

            if resp.status_code != 200:
                logger.error("Groq API error: %s - %s", resp.status_code, resp.text)
                return {'intent': 'help', 'error': 'API Error', 'status': resp.status_code}

            result = resp.json()
            choices = result.get('choices') or []
            if not choices:
                logger.error("Groq response missing choices: %s", result)
                return {'intent': 'help', 'error': 'No choices in response'}

            response_text = ''
            # defensive access for new-style responses
            try:
                response_text = choices[0].get('message', {}).get('content', '').strip()
            except Exception:
                response_text = str(choices[0])

            try:
                parsed = json.loads(response_text)
                return parsed
            except json.JSONDecodeError:
                logger.error("JSON parse error from LLM response: %s", response_text)
                return {'intent': 'help', 'error': 'Parse Error', 'raw': response_text}

        except requests.Timeout:
            logger.exception("Groq API timeout")
            return {'intent': 'help', 'error': 'Timeout'}
        except Exception as e:
            logger.exception("Groq error")
            return {'intent': 'help', 'error': str(e)}

    def query_sanity_groq(self, groq_query: str) -> List[Dict[str, Any]]:
        """Run a GROQ query against Sanity and return the `result` list.

        Expects env vars `SANITY_PROJECT_ID`, `SANITY_DATASET`, and optional `SANITY_TOKEN`.
        """
        if not self.sanity_project_id:
            logger.error("SANITY_PROJECT_ID not configured")
            return []

        base = f"https://{self.sanity_project_id}.api.sanity.io/v1/data/query/{self.sanity_dataset}"
        try:
            headers = {}
            if self.sanity_token:
                headers["Authorization"] = f"Bearer {self.sanity_token}"
            resp = requests.get(base, params={"query": groq_query}, headers=headers, timeout=self.timeout)
            if resp.status_code != 200:
                logger.error("Sanity GROQ error: %s %s", resp.status_code, resp.text)
                return []
            payload = resp.json()
            return payload.get("result") or []
        except Exception:
            logger.exception("Error querying Sanity GROQ")
            return []


    def call_makcorps(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> str:
        """Call the Makcorps API with a prompt and optional context. Return text reply.

        This is a small wrapper that assumes Makcorps accepts JSON POSTs with `prompt` and `context`.
        Adjust field names to match your Makcorps API.
        """
        if not self.makcorps_url:
            logger.error("MAKCORPS_API_URL not configured")
            return "Makcorps integration not configured."

        body = {"prompt": prompt}
        if context is not None:
            body["context"] = context

        headers = {"Content-Type": "application/json"}
        if self.makcorps_key:
            headers["Authorization"] = f"Bearer {self.makcorps_key}"

        try:
            resp = requests.post(self.makcorps_url, json=body, headers=headers, timeout=self.timeout)
            if resp.status_code not in (200, 201):
                logger.error("Makcorps API error: %s %s", resp.status_code, resp.text)
                return "Désolé, l'API Makcorps a retourné une erreur."

            data = resp.json()
            # try standard fields
            for key in ("reply", "text", "message", "output"):
                if key in data:
                    return data[key]

            # fallback to flattened JSON string
            return json.dumps(data)
        except Exception:
            logger.exception("Error calling Makcorps API")
            return "Erreur réseau lors de la communication avec Makcorps."


    def orchestrate_response(self, user_message: str) -> Dict[str, Any]:
        """High-level orchestration: parse intent, run GROQ if needed, call Makcorps to produce a reply.

        Returns a dict: { 'reply': str, 'intent': str, 'recommendations': [...] }
        """
        parsed = self.parse_user_intent(user_message)
        intent = parsed.get("intent", "help")

        recommendations: List[Dict[str, Any]] = []
        # If user intends to search, build a simple GROQ query from parsed fields
        if intent == "search":
            location = parsed.get("location")
            # Simple example GROQ: adapt to your schema
            if location:
                groq_q = f"*[_type == \"hotel\" && city match \"{location}*\"]{'{'}_id, name, city, price_per_night, rating, \"images\": images[].asset->url{'}'}"
                recommendations = self.query_sanity_groq(groq_q)

        # Compose prompt for Makcorps: include user message and any found data
        prompt_parts = ["You are Hotelix assistant.", f"User: {user_message}"]
        if recommendations:
            # include a concise summary of top 5
            summary_lines = []
            for h in recommendations[:5]:
                name = h.get("name") or h.get("title") or h.get("_id")
                city = h.get("city") or h.get("location")
                price = h.get("price_per_night")
                summary_lines.append(f"- {name} | {city} | {price}")
            prompt_parts.append("Recommendations:\n" + "\n".join(summary_lines))

        final_prompt = "\n\n".join(prompt_parts)
        reply = self.call_makcorps(final_prompt, context={"intent": intent, "parsed": parsed})

        return {"reply": reply, "intent": intent, "recommendations": recommendations}

    def generate_response(self, intent: str, recommendations: Optional[List[Dict[str, Any]]] = None) -> str:
        """Generate a user-facing response given an intent and optional recommendations."""
        if intent == 'search':
            if not recommendations:
                return "Je n'ai pas trouvé de résultats. Vérifiez les dates et le lieu."

            lines: List[str] = [f"J'ai trouvé {len(recommendations)} excellents hôtels ! Voici les meilleurs :"]
            for i, hotel in enumerate(recommendations[:5], 1):
                name = hotel.get('name', '—')
                rating = hotel.get('rating', 'N/A')
                price = hotel.get('price_per_night', 'N/A')
                location = hotel.get('location', '—')
                url = hotel.get('affiliate_url') or hotel.get('url') or ''

                lines.append(f"{i}. {name} — ⭐ {rating}/10")
                lines.append(f"    {price}€/nuit — {location}")
                if url:
                    lines.append(f"    Réserver : {url}")
                lines.append("")

            return "\n".join(lines)

        if intent == 'help':
            return "Je peux vous aider à trouver les meilleurs hôtels ! Indiquez vos dates et votre destination."

        if intent in ('refine', 're ne', 'rene'):
            return "Dites-moi comment affiner votre recherche : budget, équipements, ou type de chambre."

        # default / info
        return "Je suis spécialisée dans les recommandations d'hôtels. Comment puis-je vous aider ?"
