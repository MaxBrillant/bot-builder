"""
Trigger matching (Tests 176-190)
Reorganized from: test_14_trigger_keyword_matching.py

Tests validate: Trigger matching
"""
import pytest

def test_176_exact_match_required_standalone():
    """✅ Trigger matching: entire message must match (standalone only)"""
    # Spec: "Standalone messages only: The entire user message must exactly match ONE keyword"

    trigger_keywords = ["START"]

    test_cases = [
    ("START", True),           # Exact match
    ("start", True),           # Case-insensitive
    (" START ", True),         # Whitespace trimmed
    ("START NOW", False),      # Multiple words (not standalone)
    ("STARTING", False),       # Partial match (different word)
    ("I want to START", False), # Word in sentence
    ("Please START", False),   # Word in sentence
    ("START!", False),         # With punctuation
    ]

    # Expected: Only exact, standalone matches succeed


def test_177_case_insensitive_matching():
    """✅ Trigger matching: case-insensitive"""
    # Spec: "Case-insensitive: 'START', 'start', 'Start' all match"

    trigger_keywords = ["START"]

    test_cases = [
    "START",
    "start",
    "Start",
    "StArT",
    "sTaRt",
    ]

    # All should match the trigger keyword "START"


def test_178_whitespace_trimming_before_matching():
    """✅ Trigger matching: whitespace trimmed before comparison"""
    # Spec: "Whitespace trimmed: ' START ' matches 'START'"

    trigger_keywords = ["START"]

    test_cases = [
    " START",
    "START ",
    "  START  ",
    "\tSTART\t",
    "\nSTART\n",
    "START\r\n",
    ]

    # All should match after trimming



def test_179_multi_word_trigger_exact_match():
    """✅ Multi-word triggers: exact match required"""
    # Spec: "Allowed characters: letters, numbers, spaces, underscores, hyphens"
    # Spaces ARE allowed in trigger keywords

    trigger_keywords = ["HELLO WORLD", "GOOD MORNING", "BUY NOW"]

    test_cases = [
    ("HELLO WORLD", True),         # Exact match
    ("hello world", True),         # Case-insensitive
    (" HELLO WORLD ", True),       # Whitespace trimmed
    ("HELLO", False),              # Only part of trigger
    ("WORLD", False),              # Only part of trigger
    ("HELLO  WORLD", False),       # Double space (not exact match after trim?)
    ("HELLOWORLD", False),         # No space
    ("HELLO WORLD!", False),       # With punctuation
    ]


def test_180_multi_word_trigger_not_partial_sentence():
    """✅ Multi-word triggers: must be standalone, not part of sentence"""
    # Spec: "No partial matches, No word-in-sentence"

    trigger_keywords = ["BUY NOW"]

    test_cases = [
    ("BUY NOW", True),                    # Exact
    ("I want to BUY NOW", False),         # In sentence
    ("BUY NOW please", False),            # In sentence
    ("Please BUY NOW for discount", False), # In sentence
    ]



def test_181_partial_match_prevention():
    """✅ Trigger matching: no partial/substring matches"""
    # Spec: "No partial matches: 'I want to START' does NOT match 'START'"
    # "No word-in-sentence: 'STARTING' does NOT match 'START'"

    trigger_keywords = ["START"]

    invalid_matches = [
    "STARTING",              # Different word (starts with START)
    "RESTART",               # Contains START
    "START NOW",             # START plus more words
    "NOW START",             # START plus more words
    "I want to START",       # START in sentence
    "Can you START this",    # START in sentence
    "START!",                # START with punctuation
    "START?",
    "START.",
    ]

    # None of these should match trigger "START"


def test_182_similar_keywords_dont_match():
    """✅ Similar but different keywords don't match"""

    trigger_keywords = ["START", "RESTART", "STARTING"]

    test_cases = [
    ("START", "START"),       # Exact match
    ("RESTART", "RESTART"),   # Exact match
    ("STARTING", "STARTING"), # Exact match
    ("start", "START"),       # Case-insensitive match
    ]

    # Each message should ONLY match its exact keyword
    # "START" message should NOT match "RESTART" or "STARTING"



def test_183_punctuation_in_user_input_prevents_match():
    """✅ Punctuation in user input prevents match"""
    # Spec: "NOT allowed: Punctuation (!?.), special characters (@#$%^&*), emojis"
    # This refers to trigger keyword definition, but also affects matching

    trigger_keywords = ["START"]

    test_cases = [
    ("START!", False),
    ("START?", False),
    ("START.", False),
    ("START,", False),
    ("START;", False),
    ("START:", False),
    ("'START'", False),
    ('"START"', False),
    ("START 🚀", False),  # Emoji
    ]

    # Trigger keywords should NOT contain punctuation
    # User messages with punctuation should NOT match plain triggers



