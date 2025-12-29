"""
Validate auto financing assignment
Async version migrated from Flask app/loan/utils/_validate_auto_financing_assignment.py
"""
from typing import Dict, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import logging

from app.apps.loan.models import Solicitud
from app.apps.authentication.models import User
from app.apps.advisor.models import Role

logger = logging.getLogger(__name__)


async def validate_auto_financing_assignment(
    solicitud: Solicitud, 
    combined_banks: List[Dict],
    session: AsyncSession
) -> Dict:
    """
    Validate if the credit record is bad and recommend assignment to auto financing.
    
    This function implements the following business rule:
    - For each bank in the target list (bank_id 1,2,3,4,8,9), check if it's "denied"
    - A bank is "denied" if it has either comportamiento_mop1 OR quitas as "Rechazado"
    - If ALL target banks are denied, then recommend assignment to auto financing (finva_agent_zae role)
    - This function now only validates and returns recommendation, it does NOT perform the assignment
    
    Bank IDs mapping:
    - 1: BBVA
    - 2: Santander
    - 3: Hey
    - 4: Banregio
    - 8: Afirme
    - 9: Creditogo
    
    Args:
        solicitud: The solicitud object to evaluate
        combined_banks: List of combined bank data with evaluations
        session: Async database session
    
    Returns:
        Dict with 'assigned' boolean, 'message' string, and recommendation details
    """
    try:
        # Check if solicitud is already assigned to user with role finva_agent_zae
        # TODO: Fetch finva_user relationship if needed
        # For now, skip this check as it requires relationship loading
        
        # Define target bank IDs for evaluation
        target_bank_ids = [1, 2, 3, 4, 8, 9]

        logger.info(f"Combined banks structure for solicitud {solicitud.id}:")
        logger.info(f"  - Total combined banks: {len(combined_banks)}")
        for i, bank in enumerate(combined_banks[:3]):  # Log first 3 banks for debugging
            logger.info(f"  - Bank {i}: {bank}")

        # Filter banks to only include target bank IDs
        target_banks = [
            bank for bank in combined_banks if bank.get("bank_id") in target_bank_ids
        ]

        if not target_banks:
            logger.warning(f"No target banks found for solicitud {solicitud.id}")
            return {
                "assigned": False,
                "message": "No target banks found for evaluation",
            }

        logger.info(f"Evaluating {len(target_banks)} target banks for solicitud {solicitud.id}")

        # Check if each bank is denied (has either comportamiento_mop1 OR quitas as "Rechazado")
        denied_banks = []
        for bank in target_banks:
            bank_id = bank.get("bank_id")
            bank_name = bank.get("bank_name", f"Bank {bank_id}")

            mop1_status = bank.get("comportamiento_mop1")
            quitas_status = bank.get("quitas")

            # A bank is denied if either comportamiento_mop1 OR quitas is "Rechazado"
            is_denied = (mop1_status == "Rechazado") or (quitas_status == "Rechazado")

            denied_banks.append(
                {
                    "bank_id": bank_id,
                    "bank_name": bank_name,
                    "is_denied": is_denied,
                    "mop1_status": mop1_status,
                    "quitas_status": quitas_status,
                }
            )

            logger.info(
                f"Bank {bank_name} (ID: {bank_id}): MOP1={mop1_status}, Quitas={quitas_status}, Denied={is_denied}"
            )

        # Check if ALL banks are denied - handle empty list case
        all_banks_denied = len(denied_banks) > 0 and all(
            bank["is_denied"] for bank in denied_banks
        )

        # Log evaluation results
        logger.info(f"Solicitud {solicitud.id} evaluation:")
        logger.info(f"  - Total target banks: {len(target_banks)}")
        logger.info(f"  - Denied banks count: {len(denied_banks)}")
        if denied_banks:
            logger.info(
                f"  - Denied banks: {sum(1 for bank in denied_banks if bank['is_denied'])}"
            )
        else:
            logger.warning("  - No denied banks found (empty list)")
        logger.info(f"  - All banks denied: {all_banks_denied}")

        # Determine if assignment should be recommended
        should_recommend_assign = all_banks_denied

        if should_recommend_assign:
            # Get the next finva_agent_zae for recommendation
            # First, get the role
            stmt_role = select(Role).where(Role.name == "finva_agent_zae")
            result_role = await session.execute(stmt_role)
            role = result_role.scalar_one_or_none()

            if not role:
                logger.warning("No finva_agent_zae role found")
                return {
                    "assigned": False,
                    "message": "No finva_agent_zae role available",
                    "recommend_reassign": False,
                }

            # Get all finva_agent_zae advisors
            stmt_advisors = select(User).where(User.role_id == role.id)
            result_advisors = await session.execute(stmt_advisors)
            all_finva_advisors = result_advisors.scalars().all()
            finva_advisor_ids = [adv.id for adv in all_finva_advisors]

            if not finva_advisor_ids:
                logger.warning("No finva_agent_zae advisors found")
                return {
                    "assigned": False,
                    "message": "No finva_agent_zae advisors available",
                    "recommend_reassign": False,
                }

            # Get advisors ordered by last_selected_at (NULL first), then by ID
            # Note: This assumes User model has last_selected_at and is_selected fields
            # TODO: Implement proper ordering if these fields exist
            next_finva_agent_zae = all_finva_advisors[0] if all_finva_advisors else None

            if not next_finva_agent_zae:
                logger.warning("No finva_agent_zae advisor available")
                return {
                    "assigned": False,
                    "message": "No finva_agent_zae advisor available",
                    "recommend_reassign": False,
                }

            logger.info(
                f"Solicitud {solicitud.id} meets criteria for auto financing assignment recommendation"
            )

            return {
                "assigned": False,
                "message": "Solicitud meets criteria for auto financing assignment due to bad credit score and history",
                "recommend_reassign": True,
                "recommended_user_id": next_finva_agent_zae.id,
                "recommended_user_name": f"{next_finva_agent_zae.name} {next_finva_agent_zae.first_last_name}".strip() if hasattr(next_finva_agent_zae, 'first_last_name') else next_finva_agent_zae.name,
                "reason": "All target banks (BBVA, Santander, Hey, Banregio, Afirme, Creditogo) have been denied due to bad credit score and history",
                "denied_banks": [
                    bank["bank_name"] for bank in denied_banks if bank["is_denied"]
                ],
            }
        else:
            logger.info(
                f"Solicitud {solicitud.id} does not meet criteria for auto financing assignment"
            )
            return {
                "assigned": False,
                "message": "Solicitud does not meet criteria for auto financing",
                "recommend_reassign": False,
            }

    except Exception as e:
        logger.error(
            f"Error validating auto financing assignment for solicitud {solicitud.id}: {str(e)}",
            exc_info=True
        )
        return {"assigned": False, "message": f"Error during validation: {str(e)}"}


