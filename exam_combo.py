import os
import io
import zipfile
from datetime import datetime
from google import genai

from flask import send_file
from utils.exam_utils import (
    extract_json_from_ai,
    normalize_questions,
    normalize_answers,
    clean_ai_text,
    create_pdf
)



def handle_exam_combo(request):
    """
    Handles combo grade + combo board exam paper generation
    """

    grade = request.form.get("grade")
    board = request.form.get("board")
    paper_type = request.form.get("paper_type")
    year = request.form.get("year")
    include_answers = request.form.get("include_answers") == "1"

    if not grade or not board or not paper_type:
        raise ValueError("Missing required fields")

    client = genai.Client(api_key=os.environ.get("GENAI_API_KEY"))

    # ---------------- PROMPT BUILDING ----------------
    grade_text = (
        "Grades 10, 11 and 12"
        if grade == "10-12"
        else f"Grade {grade}"
    )

    board_text = (
        "CBSE and ICSE boards"
        if board == "CBSE-ICSE"
        else f"{board} board"
    )

    if paper_type == "past":
        prompt = f"""
Generate a realistic past exam paper.

Target: {grade_text}
Board Pattern: {board_text}
Year: {year}

Rules:
- Exam-level questions
- NO answers
- Plain text only
- 15 questions

Return STRICT JSON:
[
  {{ "question": "..." }}
]
"""
        title = f"{grade_text} {board_text} Past Paper ({year})"

    else:
        prompt = f"""
Generate a mock exam paper.

Target: {grade_text}
Board Pattern: {board_text}

Rules:
- Exam-level questions
- Moderate difficulty
- NO answers
- Plain text only
- 15 questions

Return STRICT JSON
"""
        title = f"{grade_text} {board_text} Mock Paper"

    # ---------------- AI CALL ----------------
    response = client.models.generate_content(
        model="models/gemini-flash-latest",
        contents=prompt
    )

    questions_json = extract_json_from_ai(response.text)
    if not questions_json:
        raise ValueError("AI failed to generate questions")

    worksheet_text = normalize_questions(questions_json)

    # ---------------- ANSWERS ----------------
    solution_text = None
    if include_answers:
        answer_prompt = f"""
Return ONLY the answers.
No explanations.
Numbered format.

Questions:
{worksheet_text}
"""
        a_response = client.models.generate_content(
            model="models/gemini-flash-latest",
            contents=answer_prompt
        )
        solution_text = normalize_answers(
            clean_ai_text(a_response.text)
        )

    # ---------------- FILE CREATION ----------------
    info = {
        "date": datetime.now().strftime("%d %b %Y"),
        "marks": "___ / 80",
        "sub-title": board_text
    }

    files = []

    ws_path = create_pdf(worksheet_text, title, info)
    files.append(("worksheet/Worksheet.pdf", ws_path))

    if include_answers and solution_text:
        sol_path = create_pdf(
            solution_text,
            f"{title} - Solutions",
            info
        )
        files.append(("solutions/Solutions.pdf", sol_path))

    # ---------------- ZIP ----------------
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zipf:
        for name, path in files:
            with open(path, "rb") as f:
                zipf.writestr(name, f.read())

    zip_buffer.seek(0)

    return send_file(
        zip_buffer,
        as_attachment=True,
        download_name="Exam_Papers.zip",
        mimetype="application/zip"
    )
