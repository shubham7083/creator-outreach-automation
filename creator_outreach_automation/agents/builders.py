from __future__ import annotations

from creator_outreach_automation.agents.models import (
    BrandDiscoveryAgentInput,
    BrandWebsiteSummary,
    ContactAgentInput,
    CRMAgentInput,
    EmailAgentInput,
    ScoringAgentInput,
)
from creator_outreach_automation.agents.workflow import WorkflowState, WorkflowStep
from creator_outreach_automation.models.outreach import OutreachGenerationInput


def brand_discovery_input_builder(
    state: WorkflowState,
    step: WorkflowStep,
) -> BrandDiscoveryAgentInput:
    creator_output = state.get_required("creator_output")
    return BrandDiscoveryAgentInput(creator_profile=creator_output.creator_profile)


def scoring_input_builder(state: WorkflowState, step: WorkflowStep) -> ScoringAgentInput:
    creator_output = state.get_required("creator_output")
    brand_output = state.get_required("brand_discovery_output")
    return ScoringAgentInput(
        creator_profile=creator_output.creator_profile,
        brand_summaries=[
            BrandWebsiteSummary(
                brand=brand,
                website_summary=brand.description or brand.name,
            )
            for brand in brand_output.brands
        ],
    )


def contact_input_builder(state: WorkflowState, step: WorkflowStep) -> ContactAgentInput:
    scoring_output = state.get_required("scoring_output")
    return ContactAgentInput(
        brands=[item.brand for item in scoring_output.scoring_result.ranked_brands]
    )


def email_input_builder(state: WorkflowState, step: WorkflowStep) -> EmailAgentInput:
    creator_output = state.get_required("creator_output")
    scoring_output = state.get_required("scoring_output")
    contact_output = state.get_required("contact_output")
    requests: list[OutreachGenerationInput] = []
    contacts_by_brand = {contact.brand_id: contact for contact in contact_output.contacts if contact.email}
    for scored_brand in scoring_output.scoring_result.ranked_brands:
        contact = contacts_by_brand.get(str(scored_brand.brand.id))
        if contact is None or contact.email is None:
            continue
        requests.append(
            OutreachGenerationInput(
                creator_profile=creator_output.creator_profile,
                brand=scored_brand.brand,
                campaign_idea=scored_brand.score.campaign_idea,
                recipient_email=contact.email,
                recipient_name=contact.name,
                recipient_title=contact.title,
            )
        )
    return EmailAgentInput(outreach_requests=requests)


def crm_input_builder(state: WorkflowState, step: WorkflowStep) -> CRMAgentInput:
    creator_output = state.values.get("creator_output")
    brand_output = state.values.get("brand_discovery_output")
    scoring_output = state.values.get("scoring_output")
    contact_output = state.values.get("contact_output")
    email_output = state.values.get("email_output")
    return CRMAgentInput(
        creator_profile=creator_output.creator_profile if creator_output else None,
        brands=brand_output.brands if brand_output else [],
        scored_brands=(
            scoring_output.scoring_result.ranked_brands + scoring_output.scoring_result.rejected_brands
            if scoring_output
            else []
        ),
        contacts=contact_output.contacts if contact_output else [],
        outreach_sequences=email_output.sequences if email_output else [],
    )


def default_input_builders():
    return {
        "brand_discovery": brand_discovery_input_builder,
        "scoring": scoring_input_builder,
        "contact": contact_input_builder,
        "email": email_input_builder,
        "crm": crm_input_builder,
    }
