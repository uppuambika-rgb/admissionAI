import re
import json
import requests
from typing import Dict, Any, List, Tuple, Optional
from app.config import settings
from app.models.student import StudentProfile, ChatMessage, ChatResponse, StructuredQueryResult
from app.models.program import RecommendationItem, CollegeProgram
from app.services.ranker import load_college_programs
from app.services.query_service import process_counselling_query, classify_intent

def extract_profile_from_text(text: str, current: StudentProfile) -> Tuple[StudentProfile, List[str]]:
    """
    Robust rule-based extractor to parse and update student details from free-form text.
    Preserves all existing attributes unless explicitly updated.
    """
    updated = current.model_copy()
    lower_text = text.lower()

    # 1. Entrance exam extraction
    if "jee advanced" in lower_text or "jee adv" in lower_text:
        updated.entrance_exam = "JEE Advanced"
    elif "jee main" in lower_text or "jee mains" in lower_text:
        updated.entrance_exam = "JEE Main"
    elif "wbjee" in lower_text:
        updated.entrance_exam = "WBJEE"
    elif "kcet" in lower_text:
        updated.entrance_exam = "KCET"
    elif "met" in lower_text:
        updated.entrance_exam = "MET"
    elif "cet" in lower_text and not updated.entrance_exam:
        updated.entrance_exam = "State CET"

    # 2. Rank extraction
    rank_match = re.search(r'(?:rank\s*(?:is|:)?\s*|air\s*[:\s]?\s*)(\d{1,7})', lower_text)
    if not rank_match:
        rank_match = re.search(r'(\d{1,7})\s*(?:rank|air)', lower_text)
    if rank_match:
        try:
            updated.rank = int(rank_match.group(1))
        except ValueError:
            pass

    # 3. Category extraction
    if any(k in lower_text for k in ["obc-ncl", "obc ncl", "obc"]):
        updated.category = "OBC-NCL"
    elif "ews" in lower_text:
        updated.category = "EWS"
    elif re.search(r'\bsc\b', lower_text):
        updated.category = "SC"
    elif re.search(r'\bst\b', lower_text):
        updated.category = "ST"
    elif any(k in lower_text for k in ["general", "gen", "open"]):
        updated.category = "General"

    # 4. Academic strengths
    potential_strengths = ["math", "mathematics", "physics", "chemistry", "coding", "programming", "logic", "algorithms"]
    for s in potential_strengths:
        if s in lower_text:
            cleaned = "Mathematics" if s in ("math", "mathematics") else s.title()
            if cleaned not in updated.academic_strengths:
                updated.academic_strengths.append(cleaned)

    # 5. Interests
    interest_keywords = {
        "artificial intelligence": "Artificial Intelligence",
        "machine learning": "Machine Learning",
        "ai": "Artificial Intelligence",
        "ml": "Machine Learning",
        "data science": "Data Science",
        "robotics": "Robotics & Automation",
        "cybersecurity": "Cybersecurity",
        "cloud": "Cloud Computing",
        "web": "Web Development",
        "software": "Software Engineering",
        "electronics": "Core Electronics",
        "hardware": "Hardware / VLSI",
        "mechanical": "Mechanical Engineering"
    }
    for k, label in interest_keywords.items():
        if re.search(r'\b' + re.escape(k) + r'\b', lower_text):
            if label not in updated.interests:
                updated.interests.append(label)

    # 6. Career goals
    career_map = {
        "software engineer": "Software Engineering",
        "developer": "Software Engineering",
        "research": "Academic / Industrial Research",
        "quant": "Quantitative Finance",
        "finance": "Quantitative Finance",
        "product manager": "Product Management",
        "startup": "Entrepreneurship / Startups",
        "robotics engineer": "Robotics Engineering"
    }
    for k, goal in career_map.items():
        if k in lower_text:
            if goal not in updated.career_goals:
                updated.career_goals.append(goal)

    # 7. Higher study interest
    if any(k in lower_text for k in ["ms abroad", "masters", "phd", "higher studies", "higher study"]):
        updated.higher_study_interest = "Interested in MS/PhD graduate research"

    # 8. Entrepreneurship interest
    if any(k in lower_text for k in ["startup", "entrepreneurship", "incubator", "own company", "ventures"]):
        updated.entrepreneurship_interest = "Interested in tech startups & incubation"

    # 9. Placement priorities
    if any(k in lower_text for k in ["high package", "high ctc", "top placement", "good placement"]):
        if "High Placement CTC" not in updated.placement_priorities:
            updated.placement_priorities.append("High Placement CTC")

    # Missing fields for initial intake
    missing = []
    if updated.rank is None:
        missing.append("rank")
    if not updated.interests:
        missing.append("interests")
    if not updated.career_goals:
        missing.append("career_goals")
    if not updated.academic_strengths:
        missing.append("academic_strengths")

    return updated, missing

def call_gemini_api(prompt: str) -> str:
    """
    Calls Gemini REST API if GEMINI_API_KEY is configured.
    """
    if not settings.GEMINI_API_KEY:
        return ""

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={settings.GEMINI_API_KEY}"
    payload = {
        "contents": [{
            "parts": [{"text": prompt}]
        }],
        "generationConfig": {
            "temperature": 0.2,
            "maxOutputTokens": 600
        }
    }
    try:
        response = requests.post(url, json=payload, timeout=8)
        if response.status_code == 200:
            data = response.json()
            candidates = data.get("candidates", [])
            if candidates:
                return candidates[0]["content"]["parts"][0]["text"].strip()
    except Exception as e:
        print(f"[AI Counsellor] Gemini API call error: {e}")
    return ""

