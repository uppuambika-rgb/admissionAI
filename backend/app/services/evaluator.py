from typing import Tuple, List, Dict, Any, Optional
from app.models.program import CollegeProgram, LikelihoodTier

def evaluate_admission_likelihood(
    student_rank: int,
    category: str,
    program: CollegeProgram
) -> Tuple[LikelihoodTier, str, float, str]:
    """
    Deterministic evaluation of admission likelihood.
    Returns:
        (tier, likelihood_range_str, margin_percent, uncertainty_note)
    """
    # Look up category cutoff, fallback to General if category specific cutoff is unavailable
    cutoff = program.category_cutoffs.get(category)
    if not cutoff:
        cutoff = program.category_cutoffs.get("General")
    
    if not cutoff:
        return (
            LikelihoodTier.REACH,
            "Unknown (< 10%)",
            -100.0,
            "Cutoff data for this category is currently unindexed. Highly speculative."
        )

    closing_rank = cutoff.closing_rank
    opening_rank = cutoff.opening_rank

    # Margin: positive means student rank is numerically lower (better) than closing rank
    margin_percent = round(((closing_rank - student_rank) / closing_rank) * 100, 1)

    if margin_percent >= 12.0:
        tier = LikelihoodTier.SAFE
        likelihood_range = "80% - 95%"
        uncertainty = (
            f"Strong historical cushion (+{margin_percent}% margin relative to closing rank {closing_rank:,}). "
            "Categorized as Safe based on past trends; seat matrix changes or applicant surges can still shift cutoffs."
        )
    elif margin_percent >= -10.0:
        tier = LikelihoodTier.LIKELY
        likelihood_range = "50% - 75%"
        uncertainty = (
            f"Within competitive range (margin {margin_percent}% vs closing rank {closing_rank:,}). "
            "Realistic contender in standard counselling rounds, subject to year-on-year cutoff shifts of ±5-8%."
        )
    elif margin_percent >= -30.0:
        tier = LikelihoodTier.ASPIRATIONAL
        likelihood_range = "20% - 40%"
        uncertainty = (
            f"Aspirational reach (rank {student_rank:,} is {abs(margin_percent)}% above 2024 closing rank of {closing_rank:,}). "
            "Plausible during late or spot rounds if candidate choices deviate from historical patterns."
        )
    else:
        tier = LikelihoodTier.REACH
        likelihood_range = "< 15%"
        uncertainty = (
            f"High reach (rank {student_rank:,} is significantly above 2024 closing rank of {closing_rank:,}). "
            "Statistically low historical probability; recommended only as an ambitious moonshot."
        )

    return tier, likelihood_range, margin_percent, uncertainty

def filter_and_evaluate_admission(
    student_rank: int,
    category: str,
    programs: List[CollegeProgram],
    college_type: Optional[str] = None,
    branch_keyword: Optional[str] = None,
    tier_filter: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Filters programs by criteria and deterministically calculates admission chances,
    returning structured table rows with rank difference and probability ranges.
    """
    results = []

    for p in programs:
        # College type filter (e.g. "NIT", "IIT", "IIIT", etc.)
        if college_type:
            if college_type.upper() == "NIT" and p.college_type != "NIT":
                continue
            elif college_type.upper() == "IIT" and p.college_type != "IIT":
                continue
            elif college_type.upper() == "IIIT" and p.college_type != "IIIT":
                continue
            elif college_type.upper() not in ["NIT", "IIT", "IIIT"] and college_type.lower() not in p.college_type.lower():
                continue

        # Branch keyword filter (e.g. "CSE", "Computer Science", "ECE", "Mechanical")
        if branch_keyword:
            bk = branch_keyword.lower()
            if bk in ("cse", "computer science", "cs"):
                if not any(k in p.branch_name.lower() for k in ["computer", "software", "information technology"]):
                    continue
            elif bk in ("ece", "electronics"):
                if not any(k in p.branch_name.lower() for k in ["electronics", "electrical"]):
                    continue
            elif bk in ("mech", "mechanical"):
                if "mechanical" not in p.branch_name.lower():
                    continue
            elif bk not in p.branch_name.lower():
                continue

        tier, likelihood_range, margin_percent, uncertainty = evaluate_admission_likelihood(
            student_rank, category, p
        )

        # Tier filter (e.g. "Safe", "Likely", "Aspirational")
        if tier_filter and tier.value.lower() != tier_filter.lower():
            continue

        cutoff = p.category_cutoffs.get(category, p.category_cutoffs.get("General"))
        closing_rank = cutoff.closing_rank if cutoff else 0
        rank_diff = closing_rank - student_rank  # positive = better than cutoff
        diff_str = f"+{rank_diff:,}" if rank_diff >= 0 else f"{rank_diff:,}"

        results.append({
            "college": p.college_name,
            "branch": p.branch_name,
            "type": p.college_type,
            "exam": p.exam,
            "category": category,
            "candidate_rank": f"#{student_rank:,}",
            "historical_cutoff": f"{closing_rank:,}",
            "cutoff_year_round": p.cutoff_year_round,
            "rank_difference": diff_str,
            "likelihood_range": likelihood_range,
            "tier": tier.value,
            "uncertainty_note": uncertainty,
            "median_ctc": f"₹{p.placement_stats.median_salary_lpa} LPA",
            "placement_rate": f"{p.placement_stats.placement_percentage}%",
            "tuition_fee": f"₹{p.annual_tuition_fee_inr:,} / yr" if p.annual_tuition_fee_inr else "Not available",
            "location": p.location
        })

    # Sort results: Safe -> Likely -> Aspirational -> Reach, then by rank margin
    tier_order = {"Safe": 1, "Likely": 2, "Aspirational": 3, "Reach": 4}
    results.sort(key=lambda x: (tier_order.get(x["tier"], 5), -int(x["rank_difference"].replace("+", "").replace(",", ""))))
    return results
