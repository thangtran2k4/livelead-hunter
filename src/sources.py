from __future__ import annotations

from datetime import datetime, timezone

from .models import LiveEvent


def get_mock_events() -> list[LiveEvent]:
    return [
        LiveEvent(
            title="AI Agents for B2B Sales Teams",
            source="YouTube Live",
            url="https://youtube.com/live/ai-agents-sales",
            start_time=datetime(2026, 7, 3, 9, 0, tzinfo=timezone.utc),
            timezone="UTC",
            location="Online",
            description="A live session about AI agents, SDR automation, and lead qualification for revenue teams.",
            speakers=["Maria Chen, VP Sales", "Daniel Ho, Founder"],
            expected_size="500+",
            audience="Founders, Sales Leaders, RevOps",
            tags=["AI", "Sales", "SaaS"],
        ),
        LiveEvent(
            title="Hiring Engineers in a Competitive Market",
            source="LinkedIn Events",
            url="https://linkedin.com/events/hiring-engineers",
            start_time=datetime(2026, 7, 4, 11, 0, tzinfo=timezone.utc),
            timezone="UTC",
            location="Online",
            description="Practical tactics for recruiting engineering talent, employer branding, and interview process design.",
            speakers=["Alyssa Tran, Head of Talent", "Brian Lee, CTO"],
            expected_size="200-500",
            audience="HR, Recruiters, CTOs",
            tags=["HR", "Recruiting", "Startup"],
        ),
        LiveEvent(
            title="Fintech Compliance and Growth Webinar",
            source="Eventbrite",
            url="https://eventbrite.com/e/fintech-compliance-growth",
            start_time=datetime(2026, 7, 5, 13, 0, tzinfo=timezone.utc),
            timezone="UTC",
            location="Online",
            description="How fintech startups can balance compliance, trust, and rapid growth in 2026.",
            speakers=["Sophie Nguyen, Compliance Director", "Kevin Patel, Founder"],
            expected_size="100-200",
            audience="Founders, Fintech Teams",
            tags=["Fintech", "Startup"],
        ),
        LiveEvent(
            title="Startup Growth Marketing Clinic",
            source="Meetup",
            url="https://meetup.com/startup-growth-clinic",
            start_time=datetime(2026, 7, 6, 15, 0, tzinfo=timezone.utc),
            timezone="UTC",
            location="Online",
            description="A tactical live workshop on growth loops, content strategy, and demand generation for SaaS startups.",
            speakers=["Linh Pham, Marketing Lead", "Tom Alvarez, Founder"],
            expected_size="50-100",
            audience="Founders, Marketers, Operators",
            tags=["Marketing", "Startup", "SaaS"],
        ),
    ]
