import os
import asyncio
import json
from openai import AsyncOpenAI

# 2. 종속성 제거: OpenAI API 대신 GitHub Models 엔드포인트 사용
api_key = os.environ.get("GITHUB_TOKEN")

client = AsyncOpenAI(
    base_url="https://models.inference.ai.azure.com",
    api_key=api_key,
)

FALLBACK_JSON = {
    "dialogue": "지금은 조금 지쳐 보이네요. 퀘스트는 잠시 멈추고 가볍게 휴식을 취하는 건 어떨까요?",
    "npc_emotion": "calm",
    "trigger_event": "pause_quest_and_rest",
    "used_fallback": True,
}


async def process_npc_response(data: dict) -> dict:
    fail_count = data.get("fail_count", 0)
    idle_time = data.get("idle_time", 0)
    chat_text = data.get("chat_text", "").strip()

    # 1. 조용한 피로 감지 (기획 핵심)
    if fail_count >= 3 and not chat_text:
        return FALLBACK_JSON

    # 2. 일반 상태 LLM 호출 준비
    system_prompt = (
        "You are an empathetic AI-NPC assistant for digital healthcare. "
        "Analyze the user's status and respond with comforting dialogue. "
        "You MUST return your response strictly as a JSON object with the following keys: "
        "'dialogue' (string), 'npc_emotion' (string), 'trigger_event' (string or null), "
        "and 'used_fallback' (boolean, set to false)."
    )
    user_prompt = (
        f"fail_count: {fail_count}, idle_time: {idle_time}s, chat_text: '{chat_text}'"
    )

    async def _call_llm():
        response = await client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            # 3. JSON 강제: 환각 방지를 위해 response_format 적용
            response_format={"type": "json_object"},
        )
        content = response.choices[0].message.content
        return json.loads(content)

    # 4. 타임아웃 방어 (3초)
    try:
        result = await asyncio.wait_for(_call_llm(), timeout=3.0)
        return result
    except (asyncio.TimeoutError, Exception) as e:
        # 3초 지연 또는 기타 에러 발생 시 Fallback 구조 반환
        return FALLBACK_JSON