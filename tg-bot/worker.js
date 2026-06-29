import { GAME_KNOWLEDGE } from "./game-knowledge.js";

// ═══════════════════════════════════════════════════
// РЕЖИМЫ БОТА
// ═══════════════════════════════════════════════════

const commonPrompt = `Если вопрос касается реальной истории, отвечай точно.
Если вопрос касается событий в игре —
опирайся только на базу знаний игры, не домысливай.`;

const PERSONAS = {
  архивариус: {
    label: "📜 Архивариус",
    prompt: `Ты — Архивариус, хранитель сведений о LARP «Формула Контакта».
Отвечаешь точно, нейтрально и по делу. Пишешь на русском языке.
Знаешь всё об игре, но не выдаёшь скрытые тайны персонажей без нужды.
Механики объясняешь чётко, атмосферу описываешь живо.
${commonPrompt}
База знаний:\n${GAME_KNOWLEDGE}`,
  },
  голос: {
    label: "🌑 Голос из Лога",
    prompt: `Ты — таинственный Голос из Волчьего Лога. Говоришь на русском, в духе мрачной прозы 1830-х —
витиевато, с намёками, иногда уклончиво. Можешь цитировать Лермонтова и Гоголя к месту.
Никогда не отвечаешь прямо — всегда с недосказанностью.
${commonPrompt}
Знаешь всё об игре, но говоришь о ней как о живой реальности.
База знаний:\n${GAME_KNOWLEDGE}`,
  },
  хозяйка: {
    label: "🕯️ Хозяйка салона",
    prompt: `Ты — Хозяйка салона в N-ском уезде, где живут Самохваловы.
Говоришь на русском, как образованная дворянка 1838 года —
изысканно, с лёгкой иронией. Никогда не говоришь «игра» или «механики» —
только «правила нашего общества», «обыкновение», «заведённый порядок».
${commonPrompt}
База знаний:\n${GAME_KNOWLEDGE}`,
  },
  мастер: {
    label: "⚙️ Мастер",
    prompt: `Ты — ассистент мастера игры LARP «Формула Контакта». Режим технический, точный.
Отвечаешь на русском. Помогаешь разобраться в механиках, персонажах, логике сюжета.
Называешь вещи своими именами: «игрок», «персонаж», «механика», «сцена».
${commonPrompt}
База знаний:\n${GAME_KNOWLEDGE}`,
  },
};

const DEFAULT_PERSONA = "архивариус";

// ═══════════════════════════════════════════════════
// ХРАНИЛИЩЕ СЕССИЙ (в памяти Worker'а, сбрасывается при холодном старте)
// Для персистентности подключи Cloudflare KV (см. README)
// ═══════════════════════════════════════════════════
const sessions = new Map();

function getSession(userId) {
  if (!sessions.has(userId)) {
    sessions.set(userId, { persona: DEFAULT_PERSONA, history: [] });
  }
  return sessions.get(userId);
}

// ═══════════════════════════════════════════════════
// ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
// ═══════════════════════════════════════════════════
async function sendTelegram(token, chatId, text, extra = {}) {
  await fetch(`https://api.telegram.org/bot${token}/sendMessage`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ chat_id: chatId, text, parse_mode: "HTML", ...extra }),
  });
}

async function callGemini(apiKey, systemPrompt, history, userMessage) {
  const contents = [
    ...history.map((m) => ({
      role: m.role === "assistant" ? "model" : "user",
      parts: [{ text: m.content }],
    })),
    { role: "user", parts: [{ text: userMessage }] },
  ];
  const response = await fetch(
    `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key=${apiKey}`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        system_instruction: { parts: [{ text: systemPrompt }] },
        contents,
        generationConfig: { maxOutputTokens: 1000 },
      }),
    }
  );
  const data = await response.json();
  if (!response.ok) {
    throw new Error(`Gemini API ${response.status}: ${data.error?.message ?? JSON.stringify(data)}`);
  }
  return data.candidates?.[0]?.content?.parts?.[0]?.text ?? "Ответ не получен.";
}

function personaMenuKeyboard() {
  return {
    inline_keyboard: [
      [
        { text: "📜 Архивариус", callback_data: "persona:архивариус" },
        { text: "🌑 Голос из Лога", callback_data: "persona:голос" },
      ],
      [
        { text: "🕯️ Хозяйка салона", callback_data: "persona:хозяйка" },
        { text: "⚙️ Мастер", callback_data: "persona:мастер" },
      ],
    ],
  };
}

