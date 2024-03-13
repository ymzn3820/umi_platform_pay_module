from typing import Dict, Optional, Tuple

from knowledge_base.embedchain.config.vectordb.base import BaseVectorDbConfig
from knowledge_base.embedchain.helpers.json_serializable import register_deserializable


@register_deserializable
class OpenSearchDBConfig(BaseVectorDbConfig):
    def __init__(
        self,
        opensearch_url: str,
        http_auth: Tuple[str, str],
        # TODO 测试改为1024， 默认1536
        vector_dimension: int = 1536,
        # vector_dimension: int = 1024,
        collection_name: Optional[str] = None,
        dir: Optional[str] = None,
        **extra_params: Dict[str, any],
    ):
        """
        Initializes a configuration class instance for an OpenSearch client.

        :param collection_name: Default name for the collection, defaults to None
        :type collection_name: Optional[str], optional
        :param opensearch_url: URL of the OpenSearch domain
        :type opensearch_url: str, Eg, "http://localhost:9200"
        :param http_auth: Tuple of username and password
        :type http_auth: Tuple[str, str], Eg, ("username", "password")
        :param vector_dimension: Dimension of  the vector, defaults to 1536 (openai embedding model)
        :type vector_dimension: int, optional
        :param dir: Path to the database directory, where the database is stored, defaults to None
        :type dir: Optional[str], optional
        """
        self.opensearch_url = opensearch_url
        self.http_auth = http_auth
        self.vector_dimension = vector_dimension
        self.extra_params = extra_params

        super().__init__(collection_name=collection_name, dir=dir)
