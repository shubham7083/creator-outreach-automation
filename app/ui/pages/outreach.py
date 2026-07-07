from __future__ import annotations

import streamlit as st

from app.ui.runtime import run_async
from app.ui.state import add_campaign_event, approved_brands, contacts, creator_profile, outreach_sequences
from app.ui.styles import section_header
from creator_outreach_automation.config import Settings
from creator_outreach_automation.models.outreach import OutreachGenerationInput
from creator_outreach_automation.services.factory import create_outreach_engine


def render_outreach(settings: Settings) -> None:
    st.title("Email Drafts")
    section_header("Create Gmail Drafts", "Generate outreach copy and create drafts only. Nothing is sent automatically.")

    approved = approved_brands()
    if not approved:
        st.warning("Approve at least one scored brand first.")
        return

    selected = st.selectbox("Approved brand", approved, format_func=lambda item: item.brand.name)
    brand_contacts = [item for item in contacts() if item.brand_id == str(selected.brand.id)]
    contact = st.selectbox(
        "Contact",
        brand_contacts,
        format_func=lambda item: item.email or item.name or "Unnamed contact",
    ) if brand_contacts else None
    recipient_email = st.text_input("Recipient email", value=(contact.email if contact and contact.email else ""))
    recipient_name = st.text_input("Recipient name", value=(contact.name if contact and contact.name else ""))
    recipient_title = st.text_input("Recipient title", value=(contact.title if contact and contact.title else ""))
    campaign_idea = st.text_area("Campaign idea", value=selected.score.campaign_idea)

    if st.button("Create Gmail drafts", type="primary"):
        profile = creator_profile()
        if profile is None:
            st.error("Analyze a creator first.")
        elif not recipient_email.strip():
            st.error("Recipient email is required.")
        elif not campaign_idea.strip():
            st.error("Campaign idea is required.")
        else:
            try:
                engine = create_outreach_engine(settings)
                with st.spinner("Generating copy and creating Gmail drafts"):
                    result = run_async(
                        engine.create_drafts(
                            OutreachGenerationInput(
                                creator_profile=profile,
                                brand=selected.brand,
                                campaign_idea=campaign_idea.strip(),
                                recipient_email=recipient_email.strip(),
                                recipient_name=recipient_name.strip() or None,
                                recipient_title=recipient_title.strip() or None,
                            )
                        )
                    )
                sequences = outreach_sequences()
                sequences.append(result)
                st.session_state["outreach_sequences"] = sequences
                add_campaign_event(f"Created Gmail drafts for {selected.brand.name}.")
                st.success("Gmail drafts created.")
            except Exception as error:
                st.error(f"Draft creation failed: {error}")

    st.divider()
    for sequence in outreach_sequences():
        with st.container(border=True):
            st.subheader(sequence.brand_name)
            st.caption(sequence.recipient_email)
            for draft in sequence.drafts:
                st.write(f"{draft.kind.value}: `{draft.gmail_draft_id}`")
                st.text_area(draft.subject, draft.body, height=120, key=f"draft-preview-{draft.gmail_draft_id}")
