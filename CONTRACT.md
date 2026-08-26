# MistakeFix AI — API Contract

This is the fixed agreement between frontend (Person B) and backend (Person A).
Do not change this without both people agreeing and updating this file.

## Endpoint
`POST /api/diagnose`

## Request body (sent by frontend)
```json
{
  "questionId": "Q3",
  "question": "12 + 8 / 4 * 2",
  "correctSteps": "8 / 4 = 2, 2 * 2 = 4, 12 + 4 = 16",
  "studentSteps": "8 / 4 = 2, 12 + 2 = 14, 14 * 2 = 28"
}
```

## Response body (returned by backend)
```json
{
  "mistakeType": "left_to_right_assumption",
  "divergedAtStep": 2,
  "explanation": "Multiplication and division are performed before addition. You divided first, which was correct, but then added before finishing the multiplication step.",
  "correction": "8 / 4 = 2, then 2 * 2 = 4, then 12 + 4 = 16",
  "followUpQuestion": "Solve: 20 - 6 / 2 * 3"
}
```

## Error response (if diagnosis fails)
```json
{
  "error": "Could not process the submission. Please try again."
}
```
HTTP status 500 in this case. Frontend must handle this case and show a friendly message,
not crash or show a blank screen.

## Question bank format (hardcoded in frontend for now)
```json
[
  { "id": "Q1", "text": "12 + 8 / 4 * 2", "correctSteps": "8 / 4 = 2, 2 * 2 = 4, 12 + 4 = 16" },
  { "id": "Q2", "text": "20 - 6 / 2 * 3", "correctSteps": "6 / 2 = 3, 3 * 3 = 9, 20 - 9 = 11" },
  { "id": "Q3", "text": "(5 + 3) * 2 - 4", "correctSteps": "5 + 3 = 8, 8 * 2 = 16, 16 - 4 = 12" }
]
```
Person B owns this list in the frontend. Person A's backend does not need to know the
full question bank, only the specific question sent in each request.