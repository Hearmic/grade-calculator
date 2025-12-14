
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_http_methods
from django.db import connection
import logging
import json
from .translations import get_translation

logger = logging.getLogger(__name__)

# Grade thresholds (numeric grade: minimum percentage required)
GRADES_PERCENT = {
    5: 0.85,
    4: 0.65,
    3: 0.40,
    2: 0.00,
}

# Letter grade mapping for English language
LETTER_GRADES = {
    5: 'A',
    4: 'B',
    3: 'C',
    2: 'F'
}

LETTER_GRADE_RANGES = {
    5: 'A (85-100%)',
    4: 'B (65-84%)',
    3: 'C (40-64%)',
    2: 'F (0-39%)'
}

# Default weights (used as fallback)
DEFAULT_WEIGHT_ASSIGNMENTS = 0.25
DEFAULT_WEIGHT_TESTS = 0.25
DEFAULT_WEIGHT_FINAL = 0.5

# Default maximum values for different assessment types
DEFAULT_MAX_ASSIGNMENT = 10.0
DEFAULT_MAX_TEST = 10.0
DEFAULT_MAX_FINAL = 10.0

def home(request):
    return render(request, "main/home.html")

def calculate_prediction(request):
    """
    Predicts what grade a student needs on missing assessments to reach the next grade level.
    
    POST Parameters:
    - grades: comma-separated assignment grades (e.g., "8,9,7")
    - test_grades: comma-separated test grades (e.g., "9,8")
    - final_grade: final exam grade (single value)
    - total_tests: total number of tests expected (optional, defaults to completed tests)
    - language: language code (en, kk, ru) for localized messages
    
    Returns JSON with prediction message and current grade information.
    """
    if request.method != "POST":
        lang = request.POST.get("language", "en")
        return JsonResponse({"message": get_translation('invalid_request', lang)}, status=405)
    
    # Get language preference
    language = request.POST.get("language", "en")
    if language not in ['en', 'kk', 'ru']:
        language = 'en'
    
    # Parse input data
    assign_grades_str = request.POST.get("grades", "")
    assign_types_str = request.POST.get("assignment_types", "")
    assign_type_weights_str = request.POST.get("assignment_type_weights", "")
    test_grades_str = request.POST.get("test_grades", "")
    test_maxes_str = request.POST.get("test_maxes", "")
    final_grade_str = request.POST.get("final_grade", "")
    final_max_str = request.POST.get("final_max", "")
    total_tests_str = request.POST.get("total_tests", "")
    
    # Get custom weights (with defaults) - now in percentages (0-100)
    weight_assignments_percent = float(request.POST.get("weight_assignments", DEFAULT_WEIGHT_ASSIGNMENTS * 100))
    weight_tests_percent = float(request.POST.get("weight_tests", DEFAULT_WEIGHT_TESTS * 100))
    weight_final_percent = float(request.POST.get("weight_final", DEFAULT_WEIGHT_FINAL * 100))
    
    # Convert from percentages to decimals (0-1 range)
    weight_assignments = weight_assignments_percent / 100.0
    weight_tests = weight_tests_percent / 100.0
    weight_final = weight_final_percent / 100.0
    
    # Normalize weights to sum to 1.0 (in case they don't sum to 100%)
    weight_total = weight_assignments + weight_tests + weight_final
    if weight_total > 0:
        weight_assignments = weight_assignments / weight_total
        weight_tests = weight_tests / weight_total
        weight_final = weight_final / weight_total
    else:
        # Fallback to defaults if all weights are 0
        weight_assignments = DEFAULT_WEIGHT_ASSIGNMENTS
        weight_tests = DEFAULT_WEIGHT_TESTS
        weight_final = DEFAULT_WEIGHT_FINAL
    
    # Convert to lists/values
    assign_grades = [float(g) for g in assign_grades_str.split(",") if g.strip()]
    assign_types = [t.strip() for t in assign_types_str.split(",") if t.strip()] if assign_types_str else []
    
    # Parse assignment type weights
    assignment_type_weights = {}
    if assign_type_weights_str:
        try:
            assignment_type_weights = json.loads(assign_type_weights_str)
        except json.JSONDecodeError:
            assignment_type_weights = {}
    
    test_grades_raw = [float(g) for g in test_grades_str.split(",") if g.strip()]
    test_maxes = [float(m) for m in test_maxes_str.split(",") if m.strip()]
    final_grade_raw = float(final_grade_str) if final_grade_str.strip() else None
    final_max = float(final_max_str) if final_max_str.strip() else None
    total_tests = int(total_tests_str) if total_tests_str.strip() else len(test_grades_raw)
    
    # Normalize test grades to 0-10 scale
    test_grades = []
    if len(test_grades_raw) > 0:
        if len(test_grades_raw) == len(test_maxes) and len(test_maxes) > 0:
            # Both grades and maxes provided - normalize to 0-10 scale
            for grade, max_val in zip(test_grades_raw, test_maxes):
                if max_val > 0:
                    if grade > max_val:
                        return JsonResponse({"message": get_translation('grade_exceeds_max', language)}, status=400)
                    normalized = (grade / max_val) * 10
                    test_grades.append(normalized)
                else:
                    return JsonResponse({"message": get_translation('invalid_grades', language)}, status=400)
        else:
            # If maxes not provided or don't match, assume grades are already on 0-10 scale
            test_grades = [min(grade, 10.0) for grade in test_grades_raw]
    
    # Normalize final grade to 0-10 scale
    final_grade = None
    if final_grade_raw is not None:
        if final_max is not None and final_max > 0:
            if final_grade_raw > final_max:
                return JsonResponse({"message": get_translation('grade_exceeds_max', language)}, status=400)
            final_grade = (final_grade_raw / final_max) * 10
        else:
            # If max not provided, assume grade is already on 0-10 scale
            final_grade = min(final_grade_raw, 10.0)
    
    # Validate input ranges (all should be 0-10 after normalization)
    for grade in assign_grades:
        if grade < 0:
            return JsonResponse({"message": get_translation('invalid_grades', language)}, status=400)
    
    for grade in test_grades:
        if grade < 0:
            return JsonResponse({"message": get_translation('invalid_grades', language)}, status=400)
    
    if final_grade is not None and final_grade < 0:
        return JsonResponse({"message": get_translation('invalid_grades', language)}, status=400)
    
    # Calculate completed tests count
    completed_tests = len(test_grades)
    missing_tests = max(0, total_tests - completed_tests)
    has_final = final_grade is not None
    
    # Calculate current weighted score
    current_score = 0.0
    weight_used = 0.0
    
    # Add assignments contribution (with type-based weighting if applicable)
    if assign_grades:
        if assign_types and len(assign_types) == len(assign_grades) and assignment_type_weights:
            # Calculate weighted average based on assignment types
            total_weighted_sum = 0.0
            total_type_weight = 0.0
            
            for grade, assign_type in zip(assign_grades, assign_types):
                # Assignment type weights are in percentages, convert to relative weights
                type_weight_percent = assignment_type_weights.get(assign_type, 100.0)
                type_weight = type_weight_percent / 100.0  # Convert to 0-1 range
                total_weighted_sum += grade * type_weight
                total_type_weight += type_weight
            
            if total_type_weight > 0:
                assign_avg = total_weighted_sum / total_type_weight
            else:
                assign_avg = sum(assign_grades) / len(assign_grades)
        else:
            # Simple average if no types specified
            assign_avg = sum(assign_grades) / len(assign_grades)
        
        current_score += assign_avg * weight_assignments
        weight_used += weight_assignments
    
    # Add tests contribution
    if test_grades:
        test_avg = sum(test_grades) / len(test_grades)
        current_score += test_avg * weight_tests
        weight_used += weight_tests
    
    # Add final exam contribution
    if has_final:
        current_score += final_grade * weight_final
        weight_used += weight_final
    
    # Current percentage (out of total possible)
    if weight_used > 0:
        current_percent = current_score / 10
    else:
        current_percent = 0.0
    
    # Determine current and next grade
    current_grade = 2  # Default lowest grade
    for grade in sorted(GRADES_PERCENT.keys()):
        if current_percent >= GRADES_PERCENT[grade]:
            current_grade = grade
    
    # Find next grade target
    next_grade = None
    for grade in sorted(GRADES_PERCENT.keys()):
        if grade > current_grade:
            next_grade = grade
            break
    
    # If already at highest grade
    if next_grade is None:
        response_data = {
            "message": get_translation('already_highest', language),
            "current_grade": current_grade,
            "current_percent": round(current_percent * 100, 2)
        }
        # Add letter grade for English
        if language == 'en':
            response_data["current_grade_letter"] = LETTER_GRADES.get(current_grade, str(current_grade))
        return JsonResponse(response_data)
    
    # Build predictions for all reachable grades
    predictions = []
    
    # Case 1: Missing tests or final exam
    if missing_tests > 0 or not has_final:
        # Calculate for each grade higher than current
        for target_grade in sorted([g for g in GRADES_PERCENT.keys() if g > current_grade]):
            target_threshold = GRADES_PERCENT[target_grade]
            
            missing_weight = 0.0
            missing_parts = []
            
            if missing_tests > 0:
                missing_weight += weight_tests
                missing_parts.append(f"{missing_tests} test(s)")
            
            if not has_final:
                missing_weight += weight_final
                missing_parts.append("final exam")
            
            # Calculate required score on missing assessments
            needed_score = (target_threshold * 10 - current_score) / missing_weight
            needed_percent = (needed_score / 10) * 100
            
            # If only final exam is missing, calculate specifically for final
            needed_final_percent = None
            if not has_final and missing_tests == 0:
                # Only final is missing: (current_score + needed_final * weight_final) / 10 = target_threshold
                # needed_final = (target_threshold * 10 - current_score) / weight_final
                if weight_final > 0:
                    needed_final_score = (target_threshold * 10 - current_score) / weight_final
                    needed_final_percent = (needed_final_score / 10) * 100
                    if needed_final_score < 0:
                        needed_final_score = 0
                        needed_final_percent = 0
                else:
                    needed_final_score = 0
                    needed_final_percent = 0
            
            if needed_score < 0:
                needed_score = 0
                needed_percent = 0
            
            pred = {
                "target_grade": target_grade,
                "needed_score": round(needed_score, 2),
                "needed_percent": round(needed_percent, 2),
                "reachable": needed_score <= 10,
                "missing_parts": missing_parts
            }
            
            # Add final-specific calculation if applicable
            if needed_final_percent is not None:
                pred["needed_final_percent"] = round(needed_final_percent, 2)
                pred["needed_final_score"] = round(needed_final_score, 2)
            
            predictions.append(pred)
        
        response_data = {
            "message": get_translation('grade_predictions_remaining', language),
            "current_grade": current_grade,
            "current_percent": round(current_percent * 100, 2),
            "predictions": predictions,
            "language": language
        }
        # Add letter grades for English
        if language == 'en':
            response_data["current_grade_letter"] = LETTER_GRADES.get(current_grade, str(current_grade))
            for pred in predictions:
                pred["target_grade_letter"] = LETTER_GRADES.get(pred["target_grade"], str(pred["target_grade"]))
        return JsonResponse(response_data)
    
    # Case 2: All assessments completed - calculate additional perfect assignments needed
    else:
        predictions = []
        
        # Calculate for each grade higher than current
        for target_grade in sorted([g for g in GRADES_PERCENT.keys() if g > current_grade]):
            target_threshold = GRADES_PERCENT[target_grade]
            target_avg = target_threshold * 10
            
            if current_score >= target_avg:
                predictions.append({
                    "target_grade": target_grade,
                    "needed_tens": 0,
                    "reachable": True,
                    "message": "Already reached"
                })
                continue
            
            # Calculate contribution from tests and final (these don't change)
            fixed_contribution = 0.0
            if test_grades:
                test_avg = sum(test_grades) / len(test_grades)
                fixed_contribution += test_avg * weight_tests
            if final_grade is not None:
                fixed_contribution += final_grade * weight_final
            
            # Current assignments (with type-based weighting if applicable)
            if assign_grades:
                if assign_types and len(assign_types) == len(assign_grades) and assignment_type_weights:
                    # Calculate current weighted sum and total weight
                    current_assign_weighted_sum = 0.0
                    current_assign_total_weight = 0.0
                    
                    for grade, assign_type in zip(assign_grades, assign_types):
                        # Assignment type weights are in percentages, convert to relative weights
                        type_weight_percent = assignment_type_weights.get(assign_type, 100.0)
                        type_weight = type_weight_percent / 100.0  # Convert to 0-1 range
                        current_assign_weighted_sum += grade * type_weight
                        current_assign_total_weight += type_weight
                    
                    # Try adding perfect assignments (with default type weight) until we reach target
                    n = 0
                    default_type_weight_percent = assignment_type_weights.get(assign_types[0] if assign_types else 'Default', 100.0)
                    default_type_weight = default_type_weight_percent / 100.0  # Convert to 0-1 range
                    
                    while n <= 20:
                        new_weighted_sum = current_assign_weighted_sum + 10 * default_type_weight * n
                        new_total_weight = current_assign_total_weight + default_type_weight * n
                        new_assign_avg = new_weighted_sum / new_total_weight if new_total_weight > 0 else 10
                        new_weighted_score = new_assign_avg * weight_assignments + fixed_contribution
                        
                        if new_weighted_score >= target_threshold * 10:
                            break
                        n += 1
                else:
                    # Simple average calculation
                    current_assign_sum = sum(assign_grades)
                    current_assign_count = len(assign_grades)
                    
                    # Try adding perfect assignments until we reach target
                    n = 0
                    while n <= 20:
                        new_assign_avg = (current_assign_sum + 10 * n) / (current_assign_count + n) if (current_assign_count + n) > 0 else 10
                        new_weighted_score = new_assign_avg * weight_assignments + fixed_contribution
                        
                        if new_weighted_score >= target_threshold * 10:
                            break
                        n += 1
            else:
                # No assignments yet
                n = 0
                while n <= 20:
                    new_assign_avg = 10.0  # Perfect assignment
                    new_weighted_score = new_assign_avg * weight_assignments + fixed_contribution
                    
                    if new_weighted_score >= target_threshold * 10:
                        break
                    n += 1
            
            predictions.append({
                "target_grade": target_grade,
                "needed_tens": n if n <= 20 else None,
                "reachable": n <= 20
            })
        
        response_data = {
            "message": get_translation('grade_predictions_assignments', language),
            "current_grade": current_grade,
            "current_percent": round(current_percent * 100, 2),
            "predictions": predictions,
            "language": language
        }
        # Add letter grades for English
        if language == 'en':
            response_data["current_grade_letter"] = LETTER_GRADES.get(current_grade, str(current_grade))
            for pred in predictions:
                pred["target_grade_letter"] = LETTER_GRADES.get(pred["target_grade"], str(pred["target_grade"]))
        return JsonResponse(response_data)


@require_http_methods(["GET"])
def health_check(request):
    """
    Health check endpoint for monitoring and load balancers.
    Returns 200 if the application and database are healthy.
    """
    try:
        # Test database connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        
        logger.info("Health check passed")
        return JsonResponse({
            "status": "healthy",
            "database": "connected"
        }, status=200)
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return JsonResponse({
            "status": "unhealthy",
            "error": str(e)
        }, status=503)

