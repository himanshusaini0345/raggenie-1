from typing import Any
from loguru import logger
from app.base.abstract_handlers import AbstractHandler
from app.providers.container import Container
import time
import asyncio
from app.providers.config import configs

class Cachechecker(AbstractHandler):
    """
    A handler class for checking and managing cache operations.

    This class extends AbstractHandler and provides functionality to check
    if a query exists in the cache and handle the response accordingly.
    """

    def __init__(self,common_context, datasources, cachestore, forward_handler = None, forward: bool = False) -> None:
        """
        Initialize the Cachechecker.

        Args:
            common_context: The common context shared across handlers.
            Cachestore: The cache storage mechanism.
            forward_handler: The next handler in the chain.
            forward (bool): Whether to forward the request to the next handler.
        """
        self.cache = cachestore
        self.forward_handler = forward_handler
        self.forward = forward
        self.common_context = common_context
        self.context_relevance_threshold = 4
        self.datasources = datasources




    async def handle(self, request: Any) -> str:
        """
        Handle the incoming request by checking the cache

        Args:
            request (Any): The incoming request to be processed.

        Returns:
            str: The response after processing the request.
        """
        logger.info("passing through => cache_checker")

        response = request
        question = request.get("question", "")
        language_detector = response.get("language_detector",{})
        language_type = language_detector.get("language_type","english")

        start_time = time.time()
        if configs.answer_from_enabled:
            datasource = configs.answer_from
            results = [await self.cache.find_similar_cache(datasource, question)]

        else:
            tasks = [
                    self.cache.find_similar_cache(datasource, question)
                    for datasource in self.datasources
                ]
            results = await asyncio.gather(*tasks)

        end_time = time.time()
        time_taken = end_time - start_time
        logger.info(f"Time taken for cache retriever: {time_taken}")

        is_translate_required = True
        for index, out in enumerate(results):
            if len(out) > 0:
                is_translate_required = False
        if is_translate_required:
            if configs.answer_from_enabled:
                datasource = configs.answer_from
                results = [await self.cache.find_similar_cache(datasource, question)]

            else:
                tasks = [
                        self.cache.find_similar_cache(datasource, question)
                        for datasource in self.datasources
                    ]
                results = await asyncio.gather(*tasks)

        if "rag" not in response:
            response["rag"] = {"suggestions": {}}

        for index, out in enumerate(results):
            opt_cache = []            
            if out and isinstance(out, list) and len(out) > 0:
                # Check the closest distance against threshold
                if out[0]['distances'] < self.context_relevance_threshold:
                    distances = [doc['distances'] for doc in out]
                    
                    # # Clustering if enough results
                    # if len(out) > 10:
                    #     clusters = Container.clustering().kmeans(distances, 2)
                    #     # Find the shortest cluster by average distance
                    #     cluster_averages = [sum(cluster)/len(cluster) for cluster in clusters]
                    #     shortest_cluster_index = cluster_averages.index(min(cluster_averages))
                    #     shortest_cluster = clusters[shortest_cluster_index]
                        
                    #     # Match documents that belong to the shortest cluster
                    #     for doc in out:S
                    #         if any(abs(doc['distances'] - d) < 1e-6 for d in shortest_cluster):  # float-safe comparison
                    #             opt_cache.append(doc)
                    # else:
                    opt_cache = out

            # Always set, even if opt_cache is empty (helps with fallback logic)
            datasource_key = list(self.datasources.keys())[index]
            response["rag"]["suggestions"][datasource_key] = opt_cache

        if self.forward and len(results) > 0:
            if results[0]["distances"] < -10:
                result = results[0]["metadatas"]
                logger.info("query retrieved from cache")
                return await self.forward_handler.handle({"inference":result})

        logger.info("query not retrieved from cache")
        return await super().handle(response)
