import unittest
import time

from src.utils.automod_helpers import (
    extract_urls,
    count_mentions,
    match_banned_words,
    is_spam,
    SpamTracker,
)


class TestAutoModHelpers(unittest.TestCase):
    def test_extract_urls(self) -> None:
        text = "Check https://example.com and discord.gg/invite"
        urls = extract_urls(text)
        self.assertEqual(len(urls), 2)

    def test_extract_urls_none(self) -> None:
        self.assertEqual(extract_urls("no links here"), [])

    def test_count_mentions(self) -> None:
        text = "Hey <@1234567890> and <@!9876543210>"
        self.assertEqual(count_mentions(text), 2)

    def test_count_mentions_none(self) -> None:
        self.assertEqual(count_mentions("no mentions"), 0)

    def test_match_banned_words(self) -> None:
        banned = ["spam", "scam"]
        self.assertEqual(match_banned_words("this is spam", banned), ["spam"])
        self.assertEqual(match_banned_words("clean text", banned), [])

    def test_match_banned_words_partial(self) -> None:
        banned = ["spam"]
        self.assertEqual(match_banned_words("spammer", banned), [])

    def test_is_spam_true(self) -> None:
        now = time.monotonic()
        messages = [(now - 4, "a"), (now - 3, "b"), (now - 2, "c"), (now - 1, "d"), (now, "e")]
        self.assertTrue(is_spam(messages, threshold=5, window_seconds=5.0))

    def test_is_spam_false(self) -> None:
        now = time.monotonic()
        messages = [(now - 10, "a"), (now - 9, "b"), (now - 8, "c")]
        self.assertFalse(is_spam(messages, threshold=5, window_seconds=5.0))

    def test_spam_tracker(self) -> None:
        tracker = SpamTracker()
        for i in range(5):
            tracker.record(1, f"msg{i}")
        is_spam_flag, recent = tracker.check(1, threshold=5, window_seconds=5.0)
        self.assertTrue(is_spam_flag)
        self.assertEqual(len(recent), 5)

    def test_spam_tracker_cleanup(self) -> None:
        tracker = SpamTracker()
        old = time.monotonic() - 120
        tracker._user_messages[1] = [(old, "old")]
        tracker.record(1, "new")
        self.assertEqual(len(tracker._user_messages[1]), 1)
        self.assertEqual(tracker._user_messages[1][0][1], "new")


class TestIsSpamEdgeCases(unittest.TestCase):
    def test_empty_messages(self) -> None:
        self.assertFalse(is_spam([], threshold=5, window_seconds=5.0))

    def test_exact_threshold(self) -> None:
        now = time.monotonic()
        messages = [(now, "a"), (now, "b"), (now, "c")]
        self.assertTrue(is_spam(messages, threshold=3, window_seconds=0.0))


if __name__ == "__main__":
    unittest.main()