# Talking to the mind service from another bot module

The mind service (`run-mind.py`, standard-library Python, one SQLite file) knows nothing about AzerothCore, playerbots or
mod-ollama-chat. A bot module of any kind can use it: it sends small JSON requests over HTTP and says what comes back. That is the whole
integration. The Minds dashboard page is only a control panel for the same database and is not needed.

What a module has to do:

1. **Hear** chat near its bots (any `PlayerScript::OnPlayerChat`-style hook) and send it to `/ambient`.
2. **Say** the `text` of the answer as the bot (`Player::Say`, a channel, a guild message).
3. **Tell the service who the bot is**: guid, name, race, class, level, zone. Everything else (the character, its story, its memory) is the
   service's business and is keyed on the bot's guid, so the same guid must always mean the same bot.

Start it with `python3 run-mind.py` (port 18800 on 127.0.0.1; `dashboard.json` has a `"mind"` object for the port, the database path and an
optional bearer `token`). Give it a model on the Minds page, or in the database (`profile` and `lane` tables): any OpenAI-compatible
endpoint, including a local Ollama. `tools/adapter_check.py` runs the requests below against a service and prints what comes back.

## Auth

If `mind.token` is set, send `Authorization: Bearer <token>`. With no token the service accepts any caller on its address, which is only
sensible on 127.0.0.1.

## `POST /ambient`: one line of chat from one bot

The reply to something said nearby (no `mode`):

```json
{"bot_guid": 812, "bot_name": "Elorin Moonwhisper",
 "speaker_guid": 55, "speaker_name": "Kove", "speaker_is_bot": false,
 "channel": "say", "message": "Anyone know a safe road to the coast?",
 "scene": "map1:zone331", "addressed": false,
 "race": "Night Elf", "class": "Hunter", "gender": "female", "level": 34,
 "zone": "Ashenvale", "area": "Astranaar", "doing": "walking between errands",
 "quests": ["The Zoram Strand Report"], "time": "dusk"}
```

- `channel`: `say`, `yell`, `zone`, `guild`, `trade`, `lfg`, `world`.
- `scene`: any string that is the same for everyone who can hear each other. The service keeps the last lines said in a scene so that
  the bots answer the talk and not only the last line, and answers one scene one at a time.
- `addressed`: true when the speaker spoke to this bot by name or in a whisper-like way. Spoken to, a bot answers in a sentence or two;
  otherwise it keeps to a few words.
- `race` (the ten stock races, by name), `class` (or `klass`), `gender` (`male`, `female`, `0`, `1`), `level`, `zone`, `area`, `doing`,
  `quests` (a list of titles, or `{"title", "goal"}`), `events` (`[{"k": "death", "t": "was struck down", "ago": 900}]`), `time`,
  `weather`, `holidays`: the facts a character's life is built from. All optional; the more there is, the more the bot sounds like it lives
  where it is. `class_id` and `zone_id` work too.

The answer: `{"text": "Aye, keep to the main road.", "latency_ms": 480, "cost_usd": 0.0, "source": "bank"}`, or `{"text": "", "reason": "quiet"}`
when the bot has nothing to say (say nothing; this is the normal case for a quiet bot or a line that is not for it). `reason` is for your logs.

Other `mode`s on the same endpoint, each returning `{"text": ...}` the same way:

| `mode` | when | extra fields |
|---|---|---|
| `start` | nobody spoke and a bot may speak up (call it now and then for bots near a player) | `channel` |
| `welcome` | a player came near, logged in or joined the guild | `player_guid`, `player_name`, `joined` |
| `companion` | a bot travelling with a player remarks on something | `event`, `detail`, `companions` |
| `emote` | a player emoted at a bot | `emote`, `player_name` |
| `npc` | a player talked to a real NPC | `npc_name`, `npc_title`, `faction`, `message`, `player_name`, `player_race` |
| `combat` | a combat director picked a target | `kind` (`focus`, `cc`), `mob` |
| `rewrite` | a bot is about to say a stock line; put it in the bot's own words | `message`, `category` |

## `POST /v1/chat/completions`: a player talks to a bot (the Conversation lane)

An OpenAI chat completion request, with tools if the bot can act. Name the bot and the player with headers:

```
X-Mind-Bot-Guid: 812
X-Mind-Bot-Name: Elorin Moonwhisper
X-Mind-Player-Guid: 55
X-Mind-Player-Name: Kove
```

The service adds the bot's character, story and what it remembers of the player in front of the module's own system prompt, calls its model,
and returns the model's answer unchanged in shape: text, or `tool_calls` for the module to run and send back (the usual loop). The module
supplies the tools; the service never runs one. A bot that is not a bot of the service's (no headers, no names found) is passed through to the
model untouched.

## `POST /cast` and `POST /bank`

`/cast` (`op`: `sync`, `rank`, `status`, `mode`) keeps a small cast of the realm's regulars and tells the module whether the realm is in
roleplay mode (`{"op": "mode"}` returns `{"ok": true, "chat_mode": "roleplay", "channels": ["say", "yell", "guild"]}`): a module that wants to stay out of chat channels
in roleplay reads that. `/bank` (`op`: `generate`, `status`, ...) writes the line bank in the background. A new module can ignore both.

## Order of work for a new module

1. `python3 tools/adapter_check.py --url http://127.0.0.1:18800` with a model assigned: confirms the service answers.
2. Hook chat: for each bot within earshot of a player's line, send the `/ambient` request, and say any `text` after a short random delay
   (the service answers in under a second with a local model, but a person types).
3. Send `start` for a bot near a player every minute or two, and `welcome` when a player arrives.
4. Later: the Conversation lane, with the module's own tools.

Do not send a bot's chat to every bot in the world: only bots near a player are worth the call, and the service's cost is per call.
