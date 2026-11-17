#!/usr/bin/env python3
"""
EDEKA Python Connector -- Unofficiele API client gebaseerd op edekompile.
Haalt huidige aanbiedingen op van EDEKA winkels (Duitsland).
Geen authenticatie nodig -- alleen een GLN (Global Location Number) van een winkel.
"""

import json
import time
from pathlib import Path
import requests


class EDEKAOffersClient:
    """Haalt aanbiedingen op van EDEKA winkels via hun mobiele API."""

    OFFERS_CLIENT_ID = "edeka-app-android-client"
    OFFERS_CLIENT_SECRET = "wFoBG7VhAIn48kx9SDyVhaN9FttvPZi2"
    
    BASE_URL = "https://b2b-login.api.edeka.de"
    TOKEN_URL = f"{BASE_URL}/auth/realms/ekn-sys-b2b-external-oidc/protocol/openid-connect/token"

    def __init__(self):
        self._session = requests.Session()
        self._session.headers.update({
            "User-Agent": "okhttp/5.3.2",
            "Connection": "Keep-Alive",
        })
        self._bearer_token = None
        self._token_expiry = 0

    def _get_bearer_token(self):
        """Haal een OAuth bearer token op (anoniem, client_credentials)."""
        if self._bearer_token and time.time() < self._token_expiry:
            return self._bearer_token

        data = {"grant_type": "client_credentials"}
        resp = self._session.post(
            self.TOKEN_URL, data=data,
            auth=(self.OFFERS_CLIENT_ID, self.OFFERS_CLIENT_SECRET),
            timeout=15,
        )
        resp.raise_for_status()
        token_data = resp.json()

        self._bearer_token = token_data["access_token"]
        expires_in = token_data.get("expires_in", 3600)
        expires_in = min(max(expires_in, 120), 7 * 24 * 3600)
        self._token_expiry = time.time() + expires_in
        return self._bearer_token

    def get_offers(self, market_gln, page=0, page_size=200):
        """Haal aanbiedingen op voor een specifieke EDEKA winkel."""
        bearer = self._get_bearer_token()
        url = f"https://data.api.edeka.de/v2/retailers/{market_gln}/offers"
        params = {
            "marketGln": market_gln,
            "page": page,
            "size": page_size,
            "sortedByCategory": "true",
        }
        resp = self._session.get(
            url, params=params,
            headers={"Authorization": f"Bearer {bearer}"},
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()

    def get_all_offers(self, market_gln):
        """Haal ALLE aanbiedingen op voor een markt."""
        all_offers = []
        page = 0
        while True:
            data = self.get_offers(market_gln, page=page, page_size=200)
            offers = data.get("offers", [])
            all_offers.extend(offers)
            total_count = data.get("totalCount")
            if total_count is None or len(all_offers) >= total_count:
                break
            page += 1
        return {
            "offers": all_offers,
            "totalCount": len(all_offers),
            "validFrom": data.get("validFrom"),
            "validTill": data.get("validTill"),
            "national": data.get("national"),
        }


def parse_edeka_offers(edeka_data):
    """Parse EDEKA API data naar ons standaard formaat."""
    results = []
    valid_from = edeka_data.get("validFrom", "")
    valid_till = edeka_data.get("validTill", "")

    for offer in edeka_data.get("offers", []):
        price_info = offer.get("price", {})
        price_str = price_info.get("value", "0")
        try:
            price = float(price_str.replace(",", "."))
        except (ValueError, AttributeError):
            price = None

        category = offer.get("category", {}).get("name", "")
        descriptions = offer.get("descriptions", [])
        title = offer.get("title", "")

        full_name = title
        if descriptions:
            full_name = f"{title} -- {' '.join(descriptions)}"

        image_url = offer.get("image", {}).get("imageUrl", "")
        discount = offer.get("discount", "")

        results.append({
            "name": full_name,
            "price": price,
            "amount": descriptions[0] if len(descriptions) > 1 else "",
            "category": category,
            "link": None,
            "image": image_url,
            "discount": discount,
            "validFrom": valid_from,
            "validTill": valid_till,
            "national": offer.get("national"),
        })

    return results


if __name__ == "__main__":
    client = EDEKAOffersClient()
    market_gln = "4314021182307"  # Tübingen

    print("=== EDEKA Markte Tübingen (GLN: {}) ===\n".format(market_gln))

    try:
        data = client.get_all_offers(market_gln)
        products = parse_edeka_offers(data)

        print("Aanbiedingen: {}".format(len(products)))
        print("Geldig van: {} tot {}".format(data.get("validFrom"), data.get("validTill")))
        print("Type: {}".format("Nationaal" if data.get("national") else "Lokaal"))
        print()

        for i, p in enumerate(products[:30]):
            print("{}. {}".format(i+1, p["name"]))
            if p["price"]:
                print("   Prijs: EUR{:.2f}".format(p["price"]))
            if p.get("discount"):
                print("   Korting: {}".format(p["discount"]))
            if p.get("category"):
                print("   Kategorie: {}".format(p["category"]))
            print()

    except Exception as e:
        print("Fout: {}".format(e))
