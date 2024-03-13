import unittest

from chunkers.images import ImagesChunker
from config import ChunkerConfig
from models.data_type import DataType


class TestImageChunker(unittest.TestCase):
    def test_chunks(self):
        """
        Test the chunks generated by TextChunker.
        # TODO: Not a very precise test.
        """
        chunker_config = ChunkerConfig(chunk_size=1, chunk_overlap=0, length_function=len, min_chunk_size=0)
        chunker = ImagesChunker(config=chunker_config)
        # Data type must be set manually in the test
        chunker.set_data_type(DataType.IMAGES)

        image_path = "./tmp/image.jpeg"
        app_id = "app1"
        result = chunker.create_chunks(MockLoader(), image_path, app_id=app_id)

        expected_chunks = {
            "doc_id": f"{app_id}--123",
            "documents": [image_path],
            "embeddings": ["embedding"],
            "ids": ["140bedbf9c3f6d56a9846d2ba7088798683f4da0c248231336e6a05679e4fdfe"],
            "metadatas": [{"data_type": "images", "doc_id": f"{app_id}--123", "url": "none"}],
        }
        self.assertEqual(expected_chunks, result)

    def test_chunks_with_default_config(self):
        """
        Test the chunks generated by ImageChunker with default config.
        """
        chunker = ImagesChunker()
        # Data type must be set manually in the test
        chunker.set_data_type(DataType.IMAGES)

        image_path = "./tmp/image.jpeg"
        app_id = "app1"
        result = chunker.create_chunks(MockLoader(), image_path, app_id=app_id)

        expected_chunks = {
            "doc_id": f"{app_id}--123",
            "documents": [image_path],
            "embeddings": ["embedding"],
            "ids": ["140bedbf9c3f6d56a9846d2ba7088798683f4da0c248231336e6a05679e4fdfe"],
            "metadatas": [{"data_type": "images", "doc_id": f"{app_id}--123", "url": "none"}],
        }
        self.assertEqual(expected_chunks, result)

    def test_word_count(self):
        chunker_config = ChunkerConfig(chunk_size=1, chunk_overlap=0, length_function=len, min_chunk_size=0)
        chunker = ImagesChunker(config=chunker_config)
        chunker.set_data_type(DataType.IMAGES)

        document = [["ab cd", "ef gh"], ["ij kl", "mn op"]]
        result = chunker.get_word_count(document)
        self.assertEqual(result, 1)


class MockLoader:
    def load_data(self, src):
        """
        Mock loader that returns a list of data dictionaries.
        Adjust this method to return different data for testing.
        """
        return {
            "doc_id": "123",
            "data": [
                {
                    "content": src,
                    "embedding": "embedding",
                    "meta_data": {"url": "none"},
                }
            ],
        }
