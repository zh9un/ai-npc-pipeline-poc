import json
from channels.generic.websocket import AsyncWebsocketConsumer
from .llm_service import process_npc_response


class NPCConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # 웹소켓 연결 수락
        await self.accept()

    async def disconnect(self, close_code):
        # 웹소켓 연결 종료 시 처리 (필요시 추가)
        pass

    async def receive(self, text_data=None, bytes_data=None):
        if text_data:
            try:
                # 2. 클라이언트가 보낸 텍스트를 JSON으로 파싱
                data = json.loads(text_data)
                session_id = data.get("session_id", "default_session")

                # 3. llm_service.py의 process_npc_response에 전달 (비동기 호출)
                result_data = await process_npc_response(data, session_id)

                # 4. 결과를 JSON 문자열로 변환하여 클라이언트에게 전송
                await self.send(text_data=json.dumps(result_data, ensure_ascii=False))

            except json.JSONDecodeError:
                # 5. JSON 파싱 에러 처리
                error_response = {
                    "error": "Invalid JSON format received.",
                    "used_fallback": False,
                }
                await self.send(text_data=json.dumps(error_response))
            except Exception as e:
                # 기타 예외 처리
                error_response = {
                    "error": f"An unexpected error occurred: {str(e)}",
                    "used_fallback": False,
                }
                await self.send(text_data=json.dumps(error_response))


class NPCOutcomeConsumer(AsyncWebsocketConsumer):
    """개입 효과 측정을 위한 Consumer"""

    async def connect(self):
        await self.accept()

    async def receive(self, text_data=None, bytes_data=None):
        if text_data:
            try:
                data = json.loads(text_data)

                session_id = data.get("session_id")
                fail_count_post = data.get("fail_count", 0)
                idle_time_post = data.get("idle_time", 0)
                chat_text = data.get("chat_text", "").strip()

                from .models import InterventionLog, InterventionOutcome
                from asgiref.sync import sync_to_async

                # 가장 최근 개입 찾기
                latest_intervention = await sync_to_async(
                    InterventionLog.objects.filter(session_id=session_id).first
                )()

                if latest_intervention:
                    outcome = await sync_to_async(InterventionOutcome.objects.create)(
                        intervention=latest_intervention,
                        fail_count_post=fail_count_post,
                        idle_time_post=idle_time_post,
                        chat_resumed=bool(chat_text),
                    )

                    await sync_to_async(outcome.calculate_recovery)()

                    # InterventionLog 업데이트
                    latest_intervention.fail_count_after = fail_count_post
                    latest_intervention.idle_time_after = idle_time_post
                    latest_intervention.recovery_detected = outcome.recovery
                    await sync_to_async(latest_intervention.save)()

                    response = {
                        "status": "success",
                        "recovery": outcome.recovery,
                        "improvement_score": outcome.improvement_score,
                    }
                else:
                    response = {
                        "status": "error",
                        "message": "No recent intervention found"
                    }

                await self.send(text_data=json.dumps(response))

            except Exception as e:
                await self.send(text_data=json.dumps({
                    "status": "error",
                    "message": str(e)
                }))
