import unittest

from scripts.shopping_resolver import (
    MockProductProvider,
    build_shopping_spec,
    recommend_products,
    validate_product_source,
)


class ShoppingResolverTests(unittest.TestCase):
    def spec(self, missing=None, profile=None, context=None, constraints=None):
        return build_shopping_spec(missing or {"category": "bottom"}, profile, context, constraints)

    def official(self, **overrides):
        product = {
            "product_id": "official_1", "category": "bottom", "brand": "official_brand",
            "colors": ["black"], "materials": ["wool_blend"], "silhouette": "straight",
            "style_tags": ["minimal"], "occasion_tags": ["client_meeting"], "sizes": ["m"],
            "price": {"currency": "CNY", "amount": 500},
            "source": {"source_type": "brand_official", "official_domain_verified": True,
                       "official_domain": "brand.example", "product_url": "https://brand.example/p/1",
                       "shopping_region": "CN"},
        }
        product.update(overrides)
        return product

    def test_missing_gap_becomes_specification(self):
        self.assertEqual(self.spec({"category": "bag"})["required"]["category"], "bag")

    def test_style_modes_are_preserved(self):
        self.assertEqual(self.spec(profile={"style_modes": ["minimal"]})["style_modes"], ["minimal"])

    def test_budget_is_mapped_without_conversion(self):
        self.assertEqual(self.spec(profile={"budget": {"currency": "CNY", "max_total": 800}})["budget"]["max_price"], 800)

    def test_unknown_optional_values_remain_empty(self):
        self.assertEqual(self.spec()["preferred"]["colors"], [])

    def test_provider_filters_by_requested_category(self):
        self.assertEqual(len(MockProductProvider().search(self.spec({"category": "bag"}))), 3)

    def test_exact_attribute_ranks_first(self):
        result = recommend_products(self.spec({"category": "bottom", "color": "charcoal", "silhouette": "straight"}), MockProductProvider())
        self.assertEqual(result["products"][0]["product"]["product_id"], "b1")

    def test_style_preference_affects_ranking(self):
        result = recommend_products(self.spec(profile={"style_modes": ["minimal"]}), MockProductProvider())
        self.assertEqual(result["products"][0]["product"]["product_id"], "b1")

    def test_occasion_preference_affects_ranking(self):
        result = recommend_products(self.spec(context={"occasion": ["client_meeting"]}), MockProductProvider())
        self.assertEqual(result["products"][0]["product"]["product_id"], "b1")

    def test_budget_is_a_hard_constraint(self):
        self.assertEqual(recommend_products(self.spec(profile={"budget": {"currency": "CNY", "max_total": 100}}), MockProductProvider())["products"], [])

    def test_currency_mismatch_is_explicit(self):
        p = self.official(price={"currency": "USD", "amount": 10})
        result = recommend_products(self.spec(profile={"budget": {"currency": "CNY", "max_total": 100}}), MockProductProvider([p]))
        self.assertIn("currency_mismatch", result["warnings"])

    def test_known_size_constraint_filters_candidates(self):
        result = recommend_products(self.spec(constraints={"size_constraints": {"sizes": ["s"]}}), MockProductProvider())
        self.assertEqual(result["products"][0]["product"]["product_id"], "b1")

    def test_region_mismatch_is_a_tradeoff(self):
        result = recommend_products(self.spec({"category": "bag"}, constraints={"shopping_region": "CN"}), MockProductProvider())
        self.assertTrue(any("region_mismatch" in p["tradeoffs"] for p in result["products"]))

    def test_no_fake_product_url_in_mock_results(self):
        result = recommend_products(self.spec({"category": "bag"}), MockProductProvider())
        self.assertTrue(all(item["product"]["source"]["product_url"] is None for item in result["products"]))

    def test_no_quality_or_body_desirability_scores(self):
        result = str(recommend_products(self.spec(), MockProductProvider()))
        for field in ("quality_score", "beauty_score", "attractiveness", "body_score"):
            self.assertNotIn(field, result)

    def test_impossible_constraints_report_no_match(self):
        result = recommend_products(self.spec(constraints={"size_constraints": {"sizes": ["xxl"]}}), MockProductProvider())
        self.assertIn("no_matching_products", result["warnings"])

    def test_limit_is_enforced(self):
        self.assertLessEqual(len(recommend_products(self.spec(), MockProductProvider(), limit=1)["products"]), 1)

    def test_invalid_limit_is_reported(self):
        self.assertIn("invalid_limit", recommend_products(self.spec(), MockProductProvider(), limit=0)["warnings"])

    def test_mock_fixture_is_allowed_for_local_contract_testing(self):
        self.assertTrue(validate_product_source(MockProductProvider().products[0])["eligible"])

    def test_valid_official_source_is_accepted(self):
        self.assertTrue(validate_product_source(self.official())["eligible"])

    def test_disabled_official_only_policy_allows_provider_candidate(self):
        product = self.official(source={"source_type": "legacy_import"})
        validation = validate_product_source(product, official_sources_only=False)
        self.assertTrue(validation["eligible"])
        self.assertEqual(validation["reason"], "policy_disabled")

    def test_marketplace_source_is_rejected(self):
        p = self.official(source={"source_type": "marketplace", "official_domain_verified": True,
                                  "official_domain": "brand.example", "product_url": "https://brand.example/p/1"})
        self.assertFalse(validate_product_source(p)["eligible"])

    def test_missing_provenance_is_rejected(self):
        self.assertFalse(validate_product_source(self.official(source={}))["eligible"])

    def test_domain_mismatch_is_rejected(self):
        p = self.official(source={"source_type": "brand_official", "official_domain_verified": True,
                                  "official_domain": "brand.example", "product_url": "https://other.example/p/1"})
        self.assertFalse(validate_product_source(p)["eligible"])

    def test_avoided_brand_is_hard_excluded(self):
        result = recommend_products(self.spec(constraints={"brand_preferences": {"preferred": [], "avoid": ["official_brand"]}}), MockProductProvider([self.official()]))
        self.assertEqual(result["products"], [])

    def test_preferred_brand_receives_ranking_bonus(self):
        preferred = self.official()
        other = self.official(product_id="official_2", brand="other_brand")
        result = recommend_products(self.spec(constraints={"brand_preferences": {"preferred": ["official_brand"], "avoid": []}}), MockProductProvider([other, preferred]))
        self.assertEqual(result["products"][0]["product"]["brand"], "official_brand")
