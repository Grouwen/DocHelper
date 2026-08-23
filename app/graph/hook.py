import inspect
import time
from functools import wraps
from logging import Logger
from typing import Any, Callable
from app.logr.logr import get_logger


def node_hook(func: Callable) -> Callable:
    logger = get_logger("NodeHook")
    raw = getattr(func, "__wrapped__", func)

    if inspect.iscoroutinefunction(raw) or inspect.iscoroutinefunction(func):
        @wraps(func)
        async def async_wrapper(state: Any, **kwargs: Any) -> Any:

            start = _before_hook(state,func,logger)
            result = await func(state, **kwargs)
            _after_hook(func, start, result,logger)

            return result
        return async_wrapper

    else:
        @wraps(func)
        def sync_wrapper(state: Any, **kwargs: Any) -> Any:

            start = _before_hook(state, func,logger)
            result = func(state, **kwargs)
            _after_hook(func, start, result,logger)

            return result
        return sync_wrapper

def _before_hook(state: Any,func:Callable,logger:Logger) -> float:
    start = time.time()
    logger.info(f"🔵 [BEFORE] {func.__name__} -> 输入: {str(state)[:500]}")

    return start

def _after_hook(func:Callable,start:float,result:Any,logger:Logger):
    elapsed = time.time() - start
    logger.info(f"🟢 [AFTER]  {func.__name__} -> 输出: {str(result)[:500]}\n{func.__name__} | 耗时：{elapsed:.4f}秒")