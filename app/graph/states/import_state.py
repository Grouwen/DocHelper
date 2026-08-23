from pathlib import Path
from typing import TypedDict, List

from app.domain.chunk import Chunk
from app.domain.main_body import MainBody


class ImportState(TypedDict):
    task_id: str  # 唯一任务id

    origin_file_name: str  # 用户上传时的文件名（后续提取main_item失败时，才使用）

    local_file_path: str  # 用户上传后的文件地址（uuid编码）
    unique_file_name: str # 经过处理后的文件名
    file_type: str  # 文件类型pdf或md
    md_content: str  # markdown文件内容
    md_file_path:str # markdown文件本地path

    chunks:List[Chunk] # 切块
    main_bodys:List[MainBody] # 文档的描述主体，比如《烫金机使用指南》主体就是烫金机


if __name__ == '__main__':
    file_path = Path(r"F:\PythonProjects\DocHelper\out_put\docs\699f93d7-f24b-4d95-89f5-daefc29a4d42.pdf")
    print(ImportState(
        task_id="task_id",
        origin_file_name=file_path.name,
        local_file_path=str(file_path),
        file_type="",
        md_content="",
        unique_file_name=file_path.name,
        md_file_path=""
    ))