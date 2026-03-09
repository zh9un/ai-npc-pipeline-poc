from django.contrib import admin
from django.utils.html import format_html
from .models import InterventionLog, InterventionOutcome

# Admin 전체 헤더와 타이틀 변경
admin.site.site_header = "Mindtrekking DTx 관리자 패널"
admin.site.site_title = "DTx 관리자"
admin.site.index_title = "Mindtrekking 데이터 대시보드"

@admin.register(InterventionLog)
class InterventionLogAdmin(admin.ModelAdmin):
    list_display = [
        'session_id',
        'get_trigger_reason_display_korean',
        'fail_count_at_intervention',
        'npc_dialogue_short',
        'recovery_status',
        'timestamp',
    ]
    list_filter = ['trigger_reason', 'used_fallback', 'recovery_detected']
    search_fields = ['session_id', 'npc_dialogue']
    readonly_fields = ['timestamp']
    date_hierarchy = 'timestamp'
    
    # 보기 좋게 필드들을 그룹화
    fieldsets = (
        ('기본 정보', {
            'fields': ('session_id', 'timestamp')
        }),
        ('개입 당시 유저 상태', {
            'fields': ('fail_count_at_intervention', 'idle_time_at_intervention', 'chat_text_at_intervention')
        }),
        ('AI-NPC 개입 내용', {
            'fields': ('trigger_reason', 'used_fallback', 'npc_dialogue', 'npc_emotion', 'trigger_event')
        }),
        ('개입 이후 상태 (효과 측정 후 자동 기록)', {
            'fields': ('fail_count_after', 'idle_time_after', 'recovery_detected')
        }),
    )

    def get_trigger_reason_display_korean(self, obj):
        return obj.get_trigger_reason_display()
    get_trigger_reason_display_korean.short_description = "발생 원인"

    def npc_dialogue_short(self, obj):
        if len(obj.npc_dialogue) > 20:
            return f"{obj.npc_dialogue[:20]}..."
        return obj.npc_dialogue
    npc_dialogue_short.short_description = "대사 요약"

    def recovery_status(self, obj):
        if obj.recovery_detected is True:
            return format_html('<span style="color: green; font-weight: bold;">호전됨</span>')
        elif obj.recovery_detected is False:
            return format_html('<span style="color: red; font-weight: bold;">미호전</span>')
        return format_html('<span style="color: gray;">대기중</span>')
    recovery_status.short_description = "상태 호전 여부"


@admin.register(InterventionOutcome)
class InterventionOutcomeAdmin(admin.ModelAdmin):
    list_display = [
        'get_session_id',
        'fail_count_post',
        'recovery_badge',
        'improvement_score_percent',
        'measured_at',
    ]
    list_filter = ['recovery', 'chat_resumed']
    readonly_fields = ['measured_at']
    date_hierarchy = 'measured_at'

    def get_session_id(self, obj):
        return obj.intervention.session_id
    get_session_id.short_description = "세션 ID"

    def recovery_badge(self, obj):
        if obj.recovery:
            return format_html('<span style="background-color: #28a745; color: white; padding: 3px 8px; border-radius: 4px; font-weight: bold;">호전됨 (Recovery)</span>')
        return format_html('<span style="background-color: #dc3545; color: white; padding: 3px 8px; border-radius: 4px; font-weight: bold;">미호전</span>')
    recovery_badge.short_description = "판정 결과"

    def improvement_score_percent(self, obj):
        if obj.improvement_score is not None:
            return f"{obj.improvement_score * 100:.1f} %"
        return "N/A"
    improvement_score_percent.short_description = "개선율"
