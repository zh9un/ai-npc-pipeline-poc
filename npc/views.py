from django.http import JsonResponse
from django.db.models import Avg
from .models import InterventionLog, InterventionOutcome

def session_summary(request, session_id):
    """
    치료자용 세션 요약 HTTP API
    - 개입 횟수, 회복/비회복 횟수, 평균 개선율 반환
    - 연속 2회 이상 회복 실패 시 alert 발생
    """
    if request.method != 'GET':
        return JsonResponse({'error': 'GET method required'}, status=405)

    # 해당 세션의 로그를 최신순으로 조회
    logs = InterventionLog.objects.filter(session_id=session_id).order_by('-timestamp')
    total_interventions = logs.count()

    if total_interventions == 0:
        return JsonResponse({
            "session_id": session_id,
            "total_interventions": 0,
            "message": "해당 세션에 대한 개입 기록이 없습니다."
        })

    # 회복 / 비회복 횟수 계산
    recovery_count = logs.filter(recovery_detected=True).count()
    no_recovery_count = logs.filter(recovery_detected=False).count()

    # 평균 개선율 계산
    outcomes = InterventionOutcome.objects.filter(intervention__session_id=session_id)
    avg_score = outcomes.aggregate(Avg('improvement_score'))['improvement_score__avg'] or 0.0

    # 연속 회복 실패 감지 로직
    consecutive_no_recovery = 0
    for log in logs:
        if log.recovery_detected is False:
            consecutive_no_recovery += 1
        elif log.recovery_detected is True:
            # 회복된 기록이 나오면 연속 실패 카운트 중단
            break

    alert = consecutive_no_recovery >= 2

    return JsonResponse({
        "session_id": session_id,
        "total_interventions": total_interventions,
        "recovery_count": recovery_count,
        "no_recovery_count": no_recovery_count,
        "avg_improvement_score": round(avg_score, 2),
        "consecutive_no_recovery": consecutive_no_recovery,
        "alert": alert
    })