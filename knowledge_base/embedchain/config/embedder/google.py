from typing import Optional

from knowledge_base.embedchain.config.embedder.base import BaseEmbedderConfig
from knowledge_base.embedchain.helpers.json_serializable import register_deserializable


@register_deserializable
class GoogleAIEmbedderConfig(BaseEmbedderConfig):
    def __init__(
        self,
        model: Optional[str] = None,
        deployment_name: Optional[str] = None,
        task_type: Optional[str] = None,
        title: Optional[str] = None,
    ):
        super().__init__(model, deployment_name)
        self.task_type = task_type or "retrieval_document"
        self.title = title or "Embeddings for Embedchain"
