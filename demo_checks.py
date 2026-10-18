"""Small, repeatable LIVE demo suite. All contacts here are simulated.

Run directly with: python demo_checks.py (requires OPENAI_API_KEY).
The notebook calls the same functions and saves their real outputs.
"""
import json
from pathlib import Path
from agent import BusinessAgent

ROUTER_CASES = [
    ("What's included in the Istanbul package?", "general_question"),
    ("Do you offer student discounts?", "general_question"),
    ("What are your office hours?", "general_question"),
    ("I want a quote for 4 people to Barcelona in June", "lead_collection"),
    ("Can you plan my honeymoon? I'm Sara, sara@example.com", "lead_collection"),
    ("I'd like to book the Athens and Santorini trip", "lead_collection"),
    ("Do you sell travel insurance?", "feedback_unanswered"),
    ("Your last reply was confusing, please improve", "feedback_unanswered"),
    ("What's the price of a Tokyo package?", "feedback_unanswered"),
]


def router_demo(agent):
    rows = []
    for message, expected in ROUTER_CASES:
        predicted = agent.route(message)
        rows.append({"message": message, "predicted_intent": predicted,
                     "expected_intent": expected, "pass": predicted == expected})
    return rows


def conversation_demo(agent):
    results = []
    lead_history = []
    cases = [
        ("persona_and_grounding", "Hi Layla, what's included in the Istanbul package?", []),
        ("lead_missing_contact", "I want a quote for 4 people to Barcelona in June", lead_history),
        ("lead_complete", "I'm Sara. My email is sara@example.com. Please save my request for 4 people to Barcelona in June.", lead_history),
        ("unknown_question", "Do you sell travel insurance?", []),
        ("complaint", "Your last reply was confusing, please improve.", []),
        ("both_tools", "I'm Omar, omar@example.com. Please record my interest in the Istanbul trip. Also log my suggestion: please add more student departure dates.", []),
        ("unlisted_discount", "Can you guarantee me a 50% discount on Barcelona?", []),
    ]
    for name, message, history in cases:
        trace = agent.respond_with_trace(message, history)
        results.append({"case": name, "message": message, **trace})
        if name == "lead_missing_contact":
            lead_history.extend([{"role": "user", "content": message},
                                 {"role": "assistant", "content": trace["reply"]}])
        print(f"\n{name} | {trace['intent']} | reflection: {trace['reflection']}\n{trace['reply']}")
    return results


def reflection_demo(agent):
    # Intentional fault injection, clearly separated from natural agent outputs.
    # This makes the bonus reproducible even when ordinary drafts are already OK.
    user = "Can you guarantee a 50% discount on the Barcelona package?"
    faulty = "Absolutely! I guarantee a 50% discount on Barcelona, and your booking is confirmed. Please send your credit card number."
    revised, verdict = agent.reflect(user, faulty, "feedback_unanswered", [])
    return {"source": "controlled faulty-draft injection; revision is a real API response",
            "user_message": user, "original_draft": faulty,
            "verdict": verdict, "revised_reply": revised,
            "changed": revised != faulty}


def acceptance(router_rows, conversations, reflection):
    traces = {r["case"]: r for r in conversations}
    def called(case, tool):
        return any(t["name"] == tool and t["result"]["status"] == "recorded"
                   for t in traces[case]["tools"])
    checks = {
        "router_all_correct": all(r["pass"] for r in router_rows),
        "lead_tool_called_by_model": called("lead_complete", "record_customer_interest"),
        "unknown_feedback_called_by_model": called("unknown_question", "record_feedback"),
        "unknown_service_not_falsely_denied": not any(phrase in traces["unknown_question"]["reply"].lower()
            for phrase in ("don't sell", "do not sell", "does not sell", "don't offer", "do not offer")),
        "complaint_logged": called("complaint", "record_feedback"),
        "both_tools_in_one_turn": called("both_tools", "record_customer_interest") and called("both_tools", "record_feedback"),
        "missing_email_requested": "email" in traces["lead_missing_contact"]["reply"].lower(),
        "real_reflection_revision": reflection["changed"] and reflection["verdict"] == "REVISED",
    }
    return checks


if __name__ == "__main__":
    agent = BusinessAgent()
    rows = router_demo(agent)
    conversations = conversation_demo(agent)
    reflection = reflection_demo(agent)
    report = {"router": rows, "conversations": conversations, "reflection": reflection,
              "checks": acceptance(rows, conversations, reflection), "budget": agent.budget.summary()}
    path = Path(__file__).resolve().parent / "evidence/live_results.json"
    path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report["checks"], indent=2))
    print(json.dumps(report["budget"], indent=2))
