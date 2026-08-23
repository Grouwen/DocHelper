from pymilvus.model.hybrid import BGEM3EmbeddingFunction

from app.config.model_config import embedding_config

def init_embedding_model()->BGEM3EmbeddingFunction:
    embedding_model = BGEM3EmbeddingFunction(
        model_name=embedding_config.file_path,
        device=embedding_config.device,
        use_fp16=embedding_config.bge_fp16,
        normalize_embeddings=embedding_config.normalize_embeddings
    )

    return embedding_model