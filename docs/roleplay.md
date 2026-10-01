# Roleplay mode: bots that are people in the world of Warcraft

Out of the box a bot talks like a player at a keyboard (banter, hot takes, LFG and Trade adverts). **Roleplay mode, the default,
makes every bot a character in the lore instead:** a person of its race and calling, with a backstory that grows as it levels, who
knows the zone it is standing in and what it is doing there, who talks in character in `/say`, `/yell` and guild chat and stays out
of the realm channel, General, Trade and Looking For Group. You can talk to them, roleplay with them, and they stay in character.

Switch it on the **Minds page, Chat style**: *Roleplay* or *Fake players*. The game follows within a few seconds, with no restart.
Nothing of the fake-player side is removed: its personalities, line bank and settings are kept, and switching back restores them.

This needs the game module's roleplay support (`synthiqbots`, `docs/roleplay.md`): it tells the service each bot's race, class,
gender, level, zone and open errands, and it keeps the bots quiet in the channels a character would not use. A bot the game has not yet
described to the service simply talks as a player until it has.

## What a character is

The first time the service is told a bot's race and class it makes a character, deterministically from the bot's guid (so a bot is the
same person after a restart, and two runs agree):

- **A calling** that suits its race and class: four per race, forty in all. A human may be a knight-errant, a plague refugee, a
  farmstead child or a Kirin Tor scholar; a night elf a Sentinel, a druid of the Cenarion Circle, a devotee of Elune or a long-memoried
  elder; an orc a spirit-walker, a veteran of the Dark Portal wars, a Durotar-born warrior or a Warsong grunt. A paladin is more likely
  a knight-errant than a farm child, never certainly.
- **A temperament, a way of speaking, convictions and a goal**, from the calling and the people's own voice (a dwarf's "lad" and "by
  me beard", a troll's "mon", a Forsaken's dry remarks about being dead).
- **A life**: where they were born, three formative events, a teacher, a relative, a rival (named, with names that suit the race), a
  keepsake, a habit, a fear. These are the *facts*, which the story and every chapter must agree with.
- **A story and chapters.** A model writes the backstory in full from the facts, and as the bot levels it writes a new chapter for each
  stretch of life (levels 1-9, 10-19, 20-29, ... 70-80): where they were, what happened, what changed in them, consistent with
  everything before. Until a model has written a piece (or with no model at all) a template stands in, so a prompt is never
  short of a life. A bot first seen at level 45 gets chapters for every stretch up to 45.
- **A race-suited name** (optional): see *Names* below.

Everything in the character is shown on the bot's sheet (Minds page, *A bot's mind*), where you can rewrite any of it. A character
you edit is marked *written by you* and is never rewritten behind your back.

## The Conquest of Azeroth crafts in the lore

The realm's twenty-one extra classes (ids 12 to 32: Barbarian, Witch Doctor, Felsworn, Witch Hunter, Stormbringer, Knight of Xoroth,
Guardian, Templar, Bloodmage, Ranger, Chronomancer, Necromancer, Pyromancer, Cultist, Starcaller, Sun Cleric, Tinker, Venomancer, Reaper,
Primalist, Runemaster) are written into the world rather than left as game terms (`CLASS_LORE` in `mind/lore.py`). Each has what the
craft does, where it comes from and who teaches it, and how ordinary people see it: a Necromancer practises the Scourge's art taken up
by the living and the Forsaken, and is shunned in Stormwind and merely avoided in Undercity; a Runemaster carries the rune-lore of the
dwarves and their Earthen forebears; a Chronomancer studied beside the Bronze Dragonflight's mortal students. Any race may follow any of
them. A character is told its own craft's origin and reputation, and (in the full prompt) one line on each of the others it may meet on
the road, so bots can talk about each other's crafts in the world's terms. These are our own tie-ins between the classes and
Warcraft's established peoples and places, not canon; edit the table to change them.

## What the model is shown

