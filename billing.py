"""
Stripe Billing Integration
Handles subscription management, invoicing, and payment processing
"""

import stripe
import os
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import and_

logger = logging.getLogger(__name__)

# Initialize Stripe
stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "sk_test_placeholder")


class StripeIntegration:
    """Handle all Stripe operations"""

    def __init__(self):
        self.api_version = "2023-10-16"

    async def create_customer(
        self,
        db: AsyncSession,
        organization_id: int,
        org_name: str,
        email: str
    ) -> Optional[str]:
        """
        Create Stripe customer for organization

        Returns: Stripe customer ID or None
        """
        try:
            customer = stripe.Customer.create(
                email=email,
                name=org_name,
                metadata={"organization_id": organization_id}
            )

            # Store Stripe ID in database
            from models import Organization
            org = await db.execute(
                select(Organization).where(Organization.id == organization_id)
            )
            org_obj = org.scalar_one_or_none()

            if org_obj:
                org_obj.stripe_customer_id = customer.id
                await db.commit()

            logger.info(f"Created Stripe customer {customer.id} for org {organization_id}")
            return customer.id

        except Exception as e:
            logger.error(f"Failed to create Stripe customer: {e}")
            return None

    async def create_subscription(
        self,
        db: AsyncSession,
        organization_id: int,
        tier_name: str,
        stripe_customer_id: str
    ) -> Optional[str]:
        """
        Create subscription for organization

        Returns: Stripe subscription ID or None
        """
        try:
            from models import SubscriptionTier, Subscription

            # Get tier pricing
            tier_result = await db.execute(
                select(SubscriptionTier).where(SubscriptionTier.name == tier_name)
            )
            tier = tier_result.scalar_one_or_none()

            if not tier:
                logger.error(f"Tier not found: {tier_name}")
                return None

            # Create Stripe subscription
            if tier.price_usd > 0:
                # For paid plans, create a subscription
                # In production, you'd use Stripe price IDs from dashboard
                subscription = stripe.Subscription.create(
                    customer=stripe_customer_id,
                    items=[{
                        "price_data": {
                            "currency": "usd",
                            "unit_amount": tier.price_usd * 100,  # Convert to cents
                            "recurring": {"interval": "month"},
                            "product_data": {"name": f"{tier_name.upper()} Plan"}
                        }
                    }],
                    metadata={
                        "organization_id": organization_id,
                        "tier_name": tier_name
                    }
                )

                stripe_subscription_id = subscription.id
            else:
                # Free tier - no Stripe subscription needed
                stripe_subscription_id = None

            # Store in database
            db_subscription = Subscription(
                organization_id=organization_id,
                tier_id=tier.id,
                status="active",
                stripe_subscription_id=stripe_subscription_id
            )
            db.add(db_subscription)
            await db.commit()

            logger.info(f"Created subscription {stripe_subscription_id} for org {organization_id}")
            return stripe_subscription_id

        except Exception as e:
            logger.error(f"Failed to create subscription: {e}")
            return None

    async def update_subscription(
        self,
        db: AsyncSession,
        organization_id: int,
        new_tier_name: str
    ) -> bool:
        """
        Upgrade/downgrade organization subscription

        Returns: True if successful, False otherwise
        """
        try:
            from models import Organization, Subscription, SubscriptionTier

            # Get current subscription
            sub_result = await db.execute(
                select(Subscription).where(Subscription.organization_id == organization_id)
            )
            subscription = sub_result.scalar_one_or_none()

            if not subscription or not subscription.stripe_subscription_id:
                logger.warning(f"No Stripe subscription found for org {organization_id}")
                return False

            # Get new tier
            tier_result = await db.execute(
                select(SubscriptionTier).where(SubscriptionTier.name == new_tier_name)
            )
            new_tier = tier_result.scalar_one_or_none()

            if not new_tier:
                logger.error(f"Tier not found: {new_tier_name}")
                return False

            # Update Stripe subscription
            if new_tier.price_usd > 0:
                stripe.Subscription.modify(
                    subscription.stripe_subscription_id,
                    items=[{
                        "id": subscription.stripe_subscription_id,
                        "price_data": {
                            "currency": "usd",
                            "unit_amount": new_tier.price_usd * 100,
                            "recurring": {"interval": "month"},
                            "product_data": {"name": f"{new_tier_name.upper()} Plan"}
                        }
                    }]
                )

            # Update database
            subscription.tier_id = new_tier.id
            await db.commit()

            logger.info(f"Updated subscription for org {organization_id} to {new_tier_name}")
            return True

        except Exception as e:
            logger.error(f"Failed to update subscription: {e}")
            return False

    async def cancel_subscription(
        self,
        db: AsyncSession,
        organization_id: int
    ) -> bool:
        """
        Cancel organization subscription

        Returns: True if successful, False otherwise
        """
        try:
            from models import Subscription

            sub_result = await db.execute(
                select(Subscription).where(Subscription.organization_id == organization_id)
            )
            subscription = sub_result.scalar_one_or_none()

            if not subscription or not subscription.stripe_subscription_id:
                logger.warning(f"No Stripe subscription found for org {organization_id}")
                return False

            # Cancel Stripe subscription
            stripe.Subscription.delete(subscription.stripe_subscription_id)

            # Update database
            subscription.status = "canceled"
            subscription.stripe_subscription_id = None
            await db.commit()

            logger.info(f"Canceled subscription for org {organization_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to cancel subscription: {e}")
            return False

    async def create_invoice(
        self,
        db: AsyncSession,
        organization_id: int,
        subscription_id: int,
        amount_cents: int,
        period_start: datetime,
        period_end: datetime
    ) -> bool:
        """
        Create invoice for organization

        Returns: True if successful, False otherwise
        """
        try:
            from models import Invoice, Organization

            org_result = await db.execute(
                select(Organization).where(Organization.id == organization_id)
            )
            org = org_result.scalar_one_or_none()

            if not org:
                logger.error(f"Organization not found: {organization_id}")
                return False

            # Create Stripe invoice if customer exists
            stripe_invoice_id = None
            if hasattr(org, 'stripe_customer_id') and org.stripe_customer_id:
                invoice = stripe.Invoice.create(
                    customer=org.stripe_customer_id,
                    auto_advance=False,
                    collection_method="send_invoice",
                    days_until_due=30,
                    metadata={
                        "organization_id": organization_id,
                        "period_start": period_start.isoformat(),
                        "period_end": period_end.isoformat()
                    }
                )
                stripe_invoice_id = invoice.id

            # Store in database
            db_invoice = Invoice(
                organization_id=organization_id,
                subscription_id=subscription_id,
                amount_cents=amount_cents,
                status="draft",
                period_start=period_start,
                period_end=period_end,
                stripe_invoice_id=stripe_invoice_id
            )
            db.add(db_invoice)
            await db.commit()

            logger.info(f"Created invoice for org {organization_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to create invoice: {e}")
            return False

    def handle_webhook(self, event: Dict) -> bool:
        """
        Handle Stripe webhook events

        Supported events:
        - customer.subscription.updated
        - customer.subscription.deleted
        - invoice.payment_succeeded
        - invoice.payment_failed
        """
        try:
            event_type = event["type"]

            if event_type == "customer.subscription.updated":
                logger.info(f"Subscription updated: {event['data']['object']['id']}")
                return True

            elif event_type == "customer.subscription.deleted":
                logger.info(f"Subscription deleted: {event['data']['object']['id']}")
                return True

            elif event_type == "invoice.payment_succeeded":
                logger.info(f"Invoice paid: {event['data']['object']['id']}")
                return True

            elif event_type == "invoice.payment_failed":
                logger.warning(f"Invoice payment failed: {event['data']['object']['id']}")
                return True

            else:
                logger.info(f"Unhandled event type: {event_type}")
                return True

        except Exception as e:
            logger.error(f"Webhook handling failed: {e}")
            return False


# Singleton instance
_stripe_integration = None

def get_stripe_integration() -> StripeIntegration:
    """Get or create Stripe integration instance"""
    global _stripe_integration
    if _stripe_integration is None:
        _stripe_integration = StripeIntegration()
    return _stripe_integration
