# Suppress external dependency warnings before any other imports
import warnings

warnings.simplefilter("ignore", DeprecationWarning)

import unittest
from pydantic import Field, BaseModel
from unittest.mock import patch, MagicMock
import requests

from llama_index.indices.managed.vectara import VectaraIndex

from vectara_agentic.tools import (
    VectaraTool,
    VectaraToolFactory,
    ToolsFactory,
    ToolType,
)
from vectara_agentic.agent import Agent
from vectara_agentic.agent_config import AgentConfig

from llama_index.core.tools import FunctionTool

# Special test account credentials for Vectara
vectara_corpus_key = "vectara-docs_1"
vectara_api_key = "zqt_UXrBcnI2UXINZkrv4g1tQPhzj02vfdtqYJIDiA"

from typing import Optional


class TestToolsPackage(unittest.TestCase):

    def test_vectara_rag_tool(self):
        vec_factory = VectaraToolFactory(vectara_corpus_key, vectara_api_key)

        self.assertEqual(vectara_corpus_key, vec_factory.vectara_corpus_key)
        self.assertEqual(vectara_api_key, vec_factory.vectara_api_key)

        query_tool = vec_factory.create_rag_tool(
            tool_name="rag_tool",
            tool_description="""
            Returns a response (str) to the user query based on the data in this corpus.
            """,
        )

        self.assertIsInstance(query_tool, VectaraTool)
        self.assertIsInstance(query_tool, FunctionTool)
        self.assertEqual(query_tool.metadata.tool_type, ToolType.QUERY)

        res = query_tool(query="What is Vectara?")
        self.assertIn("Vectara is an end-to-end platform", str(res))

    def test_vectara_search_tool(self):
        vec_factory = VectaraToolFactory(vectara_corpus_key, vectara_api_key)

        search_tool = vec_factory.create_search_tool(
            tool_name="search_tool",
            tool_description="Returns a list of documents (str) that match the user query.",
        )
        self.assertIsInstance(search_tool, VectaraTool)
        self.assertIsInstance(search_tool, FunctionTool)
        self.assertEqual(search_tool.metadata.tool_type, ToolType.QUERY)
        self.assertIn("summarize", search_tool.metadata.description)

        res = search_tool(query="What is Vectara?")
        self.assertIn("https-docs-vectara-com-docs", str(res))

        search_tool = vec_factory.create_search_tool(
            tool_name="search_tool",
            tool_description="Returns a list of documents (str) that match the user query.",
            summarize_docs=False,
        )
        self.assertIsInstance(search_tool, VectaraTool)
        self.assertIsInstance(search_tool, FunctionTool)
        self.assertEqual(search_tool.metadata.tool_type, ToolType.QUERY)
        self.assertNotIn("summarize", search_tool.metadata.description)

        res = search_tool(query="What is Vectara?")
        self.assertIn("https-docs-vectara-com-docs", str(res))

        search_tool = vec_factory.create_search_tool(
            tool_name="search_tool",
            tool_description="Returns a list of documents (str) that match the user query.",
            summarize_docs=True,
        )
        self.assertIsInstance(search_tool, VectaraTool)
        self.assertIsInstance(search_tool, FunctionTool)
        self.assertEqual(search_tool.metadata.tool_type, ToolType.QUERY)
        self.assertNotIn("summarize", search_tool.metadata.description)

        res = search_tool(query="What is Vectara?")
        self.assertIn("Vectara is", str(res))

    def test_vectara_tool_validation(self):
        vec_factory = VectaraToolFactory(vectara_corpus_key, vectara_api_key)

        class QueryToolArgs(BaseModel):
            ticker: str = Field(
                description="The ticker symbol for the company",
                examples=["AAPL", "GOOG"],
            )
            year: Optional[int | str] = Field(
                description="The year this query relates to. An integer between 2015 and 2024 or a string specifying a condition on the year",
                examples=[
                    2020,
                    ">2021",
                    "<2023",
                    ">=2021",
                    "<=2023",
                    "[2021, 2023]",
                    "[2021, 2023)",
                ],
            )

        query_tool = vec_factory.create_rag_tool(
            tool_name="rag_tool",
            tool_description="Returns a response (str) to the user query based on the data in this corpus.",
            tool_args_schema=QueryToolArgs,
        )

        # test an invalid argument name
        res = query_tool(
            query="What is the stock price?",
            the_year=2023,
        )
        self.assertIn("got an unexpected keyword argument 'the_year'", str(res))

        search_tool = vec_factory.create_search_tool(
            tool_name="search_tool",
            tool_description="Returns a list of documents (str) that match the user query.",
            tool_args_schema=QueryToolArgs,
        )
        res = search_tool(
            query="What is the stock price?",
            the_year=2023,
        )
        self.assertIn("got an unexpected keyword argument 'the_year'", str(res))

    @patch.object(requests.Session, "post")
    def test_vectara_tool_ranges(self, mock_post):
        # Configure the mock to return a dummy response.
        response_text = "ALL GOOD"
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "summary": response_text,
            "search_results": [
                {"text": "ALL GOOD", "document_id": "12345", "score": 0.9},
            ],
        }
        mock_post.return_value = mock_response

        vec_factory = VectaraToolFactory(vectara_corpus_key, vectara_api_key)

        class QueryToolArgs(BaseModel):
            ticker: str = Field(
                description="The ticker symbol for the company",
                examples=["AAPL", "GOOG"],
            )
            year: Optional[int | str] = Field(
                description="The year this query relates to. An integer between 2015 and 2024 or a string specifying a condition on the year",
                examples=[
                    2020,
                    ">2021",
                    "<2023",
                    ">=2021",
                    "<=2023",
                    "[2021, 2023]",
                    "[2021, 2023)",
                ],
            )

        query_tool = vec_factory.create_rag_tool(
            tool_name="rag_tool",
            tool_description="Returns a response (str) to the user query based on the data in this corpus.",
            tool_args_schema=QueryToolArgs,
        )

        # test an invalid argument name
        res = query_tool(query="What is the stock price?", year=">2023")
        self.assertIn(response_text, str(res))

        # Test a valid range
        res = query_tool(
            query="What is the stock price?",
            year="[2021, 2023]",
        )
        self.assertIn(response_text, str(res))

        # Test a valid half closed range
        res = query_tool(
            query="What is the stock price?",
            year="[2020, 2023)",
        )
        self.assertIn(response_text, str(res))

        # Test an operator
        res = query_tool(
            query="What is the stock price?",
            year=">2022",
        )
        self.assertIn(response_text, str(res))

        search_tool = vec_factory.create_search_tool(
            tool_name="search_tool",
            tool_description="Returns a list of documents (str) that match the user query.",
            tool_args_schema=QueryToolArgs,
        )
        res = search_tool(
            query="What is the stock price?",
            the_year=2023,
        )
        self.assertIn("got an unexpected keyword argument 'the_year'", str(res))

    def test_tool_factory(self):
        def mult(x: float, y: float) -> float:
            return x * y

        tools_factory = ToolsFactory()
        other_tool = tools_factory.create_tool(mult)
        self.assertIsInstance(other_tool, VectaraTool)
        self.assertIsInstance(other_tool, FunctionTool)
        self.assertEqual(other_tool.metadata.tool_type, ToolType.QUERY)

    def test_llama_index_tools(self):
        tools_factory = ToolsFactory()

        for name, spec in [
            ("arxiv", "ArxivToolSpec"),
            ("yahoo_finance", "YahooFinanceToolSpec"),
            ("wikipedia", "WikipediaToolSpec"),
        ]:
            tool = tools_factory.get_llama_index_tools(
                tool_package_name=name, tool_spec_name=spec
            )[0]
            self.assertIsInstance(tool, VectaraTool)
            self.assertIsInstance(tool, FunctionTool)
            self.assertEqual(tool.metadata.tool_type, ToolType.QUERY)

    @patch.object(VectaraIndex, "as_query_engine")
    def test_vectara_tool_args_type(
        self,
        mock_as_query_engine,
    ):
        fake_engine = MagicMock()
        fake_resp = MagicMock()
        fake_node = MagicMock(metadata={"docid": "123"})
        fake_resp.source_nodes, fake_resp.response, fake_resp.metadata = (
            [fake_node],
            "FAKE",
            {"fcs": "0.99"},
        )
        fake_engine.query.return_value = fake_resp
        mock_as_query_engine.return_value = fake_engine

        class QueryToolArgs(BaseModel):
            arg1: str
            arg2: str
            arg3: list[str]

        tool_args_type = {
            "arg1": {"type": "doc", "is_list": False, "filter_name": "arg1"},
            "arg2": {"type": "doc", "is_list": False, "filter_name": "arg 2"},
            "arg3": {"type": "part", "is_list": True, "filter_name": "arg_3"},
        }

        with patch("vectara_agentic.tools.build_filter_string") as mock_build_filter:
            mock_build_filter.return_value = "dummy_filter"
            vec_factory = VectaraToolFactory("dummy_key", "dummy_api")
            query_tool = vec_factory.create_rag_tool(
                tool_name="test_tool",
                tool_description="Test filter-string construction",
                tool_args_schema=QueryToolArgs,
                tool_args_type=tool_args_type,
            )
            query_tool.call(
                query="some query",
                arg1="val1",
                arg2="val2",
                arg3=["val3_1", "val3_2"],
            )
            mock_build_filter.assert_called_once()
            passed_kwargs, passed_type_map, passed_fixed = mock_build_filter.call_args[
                0
            ]
            self.assertEqual(passed_type_map, tool_args_type)
            self.assertEqual(passed_kwargs["arg1"], "val1")
            self.assertEqual(passed_kwargs["arg2"], "val2")
            self.assertEqual(passed_kwargs["arg3"], ["val3_1", "val3_2"])
            fake_engine.query.assert_called_once_with("some query")

    def test_public_repo(self):
        vectara_corpus_key = "vectara-docs_1"
        vectara_api_key = "zqt_UXrBcnI2UXINZkrv4g1tQPhzj02vfdtqYJIDiA"

        agent = Agent.from_corpus(
            vectara_corpus_key=vectara_corpus_key,
            vectara_api_key=vectara_api_key,
            tool_name="ask_vectara",
            data_description="data from Vectara website",
            assistant_specialty="RAG as a service",
            vectara_summarizer="mockingbird-2.0",
            vectara_summary_num_results=10,
        )

        self.assertIn(
            "Vectara is an end-to-end platform", str(agent.chat("What is Vectara?"))
        )

    def test_class_method_as_tool(self):
        class TestClass:
            def __init__(self):
                pass

            def mult(self, x: float, y: float) -> float:
                return x * y

        test_class = TestClass()
        tools = [ToolsFactory().create_tool(test_class.mult)]
        topic = "AI topic"
        instructions = "Always do as your father tells you, if your mother agrees!"
        config = AgentConfig()
        agent = Agent(
            tools=tools,
            topic=topic,
            custom_instructions=instructions,
            agent_config=config,
        )

        self.assertEqual(
            agent.chat(
                "What is 5 times 10. Only give the answer, nothing else"
            ).response.replace("$", "\\$"),
            "50",
        )

    def test_vectara_tool_docstring(self):
        class DummyArgs(BaseModel):
            foo: int = Field(..., description="how many foos", examples=[1, 2, 3])
            bar: str = Field(
                default="baz",
                description="what bar to use",
                examples=["x", "y"],
            )

        vec_factory = VectaraToolFactory(vectara_corpus_key, vectara_api_key)
        dummy_tool = vec_factory.create_rag_tool(
            tool_name="dummy_tool",
            tool_description="A dummy tool.",
            tool_args_schema=DummyArgs,
        )

        doc = dummy_tool.metadata.description
        self.assertTrue(
            doc.startswith(
                "dummy_tool(query: str, foo: int, bar: str | None) -> dict[str, Any]"
            )
        )
        self.assertIn("Args:", doc)
        self.assertIn(
            "query (str): The search query to perform, in the form of a question", doc
        )
        self.assertIn("foo (int): how many foos (e.g., 1, 2, 3)", doc)
        self.assertIn("bar (str | None, default='baz'): what bar to use (e.g., 'x', 'y')", doc)
        self.assertIn("Returns:", doc)
        self.assertIn("dict[str, Any]: A dictionary containing the result data.", doc)


if __name__ == "__main__":
    unittest.main()