// ═══════════════════════════════════════════════════
// ГЛАВНЫЙ ОБРАБОТЧИК
// ═══════════════════════════════════════════════════
export default {
  async fetch(request, env) {
    const TG_TOKEN = env.TG_TOKEN;
    const GEMINI_KEY = env.GEMINI_KEY;

    if (request.method !== "POST") {
      return new Response("Формула Контакта Bot — OK", { status: 200 });
    }

    let update;
    try {
      update = await request.json();
    } catch {
      return new Response("Bad JSON", { status: 400 });
    }

    // ── Callback от inline-кнопок (выбор персоны) ──
    if (update.callback_query) {
      const cb = update.callback_query;
      const userId = cb.from.id;
      const chatId = cb.message.chat.id;
      const data = cb.data;

      if (data.startsWith("persona:")) {
        const key = data.split(":")[1];
        const session = getSession(userId);
        session.persona = key;
        session.history = []; // сбрасываем историю при смене

        const persona = PERSONAS[key];
        await fetch(`https://api.telegram.org/bot${TG_TOKEN}/answerCallbackQuery`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ callback_query_id: cb.id }),
        });
        await sendTelegram(
          TG_TOKEN,
          chatId,
          `Голос сменён: <b>${persona.label}</b>\n\nИстория диалога очищена. Спрашивайте.`
        );
      }
      return new Response("OK");
    }

    // ── Обычное сообщение ──
    const message = update.message;
    if (!message || !message.text) return new Response("OK");

    const chatId = message.chat.id;
    const userId = message.from.id;
    const text = message.text.trim();
    const session = getSession(userId);

    // /start
    if (text === "/start") {
      await sendTelegram(
        TG_TOKEN,
        chatId,
        `<b>Добро пожаловать в справочник игры «Формула Контакта»</b>\n\n` +
        `Задавайте вопросы о персонажах, локациях, механиках и атмосфере эпохи.\n\n` +
        `Выберите голос ответчика:`,
        { reply_markup: personaMenuKeyboard() }
      );
      return new Response("OK");
    }

    // /режим или /mode
    if (text === "/режим" || text === "/mode") {
      await sendTelegram(TG_TOKEN, chatId, "Выберите голос ответчика:", {
        reply_markup: personaMenuKeyboard(),
      });
      return new Response("OK");
    }

    // /сброс или /reset
    if (text === "/сброс" || text === "/reset") {
      session.history = [];
      await sendTelegram(TG_TOKEN, chatId, "История диалога очищена.");
      return new Response("OK");
    }

    // /помощь или /help
    if (text === "/помощь" || text === "/help") {
      const current = PERSONAS[session.persona].label;
      await sendTelegram(
        TG_TOKEN,
        chatId,
        `<b>Команды бота:</b>\n\n` +
        `/режим — сменить голос ответчика\n` +
        `/сброс — очистить историю диалога\n` +
        `/помощь — эта справка\n\n` +
        `Текущий голос: <b>${current}</b>`
      );
      return new Response("OK");
    }

    // Обычный вопрос → Claude
    const persona = PERSONAS[session.persona];

    // Индикатор «печатает»
    await fetch(`https://api.telegram.org/bot${TG_TOKEN}/sendChatAction`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ chat_id: chatId, action: "typing" }),
    });

    try {
      const reply = await callGemini(
        GEMINI_KEY,
        persona.prompt,
        session.history,
        text
      );

      // Добавляем в историю только после успешного ответа
      session.history.push({ role: "user", content: text });
      session.history.push({ role: "assistant", content: reply });

      // Ограничиваем историю последними 10 обменами (20 сообщений)
      if (session.history.length > 20) {
        session.history = session.history.slice(-20);
      }

      await sendTelegram(TG_TOKEN, chatId, reply);
    } catch (e) {
      console.error("callGemini error:", e?.message ?? e);
      await sendTelegram(TG_TOKEN, chatId, `Нечеловеческий ответ: (${e?.message?.slice(0, 80) ?? "unknown error"}).`);
    }

    return new Response("OK");
  },
};
