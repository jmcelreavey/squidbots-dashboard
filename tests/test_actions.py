import json
import unittest

from tests.support import GatewayCase, chat, profile_fields


def tool_round(request, call_id, name, arguments, result):
    """The request the module sends for the next round of a tool loop: the model's call and the tool's answer."""
    request["messages"] += [
        {"role": "assistant", "content": None,
         "tool_calls": [{"id": call_id, "type": "function", "function": {"name": name, "arguments": json.dumps(arguments)}}]},
        {"role": "tool", "tool_call_id": call_id, "content": json.dumps(result)},
    ]
    return request


class ActionMemoryTests(GatewayCase):
    def test_a_follow_up_knows_which_item_the_bot_just_put_in_the_trade(self):
        first = tool_round(chat(20014, "Brick", 77, "Ann", "Sure"), "call_1", "economy",
                           {"action": "bot_trade_give", "params": {"botGuid": 20014, "playerGuid": 77, "item_id": 484325}},
                           {"ok": True, "item_id": 484325, "player_name": "Ann", "item_count": 1})
        self.gateway.handle("smart", first)
        self.gateway.handle("smart", chat(20014, "Brick", 77, "Ann", "I dont see the sword?"))
        system = self.system_text()
        self.assertIn("WHAT YOU JUST DID IN THE GAME", system)
        self.assertIn("bot_trade_give(item_id=484325)", system)
        self.assertIn('"ok":true', system.replace(" ", ""))
        self.assertNotIn("playerGuid=", system.split("WHAT YOU JUST DID")[1])   # ids the model is told anyway are left out

    def test_a_refusal_is_remembered_too(self):
        request = tool_round(chat(20014, "Brick", 77, "Ann", "trade me it"), "call_9", "economy",
                             {"action": "bot_trade_give", "params": {"item_id": 5}}, {"error": "not_in_party"})
        self.gateway.handle("smart", request)
        self.gateway.handle("smart", chat(20014, "Brick", 77, "Ann", "why not"))
        self.assertIn("not_in_party", self.system_text())

    def test_looking_things_up_or_asking_how_a_tool_works_is_not_remembered(self):
        request = tool_round(chat(20014, "Brick", 77, "Ann", "what do you carry"), "call_2", "core",
                             {"action": "get_inventory", "params": {}}, {"items": ["a", "b"]})
        request = tool_round(request, "call_3", "economy", {"describe": "bot_trade_give"}, {"description": "long"})
        self.gateway.handle("smart", request)
        self.gateway.handle("smart", chat(20014, "Brick", 77, "Ann", "and now?"))
        self.assertNotIn("WHAT YOU JUST DID", self.system_text())

    def test_each_call_is_kept_once_however_many_rounds_repeat_it(self):
        request = tool_round(chat(20014, "Brick", 77, "Ann", "go"), "call_4", "core",
                             {"action": "bot_follow", "params": {}}, {"ok": True})
        self.gateway.handle("smart", request)
        self.gateway.handle("smart", request)
        self.gateway.handle("smart", chat(20014, "Brick", 77, "Ann", "still there?"))
        self.assertEqual(self.system_text().count("bot_follow"), 1)

    def test_actions_belong_to_one_bot_and_one_player(self):
        request = tool_round(chat(20014, "Brick", 77, "Ann", "go"), "call_5", "core",
                             {"action": "bot_follow", "params": {}}, {"ok": True})
        self.gateway.handle("smart", request)
        self.gateway.handle("smart", chat(20014, "Brick", 88, "Bob", "hello"))
        self.assertNotIn("bot_follow", self.system_text())
        self.gateway.handle("smart", chat(20015, "Nym", 77, "Ann", "hello"))
        self.assertNotIn("bot_follow", self.system_text())

    def test_they_are_forgotten_after_half_an_hour(self):
        import time
        request = tool_round(chat(20014, "Brick", 77, "Ann", "go"), "call_6", "core",
                             {"action": "bot_follow", "params": {}}, {"ok": True})
        self.gateway.handle("smart", request)
        with self.gateway.lock:
            at, line, call_id = self.gateway.actions[(20014, 77)][0]
            self.gateway.actions[(20014, 77)][0] = (at - 31 * 60, line, call_id)
        self.gateway.handle("smart", chat(20014, "Brick", 77, "Ann", "hello"))
        self.assertNotIn("bot_follow", self.system_text())


if __name__ == "__main__":
    unittest.main()


