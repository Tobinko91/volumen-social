"""Fehler 02.11.2026: Claude-Antworten als JSON verlaesslich lesen (Code-Zaun, Text drumherum, Abbruch)."""
import unittest

from social import claude

CFG = {"text": {"modell": "m"}}


class A:
    def __init__(self, j):
        self.j = j

    def raise_for_status(self):
        pass

    def json(self):
        return self.j


class ClaudeTest(unittest.TestCase):
    def test_code_zaun_und_text(self):
        self.assertEqual(claude.json_aus_text('```json\n{"a": 1}\n```'), {"a": 1})
        self.assertEqual(claude.json_aus_text('Here you go: {"a": {"b": "}"}} trailing } text'), {"a": {"b": "}"}})

    def test_abbruch_dann_doppeltes_budget(self):
        budgets = []

        def post(url, headers=None, json=None, timeout=None):
            budgets.append(json["max_tokens"])
            if len(budgets) == 1:
                return A({"content": [{"type": "text", "text": '{"kommentare": [{"id": "1", "te'}],
                          "stop_reason": "max_tokens"})
            return A({"content": [{"type": "thinking", "thinking": "{x"}, {"type": "text", "text": '{"ok": true}'}],
                      "stop_reason": "end_turn"})
        self.assertEqual(claude.json_antwort("s", "i", CFG, "k", 1000, post=post), {"ok": True})
        self.assertEqual(budgets, [1000, 2000])

    def test_fehler_nennt_grund(self):
        post = lambda *a, **k: A({"content": [{"type": "text", "text": "Sorry, no."}], "stop_reason": "end_turn"})
        with self.assertRaises(claude.ClaudeFehler) as e:
            claude.json_antwort("s", "i", CFG, "k", post=post)
        self.assertIn("stop_reason=end_turn", str(e.exception))


if __name__ == "__main__":
    unittest.main()
