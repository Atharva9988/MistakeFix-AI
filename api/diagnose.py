import json
import os
from http.server import BaseHTTPRequestHandler
from groq import Groq

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

SYSTEM_PROMPT = """You are a math error diagnosis engine for BODMAS problems, grades 6-8.

You will receive: the question, the correct step-by-step solution, and the student's actual steps.

Find the exact step where the student's working first diverges from the correct method. Classify that divergence into exactly one of these categories:

1. full_precedence_ignore: the student computed operations in the literal left-to-right order of the expression, with zero regard for any precedence rule, from the very first step.Do NOT use this category if the student correctly handled any bracket, or correctly prioritized any single multiplication/division before an addition/subtraction. In those cases, the error belongs to category 2, 3, or 4 instead, even if other parts of the working look left-to-right.

2. add_sub_before_mul_div: the student correctly prioritized at least one multiplication or division that was NOT the leftmost operator in the expression, but then performed an addition or subtraction before finishing a separate, still-pending multiplication or division elsewhere in the expression.

3. wrong_grouping_in_mul_div_chain: within a chain of only multiplication and division operations, the student grouped two operations together in the wrong order instead of resolving strictly left to right.

4. bracket_step_error: the student used a bracket's result before fully resolving everything inside it, or resolved the bracket incorrectly relative to what was inside it.This category applies even if the student applied correct precedence rules everywhere else, as long as the bracket itself was mishandled.

5. sign_error_with_negatives: the sequence and choice of operations was entirely correct, but a negative sign was dropped, flipped, or mishandled when removing a bracket or subtracting a negative.

6. dropped_or_miscarried_term: the sequence and choice of operations was entirely correct, but a number or term was lost, miscopied, or the final combination step was skipped.

Output ONLY valid JSON, no markdown fences, no text outside the JSON, in exactly this shape:
{
  "mistakeType": "one of the six category keys above",
  "divergedAtStep": integer,
  "explanation": "plain language, one to two sentences, aimed at a 12 year old",
  "correction": "the corrected steps as a short string",
  "followUpQuestion": "a new BODMAS question testing the same misconception"
}"""


def get_diagnosis(question, correct_steps, student_steps):
    user_message = f"Question: {question}\nCorrect steps: {correct_steps}\nStudent steps: {student_steps}"

    response = client.chat.completions.create(
        model="openai/gpt-oss-120b",
        max_tokens=1000,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
    )

    raw_text = response.choices[0].message.content.strip()
    raw_text = raw_text.replace("```json", "").replace("```", "").strip()

    try:
        return json.loads(raw_text)
    except json.JSONDecodeError:
        retry_response = client.chat.completions.create(
            model="openai/gpt-oss-120b",
            max_tokens=1000,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT + "\n\nCRITICAL: your last response was not valid JSON. Output ONLY the JSON object, nothing else."},
                {"role": "user", "content": user_message},
            ],
        )
        retry_text = retry_response.choices[0].message.content.strip()
        retry_text = retry_text.replace("```json", "").replace("```", "").strip()
        return json.loads(retry_text)


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length)

        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            self.send_response(400)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": "Invalid JSON in request"}).encode())
            return

        question = data.get("question")
        correct_steps = data.get("correctSteps")
        student_steps = data.get("studentSteps")

        if not question or not correct_steps or not student_steps:
            self.send_response(400)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": "Missing required fields"}).encode())
            return

        try:
            result = get_diagnosis(question, correct_steps, student_steps)
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(result).encode())
        except Exception as e:
            self.send_response(1000)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode())