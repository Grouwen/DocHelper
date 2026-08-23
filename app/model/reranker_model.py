from FlagEmbedding import FlagReranker

from app.config.model_config import reranker_config


def init_reranker_model()->FlagReranker:
    reranker_model = FlagReranker(
            model_name_or_path=reranker_config.file_path,
            device=reranker_config.device,
            use_fp16=reranker_config.bge_fp16
        )

    return reranker_model