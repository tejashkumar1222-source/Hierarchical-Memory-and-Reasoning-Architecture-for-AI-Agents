from backend.app.memory.write_policy import assess_durability, build_memory_content

def test_rejects_rate_limit_error():
    ok, reason = assess_durability("Recall our discussion about project milestones", "I was unable to retrieve the prior discussion because of a rate-limit error.")
    assert not ok
    assert reason == "transient_or_error_output"

def test_rejects_calculation():
    ok, reason = assess_durability("Calculate (45 * 12) + (180 / 4)", "45 * 12 = 540 and 180 / 4 = 45, so the result is 585.")
    assert not ok
    assert reason == "transient_query"

def test_rejects_unresolved_uncertainty():
    ok, reason = assess_durability("What is the approved database engine?", "I cannot determine the approved database engine because there is insufficient evidence.")
    assert not ok
    assert reason == "unresolved_uncertainty"

def test_accepts_durable_project_knowledge():
    ok, reason = assess_durability("Remember the project architecture", "The project uses three memory scopes: Global, Team, and Private, with scope-aware access control.")
    assert ok
    assert reason == "durable_intent"

def test_memory_content_is_compact():
    text = build_memory_content("Remember the project architecture", "The project uses three memory scopes.")
    assert text.startswith("Topic:")
    assert "Durable knowledge:" in text
