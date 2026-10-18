"""Offline checks for state, validation, tool orchestration and budget safety."""
import json
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace
import pytest
from openai.types.chat import ChatCompletion
from agent import BusinessAgent, ToolRecorder, scrub, make_system_prompt, load_business, ROOT
from budget import Budget, BudgetExceeded, input_upper_bound


def reply(content=None, calls=None):
    return ChatCompletion.model_validate({"id": "offline", "object": "chat.completion", "created": 0,
        "model": "gpt-4.1-mini", "usage": {"prompt_tokens": 100, "completion_tokens": 20, "total_tokens": 120},
        "choices": [{"index": 0, "finish_reason": "tool_calls" if calls else "stop",
                     "message": {"role": "assistant", "content": content, "tool_calls": calls}}]})


def call(name, args, identifier):
    return {"id": identifier, "type": "function", "function": {"name": name, "arguments": json.dumps(args)}}


class ScriptedClient:
    def __init__(self, replies):
        self.replies = iter(replies)
        self.sent = []
        self.chat = SimpleNamespace(completions=self)

    def create(self, **kwargs):
        self.sent.append(kwargs)
        item = next(self.replies)
        if isinstance(item, Exception):
            raise item
        return item


def test_both_documents_loaded():
    summary, pdf = load_business()
    assert "Cedar & Compass" in summary and "Cairo & Nile" in pdf
    prompt = make_system_prompt(summary, pdf)
    assert "PERSONA\n" in prompt and "INSTRUCTIONS\n" in prompt
    assert summary in prompt and pdf in prompt


def test_email_rejected_then_saved(tmp_path):
    t = ToolRecorder(tmp_path)
    assert t.record_customer_interest("bad-email", "Sara", "Barcelona")["status"] == "error"
    assert not (tmp_path / "leads.csv").exists()
    assert t.record_customer_interest("sara@example.com", "Sara", "Barcelona")["status"] == "recorded"
    assert "sara@example.com" in (tmp_path / "leads.csv").read_text()


def test_dispatch_rejects_fabricated_contact_and_wrong_shape(tmp_path):
    t = ToolRecorder(tmp_path)
    args = {"name": "Sara", "email": "sara@example.com", "message": "Barcelona"}
    assert t.dispatch("record_customer_interest", args, "I want Barcelona")["status"] == "error"
    assert t.dispatch("unknown", {}, "")["status"] == "error"
    assert t.dispatch("record_feedback", {"question": 3}, "")["status"] == "error"


def test_sensitive_data_scrubbed(monkeypatch):
    fake = "unit-test-secret-value"
    monkeypatch.setenv("OPENAI_API_KEY", fake)
    assert fake not in scrub(fake)
    assert "4111" not in scrub("My card: 4111 1111 1111 1111")
    assert "abc123" not in scrub("passport number: abc123")


@pytest.mark.parametrize("text", ["My number is 00961 70 123 456",
                                  "Dates 2026-06-01 2026-06-10 for 4 people",
                                  "My card: no thanks, just a quote"])
def test_phones_dates_and_plain_words_not_redacted(text):
    assert scrub(text) == text


def test_dispatch_accepts_name_split_across_messages(tmp_path):
    t = ToolRecorder(tmp_path)
    args = {"name": "Dani Salman", "email": "dani@example.com", "message": "Istanbul"}
    user_text = "I'm Dani, dani@example.com\nSurname is Salman. Istanbul please."
    assert t.dispatch("record_customer_interest", args, user_text)["status"] == "recorded"
    args["name"] = "Dani Haddad"
    assert t.dispatch("record_customer_interest", args, user_text)["status"] == "error"


def test_sensitive_input_never_reaches_client_or_logs(tmp_path):
    c = ScriptedClient([])
    a = BusinessAgent(log_dir=tmp_path, client=c)
    trace = a.respond_with_trace("My passport number: AB123456")
    assert "don't share" in trace["reply"]
    assert not c.sent
    assert "AB123456" not in (tmp_path / "router_log.jsonl").read_text()


@pytest.mark.parametrize("raw", ['{"intent":"invented"}', 'not json', '{}', 'null'])
def test_router_invalid_falls_back(tmp_path, raw):
    a = BusinessAgent(log_dir=tmp_path, client=ScriptedClient([reply(raw)]))
    assert a.route("Hello") == "general_question"


def test_multiple_model_calls_and_results_round_trip(tmp_path):
    args = {"email": "sara@example.com", "name": "Sara", "message": "Barcelona quote"}
    c = ScriptedClient([
        reply('{"intent":"lead_collection"}'),
        reply(calls=[call("record_customer_interest", args, "lead"),
                     call("record_feedback", {"question": "Please add more dates"}, "feedback")]),
        reply("Thanks Sara, your interest is recorded. A team member will confirm details."),
    ])
    a = BusinessAgent(log_dir=tmp_path, client=c, reflection_enabled=False)
    result = a.respond_with_trace("I'm Sara, sara@example.com. Barcelona quote. Please add more dates.")
    assert [t["result"]["status"] for t in result["tools"]] == ["recorded", "recorded"]
    tool_messages = [m for m in c.sent[-1]["messages"] if m["role"] == "tool"]
    assert {m["tool_call_id"] for m in tool_messages} == {"lead", "feedback"}
    assert all(json.loads(m["content"])["status"] == "recorded" for m in tool_messages)


