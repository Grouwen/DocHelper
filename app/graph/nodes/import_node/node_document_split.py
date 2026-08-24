# 文档分块：解决大文本无法向量化/推理的问题

from typing import List, Dict, Any

from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter

from app.constants.constants import CHUNK_MAX_SIZE
from app.graph.node_hook import node_hook

from app.graph.states.import_state import ImportState
from app.domain.chunk import Chunk


def split_md_by_title(md_content: str) -> List[Dict[str, Any]]:
    headers_to_split_on = [
        ("#", "一级标题"),
        ("##", "二级标题"),
        ("###", "三级标题"),
    ]

    md_header_splitter = MarkdownHeaderTextSplitter(headers_to_split_on=headers_to_split_on)
    chunks_with_metadata = md_header_splitter.split_text(md_content)

    chunks: List[Dict[str, Any]] = []
    for chunk_with_metadata in chunks_with_metadata:
        chunk = {}
        metadata = chunk_with_metadata.metadata
        content = chunk_with_metadata.page_content
        if metadata:
            title = list(metadata.values())[-1]
            chunk["title"] = title
            chunk["content"] = content
            chunk["title_breadcrumb_path"] = " / ".join(metadata.values())
            chunks.append(chunk)
        else:
            chunk["title"] = "无标题"
            chunk["content"] = content
            chunk["title_breadcrumb_path"] = "无标题"
            chunks.append(chunk)
    return chunks


def split_long_text(chunks: List[Dict[str, Any]], max_len: int = CHUNK_MAX_SIZE) -> List[Dict[str, Any]]:
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=max_len,  # 每块最大 500 字符
        chunk_overlap=50,  # 块间重叠 50 字符
        separators=["\n\n", "\n", "。", "！", "？", " ", ""]  # 针对中文优化的分隔符
    )

    result_chunks: List[Dict[str, Any]] = []
    for chunk in chunks:
        content = chunk["content"]
        title = chunk["title"]
        title_breadcrumb_path = chunk["title_breadcrumb_path"]

        split_content = text_splitter.split_text(content)
        result_chunks.append({
            "title": title,
            "content": split_content,
            "title_breadcrumb_path": title_breadcrumb_path,
        })

    return result_chunks

@node_hook
def node_document_split(state: ImportState):
    md_content = state["md_content"]

    by_title_split_chunks = split_md_by_title(md_content)  # 返回格式：[{"title":"文本","metadata":""}]

    split_long_text_chunks = split_long_text(by_title_split_chunks)  # 返回格式：[{"title":["文本1","文本2"]}]

    # 封装成chunk对象，便于后续操作
    chunks: List[Chunk] = []
    for chunk in split_long_text_chunks:
        contents:List[str] = chunk["content"]
        title:str = chunk["title"]
        title_breadcrumb_path:str = chunk["title_breadcrumb_path"]

        part = 1
        for content in contents:
            chunks.append(Chunk(
                id=0,
                file_id=0,
                title=title,
                content=content,
                title_breadcrumb_path=title_breadcrumb_path,
                part=part,
                dense_vector=[],
                sparse_vector={}
            ))
            part+=1

    return {
        "chunks": chunks,
    }


if __name__ == '__main__':
    with open(r"F:\PythonProjects\DocHelper\out_put\unzips\asebdeasdf\full.md", "r",
              encoding="utf-8") as file:
        md_content = file.read()
    result = node_document_split(ImportState(
        md_content=md_content,
    ))["chunks"]

    print(result)