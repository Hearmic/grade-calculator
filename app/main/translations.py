"""
Translation strings for grade prediction application.
Supports: English (en), Kazakh (kk), Russian (ru)
"""

TRANSLATIONS = {
    'grade_predictions_remaining': {
        'en': 'Grade predictions for remaining assessments:',
        'kk': 'Қалған бағалаулар үшін баға болжамдары:',
        'ru': 'Прогнозы оценок для оставшихся оценок:'
    },
    'grade_predictions_assignments': {
        'en': 'Grade predictions with additional perfect assignments:',
        'kk': 'Қосымша тамаша тапсырмалармен баға болжамдары:',
        'ru': 'Прогнозы оценок с дополнительными идеальными заданиями:'
    },
    'already_highest': {
        'en': 'Congratulations! You already have the highest grade (5).',
        'kk': 'Құттықтаймыз! Сізде қазірдің өзінде ең жоғары баға (5) бар.',
        'ru': 'Поздравляем! У вас уже есть самая высокая оценка (5).'
    },
    'current_grade': {
        'en': 'Current Grade',
        'kk': 'Ағымды баға',
        'ru': 'Текущая оценка'
    },
    'current_percent': {
        'en': 'Current %',
        'kk': 'Ағымды %',
        'ru': 'Текущий %'
    },
    'already_reached': {
        'en': 'Already reached',
        'kk': 'Қазірдің өзінде жетті',
        'ru': 'Уже достигнуто'
    },
    'reachable': {
        'en': 'Reachable',
        'kk': 'Қол жетімді',
        'ru': 'Достижимо'
    },
    'not_reachable': {
        'en': 'Not reachable',
        'kk': 'Қол жетімсіз',
        'ru': 'Недостижимо'
    },
    'final_exam': {
        'en': 'Final Exam',
        'kk': 'Қорытынды емтихан',
        'ru': 'Финальный экзамен'
    },
    'perfect_assignments': {
        'en': 'Perfect Assignments',
        'kk': 'Тамаша тапсырмалар',
        'ru': 'Идеальные задания'
    },
    'invalid_grades': {
        'en': 'All grades must be between 0 and 10',
        'kk': 'Барлық бағалар 0 және 10 арасында болуы керек',
        'ru': 'Все оценки должны быть между 0 и 10'
    },
    'invalid_request': {
        'en': 'Invalid request',
        'kk': 'Жарамсыз сұрау',
        'ru': 'Неверный запрос'
    },
    'error': {
        'en': 'Error',
        'kk': 'Қате',
        'ru': 'Ошибка'
    }
}


def get_translation(key, language='en'):
    """
    Get a translated string.
    
    Args:
        key: Translation key
        language: Language code (en, kk, ru)
    
    Returns:
        Translated string or English fallback
    """
    if key in TRANSLATIONS:
        return TRANSLATIONS[key].get(language, TRANSLATIONS[key].get('en', key))
    return key
