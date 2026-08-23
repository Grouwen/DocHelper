from datetime import datetime
from typing import TypedDict, List, Dict, Any

from app.domain.history import History
from app.domain.recall_chunk import RecallChunk
from app.domain.recall_main_body import RecallMainBody


class QueryState(TypedDict):
    task_id: str  # 唯一任务id

    graph_start_time:datetime # 计时回复时间
    graph_end_time:datetime # 计时回复结束时间

    user_input:str # 用户输入
    history_list:List[History] # 聊天记录
    useful:bool # 是否是无用信息

    rewritten_query:str # llm处理后的用户输入
    body_names: List[str] # main_body名字列表

    need_web_search:bool # 是否需要启用web_search
    main_body_list: List[RecallMainBody] # 召回的main_body
    file_ids: List[int] # main_body对应的文件id

    hyde_recall_results:List[RecallChunk] # hyde检索返回的值
    hybrid_recall_results:List[RecallChunk] # hybrid检索返回的值
    web_search_results:List[RecallChunk] # web_search检索返回的值

    rrf_results:List[Dict[str,Any]] # rrf返回的数据

    cross_encoder_results:List[str] # cross_encoder精排返回的数据

    final_context:str # llm最终的上下文
    final_reply:str # llm最终回复内容
    input_tokens:int # 提示词token数
    output_tokens:int # llm输出token数