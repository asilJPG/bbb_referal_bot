"""
БД через Supabase — данные не теряются при редеплое.

Таблица users в Supabase (создать вручную или через SQL):

CREATE TABLE users (
    user_id        BIGINT PRIMARY KEY,
    username       TEXT,
    first_name     TEXT,
    invite_link    TEXT,
    referral_count INTEGER DEFAULT 0,
    created_at     TIMESTAMPTZ DEFAULT now()
);
"""

from supabase import create_client
from config import SUPABASE_URL, SUPABASE_KEY
from typing import Optional

db = create_client(SUPABASE_URL, SUPABASE_KEY)


def get_user(user_id: int) -> Optional[dict]:
    res = db.table("users").select("*").eq("user_id", user_id).execute()
    return res.data[0] if res.data else None


def save_user(user_id: int, username: Optional[str], first_name: Optional[str], invite_link: str):
    db.table("users").upsert({
        "user_id": user_id,
        "username": username,
        "first_name": first_name,
        "invite_link": invite_link,
    }).execute()


def find_user_by_link(invite_link: str) -> Optional[dict]:
    res = db.table("users").select("*").eq("invite_link", invite_link).execute()
    return res.data[0] if res.data else None


def increment_referral(user_id: int):
    user = get_user(user_id)
    if user:
        new_count = (user.get("referral_count") or 0) + 1
        db.table("users").update({"referral_count": new_count}).eq("user_id", user_id).execute()


def get_all_users() -> list[dict]:
    res = db.table("users").select("*").order("referral_count", desc=True).execute()
    return res.data or []


def get_top(limit: int = 10) -> list[dict]:
    res = (db.table("users").select("*")
           .gt("referral_count", 0)
           .order("referral_count", desc=True)
           .limit(limit).execute())
    return res.data or []


def clear_all_links():
    """Обнуляет все ссылки и счётчики."""
    users = get_all_users()
    for u in users:
        db.table("users").update({
            "invite_link": None,
            "referral_count": 0,
        }).eq("user_id", u["user_id"]).execute()