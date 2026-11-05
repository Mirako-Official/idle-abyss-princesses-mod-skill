# Optional: chat with the hero through the player's own AI (IAP.ai)

Since game version 3.0.2 the desktop game has an **AI interface**: in Settings → Mods → AI interface
the player enters an OpenAI-compatible service (DeepSeek, OpenAI, a local model…), a model and their
own key. Mods can then send text to that service through `IAP.ai` and get replies. The key and the
address stay in the game's main process; mods cannot read them or change where text goes. Every
request starts with fixed safety rules the game adds. The browser build has no AI interface.
Full contract: Author Kit `docs/MODDING.md` section 14.14.

```js
IAP.ai.available()            // boolean: desktop build with the AI interface
await IAP.ai.status()         // { ok, host, model, maxTokens, dailyCap, usedToday, enc }
await IAP.ai.configure()      // opens the player's settings window; resolves with the new status
await IAP.ai.chat({ messages: [{ role: 'system' | 'user' | 'assistant', content }], maxTokens, temperature })
//  → { ok: true, text, reasoning, usage: { prompt, completion, total, estimated }, model, ms }
//  → { ok: false, error: unavailable | not_configured | busy | quota | bad_request | auth | rate | server | timeout | network | bad_response, message }
```

## Using the template

`templates/ai_chat.js` is a working chat window: top-bar button while playing the hero, chat log per
character slot, status line, "AI settings" and "Clear" buttons, error messages for every error code,
reasoning shown in a collapsible block, and an optional **feeding bonus** (tokens spent → permanent
damage %, account-wide, capped). Copy it into the mod, list it last in `scripts`, edit `CONFIG`:
- `hero`: the hero id; `name`: display name per language
- `persona`: the character sheet (looks, personality, how the character talks, the skills in plain words,
  running jokes). Keep it short; it is sent with every message.
- `greeting`, `bonus` (`null` to disable), `maxTokens`, `keep` (history length)
With the bonus on, multiply `hitMultiplier` and `estimate().dmg` by `MOD.shared.tokenMul()` (the
template's header shows the two lines).

## Rules that matter

- **Replies are untrusted text.** A model can output anything, including HTML. Put replies in the page
  with `createTextNode` / `textContent` only (the template does), never `innerHTML`.
- Send only what the chat needs: the character sheet, recent messages, a line of game state (level,
  stage). Never whole saves or account data (Workshop rule 3).
- Say in the Workshop description that the hero can call the player's own AI service and that the
  player's provider bills the tokens. The feature must work as an extra: the hero has to be complete
  without it.
- A token-based bonus rewards spending the player's money: keep it small and capped, and do not let
  the character beg for tokens in a pushy way (the template's persona says so).
- Fan characters based on a real company's mascot: say in the persona and the description that it is
  a fan-made character, not the company.

## Testing

Ask the player to connect a service in Settings → Mods → AI interface, then chat a few lines while
playing the hero. Check: replies appear in the player's language, errors show friendly lines (try
a wrong key → auth; airplane mode → network), the bonus line updates, the character page DPS goes up
by the bonus. The game shows today's token use and the daily cap in the AI interface row.
