from __future__ import annotations

import streamlit as st

from app.ui.runtime import run_async
from app.ui.state import add_campaign_event, brands, contacts
from app.ui.styles import section_header
from creator_outreach_automation.config import Settings
from creator_outreach_automation.models.contact import Contact, ContactRole, ContactSource
from creator_outreach_automation.services.factory import create_contact_discovery_service


def render_contact_details(settings: Settings) -> None:
    st.title("Contact Discovery")
    section_header("Decision Makers", "Track marketing, growth, partnerships, creator, and influencer contacts.")

    brand_options = brands()
    if not brand_options:
        st.warning("Add brands before collecting contacts.")
        return
    brands_by_id = {str(brand.id): brand for brand in brand_options}

    selected_for_discovery = st.selectbox(
        "Discover contacts for",
        list(brands_by_id),
        format_func=lambda brand_id: brands_by_id.get(str(brand_id), brand_options[0]).name,
        key="contact-discovery-brand-id",
    )
    if selected_for_discovery not in brands_by_id:
        selected_for_discovery = next(iter(brands_by_id))
    discovery_brand = brands_by_id[selected_for_discovery]
    if st.button("Discover contacts", type="primary"):
        try:
            service = create_contact_discovery_service(settings)
            with st.spinner("Discovering contacts"):
                discovered = run_async(service.discover(discovery_brand))
            current = contacts()
            current.extend(discovered)
            st.session_state["contacts"] = _dedupe_contacts(current)
            add_campaign_event(f"Discovered {len(discovered)} contacts for {discovery_brand.name}.")
            if discovered:
                st.success("Contacts discovered.")
            else:
                st.warning("No contacts found. Add one manually or configure Apollo/Google credentials.")
        except Exception as error:
            st.error(f"Contact discovery failed: {error}")

    with st.expander("Add contact", expanded=True):
        selected_brand_id = st.selectbox(
            "Brand",
            list(brands_by_id),
            format_func=lambda brand_id: brands_by_id.get(str(brand_id), brand_options[0]).name,
            key="contact-manual-brand-id",
        )
        if selected_brand_id not in brands_by_id:
            selected_brand_id = next(iter(brands_by_id))
        brand = brands_by_id[selected_brand_id]
        col_a, col_b = st.columns(2)
        name = col_a.text_input("Name")
        title = col_b.text_input("Title")
        email = col_a.text_input("Email")
        linkedin = col_b.text_input("LinkedIn")
        role = st.selectbox("Role", list(ContactRole), format_func=lambda item: item.value.replace("_", " ").title())
        confidence = st.slider("Confidence", 0.0, 1.0, 0.7, 0.05)
        if st.button("Save contact", type="primary"):
            current = contacts()
            contact = Contact(
                brand_id=str(brand.id),
                brand_name=brand.name,
                name=name.strip() or None,
                title=title.strip() or None,
                email=email.strip() or None,
                linkedin=linkedin.strip() or None,
                role=role,
                confidence_score=confidence,
                sources=[ContactSource.COMPANY_WEBSITE],
            )
            current.append(contact)
            st.session_state["contacts"] = _dedupe_contacts(current)
            add_campaign_event(f"Saved contact for {brand.name}.")
            st.success("Contact saved.")

    rows = [
        {
            "brand": contact.brand_name,
            "name": contact.name or "",
            "title": contact.title or "",
            "email": contact.email or "",
            "linkedin": str(contact.linkedin) if contact.linkedin else "",
            "role": contact.role.value if contact.role else "",
            "confidence": contact.confidence_score,
        }
        for contact in contacts()
    ]
    if rows:
        st.dataframe(rows, width="stretch", hide_index=True)
    else:
        st.info("No contacts saved yet.")


def _dedupe_contacts(items: list[Contact]) -> list[Contact]:
    deduped: dict[str, Contact] = {}
    for item in items:
        key = item.email or str(item.linkedin or "") or f"{item.brand_id}:{item.name}:{item.title}"
        deduped[key.lower()] = item
    return list(deduped.values())