class ToolRoundLimitTests(GatewayCase):
    def setUp(self):
        super().setUp()
        self.store.set_setting("plain_chat_no_tools", "0")      # these are about the round limit, not about plain chat

    def rounds(self, count):
        request = chat(20014, "Brick", 77, "Ann", "trade me your staff")
        request["tools"] = [{"type": "function", "function": {"name": "core", "parameters": {"type": "object"}}}]
        for number in range(count):
            request = tool_round(request, "call_%d" % number, "core", {"action": "get_inventory"}, {"items": []})
        return request

    def test_tools_are_withdrawn_after_the_limit_so_the_bot_must_answer(self):
        self.gateway.store.set_setting("max_tool_rounds", "4")
        self.gateway.handle("smart", self.rounds(4))
        self.assertNotIn("tools", self.provider.requests[-1]["body"])

    def test_tools_stay_until_the_limit_is_reached(self):
        self.gateway.store.set_setting("max_tool_rounds", "4")
        self.gateway.handle("smart", self.rounds(3))
        self.assertIn("tools", self.provider.requests[-1]["body"])

    def test_only_rounds_since_the_players_last_message_count(self):
        self.gateway.store.set_setting("max_tool_rounds", "2")
        request = self.rounds(3)
        request["messages"].append({"role": "assistant", "content": "done"})
        request["messages"].append({"role": "user", "content": "thanks, one more thing"})
        self.gateway.handle("smart", request)
        self.assertIn("tools", self.provider.requests[-1]["body"])


def call_answer(name, arguments):
    """What a model answers when it wants a tool run."""
    return {"id": "x", "choices": [{"index": 0, "finish_reason": "tool_calls", "message": {"role": "assistant", "content": None, "tool_calls": [
        {"id": "c2", "type": "function", "function": {"name": name, "arguments": json.dumps(arguments)}}]}}],
        "usage": {"prompt_tokens": 100, "completion_tokens": 10}}


class RepeatedCallTests(GatewayCase):
    """A small model answers a tool that worked by calling it again; the player should be told it worked, and the module should not run it twice."""

    def invited(self):
        request = tool_round(chat(20014, "Brick", 77, "Ann", "invite me please"), "c1", "social",
                             {"action": "bot_invite_to_group", "params": {"target_guid": "1114", "target_name": "Ann"}}, {"ok": True})
        request["tools"] = [{"type": "function", "function": {"name": "social", "parameters": {"type": "object"}}}]
        return request

    def test_the_same_call_again_becomes_words(self):
        # The second call names the target differently, as models do: it is still the same invite.
        self.provider.answers += [call_answer("social", {"action": "bot_invite_to_group", "params": {"name": "Ann", "target_guid": 1114}}), "Invite sent, come along."]
        status, answer = self.gateway.handle("smart", self.invited())
        self.assertEqual(status, 200)
        message = answer["choices"][0]["message"]
        self.assertEqual(message["content"], "Invite sent, come along.")
        self.assertFalse(message.get("tool_calls"))
        self.assertNotIn("tools", self.provider.requests[-1]["body"])
        self.assertEqual(self.gateway.repeated_calls, 1)

    def test_a_different_call_in_the_same_turn_is_let_through(self):
        self.provider.answers += [call_answer("social", {"action": "bot_invite_to_group", "params": {"target_guid": "2222", "target_name": "Bob"}})]
        status, answer = self.gateway.handle("smart", self.invited())
        self.assertEqual(status, 200)
        self.assertTrue(answer["choices"][0]["message"].get("tool_calls"))
        self.assertEqual(self.gateway.repeated_calls, 0)

    def test_the_first_call_of_a_turn_is_never_a_repeat(self):
        request = chat(20014, "Brick", 77, "Ann", "invite me please")
        request["tools"] = [{"type": "function", "function": {"name": "social", "parameters": {"type": "object"}}}]
        self.provider.answers += [call_answer("social", {"action": "bot_invite_to_group", "params": {"target_guid": "1114"}})]
        status, answer = self.gateway.handle("smart", request)
        self.assertTrue(answer["choices"][0]["message"].get("tool_calls"))
        self.assertEqual(self.gateway.repeated_calls, 0)

    def test_if_the_retry_says_nothing_the_first_answer_stands(self):
        self.provider.answers += [call_answer("social", {"action": "bot_invite_to_group", "params": {"target_guid": "1114", "target_name": "Ann"}}), ""]
        status, answer = self.gateway.handle("smart", self.invited())
        self.assertEqual(status, 200)
        self.assertTrue(answer["choices"][0]["message"].get("tool_calls"))