Every time a bot speaks, the model gets one system prompt (`mind/rp.py`, `persona_block`): who the bot is; its people's history,
beliefs, view of the other peoples and enemies; its story so far; a few lines of its own bank as examples of how it sounds; and **right now**:
the zone and its lore (`mind/lore.py` holds 70 zones), the area, what it is doing, the time of day and any holiday being kept (Brewfest is
on right now on the test realm), the errands in its log (told as tasks and commissions, never as "quests", each with a one-line description
a model wrote once from the quest's own aim), what has happened to it lately (below), and how seasoned it is for its level, so a level-5
does not talk like a level-75. Then the rules (editable on the page): stay in character, never mention
levels, servers or the game, know only what someone of this age and place would know, be vague rather than invent a fact, answer
out-of-character `(( ))` briefly and then go back to the scene, but only when the other person writes `(( ))` or `ooc` first: an odd question ("are you an AI?") is put to the person being played and answered in character.

The lore is Warcraft as of Wrath of the Lich King, which is what the realm runs, and every character lives in that age: nothing
later is known. Conversation uses the same memory as before (what each player said, how the bot feels about them), so a bot
remembers you and can become a friend or a rival.

Short remarks use a compact version of the prompt, so a line costs about as much as before.

## How they talk: short and direct

Chat is short. A bot talking among other bots, greeting someone or remarking on the road is asked for **a few words or one short sentence**
(`RP_MAX_CHARS` 90, cut at 130). Only when a player is really talking with it (spoken to by name, or answering something the bot said a moment ago)
does it get the conversation tier: one or two short sentences, up to 160 characters (cut at 220), still answering first and plainly. An NPC
answering a player is in a conversation too.

Guild chat had read like a sermon, with every greeting and farewell a blessing ("Elune watch over you", "by the Light", "may the ancestors guide
you"). Four things now stop it:

- **The prompt.** The reply rules say to be direct, with no blessings, prayers, speeches, riddles or scenery, and to mention the faith only when
  the talk is about faith. The guild scene is "plain and practical, like workmates on a break" (it was "the fireside talk of your
  guild-fellows"). A character's sayings are for one line in ten at most, never to open or close a reply, and the "lore" register no longer asks
  for beliefs.
- **The model's line.** A blessing at the start or end of a line is cut (`rp_bank.strip_sermon`): "Elune watch over you, traveler. What brings you
  to Astranaar?" says "What brings you to Astranaar?". A line that is nothing else is not said. If the player's own line is about faith (prayer,
  the Light, the gods) the blessing stays.
- **The bank.** About 6% of the 77,000 banked lines were blessings (the prayer, faith, greeting, farewell, hail and thanks cells most of all).
  They are no longer served outside the faith cells, and the generator drops new ones.
- **The setting.** The default of the Chat style "rules" box says to be brief and direct (a blank box means the default).

## Where bots speak up

- **Always answered, in every channel:** whispers, party chat, a player talking to a bot by name, and anything a bot is asked to do.
- **Speaking up by themselves:** only in the channels ticked on the page (default `/say`, `/yell` and guild). A character near a
  whitelisted player says something in `/say` now and then; the people around may answer, in character, a few lines deep, then it goes
  quiet. Some remarks (default 40%) are written from what the bot is doing: the zone it stands in, its errands, its story. The rest
  come from the bank, free, and may be about the very zone it is in.
- **Stock playerbots chatter** (loot brags, LFG and Trade adverts) in a channel a character would not use is not said at all. In
  `/say`, `/yell` and guild it is said in the character's own words.
- The regulars (the cast) still start most of the talk. Their friendships are written in the world's own terms (old comrades, a shared
  oath, mentor and student), only between members of the same side.

## A life that follows what happened

The module keeps a small journal of every bot: level-ups, a new zone, a finished errand, a fall in battle, a dungeon boss or a notorious foe
brought down, a rare find. It goes to the service with the bot's context, which keeps it (`rp_event`) and shows the last few to the model as
"what has happened to you lately". When a bot enters a new stretch of life the chapter it has just finished is **rewritten around what really
happened in it** (two or more events), so the story is the bot's own and not a template. Times are in the world's terms: no numbers, no
levels.

## Gossip, the guild, the hour and the way a people talk

Four things that make the same bots read as people who share a world.

**Gossip.** The module notes a whitelisted player's deaths and level-ups and sends the last three with every bot's context (`rumours`: who, what,
where, how long ago, and how near the bot is: 2 in the same guild, 1 in the same zone, 0 elsewhere). News takes time to travel: a guildmate has it after
two minutes, someone in the zone after seven, anyone else after twenty-five, and after six hours it is no longer news. A bot hears a piece once, and passes
news on no more than once in a quarter of an hour (`rp_rumour`). It reaches the bot's prompt as "A guildmate told you that Kove was struck down ... You were
not there and cannot be sure: mention it as something you heard, vaguely", and far-off news drops the detail (no name for the killer). A bot that has news
to pass on starts a remark about it more often than not (a written one, in guild or say). Only deaths and levels are news, and only about the whitelisted.

**The guild.** The module sends each bot's guild and rank (`guild`, `guild_rank`; rank 0 leads it, rank 1 are its officers). The guild's master speaks
with quiet authority and rarely jokes, an officer is practical and a little dry, a member is easy company, and a newcomer (a rank named Initiate, or
the lowest) asks more than they tell. The place shows in the prompt ("In your guild, The Ashen Hand, you lead the guild ...") and leans what the bot
starts talking about (a master toward the work and plans, a member toward banter and stories).

**The hour.** The module sends the hour as dawn, morning, midday, afternoon, dusk or night. Each has a line in the prompt (dusk: finishing up and thinking of
a roof, a fire and a meal; night: off duty, at a fire or an inn, with no mind to work) and leans what a bot starts talking about: the fire, humour and stories at
night, the work and the zone by day. It is the bots' words that follow the hour, not their feet: nothing sends them to the inn.

**How a people talk.** Every race has a way of talking (a dwarf is gruff and hearty, a night elf measured and distant, a gnome cut off by a better idea) and three
small habits, of which each character keeps two, chosen by its guid so a bot sounds the same every time. It is in the character sheet (`lore.RACE_VOICE`). A troll's
drawl is kept by a filter on the finished line ("da", "dat", "dey", "ya"), because a small model forgets it; links, names and numbers are left alone
(`rp_bank.accent`).

## Presence

Things the module does so that a bot is a person in the world and not a chat source (`docs/roleplay.md` in synthiqbots has the keys):

- **Companions.** A bot in a party with a whitelisted player remarks on a moment of the road in party chat: a new zone, a great foe down, a
  fall, a rare find, a new stretch of its life, now and then an idle thought on a quiet road. Written by the model (`mode: companion`), at
  most one remark per party per 75 s.
- **Greetings.** A bot that knows a player says hello when they walk up to it (`welcome` with `proximity`); strangers are mostly ignored.
- **Emotes.** A bow, wave, thank or laugh aimed at a bot (or near one) is answered with an emote back and, often, a line from the bank (free).
- **The people of the world.** An innkeeper, guard, trainer, vendor or flight master near a whitelisted player answers in character when
  spoken to in `/say`: with them selected, or by name or title (`mode: npc`). They are civil to your side and curt to the other, know the
  zone's lore, and remember the last few lines of the talk. Real innkeepers answer with a warm bed "by the hearth at Tarren Mill".
- **Sides.** The two factions cannot read each other (the game shows gibberish), so a character does not answer the other side, and
  speaks up in `/say` only for those who can understand it, unless the realm allows two-side chat.
- **Quicker speech.** A character talks, it does not type: shorter pauses before and while it answers, and a thinking gesture when it is
  spoken to by name.
- **Characters answer each other from the model, mostly.** A bot's answer to another bot is written by the model reading the talk (75%, setting
  `rp_bank_share_bots`), because a banked line was written for no one in particular and reads as a non sequitur in a guild. The module also slows a
  roleplay conversation down: one answerer per line, a line spoken to someone by name answered by that someone only, at most five lines a scene.
