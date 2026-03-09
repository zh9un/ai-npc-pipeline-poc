from django.db import models

class InterventionLog(models.Model):
    """AI-NPC 개입 이력 추적 모델"""

    # 세션 식별
    session_id = models.CharField(max_length=100, db_index=True, verbose_name="세션 ID")
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name="개입 발생 시간")

    # 개입 시점 상태
    fail_count_at_intervention = models.IntegerField(verbose_name="당시 실패 횟수")
    idle_time_at_intervention = models.IntegerField(verbose_name="당시 대기 시간(초)")
    chat_text_at_intervention = models.TextField(blank=True, verbose_name="당시 입력한 채팅")

    # 개입 내용
    trigger_reason = models.CharField(
        max_length=50,
        choices=[
            ('silent_fatigue', '조용한 피로 (Silent Fatigue)'),
            ('timeout', 'API 응답 지연 (Timeout)'),
            ('api_error', 'API 통신 오류 (Error)'),
            ('llm_success', 'AI 정상 응답 (LLM Success)'),
        ],
        verbose_name="개입 발생 원인"
    )
    used_fallback = models.BooleanField(verbose_name="대체 응답(Fallback) 사용 여부")
    npc_dialogue = models.TextField(verbose_name="NPC 출력 대사")
    npc_emotion = models.CharField(max_length=50, verbose_name="NPC 감정 상태")
    trigger_event = models.CharField(max_length=50, verbose_name="발동된 게임 이벤트")

    # 개입 이후 상태 (나중에 채워짐)
    fail_count_after = models.IntegerField(null=True, blank=True, verbose_name="개입 후 실패 횟수")
    idle_time_after = models.IntegerField(null=True, blank=True, verbose_name="개입 후 대기 시간")
    recovery_detected = models.BooleanField(null=True, blank=True, verbose_name="상태 호전(Recovery) 여부")

    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['session_id', '-timestamp']),
            models.Index(fields=['trigger_reason']),
        ]
        verbose_name = "NPC 개입 기록 (Intervention Log)"
        verbose_name_plural = "1. NPC 개입 기록 모아보기"

    def __str__(self):
        return f"[{self.session_id}] {self.get_trigger_reason_display()} ({self.timestamp.strftime('%Y-%m-%d %H:%M')})"

class InterventionOutcome(models.Model):
    """개입 효과 측정 모델"""

    intervention = models.ForeignKey(
        InterventionLog,
        on_delete=models.CASCADE,
        related_name='outcomes',
        verbose_name="연결된 개입 기록"
    )

    # 개입 후 상태
    fail_count_post = models.IntegerField(verbose_name="5회 행동 후 실패 횟수")
    idle_time_post = models.IntegerField(verbose_name="5회 행동 후 대기 시간")
    chat_resumed = models.BooleanField(default=False, verbose_name="채팅 재개 여부")

    # 효과 판정
    recovery = models.BooleanField(verbose_name="상태 호전(Recovery) 판정")
    improvement_score = models.FloatField(null=True, blank=True, verbose_name="개선율(Score)")

    measured_at = models.DateTimeField(auto_now_add=True, verbose_name="효과 측정 시간")

    class Meta:
        ordering = ['-measured_at']
        verbose_name = "개입 효과 측정 결과 (Outcome)"
        verbose_name_plural = "2. 개입 효과 측정 결과 모아보기"

    def calculate_recovery(self):
        """효과 판정 로직"""
        fail_before = self.intervention.fail_count_at_intervention
        fail_after = self.fail_count_post

        self.recovery = (fail_after < fail_before) or (fail_after < 3)

        if fail_before > 0:
            self.improvement_score = (fail_before - fail_after) / fail_before
        else:
            self.improvement_score = 0.0

        self.save()
