# Tests for Related Documents transformation in markdown_utils.
# Not for testing ticket CRUD or API interactions.

import unittest

from markdown_utils import transform_related_docs_for_phabricator


class RelatedDocumentsTransformTests(unittest.TestCase):
    def test_keeps_ticket_entry_with_em_dash(self) -> None:
        content = """## Related Documents

- **Post on Behalf PRD** (T324178): [post_on_behalf_prd.md](../obo/post_on_behalf_prd.md) — Parent context
"""
        transformed = transform_related_docs_for_phabricator(content)
        self.assertIn(
            "- **Post on Behalf PRD**: [T324178](",
            transformed,
        )
        self.assertIn("Parent context", transformed)

    def test_keeps_ticket_entry_with_hyphen(self) -> None:
        content = """## Related Documents

- **Post on Behalf PRD** (T324178): [post_on_behalf_prd.md](../obo/post_on_behalf_prd.md) - Parent context
"""
        transformed = transform_related_docs_for_phabricator(content)
        self.assertIn(
            "- **Post on Behalf PRD**: [T324178](",
            transformed,
        )
        self.assertIn("Parent context", transformed)

    def test_mixed_entries_keep_only_ticket_lines(self) -> None:
        content = """## Related Documents

- **Post on Behalf PRD** (T324178): [post_on_behalf_prd.md](../obo/post_on_behalf_prd.md) — Parent context
- **Design Mockup**: [mockup.png](./images/mockup.png) — Local only file
"""
        transformed = transform_related_docs_for_phabricator(content)
        self.assertIn("[T324178](", transformed)
        self.assertNotIn("mockup.png", transformed)

    def test_remove_section_when_no_ticket_entries(self) -> None:
        content = """## Related Documents

- **Design Mockup**: [mockup.png](./images/mockup.png) — Local only file

## Data Tracking

| Metric Name | Description |
| --- | --- |
| Metric A | Example |
"""
        transformed = transform_related_docs_for_phabricator(content)
        self.assertNotIn("## Related Documents", transformed)
        self.assertIn("## Data Tracking", transformed)

    def test_real_world_hyphen_case_from_enterprise_prd(self) -> None:
        content = """## Related Documents

- **Post on Behalf PRD** (T324178): [post_on_behalf_prd.md](../obo/post_on_behalf_prd.md) - Enterprise/Ops managed workflow context
- **Quote Edit Fee Notification Modal** (T326227): [quote_edit_fee_notification_modal_for_shipper.md](../../basic_user_experience/quote_and_fees/quote_edit_fee_notification_modal_for_shipper.md) - Existing payment and fee logic baseline
"""
        transformed = transform_related_docs_for_phabricator(content)
        self.assertIn("[T324178](", transformed)
        self.assertIn("[T326227](", transformed)

    def test_keep_blank_line_after_related_documents_heading(self) -> None:
        content = """## Related Documents

- **Post on Behalf PRD** (T324178): [post_on_behalf_prd.md](../obo/post_on_behalf_prd.md) - Parent context

## Data Tracking
"""
        transformed = transform_related_docs_for_phabricator(content)
        self.assertIn(
            "## Related Documents\n\n- **Post on Behalf PRD**: [T324178](",
            transformed,
        )
        self.assertIn("## Data Tracking", transformed)


if __name__ == "__main__":
    unittest.main()