class PlainChatLaneTests(GatewayCase):
    """With plain_chat_on_ambient, a turn that offers no tools is written by the ambient lane's model."""

    def setUp(self):
        super().setUp()
        self.store.save_profile("small", dict(profile_fields(self.provider.url), model="small-model"))
        self.store.set_lane("ambient", "small")
        self.store.set_setting("plain_chat_on_ambient", "1")

    def sent_model(self, request):
        self.provider.answers.append("ok")
        self.gateway.handle("smart", request)
        return self.provider.requests[-1]["body"]["model"]

    def test_small_talk_goes_to_the_ambient_model(self):
        request = chat(20014, "Brick", 77, "Ann", "who are you?")
        request["tools"] = [{"type": "function", "function": {"name": "core", "parameters": {"type": "object"}}}]
        self.assertEqual(self.sent_model(request), "small-model")

    def test_a_turn_that_may_need_a_tool_stays_on_the_conversation_model(self):
        request = chat(20014, "Brick", 77, "Ann", "invite me please")
        request["tools"] = [{"type": "function", "function": {"name": "core", "parameters": {"type": "object"}}}]
        self.assertNotEqual(self.sent_model(request), "small-model")

    def test_it_is_off_unless_asked_for(self):
        self.store.set_setting("plain_chat_on_ambient", "0")
        request = chat(20014, "Brick", 77, "Ann", "who are you?")
        request["tools"] = [{"type": "function", "function": {"name": "core", "parameters": {"type": "object"}}}]
        self.assertNotEqual(self.sent_model(request), "small-model")


class PlainChatTests(GatewayCase):
    """A message that asks nothing of the bot is answered without the tools' schemas (most of the prompt)."""

    def ask(self, text, **more):
        request = chat(20014, "Brick", 77, "Ann", text)
        request["tools"] = [{"type": "function", "function": {"name": "core", "parameters": {"type": "object"}}}]
        request["tool_choice"] = "auto"
        request.update(more)
        self.provider.answers.append("ok")
        self.gateway.handle("smart", request)
        return self.provider.requests[-1]["body"]

    def test_conversation_is_answered_without_tools(self):
        sent = self.ask("tell me who you are, and how was the road?")
        self.assertNotIn("tools", sent)
        self.assertNotIn("tool_choice", sent)
        self.assertEqual(self.gateway.plain_chats, 1)

    def test_anything_that_could_be_a_request_keeps_the_tools(self):
        for text in ("invite me please", "can you follow me?", "what gear are you wearing", "go ahead of us", "how much gold do you have"):
            self.assertIn("tools", self.ask(text), text)

    def test_a_question_about_the_bots_own_things_or_a_follow_up_to_one_keeps_the_tools(self):
        # "whats your cape" and "can I have it?" were answered with a shrug and an acted-out hand-over because they matched no action word.
        for text in ("Aldric whats your cape", "Can I have it?", "what's in your pockets", "Can't you check?", "do you have any spare linen", "hold on"):
            self.assertIn("tools", self.ask(text), text)

    def test_only_small_talk_and_questions_about_the_person_go_without_them(self):
        for text in ("hello there", "how are you today?", "who are you?", "where do you hail from", "are you an AI?", "thanks, that helps",
                     "what do you think of the Horde?", "tell me about your home"):
            self.assertNotIn("tools", self.ask(text), text)

    def test_a_follow_up_to_something_the_bot_just_did_keeps_them(self):
        self.gateway._note_actions(tool_round(chat(20014, "Brick", 77, "Ann", "invite me"), "c1", "core", {"action": "invite"}, {"ok": True}),
                                   self.gateway_ident())
        self.assertIn("tools", self.ask("yes, that one"))

    def test_a_tick_with_no_player_and_the_middle_of_a_tool_round_keep_them(self):
        request = chat(20014, "Brick", 0, "", "x")
        request["messages"][0]["content"] = request["messages"][0]["content"].replace("- playerGuid = 0, name =   (the player talking to you)\n", "")
        request["tools"] = [{"type": "function", "function": {"name": "core"}}]
        self.provider.answers.append("ok")
        self.gateway.handle("smart", request)
        self.assertIn("tools", self.provider.requests[-1]["body"])
        round_one = tool_round(chat(20014, "Brick", 77, "Ann", "tell me about yourself"), "c1", "core", {"action": "get_state"}, {"hp": 100})
        round_one["tools"] = [{"type": "function", "function": {"name": "core"}}]
        self.provider.answers.append("ok")
        self.gateway.handle("smart", round_one)
        self.assertIn("tools", self.provider.requests[-1]["body"])

    def test_the_switch_turns_it_off(self):
        self.store.set_setting("plain_chat_no_tools", "0")
        self.assertIn("tools", self.ask("who are you?"))

    def gateway_ident(self):
        from mind import identity
        return identity.Identity(20014, "Brick", 77, "Ann")
