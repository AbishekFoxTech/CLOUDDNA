CATEGORY_KEYWORDS = {
    'academic': [
        'university', 'thesis', 'syllabus', 'lecture', 'assignment', 'course',
        'academic', 'student', 'professor', 'curriculum', 'dissertation', 'exam',
    ],
    'finance': [
        'invoice', 'budget', 'expense', 'revenue', 'balance sheet', 'tax',
        'payment', 'financial', 'salary', 'accounting', 'audit', 'income statement',
    ],
    'research': [
        'research', 'study', 'methodology', 'hypothesis', 'experiment',
        'dataset', 'machine learning', 'artificial intelligence', 'analysis',
        'findings', 'literature review', 'abstract',
    ],
    'medical': [
        'patient', 'diagnosis', 'treatment', 'medical', 'clinical',
        'prescription', 'symptom', 'hospital', 'doctor', 'health', 'physician',
    ],
    'business': [
        'business', 'strategy', 'marketing', 'client', 'proposal', 'meeting',
        'stakeholder', 'company', 'management', 'sales', 'quarterly', 'roadmap',
    ],
    'personal': [
        'diary', 'personal', 'family', 'vacation', 'birthday', 'letter',
        'journal', 'note to self',
    ],
    'legal': [
        'agreement', 'contract', 'clause', 'legal', 'law', 'terms and conditions',
        'liability', 'party', 'jurisdiction', 'plaintiff', 'defendant', 'hereby',
    ],
    'reports': [
        'report', 'quarterly', 'annual report', 'kpi', 'performance',
        'overview', 'summary of findings', 'executive summary',
    ],
}

IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg'}


def detect_category(text, title='', file_type=''):
    if (file_type or '').lower().lstrip('.') in IMAGE_EXTENSIONS:
        return 'images'

    combined = f'{title} {text}'.lower()
    if not combined.strip():
        return 'others'

    scores = {}
    for category, terms in CATEGORY_KEYWORDS.items():
        score = sum(combined.count(term) for term in terms)
        if score:
            scores[category] = score

    if not scores:
        return 'others'
    return max(scores, key=scores.get)
