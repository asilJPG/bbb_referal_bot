"""
Хэндлеры бота.

Подсчёт рефералов через ChatMemberUpdated:
  Кто-то вступает в канал → Telegram шлёт event с invite_link →
  бот находит владельца ссылки → +1 в Supabase.
"""

import os
import logging
from aiogram import Router, F, Bot
from aiogram.types import (
    Message, CallbackQuery, FSInputFile,
    ChatMemberUpdated, InlineKeyboardMarkup, InlineKeyboardButton,
)
from aiogram.filters import CommandStart, Command
from aiogram.filters.chat_member_updated import (
    ChatMemberUpdatedFilter, JOIN_TRANSITION,
)

from config import ADMIN_ID, CHANNEL_ID
from database import (
    get_user, save_user, find_user_by_link,
    increment_referral, get_all_users, get_top, clear_all_links,
)

router = Router()
logger = logging.getLogger(__name__)


# ─── Клавиатуры ──────────────────────────────────────────

def user_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔗 Получить мою ссылку", callback_data="get_link")],
        [InlineKeyboardButton(text="📊 Сколько людей пришло", callback_data="my_stats")],
    ])


def admin_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Вся статистика", callback_data="admin_stats")],
        [InlineKeyboardButton(text="🏆 Топ", callback_data="admin_top")],
        [InlineKeyboardButton(text="📥 Экспорт Excel", callback_data="admin_export")],
    ])


# ══════════════════════════════════════════════════════════
# ГЛАВНОЕ: ловим вступление в канал
# ══════════════════════════════════════════════════════════

@router.chat_member(ChatMemberUpdatedFilter(member_status_changed=JOIN_TRANSITION))
async def on_channel_join(event: ChatMemberUpdated):
    """
    Кто-то вступил в канал → Telegram шлёт invite_link →
    ищем владельца ссылки → +1 реферал.
    """
    if event.chat.id != CHANNEL_ID:
        return

    if not event.invite_link:
        return

    link = event.invite_link.invite_link
    logger.info(f"Новый участник {event.new_chat_member.user.id} по ссылке {link}")

    owner = find_user_by_link(link)
    if not owner:
        return

    # Не считаем самореферал
    if owner["user_id"] == event.new_chat_member.user.id:
        return

    increment_referral(owner["user_id"])
    logger.info(f"Реферал засчитан для {owner['user_id']}")

    # Уведомляем владельца ссылки
    try:
        updated = get_user(owner["user_id"])
        count = updated["referral_count"] if updated else "?"
        await event.bot.send_message(
            owner["user_id"],
            f"🎊 По твоей ссылке вступил новый человек!\n"
            f"Всего приглашённых: <b>{count}</b>",
            parse_mode="HTML",
        )
    except Exception:
        pass


# ─── /start ──────────────────────────────────────────────

@router.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer(
        f"👋 Привет, <b>{message.from_user.first_name or 'друг'}</b>!\n\n"
        f"Я создам тебе персональную ссылку-приглашение в канал.\n"
        f"Делись ею с друзьями — я считаю каждого вступившего!",
        reply_markup=user_kb(),
        parse_mode="HTML",
    )


# ─── Получить ссылку ─────────────────────────────────────

@router.callback_query(F.data == "get_link")
async def cb_get_link(callback: CallbackQuery):
    user = callback.from_user
    existing = get_user(user.id)

    if existing and existing.get("invite_link"):
        # Ссылка уже есть — напоминаем
        link = existing["invite_link"]
        count = existing.get("referral_count", 0)
        await callback.message.answer(
            f"📌 У тебя уже есть ссылка:\n\n"
            f"<code>{link}</code>\n\n"
            f"👥 По ней вступило: <b>{count}</b> чел.\n"
            f"Продолжай делиться ею с друзьями! 🚀",
            parse_mode="HTML",
        )
    else:
        # Первый раз — создаём ссылку
        link_obj = await callback.bot.create_chat_invite_link(
            chat_id=CHANNEL_ID,
            name=f"{user.first_name or user.id}"[:32],
            creates_join_request=False,
            member_limit=None,
            expire_date=None,
        )
        link = link_obj.invite_link
        save_user(user.id, user.username, user.first_name, link)
        await callback.message.answer(
            f"🔗 <b>Твоя ссылка на канал:</b>\n\n"
            f"<code>{link}</code>\n\n"
            f"Отправляй друзьям — каждый вступивший засчитается тебе!",
            parse_mode="HTML",
        )

    await callback.answer()


