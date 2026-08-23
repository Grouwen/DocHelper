import asyncio
from typing import List, Dict, Any

from pymilvus.model.hybrid import BGEM3EmbeddingFunction

import app.model.embedding_model as embedding_model


class EmbeddingOper:
    def __init__(self,embedding_model:BGEM3EmbeddingFunction):
        self.embedding_model = embedding_model

    def embedding_texts(self, texts: List[str]) -> Dict[str, Any]:
        embeddings = self.embedding_model.encode_documents(texts)

        dense_list = []
        sparse_list = []

        for i in range(len(texts)):
            # 处理 dense 向量
            dense_list.append(embeddings["dense"][i].tolist())

            # 处理 sparse 向量
            row = embeddings["sparse"]._getrow(i)
            sparse_dict = dict(zip(row.indices.tolist(), row.data.tolist()))
            sparse_list.append(sparse_dict)

        return {
            "dense": dense_list,
            "sparse": sparse_list
        }

    async def aembedding_texts(self, texts: List[str]) -> Dict[str, Any]:
        return await asyncio.to_thread(self.embedding_texts, texts)

if __name__ == '__main__':
    embedding_model.init_embedding_model()

    oper = EmbeddingOper(embedding_model=embedding_model.embedding_model)
    print(len(oper.embedding_texts(["你好", "你是谁"])["dense"]))
    print(len(oper.embedding_texts(["你好", "你是谁"])["dense"]))