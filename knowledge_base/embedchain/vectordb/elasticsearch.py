import logging
from typing import Any, Dict, List, Optional, Tuple, Union

try:
    from elasticsearch import Elasticsearch
    from elasticsearch.helpers import bulk
except ImportError:
    raise ImportError(
        "Elasticsearch requires extra dependencies. Install with `pip install --upgrade embedchain[elasticsearch]`"
    ) from None

from knowledge_base.embedchain.config import ElasticsearchDBConfig
from knowledge_base.embedchain.helpers.json_serializable import register_deserializable
from knowledge_base.embedchain.utils import chunks
from knowledge_base.embedchain.vectordb.base import BaseVectorDB


@register_deserializable
class ElasticsearchDB(BaseVectorDB):
    """
    Elasticsearch as vector database
    """

    BATCH_SIZE = 100

    def __init__(
        self,
        config: Optional[ElasticsearchDBConfig] = None,
        es_config: Optional[ElasticsearchDBConfig] = None,  # Backwards compatibility
    ):
        """Elasticsearch as vector database.

        :param config: Elasticsearch database config, defaults to None
        :type config: ElasticsearchDBConfig, optional
        :param es_config: `es_config` is supported as an alias for `config` (for backwards compatibility),
        defaults to None
        :type es_config: ElasticsearchDBConfig, optional
        :raises ValueError: No config provided
        """
        if config is None and es_config is None:
            self.config = ElasticsearchDBConfig()
        else:
            if not isinstance(config, ElasticsearchDBConfig):
                raise TypeError(
                    "config is not a `ElasticsearchDBConfig` instance. "
                    "Please make sure the type is right and that you are passing an instance."
                )
            self.config = config or es_config
        if self.config.ES_URL:
            self.client = Elasticsearch(self.config.ES_URL, **self.config.ES_EXTRA_PARAMS)
        elif self.config.CLOUD_ID:
            self.client = Elasticsearch(cloud_id=self.config.CLOUD_ID, **self.config.ES_EXTRA_PARAMS)
        else:
            raise ValueError(
                "Something is wrong with your config. Please check again - `https://docs.ai/components/vector-databases#elasticsearch`"  # noqa: E501
            )

        # Call parent init here because embedder is needed
        super().__init__(config=self.config)

    def _initialize(self):
        """
        This method is needed because `embedder` attribute needs to be set externally before it can be initialized.
        """
        logging.info(self.client.info())
        index_settings = {
            "mappings": {
                "properties": {
                    "text": {"type": "text"},
                    "embeddings": {"type": "dense_vector", "index": False, "dims": self.embedder.vector_dimension},
                }
            }
        }
        es_index = self._get_index()
        if not self.client.indices.exists(index=es_index):
            # create index if not exist
            print("Creating index", es_index, index_settings)
            self.client.indices.create(index=es_index, body=index_settings)

    def _get_or_create_db(self):
        """Called during initialization"""
        return self.client

    def _get_or_create_collection(self, name):
        """Note: nothing to return here. Discuss later"""

    def get(self, ids: Optional[List[str]] = None, where: Optional[Dict[str, any]] = None, limit: Optional[int] = None):
        """
        Get existing doc ids present in vector database

        :param ids: _list of doc ids to check for existance
        :type ids: List[str]
        :param where: to filter data
        :type where: Dict[str, any]
        :return: ids
        :rtype: Set[str]
        """
        if ids:
            query = {"bool": {"must": [{"ids": {"values": ids}}]}}
        else:
            query = {"bool": {"must": []}}
        if "app_id" in where:
            app_id = where["app_id"]
            query["bool"]["must"].append({"term": {"metadata.app_id": app_id}})

        response = self.client.search(index=self._get_index(), query=query, _source=False, size=limit)
        docs = response["hits"]["hits"]
        ids = [doc["_id"] for doc in docs]
        return {"ids": set(ids)}

    def add(
        self,
        embeddings: List[List[float]],
        documents: List[str],
        metadatas: List[object],
        ids: List[str],
        skip_embedding: bool,
        **kwargs: Optional[Dict[str, any]],
    ) -> Any:
        """
        add data in vector database
        :param embeddings: list of embeddings to add
        :type embeddings: List[List[str]]
        :param documents: list of texts to add
        :type documents: List[str]
        :param metadatas: list of metadata associated with docs
        :type metadatas: List[object]
        :param ids: ids of docs
        :type ids: List[str]
        :param skip_embedding: Optional. If True, then the input_query is assumed to be already embedded.
        :type skip_embedding: bool
        """

        if not skip_embedding:
            embeddings = self.embedder.embedding_fn(documents)

        for chunk in chunks(
            list(zip(ids, documents, metadatas, embeddings)), self.BATCH_SIZE, desc="Inserting batches in elasticsearch"
        ):  # noqa: E501
            ids, docs, metadatas, embeddings = [], [], [], []
            for id, text, metadata, embedding in chunk:
                ids.append(id)
                docs.append(text)
                metadatas.append(metadata)
                embeddings.append(embedding)

            batch_docs = []
            for id, text, metadata, embedding in zip(ids, docs, metadatas, embeddings):
                batch_docs.append(
                    {
                        "_index": self._get_index(),
                        "_id": id,
                        "_source": {"text": text, "metadata": metadata, "embeddings": embedding},
                    }
                )
            bulk(self.client, batch_docs, **kwargs)
        self.client.indices.refresh(index=self._get_index())

    def query(
        self,
        input_query: List[str],
        n_results: int,
        where: Dict[str, any],
        skip_embedding: bool,
        citations: bool = False,
        **kwargs: Optional[Dict[str, Any]],
    ) -> Union[List[Tuple[str, str, str]], List[str]]:
        """
        query contents from vector data base based on vector similarity

        :param input_query: list of query string
        :type input_query: List[str]
        :param n_results: no of similar documents to fetch from database
        :type n_results: int
        :param where: Optional. to filter data
        :type where: Dict[str, any]
        :param skip_embedding: Optional. If True, then the input_query is assumed to be already embedded.
        :type skip_embedding: bool
        :return: The context of the document that matched your query, url of the source, doc_id
        :param citations: we use citations boolean param to return context along with the answer.
        :type citations: bool, default is False.
        :return: The content of the document that matched your query,
        along with url of the source and doc_id (if citations flag is true)
        :rtype: List[str], if citations=False, otherwise List[Tuple[str, str, str]]
        """
        if skip_embedding:
            query_vector = input_query
        else:
            input_query_vector = self.embedder.embedding_fn(input_query)
            query_vector = input_query_vector[0]

        # `https://www.elastic.co/guide/en/elasticsearch/reference/7.17/query-dsl-script-score-query.html`
        query = {
            "script_score": {
                "query": {"bool": {"must": [{"exists": {"field": "text"}}]}},
                "script": {
                    "source": "cosineSimilarity(params.input_query_vector, 'embeddings') + 1.0",
                    "params": {"input_query_vector": query_vector},
                },
            }
        }
        if "app_id" in where:
            app_id = where["app_id"]
            query["script_score"]["query"] = {"match": {"metadata.app_id": app_id}}
        _source = ["text", "metadata.url", "metadata.doc_id"]
        response = self.client.search(index=self._get_index(), query=query, _source=_source, size=n_results)
        docs = response["hits"]["hits"]
        contexts = []
        for doc in docs:
            context = doc["_source"]["text"]
            if citations:
                metadata = doc["_source"]["metadata"]
                source = metadata["url"]
                doc_id = metadata["file_id"]
                contexts.append(tuple((context, source, doc_id)))
            else:
                contexts.append(context)
        return contexts

    def set_collection_name(self, name: str):
        """
        Set the name of the collection. A collection is an isolated space for vectors.

        :param name: Name of the collection.
        :type name: str
        """
        if not isinstance(name, str):
            raise TypeError("Collection name must be a string")
        self.config.collection_name = name

    def count(self) -> int:
        """
        Count number of documents/chunks embedded in the database.

        :return: number of documents
        :rtype: int
        """
        query = {"match_all": {}}
        response = self.client.count(index=self._get_index(), query=query)
        doc_count = response["count"]
        return doc_count

    def reset(self):
        """
        Resets the database. Deletes all embeddings irreversibly.
        """
        # Delete all data from the database
        if self.client.indices.exists(index=self._get_index()):
            # delete index in Es
            self.client.indices.delete(index=self._get_index())

    def _get_index(self) -> str:
        """Get the Elasticsearch index for a collection

        :return: Elasticsearch index
        :rtype: str
        """
        # NOTE: The method is preferred to an attribute, because if collection name changes,
        # it's always up-to-date.
        return f"{self.config.collection_name}_{self.embedder.vector_dimension}".lower()
