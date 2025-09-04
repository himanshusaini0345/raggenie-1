from app.base.abstract_handlers import AbstractHandler
from loguru import logger
from typing import Any
from app.providers.container import Container
import asyncio
from app.providers.config import configs
import time



class DocumentRetriever(AbstractHandler):
    """
    A handler class for retrieving relevant documents based on the input question.

    This class extends AbstractHandler and provides functionality to find and
    process similar documents from a vector store based on the input question.
    """

    def __init__(self,store, datasources):
        """
        Initialize the DocumentRetriever.

        Args:
            store (Any): The vector store for document retrieval.
        """

        self.store =store
        self.context_relevance_threshold = 4
        self.datasources = datasources


    async def handle(self, request: Any) -> str:
        """
        Handle the incoming request by retrieving relevant documents.

        Args:
            request (Dict[str, Any]): The incoming request to be processed.

        Returns:
            str: The response after processing the request.
        """

        logger.info("passing through => document_retriever")
        response = request
        start_time = time.time()
        question = request['question']
        language_detector = response.get("language_detector",{})
        language_type = language_detector.get("language_type","english")
        if language_type.lower() == "hindi":
            question = language_detector.get("translated_question",question)

        if configs.answer_from_enabled:
            datasource = configs.answer_from
            logger.info(f"datasource:{datasource}")
            results = [await self.store.find_similar_documentation(datasource,question, 10)]

        else:
            tasks = [
                    self.store.find_similar_documentation(datasource, question, 10)
                    for datasource in self.datasources
                ]
            results = await asyncio.gather(*tasks)
        end_time = time.time()
        time_taken = end_time - start_time
        logger.info(f"Time taken for document retriever: {time_taken}")

        if "rag" not in response:
            response["rag"] = {"context": {}}
        if "context" not in response["rag"]:
            response["rag"]["context"] = {}

        logger.info("sorting retrieved documents")
        for index, out in enumerate(results):
            opt_doc = []
            if out and len(out) > 0 and out[0]['distances'] < self.context_relevance_threshold:
                distances = [doc['distances'] for doc in out]
                if len(out) > 5:
                    clusters = Container.clustering().kmeans(distances, 2)
                    shortest_cluster = clusters[0]
                    for doc in out:
                        if doc['distances'] in shortest_cluster:
                            opt_doc.append(doc)
                else:
                    opt_doc = out

            datasource_key = list(self.datasources.keys())[index]
    
            response["rag"]["context"][datasource_key] = opt_doc 


        return await super().handle(response)





