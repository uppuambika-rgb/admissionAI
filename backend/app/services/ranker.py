import json
from pathlib import Path
from typing import List, Dict, Any
from app.models.student import StudentProfile
from app.models.program import (
    CollegeProgram,
    RecommendationItem,
    RecommendationResponse,
    LikelihoodTier
)
from app.services.evaluator import evaluate_admission_likelihood
from app.services.matcher import calculate_curriculum_match, calculate_placement_score

DATA_FILE = Path(__file__).resolve().parent.parent / "data" / "sample_colleges.json"

def load_college_programs() -> List[CollegeProgram]:
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    return [CollegeProgram(**item) for item in data]

def generate_recommendations(
    student: StudentProfile,
    programs: List[CollegeProgram] = None
) -> RecommendationResponse:
    """
    Deterministically evaluates all programs and constructs a balanced,
    strategically ordered preference list (Aspirational -> Likely -> Safe).
    """
    if programs is None:
        programs = load_college_programs()

    evaluated_items: List[RecommendationItem] = []

    # Map tier to baseline feasibility score for composite ranking
    tier_feasibility_map = {
        LikelihoodTier.SAFE: 90.0,
        LikelihoodTier.LIKELY: 75.0,
        LikelihoodTier.ASPIRATIONAL: 55.0,
        LikelihoodTier.REACH: 25.0
    }

    tier_counts = {
        LikelihoodTier.SAFE.value: 0,
        LikelihoodTier.LIKELY.value: 0,
        LikelihoodTier.ASPIRATIONAL.value: 0,
        LikelihoodTier.REACH.value: 0
    }

    rank = student.rank if student.rank is not None else 10000

    for program in programs:
        tier, likelihood_range, margin, uncertainty_note = evaluate_admission_likelihood(
            student_rank=rank,
            category=student.category,
            program=program
        )
        tier_counts[tier.value] += 1

        interest_score, matched_tags = calculate_curriculum_match(student, program)
        placement_score = calculate_placement_score(program, student)

        feasibility_score = tier_feasibility_map.get(tier, 50.0)
        # Composite score blends feasibility (40%), curriculum fit (35%), and placement outcomes (25%)
        composite = (feasibility_score * 0.40) + (interest_score * 0.35) + (placement_score * 0.25)

        # Baseline explanation template (can be enriched by AI service)
        base_explanation = (
            f"Categorized as {tier.value} based on your rank of {rank} (closing cutoff: "
            f"{program.category_cutoffs.get(student.category, program.category_cutoffs['General']).closing_rank}). "
            f"Curriculum aligns well with your interest in {', '.join(matched_tags[:2])}. "
            f"Offers {program.placement_stats.placement_percentage}% placement rate with a median CTC of ₹{program.placement_stats.median_salary_lpa} LPA."
        )

        item = RecommendationItem(
            program=program,
            tier=tier,
            likelihood_range=likelihood_range,
            composite_score=round(composite, 1),
            cutoff_margin_percent=margin,
            interest_alignment_tags=matched_tags,
            placement_score=placement_score,
            ai_explanation=base_explanation,
            uncertainty_note=uncertainty_note
        )
        evaluated_items.append(item)

    # Separate items by tier
    aspirational = [i for i in evaluated_items if i.tier == LikelihoodTier.ASPIRATIONAL]
    likely = [i for i in evaluated_items if i.tier == LikelihoodTier.LIKELY]
    safe = [i for i in evaluated_items if i.tier == LikelihoodTier.SAFE]
    reach = [i for i in evaluated_items if i.tier == LikelihoodTier.REACH]

    # Sort each tier internally by composite score (highest match & placement first)
    aspirational.sort(key=lambda x: x.composite_score, reverse=True)
    likely.sort(key=lambda x: x.composite_score, reverse=True)
    safe.sort(key=lambda x: x.composite_score, reverse=True)
    reach.sort(key=lambda x: x.composite_score, reverse=True)

    # Build optimal choice-filling preference sequence:
    # Recommended strategy:
    # 1. Top 2-3 Aspirational choices (reach for dream colleges first)
    # 2. Top 3-5 Likely choices (solid realistic goals)
    # 3. Top 2-3 Safe choices (safety cushion)
    # 4. If any tier is sparse, fill from adjacent tiers
    preference_list: List[RecommendationItem] = []
    
    # Take top 2-3 aspirational
    preference_list.extend(aspirational[:3])
    # Take top 3-4 likely
    preference_list.extend(likely[:4])
    # Take top 2-3 safe
    preference_list.extend(safe[:3])

    # If list is small (e.g. extreme rank), ensure we have at least 5-6 recommendations
    if len(preference_list) < 5:
        remaining = [i for i in (likely + safe + aspirational + reach) if i not in preference_list]
        preference_list.extend(remaining[:(5 - len(preference_list))])

    disclaimer_text = (
        "Advisory Disclaimer: Historical cutoffs and seat allotments are subject to annual changes in applicant volumes, "
        "seat matrix alterations, and examination difficulty. These estimates represent probabilistic likelihood ranges "
        "and do not constitute an admission or placement guarantee. Verify official counselling authority guidelines before submitting your final preference sheet."
    )

    return RecommendationResponse(
        student_profile=student,
        total_evaluated=len(programs),
        preferences=preference_list,
        tier_summary=tier_counts,
        disclaimer=disclaimer_text
    )
