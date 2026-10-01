"""Does the mind service answer what a bot module would ask it? No realm, no module needed.

    python3 tools/adapter_check.py --url http://127.0.0.1:18800 [--token T]
    python3 tools/adapter_check.py --spawn --llm-url http://127.0.0.1:11434/v1 --model qwen3.5:4b

`--url` talks to a service that is already running. Use a scratch one, not the realm's: the requests below name a bot (guid 990001) and the
service will give it a character and a memory in its database. `--spawn` starts a throwaway service of its own on a free port with an empty
database in a temporary folder, one model profile (any OpenAI-compatible endpoint, such as a local Ollama) on every lane, and stops it
afterwards. The requests are the ones a module sends (docs/protocol.md): a line said nearby, a welcome, a remark nobody asked for, an emote
and a whisper. Each prints what the bot would say and how long the service took. Exit status 1 when a request fails outright; a bot that
chooses to say nothing is not a failure.
"""
import argparse
import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

BOT = {"bot_guid": 990001, "bot_name": "Elorin Moonwhisper", "race": "Night Elf", "class": "Hunter", "gender": "female", "level": 34,
       "zone": "Ashenvale", "area": "Astranaar", "doing": "walking between errands", "quests": ["The Zoram Strand Report"], "time": "dusk"}
PLAYER = {"speaker_guid": 55, "speaker_name": "Kove", "speaker_is_bot": False}


def call(base, path, body=None, token="", headers=None):
    request = urllib.request.Request(base + path, data=json.dumps(body).encode() if body is not None else None,
                                     headers=dict({"Content-Type": "application/json"}, **({"Authorization": "Bearer " + token} if token else {}), **(headers or {})))
    started = time.monotonic()
    with urllib.request.urlopen(request, timeout=120) as response:
        return json.loads(response.read()), (time.monotonic() - started) * 1000


def free_port():
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


def spawn(args):
    """A throwaway service: (process, base url, temporary folder)."""
    from mind import store as store_module
    folder = tempfile.TemporaryDirectory()
    port = free_port()
    config = os.path.join(folder.name, "dashboard.json")
    with open(config, "w") as handle:
        json.dump({"mind": {"port": port, "db": "mind.sqlite", "statusFile": "status.json", "secretsFile": "secrets.json"}}, handle)
    store = store_module.Store(os.path.join(folder.name, "mind.sqlite"))
    store.save_profile("check", {"base_url": args.llm_url, "model": args.model, "api_key_env": "", "timeout_s": 90, "max_tokens": 300, "price_in": 0.0,
                                 "price_out": 0.0, "price_cached": 0.0, "max_calls_per_min": 0, "daily_budget_usd": 0.0, "fallback": "", "enabled": 1,
                                 "extra": args.extra})
    for lane in ("smart", "fast", "memory", "ambient"):
        store.set_lane(lane, "check")
    process = subprocess.Popen([sys.executable, os.path.join(ROOT, "run-mind.py")], env=dict(os.environ, SQUIDBOTS_DASHBOARD_JSON=config),
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    base = "http://127.0.0.1:%d" % port
    for _ in range(50):
        try:
            call(base, "/health")
            return process, base, folder
        except (urllib.error.URLError, OSError):
            time.sleep(0.2)
    process.terminate()
    raise SystemExit("the throwaway service did not start")


def checks():
    """[(what, path, body, headers)]"""
    near = dict(BOT, **PLAYER, channel="say", scene="check:say")
    return [
        ("a line said nearby", "/ambient", dict(near, message="Well met. Anyone know a safe road to the coast?"), None),
        ("spoken to by name", "/ambient", dict(near, message="Elorin, what brings you out here?", addressed=True), None),
        ("a player arrives", "/ambient", dict(BOT, mode="welcome", player_guid=55, player_name="Kove", channel="say"), None),
        ("speaking up unprompted", "/ambient", dict(BOT, mode="start", channel="say", scene="check:say"), None),
        ("an emote", "/ambient", dict(BOT, mode="emote", emote="bow", player_name="Kove", channel="say"), None),
        ("a whisper (conversation lane)", "/v1/chat/completions",
         {"messages": [{"role": "system", "content": "You are a bot in an online game. Reply briefly."}, {"role": "user", "content": "Who are you?"}]},
         {"X-Mind-Bot-Guid": "990001", "X-Mind-Bot-Name": "Elorin Moonwhisper", "X-Mind-Player-Guid": "55", "X-Mind-Player-Name": "Kove"}),
    ]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--url", help="a running mind service, such as http://127.0.0.1:18800")
    parser.add_argument("--token", default="", help="its bearer token, if it has one")
    parser.add_argument("--spawn", action="store_true", help="start a throwaway service instead (needs --llm-url and --model)")
    parser.add_argument("--llm-url", default="http://127.0.0.1:11434/v1", help="with --spawn: an OpenAI-compatible endpoint")
    parser.add_argument("--model", default="", help="with --spawn: the model name")
    parser.add_argument("--extra", default="", help='with --spawn: extra request fields as JSON, such as \'{"reasoning_effort": "none"}\'')
    args = parser.parse_args(argv)
    if bool(args.url) == bool(args.spawn):
        parser.error("give --url, or --spawn")
    if args.spawn and not args.model:
        parser.error("--spawn needs --model")
    process = folder = None
    base = args.url.rstrip("/") if args.url else ""
    if args.spawn:
        process, base, folder = spawn(args)
    failed = silent = 0
    try:
        health, _ = call(base, "/health", token=args.token)
        print("service: %s %s" % (base, health))
        for what, path, body, headers in checks():
            try:
                answer, ms = call(base, path, body, args.token, headers)
            except (urllib.error.URLError, OSError, ValueError) as error:
                failed += 1
                print("  FAIL  %-30s %s" % (what, error))
                continue
            text = answer.get("text")
            if text is None:                                   # a chat completion
                text = (((answer.get("choices") or [{}])[0].get("message") or {}).get("content") or "")
            silent += 0 if text else 1
            print("  %-4s  %-30s %5.0f ms  %s" % ("ok" if text else "—", what, ms, text or "(says nothing: %s)" % answer.get("reason", "")))
    finally:
        if process:
            process.terminate()
            process.wait(timeout=10)
        if folder:
            folder.cleanup()
    if failed:
        print("%d request(s) failed." % failed)
    elif silent == len(checks()):
        print("Every request came back empty: is a model assigned, and does it answer?")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
