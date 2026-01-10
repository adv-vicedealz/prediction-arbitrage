"""
Fetch Polymarket user profiles to get usernames from wallet addresses.
"""

import requests
import re
import time
import json
from typing import Optional, Dict, List
from dataclasses import dataclass

from .config import RATE_LIMIT_DELAY


@dataclass
class UserProfile:
    """Polymarket user profile data."""
    wallet: str
    username: Optional[str] = None
    display_name: Optional[str] = None
    bio: Optional[str] = None
    profile_url: str = ""

    @property
    def short_wallet(self) -> str:
        """Shortened wallet address."""
        if len(self.wallet) > 10:
            return f"{self.wallet[:6]}...{self.wallet[-4:]}"
        return self.wallet

    @property
    def display(self) -> str:
        """Best available display name."""
        if self.username:
            return f"@{self.username}"
        if self.display_name:
            return self.display_name
        return self.short_wallet


def fetch_profile(wallet: str) -> UserProfile:
    """
    Fetch profile data for a wallet address.

    Scrapes the Polymarket profile page to extract username and other info.
    """
    wallet = wallet.lower()
    profile_url = f"https://polymarket.com/profile/{wallet}"

    profile = UserProfile(
        wallet=wallet,
        profile_url=profile_url
    )

    try:
        # Fetch the profile page
        resp = requests.get(
            profile_url,
            headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
            },
            timeout=30
        )

        if resp.status_code != 200:
            return profile

        html = resp.text

        # Look for __NEXT_DATA__ JSON which contains the profile data
        match = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', html, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group(1))

                # Navigate to profile data (structure may vary)
                props = data.get("props", {})
                page_props = props.get("pageProps", {})

                # Try to find user data in various locations
                user_data = page_props.get("user") or page_props.get("profile") or {}

                if user_data:
                    profile.username = user_data.get("username") or user_data.get("name")
                    profile.display_name = user_data.get("displayName") or user_data.get("display_name")
                    profile.bio = user_data.get("bio")

                # Also check dehydratedState for React Query data
                dehydrated = page_props.get("dehydratedState", {})
                queries = dehydrated.get("queries", [])
                for query in queries:
                    state = query.get("state", {})
                    query_data = state.get("data", {})
                    if isinstance(query_data, dict):
                        if query_data.get("name") and not profile.username:
                            profile.username = query_data.get("name")
                        if query_data.get("displayName") and not profile.display_name:
                            profile.display_name = query_data.get("displayName")
                        if query_data.get("bio") and not profile.bio:
                            profile.bio = query_data.get("bio")

            except json.JSONDecodeError:
                pass

        # Parse username from title tag: "@username on Polymarket"
        if not profile.username:
            match = re.search(r'<title[^>]*>@(\w+) on Polymarket</title>', html)
            if match:
                profile.username = match.group(1)

        # Also check og:title meta tag
        if not profile.username:
            match = re.search(r'<meta property="og:title" content="@(\w+) on Polymarket"', html)
            if match:
                profile.username = match.group(1)

        # Check canonical URL for username
        if not profile.username:
            match = re.search(r'<link rel="canonical" href="https://polymarket.com/@(\w+)"', html)
            if match:
                profile.username = match.group(1)

    except Exception as e:
        print(f"    Error fetching profile for {wallet[:10]}...: {e}")

    return profile


def fetch_profiles(wallets: List[str], limit: int = 50) -> Dict[str, UserProfile]:
    """
    Fetch profiles for multiple wallets.

    Args:
        wallets: List of wallet addresses
        limit: Maximum number of profiles to fetch

    Returns:
        Dict mapping wallet address to UserProfile
    """
    profiles = {}

    for i, wallet in enumerate(wallets[:limit]):
        if (i + 1) % 10 == 0:
            print(f"  Fetching profiles: {i + 1}/{min(len(wallets), limit)}")

        profile = fetch_profile(wallet)
        profiles[wallet.lower()] = profile

        time.sleep(RATE_LIMIT_DELAY * 2)  # Be gentle with rate limiting

    return profiles


def enrich_traders_with_profiles(
    traders: List[dict],
    profiles: Dict[str, UserProfile]
) -> List[dict]:
    """
    Add profile data to trader records.
    """
    for trader in traders:
        wallet = trader.get("wallet", "").lower()
        if wallet in profiles:
            profile = profiles[wallet]
            trader["username"] = profile.username
            trader["display_name"] = profile.display_name
            trader["display"] = profile.display

    return traders
