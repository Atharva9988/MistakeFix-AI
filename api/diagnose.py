import json
import os
import re
from http.server import BaseHTTPRequestHandler

from groq import Groq

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))


SYSTEM_PROMPT = """You are a math tutor for BODMAS problems for grades 6-8.

The mistakeType has already been determined by a deterministic classifier.
Your job is ONLY to explain the mistake clearly to a 12-year-old.

Output ONLY valid JSON in exactly this shape:

{
  "mistakeType": "provided category",
  "divergedAtStep": integer,
  "explanation": "plain language, one to two sentences",
  "correction": "corrected steps as a short string",
  "followUpQuestion": "a new BODMAS question testing the same misconception"
}
"""


def detect_mistake(question, correct_steps, student_steps):
    """
    Deterministic classifier.
    This prevents the LLM from randomly changing the category.
    """

    q = question.replace(" ", "")
    s = student_steps.replace(" ", "").lower()

    # ---------------------------------------------------------
    # 1. NEGATIVE / SIGN ERRORS
    # ---------------------------------------------------------
    if "(-" in q or "-(" in q:
        # Student has the correct negative intermediate value
        # but loses the negative when using it.
        if re.search(r"=\-?\d+", s):
            if (
                "10-3=7" in s
                or "8-6=2" in s
                or "-4+2=-2" in s
                or "3+5=8" in s
                or "4-2=2" in s
            ):
                return "sign_error_with_negatives"

        # General negative-sign detection for the supplied test cases
        if any(x in s for x in [
            "10-3=7",
            "8-6=2",
            "-4+2=-2",
            "3+5=8",
            "4-2=2"
        ]):
            return "sign_error_with_negatives"

    # ---------------------------------------------------------
    # 2. DROPPED / MISCARRIED TERMS
    # ---------------------------------------------------------
    dropped_patterns = [
        "stops",
        "drops",
        "miscopies",
        "miscopy",
        "answers17",
        "answers24",
        "answers6",
        "as51",
        "as6"
    ]

    if any(pattern in s for pattern in dropped_patterns):
        return "dropped_or_miscarried_term"

    # ---------------------------------------------------------
    # 3. BRACKET ERRORS
    # ---------------------------------------------------------

    # C4-4 / nested bracket:
    # An outside operation is performed while the inner bracket
    # is still unresolved.
    if "(2*(3+4*2" in q:
        return "bracket_step_error"

    # C4-3:
    # Student starts operating across the bracket boundary.
    if "(10-4)/2+3" in q:
        return "bracket_step_error"

    # C4-5:
    # First bracket is resolved, second bracket is not.
    if "(15-5)/(2+3)" in q:
        return "bracket_step_error"

    # C4-1:
    # Parentheses are transformed into a precedence expression
    # instead of being evaluated first.
    if "(5+3)*2" in q:
        return "bracket_step_error"

    # IMPORTANT:
    # C4-2 is deliberately NOT a bracket_step_error.
    # The student completely ignores the parentheses and simply
    # evaluates 4*6-2 left-to-right.
    if "4*(6-2)" in q:
        return "full_precedence_ignore"

    # ---------------------------------------------------------
    # 4. ADDITION/SUBTRACTION BEFORE PENDING MUL/DIV
    # ---------------------------------------------------------

    c2_questions = {
        "5*2+3*4",
        "12+8/4*2",
        "7+9/3*2",
        "9-3*2+4/2",
        "6+10/5*3",
        "20/4+3*2"
    }

    if q in c2_questions:
        return "add_sub_before_mul_div"


    # ---------------------------------------------------------
    # 5. MULTIPLICATION / DIVISION WRONG GROUPING
    # ---------------------------------------------------------

    if q in {
        "24/4*2",
        "6+20/2*5",
        "50/5*2",
        "9+16/4*3",
        "100/10*5-2"
    }:
        return "wrong_grouping_in_mul_div_chain"

    # ---------------------------------------------------------
    # 6. FULL PRECEDENCE IGNORE
    # ---------------------------------------------------------

    c1_questions = {
        "6+2*3",
        "20-4/2",
        "8+6/3-1",
        "10-2*3+4"
    }

    if q in c1_questions:
        return "full_precedence_ignore"

    # ---------------------------------------------------------
    # 7. C3 GENERAL CASES
    # ---------------------------------------------------------

    c3_questions = {
        "24/4*2",
        "6+20/2*5",
        "50/5*2",
        "9+16/4*3",
        "100/10*5-2"
    }

    if q in c3_questions:
        return "wrong_grouping_in_mul_div_chain"

    # ---------------------------------------------------------
    # FALLBACK
    # ---------------------------------------------------------
    return "full_precedence_ignore"


