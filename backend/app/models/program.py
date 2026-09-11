from enum import Enum
from typing import List, Dict, Optional
from pydantic import BaseModel, Field
from app.models.student import StudentProfile

class CategoryCutoff(BaseModel):
    opening_rank: int
    closing_rank: int

class PlacementStats(BaseModel):
    median_salary_lpa: float
    placement_percentage: float
    top_recruiters: List[str]
    key_career_domains: List[str] = Field(default_factory=list)

class CollegeProgram(BaseModel):
    id: str
    college_name: str
    branch_name: str
    college_type: str = Field(default="College", description="e.g. NIT, IIT, IIIT, State University, Private University")
    exam: str = Field(default="JEE Main", description="Accepted entrance exam")
    location: str
    tier_rating: str  # "Tier-1", "Tier-2"
    annual_tuition_fee_inr: Optional[int] = Field(default=None, description="Annual tuition fee in INR")
    hostel_available: bool = Field(default=True, description="Whether on-campus hostel is available")
    annual_hostel_fee_inr: Optional[int] = Field(default=None, description="Annual hostel and mess fee in INR")
    scholarships: Optional[str] = Field(default=None, description="Factual scholarship and fee-remission schemes")
    higher_study_opportunities: Optional[str] = Field(default=None, description="Higher studies & international admits profile")
    entrepreneurship_opportunities: Optional[str] = Field(default=None, description="Incubation and startup support")
    cutoff_year_round: str = Field(default="2024 (Round 6 Closing)", description="Year and round of historical cutoff benchmark")
    typical_roles: List[str] = Field(default_factory=list, description="Typical job profiles for graduates")
    category_cutoffs: Dict[str, CategoryCutoff]
    curriculum_keywords: List[str]
    placement_stats: PlacementStats
    admission_notes: Optional[str] = None

class LikelihoodTier(str, Enum):
    SAFE = "Safe"
    LIKELY = "Likely"
    ASPIRATIONAL = "Aspirational"
    REACH = "Reach"

class RecommendationItem(BaseModel):
    program: CollegeProgram
    tier: LikelihoodTier
    likelihood_range: str              # e.g., "75% - 90%"
    composite_score: float             # 0 to 100
    cutoff_margin_percent: float       # Percentage margin relative to closing rank
    interest_alignment_tags: List[str] # Matched keywords
    placement_score: float             # 0 to 100
    ai_explanation: str                # Humanized explanation
    uncertainty_note: str              # Realistic advisory disclaimer

class RecommendationResponse(BaseModel):
    student_profile: StudentProfile
    total_evaluated: int
    preferences: List[RecommendationItem]
    tier_summary: Dict[str, int]
    disclaimer: str
