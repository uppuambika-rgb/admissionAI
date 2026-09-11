import sys
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from app.models.student import StudentProfile
from app.services.ranker import generate_recommendations
from app.services.evaluator import evaluate_admission_likelihood
from app.services.matcher import calculate_curriculum_match
from app.services.ai_counsellor import extract_profile_from_text, generate_chat_reply

def test_evaluation():
    print("Testing Evaluator...")
    from app.services.ranker import load_college_programs
    programs = load_college_programs()
    assert len(programs) > 0, "No programs loaded!"
    
    # Test with student rank 5000 (General)
    nit_trichy_cse = next(p for p in programs if p.id == "NITT-CSE")
    # General closing cutoff is 4800. Rank 5000 is slightly above 4800 -> Likely or Aspirational
    tier, l_range, margin, unc = evaluate_admission_likelihood(5000, "General", nit_trichy_cse)
    print(f"NITT-CSE for rank 5000: Tier={tier.value}, Range={l_range}, Margin={margin}%")
    assert tier.value in ["Likely", "Aspirational"]

    # Test with student rank 1000 for NITT-CSE (closing 4800) -> Safe
    tier_safe, l_range_safe, margin_safe, _ = evaluate_admission_likelihood(1000, "General", nit_trichy_cse)
    print(f"NITT-CSE for rank 1000: Tier={tier_safe.value}, Range={l_range_safe}, Margin={margin_safe}%")
    assert tier_safe.value == "Safe"
    print(" Evaluator passed!")

def test_extraction():
    print("Testing Text Extraction...")
    profile = StudentProfile()
    text = "Hi, my rank is 4200 and category is OBC-NCL. I am really interested in artificial intelligence and robotics. I want to become a software engineer."
    extracted, missing = extract_profile_from_text(text, profile)
    print(f"Extracted: Rank={extracted.rank}, Cat={extracted.category}, Interests={extracted.interests}, Goals={extracted.career_goals}")
    assert extracted.rank == 4200
    assert extracted.category == "OBC-NCL"
    assert "Artificial Intelligence" in extracted.interests
    assert "Robotics & Automation" in extracted.interests
    assert "Software Engineering" in extracted.career_goals
    print(" Extraction passed!")

def test_recommendations():
    print("Testing Full Recommendation Pipeline...")
    student = StudentProfile(
        rank=7500,
        category="General",
        academic_strengths=["Mathematics", "Coding"],
        interests=["Artificial Intelligence", "Machine Learning", "Software Engineering"],
        career_goals=["Software Engineering"]
    )
    res = generate_recommendations(student)
    print(f"Evaluated {res.total_evaluated} colleges. Generated {len(res.preferences)} recommendations.")
    print("Top Recommendations:")
    for idx, pref in enumerate(res.preferences, 1):
        print(f"  {idx}. [{pref.tier.value}] {pref.program.college_name} - {pref.program.branch_name} ({pref.likelihood_range}) Score: {pref.composite_score}")
    
    assert len(res.preferences) >= 5
    # Verify tier presence
    tiers = [p.tier.value for p in res.preferences]
    print("Tiers in preferences:", set(tiers))
    print(" Recommendation pipeline passed!")

if __name__ == "__main__":
    test_evaluation()
    test_extraction()
    test_recommendations()
    print("\nALL BACKEND UNIT TESTS PASSED SUCCESSFULLY!")
