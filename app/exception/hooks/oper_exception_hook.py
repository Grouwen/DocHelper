import inspect
from functools import wraps

from app.exception.exceptions import AppError, InfraError


def oper_exception_hook(resource: str):
    """
    装饰在 oper 方法上:把任意异常翻译成 InfraError(resource, ...)
    已是 AppError 的原样放行(避免重复包装)
    其余异常统一视为该基础设施调用失败,保留 __cause__ 便于调试
    用法:
        @oper_exception_hook("mongodb")
        async def find_history()
    """

    def _oper_exception_hook(func):

        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except AppError:
                raise
            except Exception as e:
                raise InfraError(resource, f"{func.__qualname__} 失败: {e}", e) from e

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except AppError:
                raise
            except Exception as e:
                raise InfraError(resource, f"{func.__qualname__} 失败: {e}", e) from e

        return async_wrapper if inspect.iscoroutinefunction(func) else sync_wrapper

    return _oper_exception_hook