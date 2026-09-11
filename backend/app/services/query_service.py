import re
from typing import Dict, Any, List, Optional, Tuple
from app.models.student import StudentProfile, StructuredQueryResult
from app.models.program import CollegeProgram
from app.services.evaluator import filter_and_evaluate_admission
from app.services.matcher import find_programmes_matching_interests, detect_curriculum_mismatch
from app.services.college_info_service import (
    get_fees_information,
    get_scholarships_information,
    get_hostel_information,
    get_location_information
)
from app.services.placement_service import (
    get_placement_comparison,
    get_job_roles_information,
    get_higher_studies_information,
    get_entrepreneurship_information
)
from app.services.ranker import generate_recommendations

DISCLAIMER_TEXT = (
    "Historical Trend Notice: Admission probabilities, cutoff margins, and placement records are derived from historical 2024 benchmarks. "
    "They represent estimated probabilistic ranges and do not guarantee future seat allotment or job placement."
)

def classify_intent(message: str) -> str:
    """
    Classifies student question into a normalized intent category without hardcoded sentence matching.
    """
    msg = message.lower().strip()

    # 1. Why ranked first / ranking rationale
    if any(k in msg for k in ["why did you rank", "why is this ranked first", "why ranked #1", "why rank this first", "why first"]):
        return "WHY_FIRST_RANK"

    # 2. Preference list inquiry
    if any(k in msg for k in ["preference list", "choice filling", "my choices", "show preference", "show choices"]):
        return "PREFERENCE_LIST"

    # 3. Specific college type queries (e.g. NITs, IITs)
    if "nit" in msg or "nits" in msg:
        return "NIT_ADMISSION"
    if "iit" in msg or "iits" in msg:
        return "IIT_ADMISSION"

    # 4. Branch queries (CSE, ECE, Mechanical)
    if any(k in msg for k in ["can i get cse", "get cse", "computer science", "cse options", "cs options"]):
        return "BRANCH_CSE"

    # 5. Tier-specific queries (Safest, Likely, Aspirational)
    if any(k in msg for k in ["safest", "safest options", "safest colleges", "safe options", "safe colleges", "my safe"]):
        return "SAFEST_OPTIONS"
    if any(k in msg for k in ["aspirational", "reach options", "dream colleges", "dream options"]):
        return "ASPIRATIONAL_OPTIONS"
    if any(k in msg for k in ["likely options", "likely colleges", "moderate options", "realistic options"]):
        return "LIKELY_OPTIONS"

    # 6. Colleges general availability
    if any(k in msg for k in ["which colleges can i get", "what colleges can i get", "colleges for my rank", "where can i get", "what can i get"]):
        return "COLLEGES_AVAILABLE"

    # 7. AI and Curriculum matching
    if any(k in msg for k in ["best for ai", "best for machine learning", "programme for ai", "teach ai", "matches my interests", "match my interests"]):
        return "AI_CURRICULUM"

    # 8. Placements & Job roles
    if any(k in msg for k in ["better placement", "best placement", "compare placement", "highest ctc", "placement rate", "placements"]):
        return "PLACEMENTS_COMPARE"
    if any(k in msg for k in ["job roles", "typical roles", "what jobs", "career roles", "job profiles"]):
        return "JOB_ROLES"

    # 9. Fees, Scholarships, Hostels, Location
    if any(k in msg for k in ["fee", "fees", "tuition", "cost of study", "how expensive"]):
        return "FEES_INQUIRY"
    if any(k in msg for k in ["scholarship", "scholarships", "fee waiver", "financial aid", "concession"]):
        return "SCHOLARSHIPS"
    if any(k in msg for k in ["hostel", "hostels", "accommodation", "dorm", "hostel fee"]):
        return "HOSTEL_INQUIRY"
    if any(k in msg for k in ["located", "location", "locations", "which city", "which state"]):
        return "LOCATION_INQUIRY"

    # 10. Higher studies & Entrepreneurship
    if any(k in msg for k in ["higher study", "higher studies", "ms abroad", "masters", "phd", "research"]):
        return "HIGHER_STUDIES"
    if any(k in msg for k in ["entrepreneurship", "startup", "startups", "incubator", "incubation", "ventures"]):
        return "ENTREPRENEURSHIP"

    return "GENERAL_CONVERSATION"

