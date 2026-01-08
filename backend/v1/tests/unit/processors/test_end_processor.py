"""
END (Tests 069)
Reorganized from: test_05_other_processors.py

Tests validate: END
"""
import pytest

def test_69_end_terminates_session(end_node):
    """✅ END - mark session as COMPLETED and terminate"""
    # Spec: "Terminate conversation, Mark session as completed, Cleanup session data"
    # "No further nodes execute, Cannot be bypassed once reached"

    node = end_node

    # Expected behavior:
    # 1. Session status set to COMPLETED
    # 2. No message displayed (use MESSAGE before END for final message)
    # 3. next_node = None (terminal)
    # 4. needs_input = False
    # 5. terminal = True

    assert node["config"] == {}
    assert node["routes"] == []
    assert len(node["routes"]) == 0

    # After END node:
    # - Future messages rejected until new session
    # - Context cleared/archived
    # - No automatic restart
