from __future__ import annotations

TARGET_INDUSTRIES = [
    "AI",
    "Fintech",
    "Startup",
    "SaaS",
    "HR",
    "Marketing",
    "Recruiting",
]

TARGET_PERSONAS = [
    "Founder",
    "CTO",
    "HR Manager",
    "Recruiter",
    "Sales Director",
    "Marketing Lead",
]

INDUSTRY_KEYWORDS = {
    "AI": ["ai", "machine learning", "llm", "agents", "genai", "artificial intelligence"],
    "Fintech": ["fintech", "payments", "banking", "wallet", "lending", "fraud"],
    "Startup": ["startup", "founder", "product-market fit", "fundraising", "bootstrapped"],
    "SaaS": ["saas", "b2b", "subscription", "customer success", "retention"],
    "HR": ["hr", "talent", "hiring", "people ops", "employee experience"],
    "Marketing": ["marketing", "growth", "brand", "content", "demand gen"],
    "Recruiting": ["recruiting", "recruiter", "headhunt", "sourcing", "talent acquisition"],
}

PERSONA_KEYWORDS = {
    "Founder": ["founder", "ceo", "cofounder", "entrepreneur"],
    "CTO": ["cto", "engineering", "technical", "developer", "platform"],
    "HR Manager": ["hr", "people", "talent", "employee", "hr manager"],
    "Recruiter": ["recruiter", "talent acquisition", "sourcing", "headhunter"],
    "Sales Director": ["sales", "revenue", "pipeline", "go-to-market"],
    "Marketing Lead": ["marketing", "growth", "demand gen", "brand", "content"],
}

SPEAKER_QUALITY_KEYWORDS = ["vp", "head of", "founder", "cto", "ceo", "director", "manager"]
