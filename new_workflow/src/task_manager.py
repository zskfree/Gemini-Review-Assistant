import threading
import queue
import json
import time
from typing import Dict, Any, Generator

class MessageAnnouncer:
    """SSE 消息广播器"""
    def __init__(self):
        self.listeners = []
        self.lock = threading.Lock()

    def listen(self):
        q = queue.Queue(maxsize=10)
        with self.lock:
            self.listeners.append(q)
        return q

    def announce(self, msg: str):
        with self.lock:
            for i in reversed(range(len(self.listeners))):
                try:
                    self.listeners[i].put_nowait(msg)
                except queue.Full:
                    del self.listeners[i]

class TaskManager:
    """
    任务管理器
    负责管理全局进度状态和通过 SSE 广播消息
    """
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if not cls._instance:
            with cls._lock:
                if not cls._instance:
                    cls._instance = super(TaskManager, cls).__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if getattr(self, "_initialized", False):
            return
            
        self.announcer = MessageAnnouncer()
        self.progress = {
            "current": 0,
            "total": 0,
            "last_item": "等待中..."
        }
        self.lock = threading.Lock()
        self._initialized = True

    def format_sse(self, data: str, event=None) -> str:
        msg = f"data: {data}\n\n"
        if event:
            msg = f"event: {event}\n{msg}"
        return msg

    def update_progress(self, current: int, total: int, message: str):
        """更新进度并通过 SSE 广播"""
        with self.lock:
            self.progress["current"] = current
            self.progress["total"] = total
            self.progress["last_item"] = message
        
        data = json.dumps({'current': current, 'total': total, 'message': message})
        self.announcer.announce(self.format_sse(data, event='progress'))

    def get_progress(self) -> Dict[str, Any]:
        with self.lock:
            return self.progress.copy()

    def listen(self) -> Generator[str, None, None]:
        """Generator for Flask Response"""
        messages = self.announcer.listen()
        while True:
            msg = messages.get()
            yield msg

    def announce_event(self, event_name: str, data: Dict[str, Any]):
        """广播自定义事件"""
        msg = self.format_sse(json.dumps(data), event=event_name)
        self.announcer.announce(msg)

    def announce_error(self, event_name: str, error_message: str):
        """广播错误信息"""
        data = {"status": "error", "message": error_message}
        self.announce_event(event_name, data)

# 全局单例
task_manager = TaskManager()
