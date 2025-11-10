
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_http_methods
from django.db import connection
import logging

logger = logging.getLogger(__name__)

# Grade thresholds (numeric grade: minimum percentage required)
GRADES_PERCENT = {
    5: 0.85,
    4: 0.65,
    3: 0.40,
    2: 0.00,
}

WEIGHT_ASSIGNMENTS = 0.25
WEIGHT_TESTS = 0.25
WEIGHT_FINAL = 0.5

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
    
    Returns JSON with prediction message and current grade information.
    """
    if request.method != "POST":
        return JsonResponse({"message": "Invalid request"}, status=405)
    
    # Parse input data
    assign_grades_str = request.POST.get("grades", "")
    test_grades_str = request.POST.get("test_grades", "")
    final_grade_str = request.POST.get("final_grade", "")
    total_tests_str = request.POST.get("total_tests", "")
    
    # Convert to lists/values
    assign_grades = [float(g) for g in assign_grades_str.split(",") if g.strip()]
    test_grades = [float(g) for g in test_grades_str.split(",") if g.strip()]
    final_grade = float(final_grade_str) if final_grade_str.strip() else None
    total_tests = int(total_tests_str) if total_tests_str.strip() else len(test_grades)
    
    # Validate input ranges
    for grade in assign_grades:
        if grade < 0 or grade > 10:
            return JsonResponse({"message": "All grades must be between 0 and 10"}, status=400)
    
    # Calculate completed tests count
    completed_tests = len(test_grades)
    missing_tests = max(0, total_tests - completed_tests)
    has_final = final_grade is not None
    
    # Calculate current weighted score
    current_score = 0.0
    weight_used = 0.0
    
    # Add assignments contribution
    if assign_grades:
        assign_avg = sum(assign_grades) / len(assign_grades)
        current_score += assign_avg * WEIGHT_ASSIGNMENTS
        weight_used += WEIGHT_ASSIGNMENTS
    
    # Add tests contribution
    if test_grades:
        test_avg = sum(test_grades) / len(test_grades)
        current_score += test_avg * WEIGHT_TESTS
        weight_used += WEIGHT_TESTS
    
    # Add final exam contribution
    if has_final:
        current_score += final_grade * WEIGHT_FINAL
        weight_used += WEIGHT_FINAL
    
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
        return JsonResponse({
            "message": f"Congratulations! You already have the highest grade (5).",
            "current_grade": current_grade,
            "current_percent": round(current_percent * 100, 2)
        })
    
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
                missing_weight += WEIGHT_TESTS
                missing_parts.append(f"{missing_tests} test(s)")
            
            if not has_final:
                missing_weight += WEIGHT_FINAL
                missing_parts.append("final exam")
            
            # Calculate required score on missing assessments
            needed_score = (target_threshold * 10 - current_score) / missing_weight
            needed_percent = (needed_score / 10) * 100
            
            # If only final exam is missing, calculate specifically for final
            needed_final_percent = None
            if not has_final and missing_tests == 0:
                # Only final is missing: (current_score + needed_final * WEIGHT_FINAL) / 10 = target_threshold
                # needed_final = (target_threshold * 10 - current_score) / WEIGHT_FINAL
                needed_final_score = (target_threshold * 10 - current_score) / WEIGHT_FINAL
                needed_final_percent = (needed_final_score / 10) * 100
                if needed_final_score < 0:
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
        
        return JsonResponse({
            "message": "Grade predictions for remaining assessments:",
            "current_grade": current_grade,
            "current_percent": round(current_percent * 100, 2),
            "predictions": predictions
        })
    
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
                fixed_contribution += test_avg * WEIGHT_TESTS
            if final_grade is not None:
                fixed_contribution += final_grade * WEIGHT_FINAL
            
            # Current assignments
            current_assign_sum = sum(assign_grades) if assign_grades else 0
            current_assign_count = len(assign_grades) if assign_grades else 0
            
            # Try adding perfect assignments until we reach target
            n = 0
            while n <= 20:
                new_assign_avg = (current_assign_sum + 10 * n) / (current_assign_count + n) if (current_assign_count + n) > 0 else 10
                new_weighted_score = new_assign_avg * WEIGHT_ASSIGNMENTS + fixed_contribution
                
                if new_weighted_score >= target_threshold * 10:
                    break
                n += 1
            
            predictions.append({
                "target_grade": target_grade,
                "needed_tens": n if n <= 20 else None,
                "reachable": n <= 20
            })
        
        return JsonResponse({
            "message": "Grade predictions with additional perfect assignments:",
            "current_grade": current_grade,
            "current_percent": round(current_percent * 100, 2),
            "predictions": predictions
        })


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

