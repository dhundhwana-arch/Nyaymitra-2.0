"""Constitution search, article detail, provenance and coverage honesty."""
from __future__ import annotations


def test_search_english(client):
    body = client.get("/api/v1/constitution/articles", params={"q": "equality", "language": "en"}).json()
    assert body["total"] >= 1
    labels = [item["article_label"] for item in body["items"]]
    assert "Article 14" in labels


def test_search_gujarati(client):
    body = client.get(
        "/api/v1/constitution/articles",
        params={"q": "કાયદા સમક્ષ સમાનતા", "language": "gu"},
    ).json()
    assert body["total"] >= 1
    assert any(item["article_label"] == "Article 14" for item in body["items"])
    assert body["items"][0]["snippet"], "Gujarati snippet expected"


def test_search_without_query_browses_articles(client):
    body = client.get("/api/v1/constitution/articles", params={"page_size": 5}).json()
    assert body["total"] >= 9
    assert len(body["items"]) <= 5
    assert body["notice"] is None


def test_search_pagination_is_stable(client):
    first = client.get("/api/v1/constitution/articles", params={"page_size": 3, "page": 1}).json()
    second = client.get("/api/v1/constitution/articles", params={"page_size": 3, "page": 2}).json()
    assert first["page"] == 1 and second["page"] == 2
    assert {i["id"] for i in first["items"]}.isdisjoint({i["id"] for i in second["items"]})


def test_search_rejects_oversized_query(client):
    response = client.get("/api/v1/constitution/articles", params={"q": "a" * 500})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_failed"


def test_article_detail_includes_source_and_disclaimers(client):
    body = client.get("/api/v1/constitution/articles/14").json()
    assert body["article_label"] == "Article 14"
    assert body["verification_status"] == "requires_human_verification"
    assert body["text_status"] == "owner_authored_summary"
    assert body["text_en"] is None, "a paraphrase must never be stored as the article text"
    assert body["citizen_explanation_en"]
    assert body["sources"]
    owner_source = body["sources"][0]
    assert owner_source["source_type"] == "owner_authored"
    assert owner_source["document_ref"], "every source needs a locator, even when it has no URL"
    assert body["source_url"].startswith("https://")
    assert body["last_checked_at"] is None
    assert any("not been loaded" in line or "authoritative" in line for line in body["disclaimers"])


def test_article_detail_by_key_and_suffix_number(client):
    assert client.get("/api/v1/constitution/articles/39A").json()["article_no"] == "39A"
    assert client.get("/api/v1/constitution/articles/article-21a").json()["article_no"] == "21A"


def test_unknown_article_returns_404_envelope(client):
    response = client.get("/api/v1/constitution/articles/999")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"
    assert response.json()["error"]["request_id"]


def test_invalid_identifier_is_rejected(client):
    assert client.get("/api/v1/constitution/articles/..%2Fetc%2Fpasswd").status_code in {404, 422}


def test_parts_and_coverage(client):
    parts = client.get("/api/v1/constitution/parts").json()
    assert any(part["part_no"] == "III" for part in parts)
    coverage = client.get("/api/v1/constitution/coverage").json()
    assert coverage["total_articles"] >= 9
    assert coverage["verified_text"] == 0
    assert coverage["owner_summaries"] >= 9
    assert "395" in str(coverage["expected_article_count"])
    assert coverage["missing_standard_articles"], "unloaded articles must be reported"
    assert "not a fixed number" in coverage["note"]


def test_fabricated_legacy_remedy_text_is_never_exposed(client):
    """The legacy DB attached two invented 'remedy' strings to every row (audit §6)."""
    for params in ({"q": "Constitutional Provision"}, {"q": "Statutory Guidelines"}):
        body = client.get("/api/v1/constitution/articles", params=params).json()
        for item in body["items"]:
            detail = client.get(f"/api/v1/constitution/articles/{item['article_no']}").json()
            assert "remedy" not in detail
            assert "Statutory Guidelines" not in str(detail)


def test_part_filter(client):
    body = client.get("/api/v1/constitution/articles", params={"part": "IV"}).json()
    assert body["total"] >= 1
    assert all(item["part_no"] == "IV" for item in body["items"])


def test_verification_status_filter(client):
    body = client.get(
        "/api/v1/constitution/articles", params={"verification_status": "verified"}
    ).json()
    assert body["total"] == 0, "nothing has been human-verified yet"


def test_search_results_carry_verification_metadata(client):
    body = client.get("/api/v1/constitution/articles", params={"q": "liberty"}).json()
    assert body["items"]
    for item in body["items"]:
        assert item["verification_status"] in {
            "verified", "requires_human_verification", "unverified", "outdated"
        }
        assert item["text_status"] in {
            "verified_source_text", "owner_authored_summary", "not_available"
        }