def process_counselling_query(
    message: str,
    student: StudentProfile,
    programs: List[CollegeProgram]
) -> Tuple[str, Optional[StructuredQueryResult]]:
    """
    Executes intent-based processing across reusable backend services.
    Returns (natural_text_explanation, structured_query_result).
    """
    intent = classify_intent(message)
    rank = student.rank if student.rank is not None else 8000
    category = student.category or "General"

    if intent == "NIT_ADMISSION":
        rows = filter_and_evaluate_admission(rank, category, programs, college_type="NIT")
        columns = ["College", "Branch", "Candidate Rank", "Historical Cutoff", "Rank Difference", "Likelihood Range", "Tier", "Median CTC"]
        table_rows = []
        for r in rows:
            table_rows.append({
                "College": r["college"],
                "Branch": r["branch"],
                "Candidate Rank": r["candidate_rank"],
                "Historical Cutoff": r["historical_cutoff"],
                "Rank Difference": r["rank_difference"],
                "Likelihood Range": r["likelihood_range"],
                "Tier": r["tier"],
                "Median CTC": r["median_ctc"]
            })

        safe_count = sum(1 for r in rows if r["tier"] == "Safe")
        likely_count = sum(1 for r in rows if r["tier"] == "Likely")
        asp_count = sum(1 for r in rows if r["tier"] == "Aspirational")

        explanation = (
            f"Based on your rank of **#{rank:,}** ({category} category), we evaluated all National Institutes of Technology (NITs) in our database. "
            f"You have **{safe_count} Safe** option(s), **{likely_count} Likely** option(s), and **{asp_count} Aspirational** reach option(s). "
            f"Review the deterministic admission likelihood comparison table below."
        )
        res = StructuredQueryResult(
            query_type=intent,
            title=f"NIT Admission Possibilities for Rank #{rank:,} ({category})",
            columns=columns,
            rows=table_rows,
            disclaimer=DISCLAIMER_TEXT
        )
        return explanation, res

    elif intent == "COLLEGES_AVAILABLE":
        rows = filter_and_evaluate_admission(rank, category, programs)
        # Filter to Safe and Likely options for clarity
        relevant = [r for r in rows if r["tier"] in ("Safe", "Likely", "Aspirational")][:8]
        columns = ["College", "Branch", "Type", "Historical Cutoff", "Rank Difference", "Likelihood Range", "Tier"]
        table_rows = [
            {
                "College": r["college"],
                "Branch": r["branch"],
                "Type": r["type"],
                "Historical Cutoff": r["historical_cutoff"],
                "Rank Difference": r["rank_difference"],
                "Likelihood Range": r["likelihood_range"],
                "Tier": r["tier"]
            }
            for r in relevant
        ]
        explanation = (
            f"For rank **#{rank:,}** ({category}), here are the institutions where you stand a strong-to-moderate chance of admission across Safe, Likely, and Aspirational tiers. "
            "Options are ranked by eligibility feasibility and cutoff margins."
        )
        res = StructuredQueryResult(
            query_type=intent,
            title=f"Colleges Available for Rank #{rank:,} ({category})",
            columns=columns,
            rows=table_rows,
            disclaimer=DISCLAIMER_TEXT
        )
        return explanation, res

    elif intent == "SAFEST_OPTIONS":
        rows = filter_and_evaluate_admission(rank, category, programs, tier_filter="Safe")
        columns = ["College", "Branch", "Historical Cutoff", "Rank Difference", "Likelihood Range", "Median CTC", "Location"]
        table_rows = [
            {
                "College": r["college"],
                "Branch": r["branch"],
                "Historical Cutoff": r["historical_cutoff"],
                "Rank Difference": r["rank_difference"],
                "Likelihood Range": r["likelihood_range"],
                "Median CTC": r["median_ctc"],
                "Location": r["location"]
            }
            for r in rows
        ]
        explanation = (
            f"Here are your **Safest options** where your rank of **#{rank:,}** provides a healthy cushion (margin > 12%) "
            "over historical closing cutoffs. These serve as reliable safety nets to guarantee seat security."
        )
        res = StructuredQueryResult(
            query_type=intent,
            title=f"Safest Admission Options for Rank #{rank:,} ({category})",
            columns=columns,
            rows=table_rows,
            disclaimer=DISCLAIMER_TEXT
        )
        return explanation, res

    elif intent == "LIKELY_OPTIONS":
        rows = filter_and_evaluate_admission(rank, category, programs, tier_filter="Likely")
        columns = ["College", "Branch", "Historical Cutoff", "Rank Difference", "Likelihood Range", "Median CTC"]
        table_rows = [
            {
                "College": r["college"],
                "Branch": r["branch"],
                "Historical Cutoff": r["historical_cutoff"],
                "Rank Difference": r["rank_difference"],
                "Likelihood Range": r["likelihood_range"],
                "Median CTC": r["median_ctc"]
            }
            for r in rows
        ]
        explanation = (
            f"These programmes are your **Likely options** (estimated likelihood `50% - 75%`). Your rank **#{rank:,}** is within "
            "competitive striking distance of historical closing ranks."
        )
        res = StructuredQueryResult(
            query_type=intent,
            title=f"Likely Strategic Targets for Rank #{rank:,} ({category})",
            columns=columns,
            rows=table_rows,
            disclaimer=DISCLAIMER_TEXT
        )
        return explanation, res

    elif intent == "ASPIRATIONAL_OPTIONS":
        rows = filter_and_evaluate_admission(rank, category, programs, tier_filter="Aspirational")
        columns = ["College", "Branch", "Historical Cutoff", "Rank Difference", "Likelihood Range", "Median CTC"]
        table_rows = [
            {
                "College": r["college"],
                "Branch": r["branch"],
                "Historical Cutoff": r["historical_cutoff"],
                "Rank Difference": r["rank_difference"],
                "Likelihood Range": r["likelihood_range"],
                "Median CTC": r["median_ctc"]
            }
            for r in rows
        ]
        explanation = (
            f"These are your **Aspirational reach options** (likelihood `20% - 40%`). While your rank **#{rank:,}** is numerically higher than "
            "2024 closing ranks, seat vacancies in later sliding or spot rounds could make an admission possible."
        )
        res = StructuredQueryResult(
            query_type=intent,
            title=f"Aspirational Dream Choices for Rank #{rank:,} ({category})",
            columns=columns,
            rows=table_rows,
            disclaimer=DISCLAIMER_TEXT
        )
        return explanation, res

    elif intent == "BRANCH_CSE":
        rows = filter_and_evaluate_admission(rank, category, programs, branch_keyword="CSE")
        columns = ["College", "Branch", "Historical Cutoff", "Rank Difference", "Likelihood Range", "Tier", "Median CTC"]
        table_rows = [
            {
                "College": r["college"],
                "Branch": r["branch"],
                "Historical Cutoff": r["historical_cutoff"],
                "Rank Difference": r["rank_difference"],
                "Likelihood Range": r["likelihood_range"],
                "Tier": r["tier"],
                "Median CTC": r["median_ctc"]
            }
            for r in rows
        ]
        explanation = (
            f"Here is your Computer Science and Engineering (CSE / IT) eligibility evaluation for rank **#{rank:,}** ({category}). "
            "Computer Science is consistently the most competitive branch across all counselling rounds."
        )
        res = StructuredQueryResult(
            query_type=intent,
            title=f"Computer Science (CSE) Possibilities for Rank #{rank:,}",
            columns=columns,
            rows=table_rows,
            disclaimer=DISCLAIMER_TEXT
        )
        return explanation, res

    elif intent == "AI_CURRICULUM":
        matches = find_programmes_matching_interests(student, programs, focus_keyword="Artificial Intelligence")
        top_matches = matches[:6]
        columns = ["College", "Branch", "AI/ML Relevance", "Curriculum Focus", "Curriculum Fit Score", "Median CTC"]
        table_rows = [
            {
                "College": m["college"],
                "Branch": m["branch"],
                "AI/ML Relevance": m["ai_ml_relevance"],
                "Curriculum Focus": m["curriculum_focus"],
                "Curriculum Fit Score": m["curriculum_fit_score"],
                "Median CTC": m["median_ctc"]
            }
            for m in top_matches
        ]
        mismatch_note = next((m["mismatch_warning"] for m in top_matches if m.get("mismatch_warning")), None)
        explanation = (
            "Programmes with the strongest curriculum alignment in Artificial Intelligence, Machine Learning, and Data Systems "
            "are listed below. PES University (specialized AI degree) and IIIT Hyderabad (NLP/Vision research culture) lead the index."
        )
        res = StructuredQueryResult(
            query_type=intent,
            title="Top Programmes for Artificial Intelligence & Machine Learning",
            columns=columns,
            rows=table_rows,
            disclaimer=DISCLAIMER_TEXT,
            mismatch_warning=mismatch_note
        )
        return explanation, res

    elif intent == "PLACEMENTS_COMPARE":
        rows = get_placement_comparison(programs)[:7]
        columns = ["College", "Branch", "Median CTC", "Placement Rate", "Top Recruiters", "Key Domains"]
        table_rows = [
            {
                "College": r["college"],
                "Branch": r["branch"],
                "Median CTC": r["median_ctc"],
                "Placement Rate": r["placement_rate"],
                "Top Recruiters": r["top_recruiters"],
                "Key Domains": r["career_domains"]
            }
            for r in rows
        ]
        explanation = (
            "Here is the verified placement and salary comparison across programmes, sorted by median CTC. "
            "IIT Bombay CSE, IIIT Hyderabad CSE, and IIT Delhi Mathematics & Computing lead in recruitment compensation."
        )
        res = StructuredQueryResult(
            query_type=intent,
            title="Comparative Placement Outcomes (Median CTC & Rates)",
            columns=columns,
            rows=table_rows,
            disclaimer=DISCLAIMER_TEXT
        )
        return explanation, res

    elif intent == "JOB_ROLES":
        rows = get_job_roles_information(programs)[:7]
        columns = ["College", "Branch", "Typical Roles", "Median CTC", "Key Recruiters"]
        table_rows = [
            {
                "College": r["college"],
                "Branch": r["branch"],
                "Typical Roles": r["typical_roles"],
                "Median CTC": r["median_ctc"],
                "Key Recruiters": r["key_recruiters"]
            }
            for r in rows
        ]
        explanation = (
            "Below are verified typical job profiles and roles that graduates from each programme step into, "
            "spanning Software Development, AI/ML Engineering, Quantitative Analytics, and Core Hardware."
        )
        res = StructuredQueryResult(
            query_type=intent,
            title="Typical Graduate Roles & Career Profiles",
            columns=columns,
            rows=table_rows,
            disclaimer=DISCLAIMER_TEXT
        )
        return explanation, res

    elif intent == "FEES_INQUIRY":
        rows = get_fees_information(programs)[:8]
        columns = ["College", "Branch", "Type", "Annual Tuition Fee", "Hostel Available", "Annual Hostel Fee", "Location"]
        table_rows = [
            {
                "College": r["college"],
                "Branch": r["branch"],
                "Type": r["type"],
                "Annual Tuition Fee": r["annual_tuition_fee"],
                "Hostel Available": r["hostel_available"],
                "Annual Hostel Fee": r["annual_hostel_fee"],
                "Location": r["location"]
            }
            for r in rows
        ]
        explanation = (
            "Here is the factual fee schedule for relevant institutions. Government and National Institutes (NITs, IITs, State Universities) "
            "offer highly subsidized tuition compared to private universities, and Jadavpur University offers exceptional ROI."
        )
        res = StructuredQueryResult(
            query_type=intent,
            title="Annual Tuition and Hostel Fee Comparison",
            columns=columns,
            rows=table_rows,
            disclaimer="Fee structures are indicative based on 2024 academic year announcements and exclude refundable caution deposits."
        )
        return explanation, res

    elif intent == "SCHOLARSHIPS":
        rows = get_scholarships_information(programs)[:7]
        columns = ["College", "Branch", "Type", "Scholarship & Fee Remission Schemes", "Annual Tuition"]
        table_rows = [
            {
                "College": r["college"],
                "Branch": r["branch"],
                "Type": r["type"],
                "Scholarship & Fee Remission Schemes": r["scholarships"],
                "Annual Tuition": r["annual_tuition_fee"]
            }
            for r in rows
        ]
        explanation = (
            "Verified scholarship and fee waiver guidelines. All central NITs and IITs offer 100% tuition remission "
            "for SC/ST students and candidates with annual family income below ₹1 Lakh, and 66% remission for income between ₹1-5 Lakhs."
        )
        res = StructuredQueryResult(
            query_type=intent,
            title="Official Scholarship Schemes and Fee Remissions",
            columns=columns,
            rows=table_rows,
            disclaimer="Verify eligibility certificates with the respective institute financial aid office during document verification."
        )
        return explanation, res

    elif intent == "HOSTEL_INQUIRY":
        rows = get_hostel_information(programs)[:8]
        columns = ["College", "Location", "Hostel Available", "Annual Hostel & Mess Fee"]
        table_rows = [
            {
                "College": r["college"],
                "Location": r["location"],
                "Hostel Available": r["hostel_available"],
                "Annual Hostel & Mess Fee": r["hostel_fee"]
            }
            for r in rows
        ]
        explanation = (
            "Hostel and accommodation details for colleges on your sheet. All premier residential institutes (IITs, NITs, BITS) "
            "provide mandatory/guaranteed on-campus accommodation with mess facilities."
        )
        res = StructuredQueryResult(
            query_type=intent,
            title="Hostel Accommodation and Living Costs",
            columns=columns,
            rows=table_rows,
            disclaimer="Hostel allotment is generally confirmed upon payment of the semester seat acceptance fee."
        )
        return explanation, res

    elif intent == "LOCATION_INQUIRY":
        rows = get_location_information(programs)[:8]
        columns = ["College", "Type", "Location"]
        table_rows = [
            {
                "College": r["college"],
                "Type": r["type"],
                "Location": r["location"]
            }
            for r in rows
        ]
        explanation = (
            "Campus geographic locations. Proximity to tech clusters (like Bengaluru, Delhi-NCR, Hyderabad) provides "
            "distinct advantages for in-semester internships, meetups, and local industry networking."
        )
        res = StructuredQueryResult(
            query_type=intent,
            title="College Campus Locations",
            columns=columns,
            rows=table_rows,
            disclaimer="Review travel connectivity and climate preferences when ordering your choices."
        )
        return explanation, res

    elif intent == "WHY_FIRST_RANK":
        rec_res = generate_recommendations(student)
        top_pref = rec_res.preferences[0] if rec_res.preferences else None
        if not top_pref:
            return "No recommendation list has been generated yet.", None

        explanation = (
            f"**{top_pref.program.college_name} - {top_pref.program.branch_name}** is ranked #1 on your strategic preference list "
            f"because it maximizes your composite score ({top_pref.composite_score}/100).\n\n"
            f"1. **Strategic Feasibility ({top_pref.tier.value} Tier)**: At rank #{rank:,}, you have a {top_pref.likelihood_range} admission likelihood range "
            f"relative to its historical closing rank of {top_pref.program.category_cutoffs.get(category, top_pref.program.category_cutoffs['General']).closing_rank:,}.\n"
            f"2. **Curriculum & Passion Fit**: Matches your interests in {', '.join(top_pref.interest_alignment_tags)}.\n"
            f"3. **Career & Placement Outcomes**: 95%+ placement rate with a median CTC of ₹{top_pref.program.placement_stats.median_salary_lpa} LPA "
            f"and top recruiters ({', '.join(top_pref.program.placement_stats.top_recruiters[:3])})."
        )
        columns = ["Preference #", "College", "Branch", "Tier", "Likelihood Range", "Strategy Score", "Median CTC"]
        table_rows = [{
            "Preference #": "#1",
            "College": top_pref.program.college_name,
            "Branch": top_pref.program.branch_name,
            "Tier": top_pref.tier.value,
            "Likelihood Range": top_pref.likelihood_range,
            "Strategy Score": f"{top_pref.composite_score} / 100",
            "Median CTC": f"₹{top_pref.program.placement_stats.median_salary_lpa} LPA"
        }]
        res = StructuredQueryResult(
            query_type=intent,
            title="Reasoning for #1 Preference Allocation",
            columns=columns,
            rows=table_rows,
            disclaimer=DISCLAIMER_TEXT
        )
        return explanation, res

    elif intent == "HIGHER_STUDIES":
        rows = get_higher_studies_information(programs)[:7]
        columns = ["College", "Branch", "Higher Study & Research Track Record", "Tier Rating"]
        table_rows = [
            {
                "College": r["college"],
                "Branch": r["branch"],
                "Higher Study & Research Track Record": r["higher_studies"],
                "Tier Rating": r["tier"]
            }
            for r in rows
        ]
        explanation = (
            "Higher studies and international graduate school admit records. Premier institutes (IIT Bombay, IIT Delhi, IIIT Hyderabad) "
            "have dedicated research labs and strong faculty recommendation letters leading to direct PhD/MS admissions in the US and Europe."
        )
        res = StructuredQueryResult(
            query_type=intent,
            title="Graduate Studies and Academic Research Opportunities",
            columns=columns,
            rows=table_rows,
            disclaimer="Graduate admissions depend directly on undergraduate CGPA, research publications, and GRE/TOEFL scores."
        )
        return explanation, res

    elif intent == "ENTREPRENEURSHIP":
        rows = get_entrepreneurship_information(programs)[:7]
        columns = ["College", "Branch", "Campus Startup & Incubation Ecosystem"]
        table_rows = [
            {
                "College": r["college"],
                "Branch": r["branch"],
                "Campus Startup & Incubation Ecosystem": r["entrepreneurship_support"]
            }
            for r in rows
        ]
        explanation = (
            "Entrepreneurship support, incubation facilities, and student venture funding across campuses. "
            "IIT Madras Research Park, IIIT Hyderabad CIE, and SINE at IIT Bombay lead in university startup creation."
        )
        res = StructuredQueryResult(
            query_type=intent,
            title="Campus Entrepreneurship and Incubation Support",
            columns=columns,
            rows=table_rows,
            disclaimer="Seed funding amounts and incubation space depend on annual faculty and investor committee evaluations."
        )
        return explanation, res

    elif intent == "PREFERENCE_LIST":
        rec_res = generate_recommendations(student)
        columns = ["Preference #", "College", "Branch", "Tier", "Likelihood Range", "Strategy Score", "Median CTC"]
        table_rows = [
            {
                "Preference #": f"#{idx}",
                "College": p.program.college_name,
                "Branch": p.program.branch_name,
                "Tier": p.tier.value,
                "Likelihood Range": p.likelihood_range,
                "Strategy Score": f"{p.composite_score} / 100",
                "Median CTC": f"₹{p.program.placement_stats.median_salary_lpa} LPA"
            }
            for idx, p in enumerate(rec_res.preferences, 1)
        ]
        explanation = (
            f"Here is your balanced counselling preference list for rank **#{rank:,}** ({category}). "
            "It strategically sequences Aspirational reach programs at the top, high-probability Likely programs in the middle, "
            "and secure Safe programs at the base."
        )
        res = StructuredQueryResult(
            query_type=intent,
            title=f"Strategic Choice Filling Preference Sheet for Rank #{rank:,}",
            columns=columns,
            rows=table_rows,
            disclaimer=DISCLAIMER_TEXT
        )
        return explanation, res

    return "", None
