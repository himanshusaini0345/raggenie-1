from typing import List, Optional, Any
import json
import httpx  # async HTTP client
from langchain.callbacks.manager import (
    AsyncCallbackManagerForLLMRun,
    CallbackManagerForLLMRun,
)
from langchain.llms.base import LLM
from loguru import logger


class BaseLLM(LLM):
    temperature: Optional[float] = 0.5
    url: str = ""
    headers: Optional[dict] = {}
    body: Optional[dict] = {}

    def _call(
        self,
        prompt: Optional[str] = "",
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
    ) -> str:
        """Synchronous call to LLM (blocking)."""
        if prompt:
            self.body["prompt"] = prompt
        try:
            r = requests.post(self.url, json=self.body, headers=self.headers)
            r.raise_for_status()
            model_out = r.json()
        except Exception as e:
            logger.error(f"LLM request failed: {e}")
            model_out = {}

        return model_out

    async def _acall(
        self,
        prompt: str,
        stop: Optional[List[str]] = None,
        run_manager: Optional[AsyncCallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> str:
        """Asynchronous call to LLM (non-blocking, can be used in async streaming)."""
        if prompt:
            self.body["prompt"] = prompt

        try:
            async with httpx.AsyncClient(timeout=120) as client:
                r = await client.post(self.url, json=self.body, headers=self.headers)
                r.raise_for_status()
                model_out = r.json()
        except Exception as e:
            logger.error(f"Async LLM request failed: {e}")
            model_out = {}

        return model_out

    @property
    def _llm_type(self) -> str:
        return "rest_llm"

    @property
    def _identifying_params(self) -> dict:
        return {"url": self.url}
