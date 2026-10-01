import os
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))
import roster  # noqa: E402
import rename_bots  # noqa: E402

# guid, name, race id, class id, level, online
PEOPLE = [["1", "Walenno Wyndsong", "4", "3", "20", "1"], ["2", "Edimin Ironbeard", "3", "1", "30", "1"],
          ["3", "Ann", "1", "8", "70", "1"], ["4", "Gorgrim Skullcleaver", "2", "1", "12", "0"]]


def fake_mysql(statements, roster_guids=("1", "2"), benched=(), remembered=()):
    def run(args, sql, write=False):
        statements.append(sql)
        if "event = 'add'" in sql:
            return [[guid] for guid in roster_guids]
        if "event = 'ollama_roster'" in sql:
            return [[guid] for guid in remembered]
        if "event = 'logout'" in sql:
            return [[guid] for guid in benched]
        if "FROM `chars`.characters" in sql:
            return [list(row) for row in PEOPLE]
        return []
    return run


class RosterTests(unittest.TestCase):
    def run_tool(self, *words, **mysql_options):
        statements = []
        argv = ["--defaults-file", "x.cnf", "--characters-db", "chars", "--playerbots-db", "pb", "--world-port", "1"] + list(words)
        with mock.patch.object(rename_bots, "mysql", fake_mysql(statements, **mysql_options)):
            return roster.main(argv), statements

    def test_list_counts_the_cast_and_names_a_stranger_online(self):
        with mock.patch("builtins.print") as shown:
            code, _ = self.run_tool("list", "--names")
        text = "\n".join(str(call.args[0]) for call in shown.call_args_list if call.args)
        self.assertEqual(code, 0)
        self.assertIn("2 bots in the roster, 2 of them online now", text)
        self.assertIn("Online but not in the roster: 1", text)      # Ann, a player
        self.assertIn("Walenno Wyndsong", text)
        self.assertNotIn("Gorgrim", text)                                    # not in the roster and not benched

    def test_list_counts_a_bot_that_is_only_remembered_for_the_next_start(self):
        # A stopped realm has live rows from its last run and the copy; a bot in either is in the roster.
        with mock.patch("builtins.print") as shown:
            self.run_tool("list", roster_guids=("1",), remembered=("1", "2"))
        self.assertIn("2 bots in the roster", str(shown.call_args_list[0].args[0]))

    def test_benching_takes_the_bot_out_of_the_cast_and_marks_it(self):
        code, statements = self.run_tool("--force", "bench", "walenno wyndsong")
        written = " ".join(statements)
        self.assertEqual(code, 0)
        self.assertIn("DELETE FROM `pb`.playerbots_random_bots WHERE owner = 0 AND bot = 1 AND event IN ('logout', 'add', 'ollama_roster')", written)
        self.assertIn("INSERT INTO `pb`.playerbots_random_bots (owner, bot, time, validIn, event, value) VALUES (0, 1,", written)
        self.assertIn("'logout', 1)", written)

    def test_unbenching_only_removes_the_mark(self):
        code, statements = self.run_tool("--force", "unbench", "Walenno Wyndsong")
        written = " ".join(statements)
        self.assertEqual(code, 0)
        self.assertIn("event IN ('logout')", written)
        self.assertNotIn("INSERT", written)

    def test_it_refuses_to_change_the_cast_under_a_running_realm(self):
        with mock.patch.object(rename_bots, "world_is_running", return_value=True):
            code, statements = self.run_tool("bench", "Walenno Wyndsong")
        self.assertEqual(code, 1)
        self.assertFalse([sql for sql in statements if "DELETE" in sql or "INSERT" in sql])

    def test_an_unknown_name_changes_nothing(self):
        with self.assertRaises(SystemExit):
            self.run_tool("--force", "bench", "Nobody Atall")


if __name__ == "__main__":
    unittest.main()
