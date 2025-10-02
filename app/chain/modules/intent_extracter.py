from app.base.abstract_handlers import AbstractHandler
from typing import Any
from loguru import logger
from app.providers.config import configs
from app.loaders.base_loader import BaseLoader
from string import Template
from app.chain.formatter.general_response import Formatter
from app.utils.parser import parse_llm_response, updated_parse_llm_response


class IntentExtracter(AbstractHandler):
    """
    A handler for extracting user intents from chat queries based on a provided use case configuration.

    This class processes chat requests to determine the intent behind user queries using a language model.
    It generates a prompt with the chat context, available intents, and instructions to guide the model in
    intent extraction.

    Attributes:
        common_context (Any): Shared context information used across handlers.
        model_configs (dict): Configuration settings for the model, including use case details and model paths.
    """

    def __init__(self, common_context , model_configs, datasources) -> None:
        """
        Initializes the IntentExtractor with common context and model configurations.

        Args:
            common_context (Any): Shared context information used across handlers.
            model_configs (dict): Configuration settings for the model.
        """
        self.model_configs = model_configs
        self.common_context = common_context
        self.datasources = datasources

    async def handle(self, request: Any) -> str:
        """
        Processes the request to extract the intent from the user's query.

        Args:
            request (Any): The incoming request containing the user query and context.

        Returns:
            str: The result of the superclass's handle method with updated response information.
        """

        response = request
        logger.info("passing through => Intent extractor")

        if configs.answer_from_enabled:
            response["intent_extractor"] = {
                "intent" : configs.answer_from
            }
        else:
            use_case = self.model_configs.get("use_case", {})
            long_description = use_case.get("long_description", "")
            short_description = use_case.get("short_description", "")
            capabilities = use_case.get("capabilities", [])
            rag = request.get("rag", {})
            context = rag.get("context", {})
            suggestions = rag.get("suggestions", {})

            capability_description = ""
            capability_names = ["out_of_context"]

            for capability in capabilities:
                name = capability["name"]
                description = capability["description"]
                capability_names.append(name)
                capability_description += f"{name} : {description}\n"


            datasources = self.model_configs.get("datasources", [])
            datasource_names = []
            for datasource in datasources:
                if datasource["name"] in self.datasources:
                    name = datasource["name"]
                    description = datasource["description"]

                    capability_names.append(name)
                    datasource_names.append(name)
                    capability_description += f"\n{name} : {description}\n"
                    datasource_context = context.get(name, [])
                    for index,cont in enumerate(datasource_context[:2]):
                        if index == 0:
                            capability_description += f"{cont.get('document','')}\n"
                        else:
                            capability_description += f"{cont.get('document','')}\n"
                    suggestion_context = suggestions.get(name, [])
                    capability_description += "\n Sample questions under this intent: \n"
                    for index,cont in enumerate(suggestion_context[:2]):
                        if index == 0:
                            capability_description += f"Question:{cont.get('document','')}\n"
                        else:
                            capability_description += f"Question:{cont.get('document','')}\n"

                    
            response["available_datasources"] = datasource_names

            chat_contexts = request.get("context", [])
            previous_intent = chat_contexts[-1].chat_answer.get("intent","") if len(chat_contexts) > 0 else "None"

            prompt = """
            You are part of a chatbot system where you have to extract intent from users chats and match it with given intents.

            -- chatbot context ---
            $long_description
            Also provide data structure information and overview of available data.
            -- chatbot context ---

            Available intents are:
            -- Intent section ---
            $capabilities
            out_of_context: If chat is irrelevant to chatbot context and its capabilities
            --- Intent section ---

            Previous last message Intent : $previous_intent

            Instructions:
            1.Only one intent must be identified.Multiple intents are prohibited.
            2.Pay special attention to whether the previous intent has been completed.
            3.Strictly only if the current user query doesn't clearly match an intent, consider the previous messages to identify the most appropriate intent.
            4.Striclty any kind of question if not matching exaclty with their intent samples will go to database_agent 
    
            - ONLY output a **valid JSON object**, no Markdown formatting, no explanation text before or after.
            - DO NOT include anything like "Here is the response" or wrap JSON in triple backticks.

            - Provide a response in strict JSON format with the following structure, extra explanation is strictly prohibited:

            Generate a response for the user query '$question' in the following JSON format:

            {
                "explanation": "Explain how you finalized the intent based on user context and instructions. Include your reasoning for determining whether the previous intent was completed or if the current query relates to a new intent.",
                "intent": "Detected intent, strictly one from the $capability_list"
            }
            """



            capability_list = "|".join(capability_names)

            prompt = Template(prompt).safe_substitute(
                question = request["question"],
                long_description = long_description,
                short_description =short_description,
                capability_list = capability_list,
                capabilities= capability_description,
                previous_intent = previous_intent
            )
            logger.debug(f"intent prompt:{prompt}")
            model_configs = [{'unique_name': 'llama4', 'name': 'meta-llama/llama-4-scout-17b-16e-instruct', 'api_key': configs.groq_api_key, 'endpoint': 'https://api.groq.com/openai/v1/chat/completions', 'kind': 'grogcloud'}]
            loader = BaseLoader(model_configs=model_configs)
            infernce_model = loader.load_model(configs.secondary_inference_llm_model)

            output, response_metadata = await infernce_model.do_inference(
                                prompt, chat_contexts
                        )
            if output["error"] is not None:
                return Formatter.format("Oops! Something went wrong. Try Again!",output['error'])

            response["available_intents"] = capability_names
            intent_extractor = updated_parse_llm_response(output['content'])
            if intent_extractor.get("intent","").lower() == "out_of_context":
                intent_extractor["intent"] = "general_enquiry_agent"

            response["intent_extractor"] = intent_extractor
            
        response["rag_filters"] = {
            "datasources" : [response["intent_extractor"]['intent']] if 'intent_extractor' in response else [],
            "document_count" : 5,
            "schema_count" : 5
        }
        return await super().handle(response)