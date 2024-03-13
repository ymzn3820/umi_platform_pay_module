import hashlib

from knowledge_base.embedchain.helpers.json_serializable import register_deserializable
from knowledge_base.embedchain.loaders.base_loader import BaseLoader


@register_deserializable
class LocalQnaPairLoader(BaseLoader):
    def load_data(self, content):
        """Load data from a local QnA pair."""
        question, answer = content
        content = f"Q: {question}\nA: {answer}"
        url = "local"
        meta_data = {"url": url, "question": question}
        doc_id = hashlib.sha256((content + url).encode()).hexdigest()
        return {
            "file_id": doc_id,
            "data": [
                {
                    "content": content,
                    "meta_data": meta_data,
                }
            ],
        }