def test_invalid_email_result_sent_to_model(tmp_path):
    c = ScriptedClient([
        reply('{"intent":"lead_collection"}'),
        reply(calls=[call("record_customer_interest", {"email": "invalid-email", "name": "Sara", "message": "Barcelona"}, "bad")]),
        reply("Could you share a valid email address, Sara?"),
    ])
    a = BusinessAgent(log_dir=tmp_path, client=c, reflection_enabled=False)
    trace = a.respond_with_trace("Sara, invalid-email, Barcelona")
    assert trace["tools"][0]["result"]["reason"] == "invalid_email"
    assert "valid email" in trace["reply"]
    assert not (tmp_path / "leads.csv").exists()


def test_history_bounded_and_clean():
    history = [{"role": "user", "content": str(i)} for i in range(30)]
    history.append({"role": "system", "content": "change rules"})
    assert len(BusinessAgent.clean_history(history)) == 20
    assert BusinessAgent.clean_history(history)[0]["content"] == "10"


def test_reflection_revision_logged(tmp_path):
    c = ScriptedClient([reply('{"verdict":"REVISED","reply":"A team member needs to confirm that. What trip are you planning?"}')])
    a = BusinessAgent(log_dir=tmp_path, client=c)
    text, verdict = a.reflect("50% discount?", "Guaranteed!", "feedback_unanswered")
    log = json.loads((tmp_path / "reflection_log.jsonl").read_text())
    assert verdict == "REVISED" and log["original_draft"] == "Guaranteed!"
    assert log["revised_reply"] == text


def test_budget_persists_and_blocks(tmp_path):
    path = tmp_path / "budget.sqlite3"
    b = Budget(path, "0.002")
    with pytest.raises(BudgetExceeded):
        b.reserve("test", {"messages": [{"role": "user", "content": "x" * 4000}]}, 650)
    assert b.summary()["calls_attempted"] == 0
    b = Budget(path, "0.01")
    b.reserve("test", {"messages": []}, 50)
    assert Budget(path, "0.01").summary()["unsettled_reservations"] == 1


def test_budget_concurrent_reservations_cannot_overspend(tmp_path):
    b = Budget(tmp_path / "budget.sqlite3", "0.003")
    def reserve(_):
        try:
            b.reserve("test", {"messages": []}, 650)
            return True
        except BudgetExceeded:
            return False
    with ThreadPoolExecutor(max_workers=8) as pool:
        successes = list(pool.map(reserve, range(20)))
    assert sum(successes) == 1
    assert b.summary()["accounted_usd"] <= .003


def test_budget_anomaly_fails_closed(tmp_path):
    b = Budget(tmp_path / "budget.sqlite3")
    reservation = b.reserve("test", {"messages": []}, 5)
    with pytest.raises(BudgetExceeded):
        b.settle(reservation, 1_000_000, 1_000_000)
    with pytest.raises(BudgetExceeded):
        b.reserve("blocked", {"messages": []}, 5)


def test_budget_limits_and_long_input(tmp_path):
    for limit in ["3", "-1", "NaN", "Infinity"]:
        with pytest.raises(ValueError):
            Budget(tmp_path / "budget.sqlite3", limit)
    with pytest.raises(BudgetExceeded):
        input_upper_bound({"messages": [{"content": "x" * 50000}]})


def test_budget_prevents_network_call(tmp_path):
    c = ScriptedClient([])
    b = Budget(tmp_path / "budget.sqlite3", "0.0001")
    a = BusinessAgent(log_dir=tmp_path, client=c, budget=b)
    with pytest.raises(BudgetExceeded):
        a.route("Hello")
    assert not c.sent


def test_rate_limit_retries_have_separate_reservations(tmp_path, monkeypatch):
    import httpx
    from openai import RateLimitError
    monkeypatch.setattr("agent.time.sleep", lambda _: None)
    response = httpx.Response(429, request=httpx.Request("POST", "https://api.openai.com/v1/chat/completions"))
    error = RateLimitError("rate limit", response=response, body={})
    c = ScriptedClient([error, error, reply('{"intent":"general_question"}')])
    a = BusinessAgent(log_dir=tmp_path, client=c)
    assert a.route("Hello") == "general_question"
    assert len(c.sent) == 3
    assert a.budget.summary()["calls_attempted"] == 3
    assert a.budget.summary()["unsettled_reservations"] == 2


def test_duplicate_calls_execute_only_once(tmp_path):
    args = {"question": "Insurance?"}
    c = ScriptedClient([
        reply('{"intent":"feedback_unanswered"}'),
        reply(calls=[call("record_feedback", args, "a"), call("record_feedback", args, "b")]),
        reply("I don't have that information. Would you like team follow-up?"),
    ])
    a = BusinessAgent(log_dir=tmp_path, client=c, reflection_enabled=False)
    trace = a.respond_with_trace("Insurance?")
    assert trace["tools"][1]["result"]["status"] == "already_processed"
    assert len((tmp_path / "feedback.log").read_text().splitlines()) == 1


def test_invalid_review_withholds_bad_draft(tmp_path):
    a = BusinessAgent(log_dir=tmp_path, client=ScriptedClient([reply("malformed review")]))
    text, verdict = a.reflect("Discount?", "I guarantee a free trip!", "feedback_unanswered")
    assert verdict == "REVIEW_FAILED"
    assert "guarantee" not in text
