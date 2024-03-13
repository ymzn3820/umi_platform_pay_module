import os

import pytest
from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler

from config import BaseLlmConfig
from llm.openai import OpenAILlm


@pytest.fixture
def config():
    os.environ["OPENAI_API_KEY"] = "test_api_key"
    config = BaseLlmConfig(
        temperature=0.7, max_tokens=50, top_p=0.8, stream=False, system_prompt="System prompt", model="gpt-3.5-turbo"
    )
    yield config
    os.environ.pop("OPENAI_API_KEY")


def test_get_llm_model_answer(config, mocker):
    mocked_get_answer = mocker.patch("llm.openai.OpenAILlm._get_answer", return_value="Test answer")

    llm = OpenAILlm(config)
    answer = llm.get_llm_model_answer("Test query")

    assert answer == "Test answer"
    mocked_get_answer.assert_called_once_with("Test query", config)


def test_get_llm_model_answer_with_system_prompt(config, mocker):
    config.system_prompt = "Custom system prompt"
    mocked_get_answer = mocker.patch("llm.openai.OpenAILlm._get_answer", return_value="Test answer")

    llm = OpenAILlm(config)
    answer = llm.get_llm_model_answer("Test query")

    assert answer == "Test answer"
    mocked_get_answer.assert_called_once_with("Test query", config)


def test_get_llm_model_answer_empty_prompt(config, mocker):
    mocked_get_answer = mocker.patch("llm.openai.OpenAILlm._get_answer", return_value="Test answer")

    llm = OpenAILlm(config)
    answer = llm.get_llm_model_answer("")

    assert answer == "Test answer"
    mocked_get_answer.assert_called_once_with("", config)


def test_get_llm_model_answer_with_streaming(config, mocker):
    config.stream = True
    mocked_openai_chat = mocker.patch("llm.openai.ChatOpenAI")

    llm = OpenAILlm(config)
    llm.get_llm_model_answer("Test query")

    mocked_openai_chat.assert_called_once()
    callbacks = [callback[1]["callbacks"] for callback in mocked_openai_chat.call_args_list]
    assert any(isinstance(callback[0], StreamingStdOutCallbackHandler) for callback in callbacks)


def test_get_llm_model_answer_without_system_prompt(config, mocker):
    config.system_prompt = None
    mocked_openai_chat = mocker.patch("llm.openai.ChatOpenAI")

    llm = OpenAILlm(config)
    llm.get_llm_model_answer("Test query")

    mocked_openai_chat.assert_called_once_with(
        model=config.model,
        temperature=config.temperature,
        max_tokens=config.max_tokens,
        model_kwargs={"top_p": config.top_p},
    )
