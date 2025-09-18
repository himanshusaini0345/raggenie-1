from app.base.abstract_handlers import AbstractHandler
from app.providers.config import configs
from app.loaders.base_loader import BaseLoader
from app.utils.parser import parse_llm_response, markdown_parse_llm_response
from app.chain.formatter.general_response import Formatter
from loguru import logger
from app.utils.sb_decoder import decode_data
from string import Template


class SummaryGenerator(AbstractHandler):
        """
        A handler class for generating inferences based on prompts and contexts.

        This class extends AbstractHandler and provides functionality to generate
        inferences using a specified language model based on given prompts and contexts.
        """

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
                """
                Handle the incoming request by generating an inference based on the prompt and context.

                This method extracts the prompt and context from the request, uses an inference model
                to generate a response, and adds the parsed inference to the response.

                Args:
                request (Dict[str, Any]): The incoming request to be processed.

                Returns:
                str: The response after processing the request, including the generated inference.
                """
                logger.info("passing through => summary generator")

                response = request
                query_response = response.get("query_response", "")
                logger.info(f"len query_response: {len(query_response)}")
                general_message = response.get("inference",{}).get("general_message")
                empty_message = response.get("inference",{}).get("empty_message")
                logger.info(f"empty_message: {empty_message}")
                language_detector = response.get("language_detector",{})
                language_type = language_detector.get("language_type","english")
                if language_type.lower() == "hindi":
                        language_type = "Romanized Hindi"
                query_response_length = len(query_response)
                if query_response and len(query_response) > 0:

                        for entry in query_response:
                                for key, value in entry.items():
                                        if isinstance(value, str):
                                                decoded_value = decode_data(value)
                                                if decoded_value != "":
                                                        entry[key] = decoded_value
                        
                        data_description = ""
                        if query_response:
                                data_description = f"No of data retrieved is {query_response_length} \n {general_message} \n {query_response}"
                        else:
                                data_description = "None"
                        prompt = '''You are a friendly and helpful assistant. Kindly answer the user's question using only the information provided below.

                        Question: $question

                        -- Data --
                        $data_description
                        -- End of Data --

                        Instructions:
                        - Respond in a polite and respectful tone.
                        - Focus on answering the question clearly and accurately.
                        - Use only the relevant information from the data.
                        - Keep the response concise and to the point.
                        - Do not mention that the information came from the data section.
                        - If there is no relevant data to answer the question, return a gentle, empty response that aligns with the intent—avoid guesses or general assumptions.
                        - Response should be in plain text format, without markdown or HTML.S
                        - Response should a insight which should be human speakable
                        - Make sure to response in Maximum 30 words.
                        - Make sure the response language is in $language_type

                        Response($language_type only in Maximum 30 words):
                        '''


                        prompt = Template(prompt).safe_substitute(question = response["question"], data_description = data_description, language_type = language_type)

                        logger.debug(f"prompt:{prompt}")
                        model_configs = [{'unique_name': 'llama4', 'name': 'meta-llama/llama-4-scout-17b-16e-instruct', 'api_key': configs.groq_api_key, 'endpoint': 'https://api.groq.com/openai/v1/chat/completions', 'kind': 'grogcloud'}]
                        loader = BaseLoader(model_configs=model_configs)
                        infernce_model = loader.load_model(configs.secondary_inference_llm_model)

                        output_response, response_metadata = infernce_model.do_inference(
                                prompt, []
                        )
                        if output_response["error"] is not None:
                                return Formatter.format("Oops! Something went wrong. Try Again!",output_response['error'])

                        response["summary"] = output_response['content']
                        if not response["summary"]:
                                response["summary"] = "No records found can you reframe your query"
                else:
                        response["summary"] = empty_message

                return await super().handle(response)
