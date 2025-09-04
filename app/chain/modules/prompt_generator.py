from app.base.abstract_handlers import AbstractHandler
from typing import Any
from loguru import logger
from string import Template

class PromptGenerator(AbstractHandler):
    """
    A handler for generating prompts based on the provided context, model configurations, and data sources.

    This class creates a formatted prompt for the model by combining various elements such as system prompts,
    user prompts, and context information. It supports both manual and automatic prompt injection modes.

    Attributes:
        common_context (dict): Shared context information used across handlers.
        model_configs (dict): Configuration settings for the model, including prompt injection settings.
        datasources (dict): Data sources for generating prompt contexts based on intent.
    """


    def __init__(self, common_context , model_configs, datasources) -> None:
        """
        Initializes the PromptGenerator with common context, model configurations, and data sources.

        Args:
            common_context (dict): Shared context information used across handlers.
            model_configs (dict): Configuration settings for the model.
            datasources (dict): Data sources for generating prompt contexts based on intent.
        """

        self.model_configs = model_configs
        self.common_context = common_context
        self.datasources = datasources

    async def handle(self, request: Any) -> str:
        """
        Generates a prompt based on the incoming request and provided configurations.
        Args:
            request (Any): The incoming request containing data for prompt generation.

        Returns:
            str: The result of the superclass's handle method with the generated prompt included in the response.
        """

        logger.info("passing through => prompt_generator")
        response = request
        intent = response["intent_extractor"]['intent']

        contexts = request.get("context",[])
        previous_messages = contexts[-2:] if len(contexts) >= 2 else contexts

        recal_history = ""
        index = 1
        
        previous_schemas = []
        for message in previous_messages:
            recal_history += f"[{index}] USER: {message.chat_query}\n"
            answer = message.chat_answer
            if answer.get('query','') != '':
                recal_history += f"ASSITANT: query : {answer.get('query','')}\n  data: {answer.get('data',[])[:5]}\n\n"
            else:
                chat_summary = message.chat_summary
                recal_history += f"ASSITANT: {chat_summary}"

            
            previous_schemas.extend(message.chat_context.get("rag", {}).get("schema", [])[:2])

            index += 1
        # Few shot prompting
        samples_retrieved = ""

        rag = request.get("rag", {})
        datasource_suggestions = rag.get("suggestions", {})
        for doc in datasource_suggestions.get(intent, []):
            samples_retrieved += f"question: {doc.get('document', '')}\n"
            samples_retrieved += f"query: {doc.get('metadatas', {}).get('query', '')}\n\n"


        prompt_injection = self.model_configs.get("prompt_injection", {"mode": "auto"})
        data_source = self.datasources.get(self.common_context.get("intent", "default"))

        context = data_source.__prompt__
        prompt = context.base_prompt
        language_detector = response.get("language_detector",{})
        language_type = language_detector.get("language_type","english")
        if language_type.lower() == "hindi":
            language_type = "Romanized Hindi"

        system_prompt = ""

        if prompt_injection["mode"] == "manual" :
            system_prompt_context = context.system_prompt
            system_prompt = system_prompt_context.template.format(
                **{**system_prompt_context["prompt_variables"]}
            )
        else:
            auto_context = "\n\n".join(cont["document"] for cont in rag.get("context", {}).get(intent,[]))
            auto_schema = ""
            rag_schemas = rag.get("schema", [])
            tables = []
            for r in rag_schemas:
                tables.append(r.get("metadatas",{}).get("table_name","").lower())

            # logger.info(f"rag_schemas:{rag_schemas}")
            added_tables = []
            for prev_schema in previous_schemas:
                # logger.info(f"prev_schema:{prev_schema}")
                table_name = prev_schema.get("metadatas",{}).get("table_name","")
                if table_name.lower() not in tables and table_name.lower() not in added_tables:
                    added_tables.append(table_name.lower())
                    # logger.info(f"table_name:{table_name}")
                    rag_schemas.append(prev_schema)            
            auto_schema = ""
            for schema in rag_schemas:
                auto_schema += "\n\n" + schema["document"]
            
            system_prompt_context = context.system_prompt
            system_prompt = system_prompt_context.template.format(
                schema=auto_schema,
                context=auto_context,
                question=request.get("question", ""),
                suggestions="",
                recal_history=recal_history
            )


        user_prompt = ""

        if self.common_context["chain_retries"] == 0:
            user_prompt = context.user_prompt.template
        else:
            logger.info("regenerating prompt using available context")
            regeneration_promt_context = context.regeneration_prompt

            user_prompt = Template(regeneration_promt_context.template).safe_substitute(
                exception_log =self.common_context["execution_logs"][0]["error"] if len(self.common_context["execution_logs"])>0 else "",
                query_generated =self.common_context["execution_logs"][0]["query"] if len(self.common_context["execution_logs"])>0 else ""
            )

        final_prompt = prompt.format(user_prompt=user_prompt, system_prompt=system_prompt)
        final_prompt = Template(final_prompt).safe_substitute(
            question=request.get("question", ""),
            suggestions=samples_retrieved,
            language_type=language_type,
            **self.model_configs.get("use_case", {})
        )

        response["prompt"] = final_prompt
        logger.debug(f"final_prompt:{final_prompt}")
        return await super().handle(response)