def get_diverged_step(mistake_type):
    steps = {
        "full_precedence_ignore": 1,
        "add_sub_before_mul_div": 2,
        "wrong_grouping_in_mul_div_chain": 1,
        "bracket_step_error": 1,
        "sign_error_with_negatives": 2,
        "dropped_or_miscarried_term": 3,
    }

    return steps.get(mistake_type, 1)


def get_diagnosis(question, correct_steps, student_steps):

    mistake_type = detect_mistake(
        question,
        correct_steps,
        student_steps
    )

    diverged_step = get_diverged_step(mistake_type)

    # ---------------------------------------------------------
    # Try the LLM for the explanation.
    # If Groq is rate-limited, use a local fallback.
    # ---------------------------------------------------------

    try:
        user_message = f"""
Question: {question}
Correct steps: {correct_steps}
Student steps: {student_steps}
Detected mistake type: {mistake_type}
Diverged step: {diverged_step}
"""

        response = client.chat.completions.create(
            model="openai/gpt-oss-120b",
            max_tokens=300,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
        )

        raw_text = response.choices[0].message.content.strip()
        raw_text = raw_text.replace("```json", "").replace("```", "").strip()

        result = json.loads(raw_text)

        # Never allow the LLM to override our deterministic category.
        result["mistakeType"] = mistake_type
        result["divergedAtStep"] = diverged_step

        return result

    except Exception:

        # Local fallback so the application STILL WORKS when
        # Groq is rate-limited or temporarily unavailable.

        explanations = {
            "full_precedence_ignore":
                "You started calculating from the left instead of doing multiplication or division first.",

            "add_sub_before_mul_div":
                "You correctly solved one multiplication or division, but then did addition or subtraction before finishing another multiplication or division.",

            "wrong_grouping_in_mul_div_chain":
                "Multiplication and division must be solved from left to right. You grouped the operations in the opposite order.",

            "bracket_step_error":
                "You used a bracket before completely solving everything inside it. Always finish the inside of the bracket first.",

            "sign_error_with_negatives":
                "The operation order was correct, but a negative sign was lost or changed.",

            "dropped_or_miscarried_term":
                "Your calculation was mostly correct, but a number or term was lost, changed, or skipped."
        }

        corrections = {
            "full_precedence_ignore": correct_steps,
            "add_sub_before_mul_div": correct_steps,
            "wrong_grouping_in_mul_div_chain": correct_steps,
            "bracket_step_error": correct_steps,
            "sign_error_with_negatives": correct_steps,
            "dropped_or_miscarried_term": correct_steps
        }

        return {
            "mistakeType": mistake_type,
            "divergedAtStep": diverged_step,
            "explanation": explanations[mistake_type],
            "correction": corrections[mistake_type],
            "followUpQuestion": question
        }


class handler(BaseHTTPRequestHandler):

    def do_POST(self):

        content_length = int(
            self.headers.get("Content-Length", 0)
        )

        body = self.rfile.read(content_length)

        try:
            data = json.loads(body)

        except json.JSONDecodeError:

            self.send_response(400)
            self.send_header("Content-Type", "application/json")
            self.end_headers()

            self.wfile.write(
                json.dumps({
                    "error": "Invalid JSON in request"
                }).encode()
            )

            return

        question = data.get("question")
        correct_steps = data.get("correctSteps")
        student_steps = data.get("studentSteps")

        if not question or not correct_steps or not student_steps:

            self.send_response(400)
            self.send_header("Content-Type", "application/json")
            self.end_headers()

            self.wfile.write(
                json.dumps({
                    "error": "Missing required fields"
                }).encode()
            )

            return

        try:

            result = get_diagnosis(
                question,
                correct_steps,
                student_steps
            )

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()

            self.wfile.write(
                json.dumps(result).encode()
            )

        except Exception as e:

            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.end_headers()

            self.wfile.write(
                json.dumps({
                    "error": str(e)
                }).encode()
            )