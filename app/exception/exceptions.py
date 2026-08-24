class AppError(Exception):
    """
    所有自定义异常的基类。
    """
    def __init__(self, message: str, cause: Exception | None = None, node: str | None = None):
        super().__init__(message)
        self.message = message
        self.node = node
        if cause is not None:
            self.__cause__ = cause

class ConfigError(AppError):
    """
    配置/初始化错误。
    """

class InfraError(AppError):
    """
    基础设施层错误(DB/向量库/对象存储/HTTP/检索 后端不可达或超时)。
    """

    def __init__(self, resource: str, message: str, cause: Exception | None = None, node: str | None = None):
        super().__init__(f"[{resource}] {message}", cause, node)
        self.resource = resource

class ValidationError(AppError):
    """
    输入校验错误(session_id 非法、message 为空等)。
    """

class LLMError(AppError):
    """
    大模型调用错误(超时、限流、响应解析失败、usage_metadata 缺失)。
    """

class GraphError(AppError):
    """
    图节点执行中的未知异常(已被 node_hook 兜底包装),附带失败节点名。
    """

    def __init__(self, node: str, message: str, cause: Exception | None = None):
        super().__init__(f"[node:{node}] {message}", cause, node)
        self.node = node