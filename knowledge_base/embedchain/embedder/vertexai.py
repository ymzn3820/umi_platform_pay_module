from typing import Optional

from langchain.embeddings import VertexAIEmbeddings

from knowledge_base.embedchain.config import BaseEmbedderConfig
from knowledge_base.embedchain.embedder.base import BaseEmbedder
from knowledge_base.embedchain.models import VectorDimensions


class VertexAIEmbedder(BaseEmbedder):
    def __init__(self, config: Optional[BaseEmbedderConfig] = None):
        super().__init__(config=config)

        embeddings = VertexAIEmbeddings(model_name=config.model)
        embedding_fn = BaseEmbedder._langchain_default_concept(embeddings)
        self.set_embedding_fn(embedding_fn=embedding_fn)

        vector_dimension = VectorDimensions.VERTEX_AI.value
        self.set_vector_dimension(vector_dimension=vector_dimension)
