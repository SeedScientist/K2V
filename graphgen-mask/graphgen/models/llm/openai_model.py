import math
from dataclasses import dataclass, field
from typing import List, Dict, Optional
import openai
from openai import AsyncOpenAI, RateLimitError, APIConnectionError, APITimeoutError
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

from graphgen.models.llm.topk_token_model import TopkTokenModel, Token
from graphgen.models.llm.tokenizer import Tokenizer
from graphgen.models.llm.limitter import RPM, TPM

def get_top_response_tokens(response: openai.ChatCompletion) -> List[Token]:
    token_logprobs = response.choices[0].logprobs.content
    tokens = []
    for token_prob in token_logprobs:
        prob = math.exp(token_prob.logprob)
        candidate_tokens = [
            Token(t.token, math.exp(t.logprob))
            for t in token_prob.top_logprobs
        ]
        token = Token(token_prob.token, prob, top_candidates=candidate_tokens)
        tokens.append(token)
    return tokens

@dataclass
class OpenAIModel(TopkTokenModel):
    model_name: str = "gpt-4o-mini"
    api_key: str = None
    base_url: str = None

    system_prompt: str = ""
    json_mode: bool = False
    seed: int = 42

    token_usage: list = field(default_factory=list)
    request_limit: bool = False
    rpm: RPM = field(default_factory=lambda: RPM(rpm=1000))
    tpm: TPM = field(default_factory=lambda: TPM(tpm=50000))

    tokenizer_instance: Tokenizer = None

    generate_kwargs: dict = field(default_factory=dict)

    def __post_init__(self):
        assert self.api_key is not None, "Please provide api key to access openai api."
        self.client = AsyncOpenAI(api_key=self.api_key, base_url=self.base_url)

    def _pre_generate(self, text: str, history: List[str]) -> Dict:
        kwargs = {
            "temperature": self.generate_kwargs.get("temperature", None),
            "top_p": self.generate_kwargs.get("top_p", None),
            "max_tokens": self.generate_kwargs.get("max_tokens", 16384),
            "extra_body": {"repetition_penalty": self.generate_kwargs.get("repetition_penalty", None),
                           "top_k": self.generate_kwargs.get("top_k", None)},
        }
        if self.generate_kwargs.get("presence_penalty", None):
            kwargs["presence_penalty"] = self.generate_kwargs.get("presence_penalty")
        if self.seed:
            kwargs["seed"] = self.seed
        if self.json_mode:
            kwargs["response_format"] = {"type": "json_object"}

        messages = []
        if self.system_prompt:
            messages.append({"role": "system", "content": self.system_prompt})
        messages.append({"role": "user", "content": text})

        if history:
            assert len(history) % 2 == 0, "History should have even number of elements."
            messages = history + messages

        kwargs['messages']= messages
        return kwargs


    @retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((RateLimitError, APIConnectionError, APITimeoutError)),
    )
    async def generate_topk_per_token(self, text: str, history: Optional[List[str]] = None) -> List[Token]:
        kwargs = self._pre_generate(text, history)
        if self.topk_per_token > 0:
            kwargs["logprobs"] = True
            kwargs["top_logprobs"] = self.topk_per_token

        # Limit max_tokens to 1 to avoid long completions
        kwargs["max_tokens"] = 1

        completion = await self.client.chat.completions.create( # pylint: disable=E1125
            model=self.model_name,
            **kwargs
        )

        tokens = get_top_response_tokens(completion)

        return tokens

    @retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((RateLimitError, APIConnectionError, APITimeoutError)),
    )
    async def generate_answer(self, text: str, history: Optional[List[str]] = None) -> str:
        kwargs = self._pre_generate(text, history)
        prompt_tokens = 0
        for message in kwargs['messages']:
            prompt_tokens += len(self.tokenizer_instance.encode_string(message['content']))
        estimated_tokens = prompt_tokens + kwargs['max_tokens']

        if self.request_limit:
            await self.rpm.wait(silent=True)
            await self.tpm.wait(estimated_tokens, silent=True)

        completion = await self.client.chat.completions.create( # pylint: disable=E1125
            model=self.model_name,
            **kwargs
        )
        if hasattr(completion, "usage"):
            self.token_usage.append({
                "prompt_tokens": completion.usage.prompt_tokens,
                "completion_tokens": completion.usage.completion_tokens,
                "total_tokens": completion.usage.total_tokens,
            })
        return completion.choices[0].message.content

    async def generate_inputs_prob(self, text: str, history: Optional[List[str]] = None) -> List[Token]:
        raise NotImplementedError
