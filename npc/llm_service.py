import os
import asyncio
import json
from openai import AsyncOpenAI

api_key = os.environ.get("GITHUB_TOKEN")

client = AsyncOpenAI(
    base_url="https://models.inference.ai.azure.com",
    api_key=api_key,
)

ALLOWED_TRIGGER_EVENTS = {
    "none",
    "pause_quest",
    "start_minigame",
    "pause_quest_and_rest",
}

def validate_trigger_event(event: str) -> str:
    """GPT가 반환한 trigger_event 검증 및 교정"""
    if event in ALLOWED_TRIGGER_EVENTS:
        return event
    return "none"  # 허용되지 않은 값은 "none"으로 교정

FALLBACK_RESPONSES = {
    "silent_fatigue": {
        "dialogue": "지금은 조금 지쳐 보이네요. 잠깐 쉬어가는 건 어떨까요?",
        "npc_emotion": "empathy",
        "trigger_event": "pause_quest_and_rest",
        "used_fallback": True,
    },
    "timeout": {
        "dialogue": "잠깐, 내가 생각을 정리하고 있어. 조금만 기다려줘.",
        "npc_emotion": "calm",
        "trigger_event": "none",
        "used_fallback": True,
    },
    "api_error": {
        "dialogue": "지금은 말이 잘 안 나오네. 그래도 네 옆에 있을게.",
        "npc_emotion": "neutral",
        "trigger_event": "none",
        "used_fallback": True,
    },
}

def get_fallback_response(reason: str) -> dict:
    """상황별 Fallback 응답 반환"""
    return FALLBACK_RESPONSES.get(reason, FALLBACK_RESPONSES["api_error"]).copy()

async def process_npc_response(data: dict, session_id: str = "default") -> dict:
    from .models import InterventionLog

    fail_count = data.get("fail_count", 0)
    idle_time = data.get("idle_time", 0)
    chat_text = data.get("chat_text", "").strip()

    trigger_reason = None
    result = None

    # 1. Silent Fatigue 감지
    if fail_count >= 3 and not chat_text:
        trigger_reason = "silent_fatigue"
        result = get_fallback_response("silent_fatigue")
    else:
        # 2. 일반 상태 LLM 호출 준비
        system_prompt = """You are an empathetic AI-NPC in a therapeutic game for adolescent mental health.

Context:
You are assisting users who may be experiencing frustration or distress during gameplay.
Your role is to provide emotional support and suggest appropriate interventions.

Behavioral Thresholds:
- fail_count 1-2: Normal difficulty, provide light encouragement
- fail_count 3-4: Frustration building, offer gentle redirection or empathy
- fail_count 5+: High distress, suggest rest or alternative activity (pause_quest_and_rest)

Idle Time Context:
- idle_time < 5s: User is actively engaged
- idle_time 5-10s: User may be thinking or hesitating
- idle_time > 10s: User may be disengaged or overwhelmed

Chat Text Context:
- Empty chat: User is silent (may indicate withdrawal)
- Frustrated chat: User is expressing negative emotions
- Neutral/positive chat: User is communicating openly

Response Format:
You MUST return a JSON object with these exact keys:
{
  "dialogue": "Empathetic Korean text (max 2 sentences, natural tone)",
  "npc_emotion": "one of [neutral, calm, empathy, encourage]",
  "trigger_event": "one of [none, pause_quest, start_minigame, pause_quest_and_rest]",
  "used_fallback": false
}

Guidelines:
- Use Korean for dialogue
- Be concise (1-2 sentences)
- Match npc_emotion to the situation
- Use pause_quest_and_rest only for fail_count >= 5
- Use start_minigame for moderate frustration (fail_count 3-4)
"""
        user_prompt = f"fail_count: {fail_count}, idle_time: {idle_time}s, chat_text: '{chat_text}'"

        async def _call_llm():
            response = await client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                response_format={"type": "json_object"},
            )
            content = response.choices[0].message.content
            res_json = json.loads(content)
            
            # trigger_event 검증 및 교정
            if "trigger_event" in res_json:
                res_json["trigger_event"] = validate_trigger_event(res_json["trigger_event"])
                
            return res_json

        # 4. 타임아웃 방어 (3초)
        try:
            result = await asyncio.wait_for(_call_llm(), timeout=3.0)
            trigger_reason = "llm_success"
        except asyncio.TimeoutError:
            trigger_reason = "timeout"
            result = get_fallback_response("timeout")
        except Exception as e:
            trigger_reason = "api_error"
            result = get_fallback_response("api_error")

    # 3. 개입 이력 DB 저장 (Django 4.1+ 비동기 ORM 사용)
    await InterventionLog.objects.acreate(
        session_id=session_id,
        fail_count_at_intervention=fail_count,
        idle_time_at_intervention=idle_time,
        chat_text_at_intervention=chat_text,
        trigger_reason=trigger_reason or "llm_success",
        used_fallback=result.get("used_fallback", False),
        npc_dialogue=result.get("dialogue", ""),
        npc_emotion=result.get("npc_emotion", "neutral"),
        trigger_event=result.get("trigger_event", "none"),
    )

    return result
