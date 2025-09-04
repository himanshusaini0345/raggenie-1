from app.models.prompt import Prompt
from collections import OrderedDict
from app.models.request import ConnectionArgument

# Plugin Metadata
__version__ = '1.0.0'
__plugin_name__ = 'website'
__display_name__ = 'Website loader'
__description__ = 'Website integration for handling website data'
__icon__ = '/assets/plugins/logos/website.svg'
__category__ = 1


# Connection arguments
__connection_args__ = OrderedDict(
    website_url= ConnectionArgument(
        type = 4,
        generic_name= 'Website URL',
        description = 'URL of website',
        order = 1,
        required = True,
        value = None,
        slug = "website_url"
    ),
    headers=ConnectionArgument(
        type= 7,
        generic_name= 'Headers to be used',
        description= 'Provide required headers',
        order= 2,
        required = True,
        value = None,
        slug = "headers"
    ),
    depth=ConnectionArgument(
        type= 3,
        generic_name= 'Depth of scanning',
        description= 'Choose the depth of scanning for child URLs. Set to 0 to scan all',
        order= 3,
        required = True,
        value=None,
        slug = "depth"
    )
)

# Prompt
__prompt__ = Prompt(**{
        "base_prompt": "{system_prompt}{user_prompt}",
        "system_prompt": {
            "template": """
            You are a helpful AI Chatbot designed to answer user questions.

            Conversation history is provided below:
            -- start chat_history section --
            {recal_history}
            -- end chat_history section --

            Strictly consider Sample answers with their questions are given below:
            -- start answer samples section--
            $suggestions
            -- end answer samples section--

            Follow these response rules:
            - The conversation history is arranged in strict chronological order from OLDEST to NEWEST.
            -  Striclty if it is a follow up from conversation history quesion then consider conversation history to construct the response
            - Always understand the **intent of the user’s question** and respond meaningfully.
            - Use a **human-like tone**, be friendly, polite, and professional in your message.
            - Ensure responses are well-structured and make complete sense to the user.
            - Utilize samples if context for answering found from it
            - Make sure to give general message in $language_type language only
            """
        },
        "user_prompt":{
            "template": """
            User question is "$question"
            generate a json in the following format without any formatting.
            {
                "operation_kind" : "none",
                "general_message": "Your response to the user;s question in a friendly, clear, and professional Markdown message in $language_type language only",
                "confidence" : "confidence in 100",
                "main_entity": "document"
            }
            """
        },
        "regeneration_prompt": {
            "template": """
            User question is "$question"
            generate a json in the following format without any formatting.
            {
                "operation_kind" : "none",
                "general_message": "Answer to user question in human readable Markdown format based on the context and samples",
                "confidence" : "confidence in 100",
                "main_entity": "document"
            }
            """
        }
    })



__all__ = [
    __version__, __plugin_name__, __display_name__ , __description__, __icon__, __category__, __prompt__
]