# ─── Моя статистика ──────────────────────────────────────

@router.callback_query(F.data == "my_stats")
async def cb_my_stats(callback: CallbackQuery):
    user = get_user(callback.from_user.id)

    if not user or not user.get("invite_link"):
        await callback.message.answer("У тебя ещё нет ссылки. Нажми «Получить мою ссылку» 👆")
        await callback.answer()
        return

    await callback.message.answer(
        f"📊 По твоей ссылке вступило: <b>{user['referral_count']}</b> чел.",
        parse_mode="HTML",
    )
    await callback.answer()


# ─── Топ рефереров ───────────────────────────────────────

@router.callback_query(F.data == "top")
async def cb_top(callback: CallbackQuery):
    top_users = get_top(10)

    if not top_users:
        await callback.message.answer("Пока никто никого не пригласил 🤷")
        await callback.answer()
        return

    medals = {1: "🥇", 2: "🥈", 3: "🥉"}
    lines = ["🏆 <b>Топ рефереров:</b>\n"]
    for i, u in enumerate(top_users, 1):
        medal = medals.get(i, f"{i}.")
        name = u["first_name"] or u["username"] or f"id:{u['user_id']}"
        lines.append(f"{medal} {name} — <b>{u['referral_count']}</b>")

    await callback.message.answer("\n".join(lines), parse_mode="HTML")
    await callback.answer()


# ─── Отзыв всех ссылок ──────────────────────────────────

@router.message(Command("revoke"))
async def cmd_revoke(message: Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("⛔ Нет доступа.")
        return

    users = get_all_users()
    count = 0
    for u in users:
        if u.get("invite_link"):
            try:
                await message.bot.revoke_chat_invite_link(
                    chat_id=CHANNEL_ID,
                    invite_link=u["invite_link"],
                )
                count += 1
            except Exception:
                pass

    clear_all_links()
    await message.answer(f"✅ Отозвано ссылок: <b>{count}</b>\nБД очищена.", parse_mode="HTML")


# ─── Админ ───────────────────────────────────────────────

@router.message(Command("admin"))
async def cmd_admin(message: Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("⛔ Нет доступа.")
        return
    users = get_all_users()
    await message.answer(
        f"🛠 <b>Админ-панель</b>\n\nПользователей: <b>{len(users)}</b>",
        reply_markup=admin_kb(),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "admin_stats")
async def cb_admin_stats(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("⛔", show_alert=True)
        return

    users = get_all_users()
    if not users:
        await callback.message.answer("Пока нет пользователей.")
        await callback.answer()
        return

    lines = [f"📊 <b>Статистика</b> ({len(users)} чел.)\n"]
    for i, u in enumerate(users[:30], 1):
        name = u["first_name"] or u["username"] or "—"
        uname = f"@{u['username']}" if u["username"] else f"id:{u['user_id']}"
        lines.append(f"{i}. {name} ({uname}) — <b>{u['referral_count']}</b>")

    if len(users) > 30:
        lines.append(f"\n... ещё {len(users) - 30}. Скачай Excel.")

    await callback.message.answer("\n".join(lines), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "admin_top")
async def cb_admin_top(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("⛔", show_alert=True)
        return
    top_users = get_top(15)
    if not top_users:
        await callback.message.answer("Рефералов пока нет.")
        await callback.answer()
        return

    medals = {1: "🥇", 2: "🥈", 3: "🥉"}
    lines = ["🏆 <b>Топ-15:</b>\n"]
    for i, u in enumerate(top_users, 1):
        medal = medals.get(i, f"{i}.")
        name = u["first_name"] or u["username"] or f"id:{u['user_id']}"
        lines.append(f"{medal} {name} — <b>{u['referral_count']}</b>")

    await callback.message.answer("\n".join(lines), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "admin_export")
async def cb_admin_export(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("⛔", show_alert=True)
        return

    users = get_all_users()
    if not users:
        await callback.message.answer("Нет данных.")
        await callback.answer()
        return

    from export import export_stats_to_xlsx
    filepath = export_stats_to_xlsx(users)

    try:
        doc = FSInputFile(filepath, filename=os.path.basename(filepath))
        await callback.message.answer_document(doc, caption=f"📊 {len(users)} пользователей")
    finally:
        if os.path.exists(filepath):
            os.remove(filepath)

    await callback.answer()