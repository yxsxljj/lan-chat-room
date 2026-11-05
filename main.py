"""简易聊天室后端：一个静态页面 + 一条 WebSocket 长连接。"""

import socket
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse

BASE_DIR = Path(__file__).parent
MAX_HISTORY = 100
HOST = "0.0.0.0"  # 监听所有网卡，局域网里的设备才连得进来
PORT = 9999

app = FastAPI(title="简易聊天室")

# 最近的消息，新进来的人先看到这些
history: list[dict] = []


def now() -> str:
    return datetime.now().strftime("%H:%M")


class Room:
    """在线用户集合：键是连接，值是昵称。"""

    def __init__(self) -> None:
        self.clients: dict[WebSocket, str] = {}

    def leave(self, ws: WebSocket) -> str | None:
        return self.clients.pop(ws, None)

    async def broadcast(self, payload: dict) -> None:
        # 发送失败的连接说明对方已经掉线，顺手清理掉
        for ws in list(self.clients):
            try:
                await ws.send_json(payload)
            except Exception:
                self.leave(ws)

    async def announce_count(self) -> None:
        await self.broadcast({"type": "online", "count": len(self.clients)})


room = Room()


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(BASE_DIR / "static" / "index.html")


@app.websocket("/ws")
async def chat(ws: WebSocket) -> None:
    await ws.accept()
    name = ""

    try:
        # 第一帧必须是加入请求，拿到昵称
        hello = await ws.receive_json()
        if hello.get("type") != "join":
            await ws.close()
            return

        name = (hello.get("name") or "").strip()[:20] or "匿名"
        room.clients[ws] = name

        await ws.send_json({"type": "history", "messages": history})
        await room.broadcast({"type": "system", "text": f"{name} 加入了聊天室", "time": now()})
        await room.announce_count()

        while True:
            data = await ws.receive_json()
            if data.get("type") != "message":
                continue

            text = (data.get("text") or "").strip()[:500]
            if not text:
                continue

            message = {"type": "message", "name": name, "text": text, "time": now()}
            history.append(message)
            if len(history) > MAX_HISTORY:
                history.pop(0)
            await room.broadcast(message)

    except WebSocketDisconnect:
        pass
    finally:
        if room.leave(ws) is not None:
            await room.broadcast(
                {"type": "system", "text": f"{name} 离开了聊天室", "time": now()}
            )
            await room.announce_count()


def lan_ip() -> str:
    """取本机在局域网里的 IP（不会真的发数据包）。"""
    probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        probe.connect(("8.8.8.8", 80))
        return probe.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        probe.close()


if __name__ == "__main__":
    import uvicorn

    ip = lan_ip()
    print()
    print("  聊天室已启动")
    print(f"  本机浏览器打开   http://127.0.0.1:{PORT}")
    print(f"  局域网其他人打开 http://{ip}:{PORT}")
    print(flush=True)
    uvicorn.run(app, host=HOST, port=PORT)
