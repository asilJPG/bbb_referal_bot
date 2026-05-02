import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
CHANNEL_ID = int(os.getenv("CHANNEL_ID", "0"))
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

for name, val in [("BOT_TOKEN", BOT_TOKEN), ("ADMIN_ID", ADMIN_ID),
                  ("CHANNEL_ID", CHANNEL_ID), ("SUPABASE_URL", SUPABASE_URL),
                  ("SUPABASE_KEY", SUPABASE_KEY)]:
    if not val:
        raise ValueError(f"{name} не установлен в .env")