"""Tests for context truncation in ChatSession."""

from sloth_agent.chat.session import ChatSession


class TestContextTruncation:
    def test_empty_session(self):
        s = ChatSession()
        msgs = s.get_messages_for_llm(max_turns=20)
        assert msgs == []

    def test_only_system_prompt(self):
        s = ChatSession()
        s.add_message("system", "You are helpful")
        msgs = s.get_messages_for_llm(max_turns=5)
        assert len(msgs) == 1
        assert msgs[0]["content"] == "You are helpful"

    def test_preserves_system_prompt(self):
        s = ChatSession()
        s.add_message("system", "System prompt")
        for i in range(50):
            s.add_message("user", f"Q{i}")
            s.add_message("assistant", f"A{i}")

        msgs = s.get_messages_for_llm(max_turns=5)
        assert msgs[0]["role"] == "system"
        assert msgs[0]["content"] == "System prompt"

    def test_truncates_to_max_turns(self):
        s = ChatSession()
        s.add_message("system", "System")
        # 20 turns = 40 messages
        for i in range(25):
            s.add_message("user", f"Q{i}")
            s.add_message("assistant", f"A{i}")

        msgs = s.get_messages_for_llm(max_turns=10)
        # 1 system + 20 messages (10 turns)
        assert len(msgs) == 21
        # Should be the last 10 turns
        assert msgs[-2]["content"] == "Q24"
        assert msgs[-1]["content"] == "A24"

    def test_odd_number_of_messages_handled(self):
        s = ChatSession()
        s.add_message("system", "System")
        s.add_message("user", "Q1")
        s.add_message("assistant", "A1")
        s.add_message("user", "Q2")  # Extra

        msgs = s.get_messages_for_llm(max_turns=5)
        assert len(msgs) == 4  # 1 system + 3 recent
