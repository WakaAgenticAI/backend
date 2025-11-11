from __future__ import annotations
from typing import Any, List
from decimal import Decimal

from sqlalchemy.orm import Session

from app.agents.orchestrator import Agent
from app.db.session import SessionLocal
from app.services.debt_service import (
    list_debts, get_debt_summary, get_debt_aging_report,
    DebtNotFound
)
from app.schemas.debts import DebtOut, DebtSummary, DebtAgingReport


class FinanceAgent(Agent):
    name = "finance"
    description = "Handles financial operations including debt management, reports, and collections"
    tools = ["debt.list_overdue", "debt.generate_collection_plan", "debt.aging_report", "debt.summary"]

    async def can_handle(self, intent: str, payload: dict) -> bool:
        return intent.startswith("debt.") or intent in ["payment.process", "payment.refund", "report.generate"]

    async def handle(self, intent: str, payload: dict) -> dict:
        db: Session = SessionLocal()
        try:
            if intent == "debt.list_overdue":
                return await self._list_overdue_debts(db, payload)
            elif intent == "debt.generate_collection_plan":
                return await self._generate_collection_plan(db, payload)
            elif intent == "debt.aging_report":
                return await self._get_aging_report(db, payload)
            elif intent == "debt.summary":
                return await self._get_debt_summary(db, payload)
            else:
                return {"handled": False, "reason": "unknown_intent"}
        finally:
            db.close()

    async def _list_overdue_debts(self, db: Session, payload: dict) -> dict:
        """List overdue debts with collection insights."""
        try:
            debts = list_debts(
                db=db,
                status_filter="overdue",
                limit=int(payload.get("limit", 50))
            )

            # Add collection insights
            insights = []
            for debt in debts:
                insight = {
                    "debt_id": debt.id,
                    "amount": str(debt.amount_ngn),
                    "entity": f"{debt.entity_type} {debt.entity_id or ''}".strip(),
                    "days_overdue": self._calculate_days_overdue(debt.due_date),
                    "priority": debt.priority,
                    "recommendation": self._get_collection_recommendation(debt)
                }
                insights.append(insight)

            return {
                "handled": True,
                "result": {
                    "overdue_count": len(debts),
                    "total_overdue_amount": str(sum(Decimal(d.amount_ngn) for d in debts)),
                    "insights": insights
                }
            }
        except Exception as e:
            return {"handled": False, "reason": str(e)}

    async def _generate_collection_plan(self, db: Session, payload: dict) -> dict:
        """Generate a collection plan for overdue debts."""
        try:
            summary = get_debt_summary(db)
            aging = get_debt_aging_report(db)

            plan = {
                "immediate_actions": [],
                "follow_up_actions": [],
                "long_term_strategies": []
            }

            # Immediate actions for critical overdue debts
            if aging.range_90_plus > 0:
                plan["immediate_actions"].append({
                    "action": "Contact customers with 90+ day overdue debts",
                    "count": aging.range_90_plus,
                    "amount": str(aging.total_overdue_amount),
                    "priority": "high"
                })

            # Follow-up actions
            if summary.overdue_receivables > 0:
                plan["follow_up_actions"].append({
                    "action": "Send payment reminders via email/SMS",
                    "target": "overdue_receivables",
                    "count": summary.overdue_receivables,
                    "priority": "medium"
                })

            # Long-term strategies
            plan["long_term_strategies"] = [
                "Implement automated payment reminders",
                "Offer payment plans for large overdue amounts",
                "Review credit terms for high-risk customers",
                "Set up regular debt aging reviews"
            ]

            return {
                "handled": True,
                "result": {
                    "collection_plan": plan,
                    "summary": {
                        "receivables": str(summary.receivables_total),
                        "payables": str(summary.payables_total),
                        "overdue_receivables": summary.overdue_receivables,
                        "overdue_payables": summary.overdue_payables
                    }
                }
            }
        except Exception as e:
            return {"handled": False, "reason": str(e)}

    async def _get_aging_report(self, db: Session, payload: dict) -> dict:
        """Get debt aging analysis."""
        try:
            aging = get_debt_aging_report(db)

            analysis = {
                "risk_assessment": "low" if aging.range_0_30 > aging.range_90_plus else "high",
                "collection_efficiency": "good" if aging.range_0_30 < aging.range_31_60 else "needs_improvement",
                "recommendations": []
            }

            if aging.range_90_plus > 0:
                analysis["recommendations"].append("Focus collection efforts on 90+ day overdue debts")

            if aging.range_31_60 > aging.range_0_30:
                analysis["recommendations"].append("Improve early-stage collection processes")

            return {
                "handled": True,
                "result": {
                    "aging_report": {
                        "0_30_days": aging.range_0_30,
                        "31_60_days": aging.range_31_60,
                        "61_90_days": aging.range_61_90,
                        "90_plus_days": aging.range_90_plus,
                        "total_overdue_amount": str(aging.total_overdue_amount)
                    },
                    "analysis": analysis
                }
            }
        except Exception as e:
            return {"handled": False, "reason": str(e)}

    async def _get_debt_summary(self, db: Session, payload: dict) -> dict:
        """Get overall debt summary with insights."""
        try:
            summary = get_debt_summary(db)

            insights = []
            if summary.overdue_receivables > 0:
                insights.append(f"{summary.overdue_receivables} overdue receivables need attention")

            if summary.payables_total > summary.receivables_total:
                insights.append("Payables exceed receivables - monitor cash flow")

            return {
                "handled": True,
                "result": {
                    "summary": {
                        "receivables_total": str(summary.receivables_total),
                        "payables_total": str(summary.payables_total),
                        "receivables_count": summary.receivables_count,
                        "payables_count": summary.payables_count,
                        "overdue_receivables": summary.overdue_receivables,
                        "overdue_payables": summary.overdue_payables
                    },
                    "insights": insights
                }
            }
        except Exception as e:
            return {"handled": False, "reason": str(e)}

    def _calculate_days_overdue(self, due_date: str | None) -> int:
        """Calculate days overdue from due date."""
        if not due_date:
            return 0
        from datetime import date
        due = date.fromisoformat(due_date)
        today = date.today()
        return max(0, (today - due).days)

    def _get_collection_recommendation(self, debt: DebtOut) -> str:
        """Generate collection recommendation based on debt details."""
        days_overdue = self._calculate_days_overdue(debt.due_date)

        if days_overdue > 90:
            return "Escalate to collections/legal action"
        elif days_overdue > 60:
            return "Send formal demand letter"
        elif days_overdue > 30:
            return "Call customer for payment arrangement"
        else:
            return "Send friendly payment reminder"
