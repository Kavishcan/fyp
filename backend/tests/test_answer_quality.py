"""MCQ parsing for the answer-quality harness (docs/38)."""
from eval.run_answer_quality import mcq_text, parse_letter

OPTS = {"A": "yes", "B": "no", "C": "maybe"}


def test_parse_letter_accepts_common_forms():
    assert parse_letter("B", OPTS) == "B"
    assert parse_letter("B.", OPTS) == "B"
    assert parse_letter("(C)", OPTS) == "C"
    assert parse_letter("The answer is A.", OPTS) == "A"
    assert parse_letter("Answer: C", OPTS) == "C"


def test_parse_letter_rejects_abstentions_and_out_of_range_letters():
    assert parse_letter("The passages do not contain the answer.", OPTS) is None
    assert parse_letter("D", OPTS) is None


def test_mcq_text_lists_options_in_order():
    text = mcq_text({"question": "Q?", "options": {"B": "two", "A": "one"}, "answer": "A"})
    assert text.index("A. one") < text.index("B. two")
    assert "single option letter" in text
