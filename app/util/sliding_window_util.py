import asyncio
import time
from collections import deque


def make_sliding_window(limit: int, window: float):
    """
    滑动窗口日志限流（纯异步闭包，无 class）

    用法:
        acquire = make_sliding_window(limit=500, window=60.0)
        await acquire()
        await api_call()
    """
    logs = deque()

    async def acquire():
        while True:
            now = time.time()
            cutoff = now - window

            # 清理过期日志
            while logs and logs[0] <= cutoff:
                logs.popleft()

            # 有名额直接通过
            if len(logs) < limit:
                logs.append(now)
                return

            # 没名额就等到最早那条过期
            wait = logs[0] + window - time.time()
            await asyncio.sleep(max(0.001, wait))

    return acquire