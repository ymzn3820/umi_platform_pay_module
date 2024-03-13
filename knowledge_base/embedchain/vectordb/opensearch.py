import logging
import time
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from tqdm import tqdm

try:
    from opensearchpy import OpenSearch
    from opensearchpy.helpers import bulk
except ImportError:
    raise ImportError(
        "OpenSearch requires extra dependencies. Install with `pip install --upgrade embedchain[opensearch]`"
    ) from None

from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.vectorstores import OpenSearchVectorSearch

from knowledge_base.embedchain.config import OpenSearchDBConfig
from knowledge_base.embedchain.helpers.json_serializable import register_deserializable
from knowledge_base.embedchain.vectordb.base import BaseVectorDB


@register_deserializable
class OpenSearchDB(BaseVectorDB):
    """
    OpenSearch as vector database
    """

    BATCH_SIZE = 100

    def __init__(self, config: OpenSearchDBConfig):
        """OpenSearch as vector database.

        :param config: OpenSearch domain config
        :type config: OpenSearchDBConfig
        """
        if config is None:
            raise ValueError("OpenSearchDBConfig is required")
        self.config = config
        self.client = OpenSearch(
            hosts=[self.config.opensearch_url],
            http_auth=self.config.http_auth,
            **self.config.extra_params,
        )
        info = self.client.info()
        logging.info(f"Connected to {info['version']['distribution']}. Version: {info['version']['number']}")
        # Remove auth credentials from config after successful connection
        super().__init__(config=self.config)

    def _initialize(self):
        logging.info(self.client.info())
        index_name = self._get_index()
        if self.client.indices.exists(index=index_name):
            logging.info(f"Index '{index_name}' already exists.")
            return

        index_body = {
            "settings": {"knn": True},
            "mappings": {
                "properties": {
                    "text": {"type": "text"},
                    "embeddings": {
                        "type": "knn_vector",
                        "index": False,
                        "dimension": self.config.vector_dimension,
                    },
                }
            },
        }
        self.client.indices.create(index_name, body=index_body)

    def _get_or_create_db(self):
        """Called during initialization"""
        return self.client

    def _get_or_create_collection(self, name):
        """Note: nothing to return here. Discuss later"""

    def get(
        self, ids: Optional[List[str]] = None, where: Optional[Dict[str, any]] = None, limit: Optional[int] = None
    ) -> Set[str]:
        """
        Get existing doc ids present in vector database

        :param ids: _list of doc ids to check for existence
        :type ids: List[str]
        :param where: to filter data
        :type where: Dict[str, any]
        :return: ids
        :type: Set[str]
        """
        query = {}
        if ids:
            query["query"] = {"bool": {"must": [{"ids": {"values": ids}}]}}
        else:
            query["query"] = {"bool": {"must": []}}

        user_id = where.get('user_id')
        company_id = where.get('company_id')
        file_id = where.get('file_id')
        file_name = where.get('file_name')

        must_conditions = []
        if user_id:
            must_conditions.append({"term": {"metadata.user_id": user_id}})

        if company_id:
            must_conditions.append({"term": {"metadata.company_id": company_id}})

        if file_id:
            must_conditions.append({"term": {"metadata.file_id": file_id}})

        if file_name:
            must_conditions.append({"term": {"metadata.file_name": file_name}})

        query["query"]["bool"]["must"] = must_conditions

        logging.info('current query params {}'.format(query))
        # OpenSearch syntax is different from Elasticsearch
        response = self.client.search(index=self._get_index(), body=query, _source=True, size=limit)
        docs = response["hits"]["hits"]
        ids = [doc["_id"] for doc in docs]
        # doc_ids = [doc["_source"]["metadata"]["doc_id"] for doc in docs]
        file_ids = [doc["_source"]["metadata"]["file_id"] for doc in docs]

        # Result is modified for compatibility with other vector databases
        # TODO: Add method in vector database to return result in a standard format
        result = {"ids": ids, "metadatas": []}

        for file_id in file_ids:
            result["metadatas"].append({"file_id": file_id})
        return result

    def add(
        self,
        embeddings: List[List[str]],
        documents: List[str],
        metadatas: List[object],
        ids: List[str],
        skip_embedding: bool,
        **kwargs: Optional[Dict[str, any]],
    ):
        """Add data in vector database.

        Args:
            embeddings (List[List[str]]): List of embeddings to add.
            documents (List[str]): List of texts to add.
            metadatas (List[object]): List of metadata associated with docs.
            ids (List[str]): IDs of docs.
            skip_embedding (bool): If True, then embeddings are assumed to be already generated.
        """
        for batch_start in tqdm(range(0, len(documents), self.BATCH_SIZE), desc="Inserting batches in opensearch"):
            batch_end = batch_start + self.BATCH_SIZE
            batch_documents = documents[batch_start:batch_end]

            # Generate embeddings for the batch if not skipping embedding
            if not skip_embedding:
                batch_embeddings = self.embedder.embedding_fn(batch_documents)
            else:
                batch_embeddings = embeddings[batch_start:batch_end]

            # Create document entries for bulk upload
            batch_entries = [
                {
                    "_index": self._get_index(),
                    "_id": doc_id,
                    "_source": {"text": text, "metadata": metadata, "embeddings": embedding},
                }
                for doc_id, text, metadata, embedding in zip(
                    ids[batch_start:batch_end], batch_documents, metadatas[batch_start:batch_end], batch_embeddings
                )
            ]

            # Perform bulk operation
            bulk(self.client, batch_entries, **kwargs)
            self.client.indices.refresh(index=self._get_index())

            # Sleep to avoid rate limiting
            time.sleep(0.1)

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
        :param citations: we use citations boolean param to return context along with the answer.
        :type citations: bool, default is False.
        :return: The content of the document that matched your query,
        along with url of the source and doc_id (if citations flag is true)
        :rtype: List[str], if citations=False, otherwise List[Tuple[str, str, str]]
        """
        # TODO(rupeshbansal, deshraj): Add support for skip embeddings here if already exists
        embeddings = OpenAIEmbeddings()
        docsearch = OpenSearchVectorSearch(
            index_name=self._get_index(),
            embedding_function=embeddings,
            opensearch_url=f"{self.config.opensearch_url}",
            http_auth=self.config.http_auth,
            use_ssl=hasattr(self.config, "use_ssl") and self.config.use_ssl,
            verify_certs=hasattr(self.config, "verify_certs") and self.config.verify_certs,
        )

        user_id = where.get('user_id')
        company_id = where.get('company_id')
        file_id = where.get('file_id')
        file_name = where.get('file_name')

        must_conditions = []
        if user_id:
            must_conditions.append({"term": {"metadata.user_id": user_id}})

        if company_id:
            must_conditions.append({"term": {"metadata.company_id": company_id}})

        if file_id:
            must_conditions.append({"term": {"metadata.file_id": file_id}})

        if file_name:
            must_conditions.append({"term": {"metadata.file_name": file_name}})

        pre_filter = {
            "bool": {"must": must_conditions}}


        docs = docsearch.similarity_search(
            input_query,
            search_type="script_scoring",
            space_type="cosinesimil",
            vector_field="embeddings",
            text_field="text",
            metadata_field="metadata",
            pre_filter=pre_filter,
            k=n_results,
            **kwargs,
        )

        contexts = []
        for doc in docs:
            context = doc.page_content
            if citations:
                source = doc.metadata["url"]
                doc_id = doc.metadata["file_id"]
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
        query = {"query": {"match_all": {}}}
        response = self.client.count(index=self._get_index(), body=query)
        doc_count = response["count"]
        return doc_count

    def reset(self):
        """
        Resets the database. Deletes all embeddings irreversibly.
        """
        # Delete all data from the database
        if self.client.indices.exists(index=self._get_index()):
            # delete index in ES
            self.client.indices.delete(index=self._get_index())

    def delete(self, where):
        """Deletes a document from the OpenSearch index"""
        if "file_id" not in where:
            raise ValueError("file_id is required to delete a document")

        query = {"query": {"bool": {"must": [{"term": {"metadata.file_id": where["file_id"]}}]}}}
        self.client.delete_by_query(index=self._get_index(), body=query)

    def _get_index(self) -> str:
        """Get the OpenSearch index for a collection

        :return: OpenSearch index
        :rtype: str
        """
        return self.config.collection_name
