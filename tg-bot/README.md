# Формула Контакта — Telegram Bot

Cloudflare Worker, который отвечает игрокам на вопросы об игре через Google Gemini (бесплатный тир).

---

## Деплой: пошагово

### 1. Создай Telegram-бота

1. Открой [@BotFather](https://t.me/BotFather) в Telegram
2. Отправь `/newbot`
3. Придумай имя и username (например `formula_kontakta_bot`)
4. Сохрани полученный **токен** — он вида `123456789:ABCdef...`

---

### 2. Установи Wrangler (если ещё нет)

```bash
npm install -g wrangler
wrangler login
```

---

### 3. Задеплой Worker

```bash
cd tg-bot
wrangler deploy
```

После деплоя Wrangler покажет URL вида:
```
https://formula-kontakta-bot.ВАШ_АККАУНТ.workers.dev
```
Сохрани его.

---

### 4. Добавь секреты

```bash
wrangler secret put TG_TOKEN
# вставь токен от BotFather

wrangler secret put GEMINI_KEY
# вставь ключ с https://aistudio.google.com/apikey
```

---

### 5. Зарегистрируй webhook

Замени `ВАШ_ТОКЕН` и `ВАШ_WORKER_URL`, затем открой в браузере:

```
https://api.telegram.org/botВАШ_ТОКЕН/setWebhook?url=https://formula-kontakta-bot.ВАШ_АККАУНТ.workers.dev
```

Должно вернуться:
```json
{"ok":true,"result":true,"description":"Webhook was set"}
```

---

### 6. Проверь

Открой бота в Telegram, отправь `/start` — должно появиться приветствие с кнопками выбора персоны.

---

## Команды бота

| Команда | Действие |
|---------|----------|
| `/start` | Приветствие + выбор голоса |
| `/режим` | Сменить голос ответчика |
| `/сброс` | Очистить историю диалога |
| `/помощь` | Список команд |

---

## Настройка контента

Открой `worker.js` и замени блок `GAME_KNOWLEDGE` в начале файла на свои материалы:
- Карточки персонажей
- Механики (открытый/полный рулсеты)
- Тайны и триггеры
- Точные локации

После изменений — снова `wrangler deploy`.

---

## Ограничения бессерверной версии

Сессии (история диалога и выбранная персона) хранятся **в памяти Worker'а** и сбрасываются при холодном старте (примерно раз в несколько часов бездействия). Для большинства игровых сценариев это нормально.

Если нужна персистентность — подключи **Cloudflare KV**:

```bash
# Создать KV namespace
wrangler kv namespace create SESSIONS

# Скопируй полученный id в wrangler.toml (раскомментируй секцию kv_namespaces)
```

Затем в `worker.js` замени `const sessions = new Map()` на работу с `env.SESSIONS`.
