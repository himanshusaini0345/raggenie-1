import json
from loguru import logger
import re 

def parse_llm_response(body):
        text = body.replace("\\n","")
        text = text.replace("\n","")
        text = text.replace("\\_","_")
        if '\\"' not in text:
            text = text.replace("\\","")
        text = text.removeprefix("```json")
        text = text.removesuffix("```")
        text = text.removesuffix("User:")
        try:
            out = json.loads(text)
            logger.info(f"parsed llm response: {out}")
        except Exception as e:
            logger.info("error parsing llm response")
            out = {}

        return out

def updated_parse_llm_response(body: str):
    text = body.strip()

    # Remove code fences like ```json ... ``` or ``` ... ```
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z0-9]*\s*", "", text)  # remove leading ```json / ```python etc
        text = re.sub(r"\s*```$", "", text)              # remove trailing ```
    
    # Clean up escape sequences
    text = text.replace("\\_", "_")
    text = text.replace("\\n", "")
    text = text.replace("\n", "")
    if '\\"' not in text:
        text = text.replace("\\", "")

    # Remove unwanted suffix if present
    text = text.removesuffix("User:").strip()

    try:
        out = json.loads(text)
        logger.info(f"parsed llm response: {out}")
    except Exception as e:
        logger.info("error parsing llm response")
        out = {}

    return out

def markdown_parse_llm_response(body):
        # text = body.replace("\\n","")
        # text = text.replace("\n","")
        # text = text.replace("\\","")
        # text = text.replace("\\_","_")
        # if '\\"' not in text:
        #     text = text.replace("\\","")
        text = body.removeprefix("```json")
        text = text.removesuffix("```")
        text = text.removesuffix("User:")

        try:
            out = json.loads(text)
        except Exception as e:
            logger.info("error parsing llm response")
            out = {}

        return out

