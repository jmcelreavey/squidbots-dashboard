"""Who is in the roster: the random bots that log in, and how to keep chosen ones offline.

Playerbots keeps its roster in its own database: one `add` row per random bot that belongs in the world (table
`playerbots_random_bots`, owner 0). Logging every bot out when the last real player leaves (AiPlayerbot.DisabledWithoutRealPlayer)
leaves those rows alone, so the same bots come back. A worldserver restart does not: playerbots deletes every `add` row at start and
draws a new roster at random. The mod-ollama-chat module (OllamaChat.Roster.KeepAcrossRestarts, on by default) keeps a copy under the
event name `ollama_roster` and puts the rows back at startup, so a restart brings back the same bots too. New ones are picked, at random,
only to fill a place that has no row: a bigger MaxRandomBots, or a bot taken out of the roster.

  python3 tools/roster.py list   [--names]        how many are in the roster, online, benched; --names lists every bot
  python3 tools/roster.py bench   NAME [NAME ...] take these bots out of the roster, and mark them so they are never picked to fill a place
  python3 tools/roster.py unbench NAME [NAME ...] let them be picked again (they do not return by themselves: the next vacancy may pick them)

Benching is a database change, so stop the worldserver first (the realm keeps these rows in memory; the tool refuses while the world
port answers). A benched bot's place is filled by another random bot at the next start. Only the random-bot pool is covered: a bot a
player adds to a party by hand, or one called into a battleground queue, is a different login that no row here controls.

    python3 tools/roster.py --defaults-file ~/.config/coa-dev/client.cnf --characters-db coa_test_minds_characters \\
        --playerbots-db coa_test_minds_playerbots list --names

Standard library only; it talks to MySQL through the `mysql` command line client.
"""
import argparse
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
import rename_bots  # noqa: E402
from mind import lore  # noqa: E402

YEAR_S = 31104000           # AiPlayerbot.PermanentlyInWorldTime's default: how long an `add` row stays valid


def events(args, event):
    """{bot guid} with a row for this event."""
    rows = rename_bots.mysql(args, "SELECT bot FROM `%s`.playerbots_random_bots WHERE owner = 0 AND event = '%s'" % (args.playerbots_db, event))
    return {int(row[0]) for row in rows}


def characters(args):
    """{guid: (name, race, class, level, online)}"""
    rows = rename_bots.mysql(args, "SELECT guid, name, race, class, level, online FROM `%s`.characters" % args.characters_db)
    return {int(guid): (name, int(race), int(klass), int(level), online == "1") for guid, name, race, klass, level, online in rows}


def show(args):
    people, benched = characters(args), events(args, "logout")
    cast = events(args, "add") | events(args, "ollama_roster")        # the live rows, and the copy kept for the next start
    online = {guid for guid, person in people.items() if person[4]}
    print("%d bots in the roster, %d of them online now; %d benched (never picked to fill a place)." % (len(cast), len(cast & online), len(benched & set(people))))
    strangers = {guid for guid in online - cast if people[guid][0]}
    if strangers:
        print("Online but not in the roster: %d (a party bot, a fleet bot, or a player)." % len(strangers))
    if args.names:
        for guid in sorted(cast | benched, key=lambda guid: people.get(guid, ("", 0, 0, 0, False))[0]):
            name, race, klass, level, here = people.get(guid, ("(deleted)", 0, 0, 0, False))
            print("  %-24s %-10s %-16s %3d  %s%s" % (name, lore.RACE_IDS.get(race, "?"), lore.CLASS_IDS.get(klass, "class %d" % klass), level,
                                                   "online" if here else "", "  BENCHED" if guid in benched else ""))
    return 0


def find(args, wanted):
    people = characters(args)
    by_name = {person[0].lower(): guid for guid, person in people.items()}
    missing = [name for name in wanted if name.lower() not in by_name]
    if missing:
        raise SystemExit("ERROR no bot is called: %s" % ", ".join(missing))
    return [by_name[name.lower()] for name in wanted]


def change(args, benching):
    if rename_bots.world_is_running(args) and not args.force:
        print("ERROR The world port %s:%d answers: stop the worldserver first (or --force, and restart it right after)." % (args.world_host, args.world_port))
        return 1
    table = "`%s`.playerbots_random_bots" % args.playerbots_db
    guids = find(args, args.names_to_change)
    statements = ["START TRANSACTION"]
    for guid in guids:
        statements.append("DELETE FROM %s WHERE owner = 0 AND bot = %d AND event IN ('logout'%s)" % (table, guid, ", 'add', 'ollama_roster'" if benching else ""))
        if benching:
            statements.append("INSERT INTO %s (owner, bot, time, validIn, event, value) VALUES (0, %d, %d, %d, 'logout', 1)" % (table, guid, int(time.time()), YEAR_S))
    statements.append("COMMIT")
    rename_bots.mysql(args, "; ".join(statements))
    print("%s %d bots. Start the realm: %s" % ("Benched" if benching else "Unbenched", len(guids),
                                               "their places are filled by other random bots." if benching else "they can be picked to fill a place again."))
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--defaults-file", required=True, help="a mysql client config (user, password, host, port)")
    parser.add_argument("--characters-db", required=True)
    parser.add_argument("--playerbots-db", required=True)
    parser.add_argument("--force", action="store_true", help="change the roster even though the world port answers (the realm keeps its own copy; restart it right after)")
    parser.add_argument("--world-host", default="127.0.0.1")
    parser.add_argument("--world-port", type=int, default=8085)
    sub = parser.add_subparsers(dest="command", required=True)
    listing = sub.add_parser("list")
    listing.add_argument("--names", action="store_true", help="list every bot in the roster and every benched one")
    for name in ("bench", "unbench"):
        sub.add_parser(name).add_argument("names_to_change", metavar="NAME", nargs="+")
    args = parser.parse_args(argv)
    return show(args) if args.command == "list" else change(args, args.command == "bench")


if __name__ == "__main__":
    sys.exit(main())
