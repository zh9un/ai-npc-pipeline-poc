import random
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from npc.models import InterventionLog, InterventionOutcome

class Command(BaseCommand):
    help = 'Seeds the database with test intervention data for patient_001 and patient_002'

    def handle(self, *args, **kwargs):
        self.stdout.write('Seeding data...')
        
        # 기존 데이터 삭제
        InterventionLog.objects.filter(session_id__in=['patient_001', 'patient_002']).delete()

        now = timezone.now()

        # 세션 1: patient_001 (회복 성공 패턴)
        # 개입 5회, 4회 recovery=True, 연속 실패 없음, alert=False 상태
        start_time_001 = now - timedelta(days=5)
        
        for i in range(5):
            t = start_time_001 + timedelta(days=i, hours=2)
            # 2번째 개입만 실패(False), 나머지는 성공(True) -> 연속 실패 없음
            is_recovery = False if i == 1 else True
            
            log = InterventionLog.objects.create(
                session_id='patient_001',
                fail_count_at_intervention=random.randint(1, 3),
                idle_time_at_intervention=random.randint(10, 30),
                trigger_reason='silent_fatigue',
                used_fallback=False,
                npc_dialogue=f'잘 하고 계시네요! (개입 {i+1})',
                npc_emotion='smile',
                trigger_event='cheer',
            )
            
            # auto_now_add가 있으므로 생성 후 timestamp를 덮어씌움
            log.timestamp = t
            
            log.fail_count_after = 0 if is_recovery else log.fail_count_at_intervention + 1
            log.recovery_detected = is_recovery
            log.save()
            
            outcome = InterventionOutcome.objects.create(
                intervention=log,
                fail_count_post=log.fail_count_after,
                idle_time_post=10 if is_recovery else 40,
                chat_resumed=True,
                recovery=is_recovery,
                improvement_score=1.0 if is_recovery else 0.0
            )
            # 측정 시간도 임의로 맞춤
            outcome.measured_at = t + timedelta(minutes=5)
            outcome.save()

        # 세션 2: patient_002 (악화 패턴)
        # 개입 6회, 마지막 3회 연속 recovery=False, alert=True 상태 유발
        start_time_002 = now - timedelta(days=6)
        
        for i in range(6):
            t = start_time_002 + timedelta(days=i, hours=2)
            # 인덱스 0, 1, 2는 성공(True), 3, 4, 5는 연속 실패(False)
            is_recovery = False if i >= 3 else True
            
            log = InterventionLog.objects.create(
                session_id='patient_002',
                fail_count_at_intervention=random.randint(1, 3) if is_recovery else 3 + (i - 2),
                idle_time_at_intervention=random.randint(20, 60),
                trigger_reason='api_error',
                used_fallback=True,
                npc_dialogue=f'괜찮으신가요? (개입 {i+1})',
                npc_emotion='sad',
                trigger_event='ask',
            )
            
            log.timestamp = t
            
            log.fail_count_after = 0 if is_recovery else log.fail_count_at_intervention + 1
            log.recovery_detected = is_recovery
            log.save()
            
            outcome = InterventionOutcome.objects.create(
                intervention=log,
                fail_count_post=log.fail_count_after,
                idle_time_post=20 if is_recovery else 60,
                chat_resumed=is_recovery,
                recovery=is_recovery,
                improvement_score=1.0 if is_recovery else -0.5
            )
            outcome.measured_at = t + timedelta(minutes=5)
            outcome.save()

        self.stdout.write(self.style.SUCCESS('Successfully seeded patient_001 and patient_002 intervention data.'))
