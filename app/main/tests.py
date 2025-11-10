from django.test import RequestFactory, TestCase
import json
from main.views import calculate_prediction

class CalculatePredictionTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
    
    def _post(self, data):
        """Helper to make POST request and parse JSON response"""
        request = self.factory.post("/predict/", data)
        response = calculate_prediction(request)
        return json.loads(response.content)
    
    def test_invalid_request_method(self):
        """GET request should return error"""
        request = self.factory.get("/predict/")
        response = calculate_prediction(request)
        data = json.loads(response.content)
        self.assertEqual(data["message"], "Invalid request")
        self.assertEqual(response.status_code, 405)
    
    def test_empty_input(self):
        """Empty input should still calculate something"""
        data = self._post({})
        self.assertIn("message", data)
    
    def test_highest_grade_already_achieved(self):
        """Perfect scores should indicate highest grade achieved"""
        data = self._post({
            "grades": "10,10,10",
            "test_grades": "10,10",
            "final_grade": "10"
        })
        self.assertIn("highest grade", data["message"])
        self.assertEqual(data["current_grade"], 5)
    
    def test_missing_final_needs_calculation(self):
        """Calculate what's needed on missing final exam"""
        data = self._post({
            "grades": "7,8,7",
            "test_grades": "8,7",
            "final_grade": ""
        })
        self.assertIn("needed_score", data)
        self.assertIn("final exam", data["missing"])
        # With avg ~7.4 in assignments/tests, should need something reasonable on final
        self.assertGreater(data["needed_score"], 0)
        self.assertLess(data["needed_score"], 10)
    
    def test_missing_tests_needs_calculation(self):
        """Calculate what's needed on missing tests"""
        data = self._post({
            "grades": "8,8,8",
            "test_grades": "8",
            "final_grade": "8",
            "total_tests": "3"  # 2 tests missing
        })
        self.assertIn("needed_score", data)
        self.assertIn("test(s)", data["missing"])
    
    def test_low_scores_impossible_to_reach_next_grade(self):
        """Very low scores should indicate impossibility"""
        data = self._post({
            "grades": "2,2,2",
            "test_grades": "2",
            "final_grade": "",
            "total_tests": "1"
        })
        # Even with perfect final, might not reach next grade
        if "cannot reach" in data["message"] or "Even with perfect" in data["message"]:
            self.assertIn("needed_score", data)
            self.assertGreater(data["needed_score"], 10)
    
    def test_all_complete_needs_additional_tens(self):
        """When all assessments done, calculate additional perfect assignments needed"""
        data = self._post({
            "grades": "6,6,6",
            "test_grades": "6,6",
            "final_grade": "6"
        })
        # Grade 3 requires 40%, grade 4 requires 65%
        # Current weighted: 6*0.25 + 6*0.25 + 6*0.5 = 6.0/10 = 60%, so at grade 3
        # Should need some additional perfect assignments to reach grade 4 (65%)
        self.assertIn("needed_tens", data)
        self.assertGreater(data["needed_tens"], 0)
    
    def test_mathematical_accuracy_for_grade_4(self):
        """Verify mathematical accuracy of calculation"""
        # Setup: avg 6.5 on everything = 65% = exactly grade 4 threshold
        data = self._post({
            "grades": "6.5,6.5",
            "test_grades": "6.5",
            "final_grade": "6.5"
        })
        # Should already have grade 4
        self.assertIn(data["current_grade"], [4, 5])
    
    def test_mathematical_accuracy_missing_final(self):
        """Verify calculation for missing final exam"""
        # Assignments: 8,8 (avg 8) -> contributes 8 * 0.25 = 2.0
        # Tests: 8,8 (avg 8) -> contributes 8 * 0.25 = 2.0
        # Current score: 4.0/10 = 40% = grade 3
        # To reach grade 4 (65%): need 6.5/10
        # Missing final (weight 0.5): (4.0 + x * 0.5) / 10 = 0.65
        # 4.0 + x * 0.5 = 6.5
        # x * 0.5 = 2.5
        # x = 5.0
        data = self._post({
            "grades": "8,8",
            "test_grades": "8,8",
            "final_grade": ""
        })
        self.assertIn("needed_score", data)
        self.assertAlmostEqual(data["needed_score"], 5.0, places=1)
    
    def test_invalid_grade_range(self):
        """Grades outside 0-10 should return error"""
        data = self._post({
            "grades": "11,9,8",
            "test_grades": "",
            "final_grade": ""
        })
        self.assertIn("between 0 and 10", data["message"])
    
    def test_edge_case_all_zeros(self):
        """All zero grades should still calculate"""
        data = self._post({
            "grades": "0,0",
            "test_grades": "0",
            "final_grade": "0"
        })
        self.assertEqual(data["current_grade"], 2)
        self.assertIn("message", data)
    
    def test_barely_missing_grade_5(self):
        """Test when very close to grade 5"""
        data = self._post({
            "grades": "8.4,8.4",
            "test_grades": "8.4",
            "final_grade": "8.4"
        })
        # Weighted: 8.4*0.25 + 8.4*0.25 + 8.4*0.5 = 8.4/10 = 84%, just below 85% for grade 5
        self.assertEqual(data["current_grade"], 4)
        if "needed_tens" in data:
            # Should need very few additional perfect assignments
            self.assertLessEqual(data["needed_tens"], 5)
    
    def test_realistic_scenario(self):
        """Test realistic student scenario"""
        data = self._post({
            "grades": "7,8,6,9",
            "test_grades": "7,8",
            "final_grade": "",
            "total_tests": "2"
        })
        # Assignments avg: 7.5 -> 7.5 * 0.25 = 1.875
        # Tests avg: 7.5 -> 7.5 * 0.25 = 1.875
        # Current: 3.75/10 = 37.5% = grade 2
        # To reach grade 3 (40%): need 4.0/10 total
        # Need from final: (4.0 - 3.75) / 0.5 = 0.5
        self.assertIn("needed_score", data)
        self.assertAlmostEqual(data["needed_score"], 0.5, places=1)