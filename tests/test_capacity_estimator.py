import unittest
from scripts.capacity_estimator import estimate_bag_capacity, check_item_fit, analyze_carry_requirements


class CapacityEstimatorTests(unittest.TestCase):
    bag = {"width_cm": 28, "height_cm": 20, "depth_cm": 11}
    laptop = {"item_type": "laptop", "name": "laptop", "width_cm": 18, "height_cm": 12, "depth_cm": 1.5}
    def test_geometric_capacity(self): self.assertEqual(estimate_bag_capacity(self.bag)["estimated_gross_capacity_l"], 6.16)
    def test_default_usable_factor(self): self.assertEqual(estimate_bag_capacity(self.bag)["estimated_usable_capacity_l"], 4.62)
    def test_stated_capacity_is_preserved(self): self.assertEqual(estimate_bag_capacity(self.bag | {"capacity_l": 8})["stated_capacity_l"], 8.0)
    def test_rectangular_item_fits(self): self.assertEqual(check_item_fit(self.bag, self.laptop)["fit_status"], "fits")
    def test_rectangular_item_does_not_fit(self): self.assertEqual(check_item_fit(self.bag, self.laptop | {"width_cm": 30})["fit_status"], "does_not_fit")
    def test_rotated_orientation_fits(self): self.assertEqual(check_item_fit({"width_cm": 20,"height_cm":30,"depth_cm":5}, self.laptop | {"width_cm":25,"height_cm":18})["orientation"], "portrait")
    def test_depth_failure(self): self.assertEqual(check_item_fit(self.bag, self.laptop | {"depth_cm": 11})["fit_status"], "does_not_fit")
    def test_missing_dimensions_unknown(self): self.assertEqual(check_item_fit(self.bag, {"item_type":"laptop","name":"13-inch laptop"})["fit_status"], "unknown")
    def test_invalid_bag_dimension_safe(self): self.assertIn("invalid_bag.width_cm", estimate_bag_capacity(self.bag | {"width_cm": -1})["warnings"])
    def test_bottle_fits(self): self.assertEqual(check_item_fit(self.bag, {"item_type":"bottle","diameter_cm":7,"height_cm":15})["fit_status"], "fits")
    def test_bottle_does_not_fit(self): self.assertEqual(check_item_fit(self.bag, {"item_type":"bottle","diameter_cm":7,"height_cm":30})["fit_status"], "does_not_fit")
    def test_a4_fit(self): self.assertEqual(check_item_fit({"width_cm":32,"height_cm":24,"depth_cm":3}, {"item_type":"a4_document"})["fit_status"], "fits")
    def test_independent_warning(self): self.assertIn("independent_fit_does_not_prove_simultaneous_packing", analyze_carry_requirements(self.bag,[self.laptop,self.laptop])["warnings"])
    def test_opening_constraint(self): self.assertEqual(check_item_fit(self.bag | {"opening_width_cm":10,"opening_height_cm":10}, self.laptop)["fit_status"], "does_not_fit")
    def test_reference_confidence_lower(self): self.assertEqual(check_item_fit(self.bag, {"item_type":"phone"})["confidence"], "medium")
    def test_no_shopping_or_style_fields(self):
        text=str(analyze_carry_requirements(self.bag,[self.laptop]))
        for key in ("brand","product_url","price","shopping_link","style_score","beauty_score"): self.assertNotIn(key,text)
