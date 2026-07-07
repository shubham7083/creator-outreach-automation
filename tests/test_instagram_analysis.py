from __future__ import annotations

from creator_outreach_automation.api.instagram_analysis import parse_instagram_profile_html


def test_parse_instagram_profile_html_from_metadata() -> None:
    html = """
    <html>
      <head>
        <meta name="description" content="12.5K Followers, 100 Following, 42 Posts - Food creator">
        <script type="application/ld+json">
        {
          "username": "foodcreator",
          "full_name": "Food Creator",
          "biography": "Easy recipes #homecooking",
          "edge_followed_by": {"count": 12500},
          "edge_follow": {"count": 100},
          "edge_owner_to_timeline_media": {
            "count": 42,
            "edges": [
              {
                "node": {
                  "shortcode": "abc123",
                  "edge_media_to_caption": {
                    "edges": [{"node": {"text": "Dinner with @PanCo #recipe"}}]
                  },
                  "edge_liked_by": {"count": 500},
                  "edge_media_to_comment": {"count": 25}
                }
              }
            ]
          }
        }
        </script>
      </head>
    </html>
    """

    snapshot = parse_instagram_profile_html(html, username="foodcreator", max_posts=5)

    assert snapshot.username == "foodcreator"
    assert snapshot.full_name == "Food Creator"
    assert snapshot.bio == "Easy recipes #homecooking"
    assert snapshot.followers == 12500
    assert snapshot.recent_posts[0].shortcode == "abc123"
    assert snapshot.recent_posts[0].hashtags == ["recipe"]
