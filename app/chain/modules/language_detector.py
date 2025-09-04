from app.base.abstract_handlers import AbstractHandler
from app.providers.config import configs
from app.loaders.base_loader import BaseLoader
from app.utils.parser import parse_llm_response, markdown_parse_llm_response
from app.chain.formatter.general_response import Formatter
from loguru import logger
from string import Template

class LanguageDetector(AbstractHandler):

    def __init__(self, common_context, model_configs) -> None:
            """
            Initialize the Generator.

            Args:
            common_context (Dict[str, Any]): The common context shared across handlers.
            model_configs (Dict[str, Any]): Configuration for the models used in processing.
            """
            self.model_configs = model_configs
            self.common_context = common_context

    async def handle(self, request: dict) -> str:
        logger.info("passing through => language detector")

        response = request

        question = response.get("question")
        logger.info(f"question:{question}")

        prompt = '''
                You are an excellent language detector
                Your task is to detect the language of the user given question

                User question: $question

                - ONLY output a **valid JSON object**, no Markdown formatting, no explanation text before or after.
                - DO NOT include anything like "Here is the response" or wrap JSON in triple backticks.

                - Provide a response in strict JSON format with the following structure, extra explanation is strictly prohibited:
                {
                "language_type" : "hindi or english",
                "translated_question" : "covert to english language"
                }
                '''


        prompt = Template(prompt).safe_substitute(question = question)

        logger.debug(f"prompt:{prompt}")
        model_configs = [{'unique_name': 'llama4', 'name': 'meta-llama/llama-4-scout-17b-16e-instruct', 'api_key': configs.groq_api_key, 'endpoint': 'https://api.groq.com/openai/v1/chat/completions', 'kind': 'grogcloud'}]
        loader = BaseLoader(model_configs=model_configs)
        infernce_model = loader.load_model(configs.secondary_inference_llm_model)

        output_response, response_metadata = infernce_model.do_inference(
                prompt, []
        )
        if output_response["error"] is not None:
                return Formatter.format("Oops! Something went wrong. Try Again!",output_response['error'])

        response["language_detector"] = parse_llm_response(output_response['content'])

        return await super().handle(response)
