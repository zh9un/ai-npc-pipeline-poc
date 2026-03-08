import asyncio
import websockets
import json

TEST_CASES = [
    {"fail_count": 0, "idle_time": 2, "chat_text": "안녕"},
    {"fail_count": 4, "idle_time": 5, "chat_text": "좀 어렵네"},
    {"fail_count": 4, "idle_time": 8, "chat_text": "아 짜증나"},
    {"fail_count": 5, "idle_time": 12, "chat_text": ""},  # 조용한 피로
    {"fail_count": 0, "idle_time": 0, "chat_text": ""},  # 데이터 없음
]

async def test_websocket_client():
    uri = "ws://localhost:8000/ws/npc/"  

    
    async with websockets.connect(uri) as websocket:
        for i, case in enumerate(TEST_CASES):
            message = json.dumps(case, ensure_ascii=False)
            print(f"전송 ({i+1}/{len(TEST_CASES)}): {message}")
            await websocket.send(message)

            response = await websocket.recv()
            print(f"응답 ({i+1}/{len(TEST_CASES)}): {response}")
            print("-" * 30)

            await asyncio.sleep(1)

        print("모든 테스트 케이스 전송 완료.")

if __name__ == "__main__":
    try:
        asyncio.run(test_websocket_client())
    except ConnectionRefusedError:
        print("Error: Connection refused. 웹소켓 서버가 켜져 있는지 확인하세요.")
    except Exception as e:
        print(f"An error occurred: {e}")