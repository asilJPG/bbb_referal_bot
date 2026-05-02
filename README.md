# 🎁 Referral Bot — инвайт-ссылки на канал

Бот создаёт **персональную invite-ссылку на канал** для каждого пользователя. Telegram сам считает сколько людей вступило по каждой ссылке — бот просто читает этот счётчик через API.

## Как работает

```
Юзер → «Получить ссылку» → бот создаёт invite link на канал
Юзер отправляет ссылку друзьям → друзья вступают в канал
Юзер → «Сколько людей пришло» → бот дёргает API → показывает число
```

Никаких deep link'ов, проверок подписки, pending-очередей. Telegram делает всю работу.

## Файлы

```
referral_bot/
├── bot.py          # Запуск
├── config.py       # .env конфиг
├── database.py     # SQLite: user_id → invite_link
├── handlers.py     # Вся логика бота
├── export.py       # Excel-экспорт
├── requirements.txt
└── .env.example
```

## Запуск

```bash
cd referral_bot
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # заполни токен, admin id, channel id
python bot.py
```

**Важно:** бот должен быть **админом канала** с правом создавать invite-ссылки.

## Команды

| Команда | Описание |
|---------|----------|
| `/start` | Главное меню |
| `/admin` | Админ-панель (статистика, топ, Excel) |
