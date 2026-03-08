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

                # 3. llm_service.py의 process_npc_response에 전달 (비동기 호출)
                result_data = await process_npc_response(data)

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