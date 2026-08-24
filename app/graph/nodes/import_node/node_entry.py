# 流程入口：参数初始化、输入校验
from pathlib import Path

from app.exception.hooks.node_hook import node_hook
from app.graph.states.import_state import ImportState


@node_hook
def node_entry(state:ImportState):
    md_file_path = ""

    # 校验suffix并设置state的type
    # 若为md，设置md_path，否则不设置
    file_suffix = Path(state["origin_file_name"]).suffix
    if file_suffix == ".pdf":
        file_type = "pdf"
    elif file_suffix == ".md":
        file_type = "md"
        md_file_path = state["local_file_path"]
    elif file_suffix == ".markdown":
        file_type = "md"
    else:
        raise ValueError(f"不支持的文件类型: {file_suffix}")

    # 校验local_file_path
    local_file_path = state["local_file_path"]
    if not local_file_path or not Path(local_file_path).exists():
        raise FileNotFoundError(f"{local_file_path}不存在")

    # 校验unique_file_name
    unique_file_name = state["unique_file_name"]
    if not unique_file_name:
        raise FileNotFoundError(f"{unique_file_name}不存在")

    return {
        "file_type": file_type,
        "md_file_path": md_file_path,
    }