def generate_chat_reply(
    message: str,
    history: List[ChatMessage],
    current_profile: StudentProfile
) -> ChatResponse:
    """
    Central admission counsellor dialogue handler.
    1. Extracts and maintains student profile.
    2. Identifies question intent and queries structured services.
    3. Provides conversational explanation grounded strictly in facts.
    """
    updated_profile, missing_fields = extract_profile_from_text(message, current_profile)
    is_complete = (updated_profile.rank is not None and len(updated_profile.interests) > 0)
    intent = classify_intent(message)
    programs = load_college_programs()

    # If the user is asking a follow-up or specific counselling question
    if intent != "GENERAL_CONVERSATION":
        factual_explanation, structured_res = process_counselling_query(
            message=message,
            student=updated_profile,
            programs=programs
        )

        # If live Gemini is enabled, synthesize a warm conversational summary strictly grounded in factual_explanation & structured data
        if settings.GEMINI_API_KEY and not settings.MOCK_MODE and structured_res:
            table_sample = json.dumps(structured_res.rows[:4])
            prompt = (
                "You are an empathetic, highly knowledgeable AI Admission Counsellor. "
                "Explain the following factual counselling data to the student in response to their question.\n"
                f"Student Question: '{message}'\n"
                f"Student Profile: Rank={updated_profile.rank}, Category={updated_profile.category}, Goals={updated_profile.career_goals}\n"
                f"Factual Result Summary: {factual_explanation}\n"
                f"Sample Data Rows: {table_sample}\n\n"
                "IMPORTANT RULES:\n"
                "1. Strictly use the provided data. NEVER invent cutoffs, fees, placement rates, or hostel facts.\n"
                "2. Clearly communicate uncertainty—historical cutoffs fluctuate and do NOT guarantee future admission.\n"
                "3. Keep the response concise (2-4 sentences) and encourage them to inspect the attached comparison table."
            )
            ai_text = call_gemini_api(prompt)
            if ai_text:
                return ChatResponse(
                    reply=ai_text,
                    extracted_profile=updated_profile,
                    is_profile_complete=is_complete,
                    missing_fields=missing_fields,
                    intent=intent,
                    structured_data=structured_res
                )

        return ChatResponse(
            reply=factual_explanation,
            extracted_profile=updated_profile,
            is_profile_complete=is_complete,
            missing_fields=missing_fields,
            intent=intent,
            structured_data=structured_res
        )

    # Initial intake / guided dialogue state machine:
    reply_lines = []
    if updated_profile.rank is None:
        reply_lines.append(
            "Hello! I am your AI Admission Counsellor. To help you evaluate realistic admission options, "
            "could you share your **entrance exam rank** (e.g. JEE Main, Advanced, or CET) and your **category** (General, OBC-NCL, SC, ST, EWS)?"
        )
    elif not updated_profile.interests:
        reply_lines.append(
            f"Got it! I have noted your rank as **#{updated_profile.rank:,}** ({updated_profile.category} category). "
            "Which engineering or technology fields excite you the most? (For example: Artificial Intelligence, Software Engineering, Robotics, or Core Electronics?)"
        )
    elif not updated_profile.career_goals:
        reply_lines.append(
            f"Great focus! With your interest in **{', '.join(updated_profile.interests)}**, what are your primary career goals "
            "or placement priorities? (e.g., Software Engineer at product firms, Academic Research/MS abroad, or Core Engineering?)"
        )
    else:
        reply_lines.append(
            f"Your counselling profile is set: Rank **#{updated_profile.rank:,}** ({updated_profile.category}), "
            f"interests in **{', '.join(updated_profile.interests)}**, and career aspirations in **{', '.join(updated_profile.career_goals)}**. "
            "Your balanced choice-filling sheet is ready! You can now ask me follow-up questions like: "
            "'*Can I get into an NIT?*', '*Which programme is best for AI?*', '*What are the fees?*', or '*Which has better placements?*'"
        )

    return ChatResponse(
        reply=" ".join(reply_lines),
        extracted_profile=updated_profile,
        is_profile_complete=is_complete,
        missing_fields=missing_fields,
        intent="INTAKE"
    )

def enrich_explanations_with_ai(
    recommendations: List[RecommendationItem],
    student: StudentProfile
) -> List[RecommendationItem]:
    """
    Enriches recommendations with personalized rationales based on deterministic scores.
    """
    for item in recommendations[:5]:
        prog = item.program
        
        tier_phrasing = {
            "Safe": "provides a comfortable safety cushion against past closing cutoffs",
            "Likely": "sits right in your competitive sweet spot based on recent cutoffs",
            "Aspirational": "represents an ambitious reach where late round movement could work in your favor",
            "Reach": "is an ambitious moonshot choice"
        }
        
        curriculum_text = (
            f"Its curriculum covers {', '.join(item.interest_alignment_tags[:2])}, aligning directly with your goals."
            if item.interest_alignment_tags else "The program offers robust foundational engineering training."
        )

        item.ai_explanation = (
            f"{prog.college_name} ({prog.branch_name}) {tier_phrasing.get(item.tier.value, 'is recommended')}. "
            f"{curriculum_text} Graduates average ₹{prog.placement_stats.median_salary_lpa} LPA with top recruiters including "
            f"{', '.join(prog.placement_stats.top_recruiters[:3])}. *Historical cutoffs fluctuate annually; not a guarantee.*"
        )

    return recommendations