- **Bots do not stay on one subject for ever.** After six lines in a row about the same thing, with no player in the talk, it is let go.

## Responsiveness

Measured on the test realm, whispers to a roleplaying bot:

| | before | now |
|---|---|---|
| prompt per whisper | 6,700 tokens | about 3,000 |
| cost per whisper | $0.00024 to $0.00046 | $0.0001 |
| model time | 1.5 to 1.9 s | about the same: the model's own time |

What changed: small talk and questions about the person ("who are you?", "where do you hail from?", a greeting, thanks) are answered **without the
tool list**, which was most of the prompt (14 tools, about 5,000 tokens); everything else keeps the tools (`plain_chat_no_tools`). The first version
stripped them from anything that named no action word, and "whats your cape" and "can I have it?" got a shrug and an acted-out hand-over: only
positively social lines go without tools now. The prompt is
ordered for the provider's cache, which keeps everything but the last message: the sheet and the module's own text come first and stay
identical from turn to turn, and what changes (the module's state snapshot, where the bot is, what it remembers of this player) is put in
front of the player's words in the last message. Cached input is a tenth of the price: **cached tokens went from 0 to about 80% of the prompt**.
A reply that slips out of the world ("level 50", a later-game name) is said again once, in character, unless the player asked for it out of
character. The service's heartbeat counts both (`plainChats`, `roleplayRetries`).

### Which model for the ambient lane

`tests/bench_roleplay.py` replays 48 situations (six characters, eight lines) against candidate models and has a judge score each answer
(in character, lore, brevity, no player talk, engaging), at about a cent a model:

| model | score /8 | median | p90 | cost per line | slips (of 48) |
|---|---|---|---|---|---|
| gpt-6-luna | 7.73 | 1.26 s | 1.56 s | $0.00014 | 4 |
| gpt-4o-mini | 7.81 | 0.92 s | 1.04 s | $0.00020 | 7 |
| gpt-5-nano | 7.62 | 1.00 s | 1.30 s | $0.00008 | 3 |
| gpt-4.1-nano | 7.60 | 0.75 s | 0.91 s | $0.00013 | 5 |
| gpt-4.1-mini | 7.69 | 0.88 s | 1.00 s | $0.00053 | 4 |
| **gpt-5.4-nano** | 7.75 | 0.87 s | 1.04 s | $0.00029 | **1** |

The scores are all within the judge's noise, so the choice is speed and slips: the test realm's ambient lane runs on gpt-5.4-nano (a third
quicker than gpt-6-luna, one slip in 48); conversation stays on gpt-6-luna, which does the tool work.

### A local model instead of the API

Tried on the test machine (RTX 3070 8 GB, Ollama 0.35 installed in a user folder, no sudo): the same 48 situations on three small open models.

| model | score /8 | median | p90 | note |
|---|---|---|---|---|
| llama3.2:3b | 7.0 to 7.4 | 0.27 to 0.31 s | 0.53 to 0.64 s | 2 GB |
| qwen2.5:7b-instruct | 7.2 | 0.46 s | 0.85 s | 4.7 GB |
| qwen3.5:4b (thinking off) | 7.4 | 0.83 s | 2.4 s | 3.4 GB |
| gemma3:4b | 7.5 | 0.83 s | 3.1 s | 3.3 GB, 7 slips of 48 |
| gpt-5.4-nano (API, for comparison) | 7.75 | 0.87 s | 1.04 s | |

One request at a time a local 3B or 7B is two to three times quicker than the API and free, at a small cost in quality (about 0.4 on the judge's scale). With
four requests at once they queue on the one GPU (median 1.3 s and 1.7 s), which is no better than the API, so it suits a realm where lines arrive a few seconds
apart. The mind service speaks to any OpenAI-compatible endpoint, so a local model is a profile with base URL `http://127.0.0.1:11434/v1`
and a model name, assigned to the Ambient lane (not Conversation, which needs dependable tool calls). `python tests/bench_roleplay.py --models
llama3.2:3b --base-url http://127.0.0.1:11434/v1 --workers 1` measures a model of your own (add `--local-effort none` for a thinking model such as
Qwen3.5, or it writes its reasoning first). The two 4B models score the same as llama within the judge's noise and take three times as long with a long tail. With the short, direct prompts
(see "How they talk") llama keeps lines shorter (median 65 characters, 5 of 48 over 130) than qwen3.5:4b (median 89, 16 of 48 over 130), which
is the other reason llama3.2:3b runs the test realm's Ambient lane (live: about 0.45 s a line, against 0.9 to 1.6 s on the API). If Ollama is down the
profile falls back to the API. The server runs as a systemd user unit (`coa-ollama.service`: 30 minutes keep-alive, flash attention, a q8 cache, an 8k window),
so it is up after a restart; `./run.sh ollama start|stop|status` drives it.

**Only the chat runs locally.** Putting every lane on one local model was tried and measured, and the lanes that call tools, or run all the time, do not work on
an 8 GB card:

- *Tool calls.* Replaying 33 captured conversation requests twice: gpt-6-luna 65 of 66; qwen3.5:4b 49 (it calls the invite tool again after it succeeded);
  llama3.2:3b 44 (it never calls a tool for "invite me" or "what class are you"); qwen2.5:7b 17. On the live realm, with every lane on qwen3.5:4b, the small
  talk scenario passed and the class-and-level, memory, invite and tool-error scenarios failed (scenery instead of a lookup, a tool error read out loud, no
  invite). With the Conversation lane back on gpt-6-luna all of them pass.
- *One GPU.* The tactical ticks (every few seconds near a player), the memory lane and the line bank all queue behind the chat. With them local a line said in
  /say was answered after 34 seconds; with them back on the API, after 2.7.

So the Ambient lane is local, and **Plain conversation on the ambient model** (`plain_chat_on_ambient`) sends a whisper that needs no tools, and the words
after a tool has run, to the same local model. Conversation (tools), Quick decisions and Memory stay on gpt-6-luna, which costs about a cent an hour.
A repeated tool call in one turn (a small model calling the invite again after it worked) is answered with words instead (`repeatedCalls` in the status file).

**Keep Jev hosted for now.** Ollama 0.35 serves TypeSafe's own wire format at `/v1/systemone`, so a local decision model is a URL swap. On 16 hand-labelled
picker cases hosted Jev got 16, `tev1:4b` (Together AI, 4.5 GB) 15 at the same ~0.3 s, and `tev1:0.8b` only 6 (it says "none fits" too often). But on an
8 GB card `tev1:4b` and llama3.2:3b do not stay loaded together: alternating them reloads a model on every call (4 to 8 s each), which throws away the speed the
local chat model was for.

To try one anyway: the mind service reads `JEV_URL` (`http://127.0.0.1:11434/v1/systemone`) and `JEV_MODEL` (`tev1:4b`) from its environment, needs no key for
it and counts it as free; the game module has `OllamaChat.Jev.Url` and `OllamaChat.Jev.Model` for the same thing. Both fall back as before when it fails.
With a bigger GPU (or a second card) that keeps both models loaded, this is the cheaper setup.

## The roleplay line bank

Like the fake-player bank (38,700 lines), but in character and twice its size: **3,440 cells** of up to 24 lines each, **77,500 lines**
written on the test realm. Every cell is one race and calling in one situation:

- 40 callings x 35 situations (small talk that stands alone, memories of home, a creed, a remark about the road, the weather, the
  other peoples, the war, a prayer, hailing a stranger, a friend by name, taking on an errand, finding something, battle shouts, and
  fourteen kinds of reply) plus 32 subjects (the Scourge, the Legion, faith, magic, honour, the road ...) as openers and as replies
- 10 peoples x 72 zones: what a person of that race says about Westfall, or Tanaris, or the Storm Peaks, in their own voice and with
  that side's feelings about whose land it is

Lines are filtered before they are kept: nothing that sounds like a player (levels, servers, dungeon finders, bots), no
actions that give the speaker a gender (the same line is said by both), no invented placeholders, battle shouts that claim a role
("I'll heal") dropped, and a second model reads every opening line to drop any that a stranger could not make sense of.

Write it from the Minds page (*Line bank*, **Write roleplay lines**; the model is the ambient lane's, and the whole bank cost $1.75 on
gpt-6-luna and took about an hour), or ask the service directly:

```
curl -s -X POST localhost:18800/bank -d '{"op":"generate","mode":"roleplay","per_cell":24}'
curl -s -X POST localhost:18800/bank -d '{"op":"status"}'
```

Narrow it with `archetypes` (`rp:Night Elf:sentinel`, `rpz:Dwarf`) and `situations` (`rp_idle_muse`, `rp_zone:Westfall`). Lines
already there are kept; a run is safe to repeat.

## Names

Playerbots names a Conquest of Azeroth bot "Alte Bot". `tools/rename_bots.py` renames the random bots to two-word names that suit their
race and gender: **Elorin Moonwhisper** (night elf), **Baldrin Ironbeard** (dwarf), **Fizzle Cogspinner** (gnome), **Gorgrim Skullcleaver**
(orc). It is a **dry run unless you pass `--apply`**, and applying needs the worldserver stopped (the realm caches names in memory).
It writes a rollback script first, renames in one transaction, and can update the mind's database so stories, memories and
friendships follow the new names:

```
python3 tools/rename_bots.py --defaults-file ~/.config/coa-dev/client.cnf \
    --characters-db coa_test_minds_characters --auth-db coa_test_minds_auth --mind-db ~/src/coa-minds/mind.sqlite          # look
python3 tools/rename_bots.py ... --apply                                                                                    # do it
```

Two-word names are left alone by playerbots' own startup rename (`AiPlayerbot.CoaBotSurname` stays on). The module calls a bot by its
first name too ("Elorin, hello"): `Promotion::ShortName` takes the first word of a two-word name, as it took "Alte" from "Alte Bot".

`tools/rename_guilds.py` does the same for guilds a bot leads (dry run unless `--apply`, needs the worldserver stopped, writes a rollback script):
"Elite Guard" becomes "Stormwind Vanguard" or "Orgrimmar Wolfriders" by the leader's side, with a message of the day and an info text in the
same voice. The cost is that nothing on a
nameplate says "bot" any more: that is the point for roleplay, and a reason to leave it undone if you want bots recognisable. Bots made
later are named from playerbots' own list; run the tool again for them. The same guid always gets the same name.

## Settings (Minds page, Chat style)

| Setting | Default | Meaning |
|---|---|---|
| Chat style (`chat_mode`) | `roleplay` | `roleplay` or `players` |
| Where characters speak up (`rp_channels`) | `say,yell,guild` | any of `say, yell, zone, world, trade, lfg, guild` |
| Answers taken from the bank (`rp_bank_share_player`) | 25 % | unnamed lines said near a character; the rest are written. Questions are always written |
| Remarks written from what the bot is doing (`rp_start_llm`) | 40 % | the rest come from the bank |
| Models write backstories and chapters (`rp_ai_story`) | on | off keeps plain templates |
| How characters behave (`rp_rules`) | built in | the rules every character is told |

The game module has its own switch, `OllamaChat.Roleplay.Mode = auto | roleplay | players`, to force a mode without asking this service.

## What it costs

A character's backstory is one model call per bot, ever (about 0.05 cent); a chapter is one call per bot per ten levels. A written
reply to a player is a little dearer than before (the sheet is longer), a bank line is free. Measured on the test realm (28 characters
met so far): every backstory and all 102 chapters written by the model for under a cent in total.

## Verified

- `python -m unittest discover -s tests -t .` (366 tests, no network; `tests/test_roleplay.py`, `tests/test_rename_bots.py` and
  `tests/test_rename_guilds.py` are the new ones).
- On the test realm with the roleplay module (`tools/e2e/roleplay_run.py` in synthiqbots, R1 to R11, all pass): a whisper is answered by a
  character with its sheet, race, calling and story shown to the model; the answer names the zone and the sub-area the bot really stands in;
  "are you an AI?" is answered in character; four minutes among a crowd of bots produced no line in the realm channel or General, and a bot
  spoke aloud in `/say`; a GM level-up reaches the service as a journal event and is shown to the model; a bow is answered with an emote; an
  innkeeper answers in character; a bot that knows the player greets them on walking up; a grouped bot remarks in party chat.
- Not tried: the Windows launcher, the Docker stack, a player of the other faction, a multi-day soak, the thinking gesture and the quicker speech
  pauses (built and deployed, not measured). The weather is not sent: the core keeps a zone's weather state private.

## Files and endpoints

| | |
|---|---|
| `mind/lore.py` | races, callings, classes, 70 zones, level stretches: the data |
| `mind/lore_names.py` | first names and surnames per race, and the generator that never runs out |
| `mind/rp.py` | characters, chapters, the prompt, the story writer |
| `mind/rp_bank.py` | the roleplay situations, subjects and the writer's prompts |
| `tools/rename_bots.py` | race-suited names (dry run by default) |
| tables `rp_character`, `rp_chapter` | in `mind.sqlite`; bank rows share the `bank` table (`rp:<Race>:<calling>`, `rpz:<Race>`) |
| `POST /cast {"op":"mode"}` | what the game polls: `{"chat_mode", "channels"}` |
| dashboard ops | `setting.set chat_mode`, `rp.save`, `rp.reset_story`, `rp.reset_all`, `bank.generate` with `"mode":"roleplay"` |
| `GET /api/mind/rp`, `/api/mind/rp/character?name=` | the characters and one sheet |

`tests/test_roleplay.py` and `tests/test_rename_bots.py` cover it offline.

## Not done, and things to know

- Nothing here makes a model good at lore it was not trained on; the sheet and the zone text steer it and the rules tell it to stay
  vague rather than invent, but it can still be wrong about a detail.
- A character's chapters follow the bot's level, which playerbots changes as it plays; a bot that is levelled by a GM command jumps
  and gets every missing chapter at once.
- Fake-player memories and relationships are shared: a bot that has talked to you remembers you in both modes.
- The Windows launcher and the Docker stack were not touched or tried.
