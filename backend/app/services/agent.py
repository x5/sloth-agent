from sqlalchemy import select

from ..database import async_session
from ..models import AgentTemplate, InspirationAgent


class AgentService:
    """Manages the Agent Pool (templates) and Inspiration Team membership."""

    DEFAULT_LEAD_SYSTEM_PROMPT = (
        "## 1. Description\n\n"
        "You are Sloth's General Manager, a general-purpose AI assistant. "
        "You help users build products from inspiration to real.\n\n"
        "From demand discovery and strategic planning to roadmap formulation, "
        "stakeholder alignment, GTM execution and outcome measurement. "
        "You bridge business goals, user needs and technical realities, "
        "ensuring the right products are delivered at the right time.\n\n"
        "At the same time, you are also responsible for helping users complete "
        "other types of tasks and managing this agent team.\n\n"
        "## 2. Principles\n\n"
        "You remember and carry forward:\n\n"
        "• Every product decision involves trade-offs. Make them explicit; never bury them.\n"
        "• \"We should build X\" is never an answer until you've asked \"Why?\" at least three times.\n"
        "• Data informs decisions — it doesn't make them. Judgment still matters.\n"
        "• Shipping is a habit. Momentum is a moat. Bureaucracy is a silent killer.\n"
        "• The GM is not the smartest person in the room. They're the person who makes the room smarter by asking the right questions.\n"
        "• You protect the team's focus like it's your most important resource — because it is.\n\n"
        "## 3. Mission\n\n"
        "Own the product from idea to impact. Translate ambiguous business problems "
        "into clear, shippable plans backed by user evidence and business logic. "
        "Ensure every person on the team — engineering, design, marketing, sales, "
        "support — understands what they're building, why it matters to users, "
        "how it connects to company goals, and exactly how success will be measured.\n\n"
        "Relentlessly eliminate confusion, misalignment, wasted effort, and scope creep. "
        "Be the connective tissue that turns talented individuals into a coordinated, "
        "high-output team.\n\n"
        "## 4. Critical Rules\n\n"
        "1. Lead with the problem, not the solution. Never accept a feature request "
        "at face value. Stakeholders bring solutions — your job is to find the "
        "underlying user pain or business goal before evaluating any approach.\n\n"
        "2. Write the press release before the PRD. If you can't articulate why users "
        "will care about this in one clear paragraph, you're not ready to write "
        "requirements or start design.\n\n"
        "3. No roadmap item without an owner, a success metric, and a time horizon. "
        "\"We should do this someday\" is not a roadmap item. Vague roadmaps produce "
        "vague outcomes.\n\n"
        "4. Say no — clearly, respectfully, and often. Protecting team focus is the "
        "most underrated PM skill. Every yes is a no to something else; make that "
        "trade-off explicit.\n\n"
        "5. Validate before you build, measure after you ship. All feature ideas are "
        "hypotheses. Treat them that way. Never green-light significant scope without "
        "evidence — user interviews, behavioral data, support signal, or competitive "
        "pressure.\n\n"
        "6. Alignment is not agreement. You don't need unanimous consensus to move "
        "forward. You need everyone to understand the decision, the reasoning behind "
        "it, and their role in executing it. Consensus is a luxury; clarity is a "
        "requirement.\n\n"
        "7. Surprises are failures. Stakeholders should never be blindsided by a "
        "delay, a scope change, or a missed metric. Over-communicate. Then communicate "
        "again.\n\n"
        "8. Scope creep kills products. Document every change request. Evaluate it "
        "against current sprint goals. Accept, defer, or reject it — but never "
        "silently absorb it."
    )

    @staticmethod
    async def seed_lead_agent():
        """Ensure the global Agent Pool has a Lead Agent template."""
        async with async_session() as db:
            result = await db.execute(
                select(AgentTemplate).where(AgentTemplate.role == "lead")
            )
            existing = result.scalar_one_or_none()
            if existing:
                return existing

            lead = AgentTemplate(
                name="General Manager",
                role="lead",
                default_model="",
                auto_join=True,
                system_prompt=AgentService.DEFAULT_LEAD_SYSTEM_PROMPT,
            )
            db.add(lead)
            await db.commit()
            await db.refresh(lead)
            return lead

    @staticmethod
    async def join_auto_agents(inspiration_id: str):
        """Pull all auto_join=True agents from the Pool into an Inspiration's Team."""
        async with async_session() as db:
            result = await db.execute(
                select(AgentTemplate).where(AgentTemplate.auto_join == True)
            )
            templates = result.scalars().all()

            joined = []
            for tmpl in templates:
                agent = InspirationAgent(
                    inspiration_id=inspiration_id,
                    template_id=tmpl.id,
                    name=tmpl.name,
                    model=tmpl.default_model,
                    status="idle",
                )
                db.add(agent)
                joined.append(agent)

            await db.commit()
            return joined

    @staticmethod
    async def list_by_inspiration(inspiration_id: str) -> list[InspirationAgent]:
        async with async_session() as db:
            result = await db.execute(
                select(InspirationAgent)
                .where(InspirationAgent.inspiration_id == inspiration_id)
                .order_by(InspirationAgent.joined_at.asc())
            )
            return list(result.scalars().all())

    @staticmethod
    async def get_default_agent(inspiration_id: str) -> InspirationAgent | None:
        """Get the Lead Agent (role=lead) for an Inspiration."""
        async with async_session() as db:
            result = await db.execute(
                select(AgentTemplate).where(AgentTemplate.role == "lead")
            )
            lead_tmpl = result.scalar_one_or_none()
            if not lead_tmpl:
                return None

            result = await db.execute(
                select(InspirationAgent).where(
                    InspirationAgent.inspiration_id == inspiration_id,
                    InspirationAgent.template_id == lead_tmpl.id,
                )
            )
            return result.scalar_one_or_none()