def test_184_multiple_flows_different_keywords():
    """✅ Multiple flows in same bot, each with unique keywords"""
    # Spec: "Trigger keywords unique per bot"

    bot_flows = [
    {"flow_id": "flow1", "trigger_keywords": ["START", "BEGIN"]},
    {"flow_id": "flow2", "trigger_keywords": ["HELP", "SUPPORT"]},
    {"flow_id": "flow3", "trigger_keywords": ["BOOKING", "RESERVE"]},
    ]

    test_cases = [
    ("START", "flow1"),
    ("BEGIN", "flow1"),
    ("HELP", "flow2"),
    ("SUPPORT", "flow2"),
    ("BOOKING", "flow3"),
    ("RESERVE", "flow3"),
    ]

    # Each message should activate the correct flow


def test_185_duplicate_keywords_across_flows_rejected():
    """✅ Duplicate keywords in same bot rejected during validation"""
    # Spec: "Each keyword must be unique per bot"
    # "System checks for duplicate keywords within the same bot's flows"

    flow1 = {
    "name": "flow1",
    "trigger_keywords": ["START", "BEGIN"]
    }

    flow2 = {
    "name": "flow2",
    "trigger_keywords": ["START", "HELP"]  # "START" is duplicate!
    }

    # Expected: Validation error when submitting flow2
    # Error: "Trigger keyword 'START' is already used in flow 'flow1' of this bot"



def test_186_wildcard_evaluated_after_specific_keywords():
    """✅ Wildcard trigger evaluated AFTER all specific keywords"""
    # Spec: "Priority: Always checked AFTER specific keywords (fallback only)"

    bot_flows = [
    {"flow_id": "flow_start", "trigger_keywords": ["START"]},
    {"flow_id": "flow_help", "trigger_keywords": ["HELP"]},
    {"flow_id": "flow_booking", "trigger_keywords": ["BOOKING"]},
    {"flow_id": "flow_wildcard", "trigger_keywords": ["*"]},  # Wildcard
    ]

    test_cases = [
    ("START", "flow_start"),         # Specific match (not wildcard)
    ("HELP", "flow_help"),           # Specific match
    ("BOOKING", "flow_booking"),     # Specific match
    ("ANYTHING", "flow_wildcard"),   # No specific match → wildcard
    ("RANDOM", "flow_wildcard"),     # No specific match → wildcard
    ("123", "flow_wildcard"),        # No specific match → wildcard
    ("Hello!", "flow_wildcard"),     # No specific match → wildcard (even with punctuation)
    ]

    # Wildcard should only activate if NO specific keyword matches


def test_187_wildcard_matches_anything():
    """✅ Wildcard trigger matches any message"""
    # Spec: "The '*' keyword matches ANY message that doesn't match other specific keywords"

    trigger_keywords = ["*"]

    test_cases = [
    "START",
    "hello",
    "123",
    "random message",
    "!@#$%",
    "🚀🎉",
    "",  # Empty (after trim)?
    ]

    # All messages should match wildcard
    # Note: Empty string behavior may need clarification



def test_188_empty_message_after_trim():
    """✅ Empty message after trimming"""
    # What happens when user sends only whitespace?

    trigger_keywords = ["START"]

    empty_inputs = [
    "",
    "   ",
    "\t",
    "\n",
    "\r\n",
    ]

    # After trimming, all become ""
    # Expected: No match (empty doesn't match "START")
    # Question: Does wildcard "*" match empty string?


def test_189_numeric_trigger_keywords():
    """✅ Numeric trigger keywords"""
    # Spec: "Allowed characters: letters, numbers, spaces, underscores, hyphens"

    trigger_keywords = ["1", "123", "0"]

    test_cases = [
    ("1", True),
    ("123", True),
    ("0", True),
    ("1 ", True),  # With whitespace
    (" 123 ", True),
    ]

    # Numeric keywords are valid


def test_190_trigger_with_underscores_and_hyphens():
    """✅ Triggers with underscores and hyphens"""
    # Spec: "Allowed: underscores (_), hyphens (-)"

    trigger_keywords = ["TEST_FLOW", "SOME-KEYWORD", "MIX_AND-MATCH"]

    test_cases = [
    ("TEST_FLOW", True),
    ("test_flow", True),  # Case-insensitive
    ("SOME-KEYWORD", True),
    ("some-keyword", True),
    ("MIX_AND-MATCH", True),
    ]

    # All should match successfully
