import abc
import os
import time
from pathlib import Path
from functools import cache

# import torch
""" from transformers import (
    AutoTokenizer,
    AutoModelForCausalLM,
    AutoModelForSeq2SeqLM,
    AutoConfig,
    pipeline as hf_pipeline,
) """
import openai
from together import Together
from together.error import TogetherException

# Constants (import or define as needed)
from llm_players.llm_constants import (
    TASK2OUTPUT_FORMAT,
    INITIAL_GENERATION_PROMPT,
    INSTRUCTION_INPUT_RESPONSE_PATTERN,
    LLAMA3_PATTERN,
    DEFAULT_PIPELINE_PROMPT_PATTERN,
    DEFAULT_PROMPT_PATTERN,
    GENERAL_SYSTEM_INFO,
    SLEEPING_TIME_FOR_API_GENERATION_ERROR,
    MAX_NEW_TOKENS_KEY,
    MAX_TOKENS_KEY,
    NUM_BEAMS_KEY,
    HUGGINGFACE_GENERATION_PARAMETERS,
    OPENAI_GENERATION_PARAMETERS,
    GENERATION_PARAMETERS,
    SECRETS_DICT_FILE_PATH,
    USE_TOGETHER_KEY,
    USE_OPENAI_KEY,
    USE_PIPELINE_KEY,
    PIPELINE_TASK_KEY,
    TOGETHER_API_KEY_KEYWORD,
    OPENAI_API_KEY_KEYWORD,
)


def _load_secrets():
    secrets_file = Path(SECRETS_DICT_FILE_PATH)
    if secrets_file.exists():
        try:
            return eval(secrets_file.read_text())
        except Exception:
            return {}
    return {}


def get_api_key(env_key: str, dict_key: str):
    key = os.getenv(env_key)
    if key:
        return key
    return _load_secrets().get(dict_key)


class LLM(abc.ABC):
    def __init__(self, logger, **llm_config):
        self.logger = logger
        self.model_name = llm_config.get("model_name")
        self.llm_config = llm_config
        self.prompt_template = self._get_prompt_template()
        # self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self._setup_generation_parameters()
        self._initialize()
        # Warm-up
        print("warm-up", flush=True)
        self.generate(INITIAL_GENERATION_PROMPT, system_info=GENERAL_SYSTEM_INFO)
        print("warm-up done", flush=True)

    def _get_prompt_template(self):
        name = self.model_name.lower()
        if "phi-3" in name:
            return INSTRUCTION_INPUT_RESPONSE_PATTERN
        if "llama-3" in name:
            return LLAMA3_PATTERN
        if self.llm_config.get(USE_OPENAI_KEY):
            return DEFAULT_PIPELINE_PROMPT_PATTERN
        return DEFAULT_PROMPT_PATTERN

    def _setup_generation_parameters(self):
        # Abstract: set self.generation_parameters from llm_config
        self.generation_parameters = {}

    @abc.abstractmethod
    def _initialize(self):
        """Instantiate client, model, tokenizer or pipeline"""
        pass

    @abc.abstractmethod
    def _call_llm(self, inputs):
        """Given preprocessed inputs, call the model and return raw outputs"""
        pass

    def generate(self, input_text: str, system_info: str = "") -> str:
        # if hasattr(self, 'pipeline') and self.pipeline:
        messages = self.pipeline_preprocessing(input_text, system_info)
        self.logger.log("Pipeline messages", messages)
        raw = self._call_llm(messages)
        return raw
        # return self.postprocess_pipeline(raw)
        # else:
        """  prompt = self.direct_preprocessing(input_text, system_info)
        self.logger.log("Direct prompt", prompt)
        raw = self._call_llm(prompt)
        return self.direct_postprocessing(raw) """

    def pipeline_preprocessing(self, input_text: str, system_info: str):
        if self.prompt_template in (
            INSTRUCTION_INPUT_RESPONSE_PATTERN,
            LLAMA3_PATTERN,
            DEFAULT_PIPELINE_PROMPT_PATTERN
        ):
            system_msg = [{"role": "system", "content": system_info}] if system_info else []
            return system_msg + [{"role": "user", "content": input_text}]
        raise NotImplementedError("Pipeline preprocessing not supported for this template")

    def direct_preprocessing(self, input_text: str, system_info: str) -> str:
        if self.prompt_template == INSTRUCTION_INPUT_RESPONSE_PATTERN:
            instruction = f"{system_info.strip()} {input_text}" if system_info else input_text
            return f"### Instruction:\n{instruction}\n### Response: "
        if self.prompt_template == LLAMA3_PATTERN:
            header = f"<|start_header_id|>system<|end_header_id|>{system_info}<|eot_id|>" if system_info else ""
            return (
                f"<|begin_of_text|>{header}"
                f"<|start_header_id|>user<|end_header_id|>{input_text}<|eot_id|>"
                f"<|start_header_id|>assistant<|end_header_id|>"
            )
        raise NotImplementedError("Direct preprocessing not supported for this template")

    def postprocess_pipeline(self, raw_output):
        # raw_output assumed str for simplicity
        return raw_output

    def direct_postprocessing(self, decoded: str) -> str:
        if self.prompt_template == INSTRUCTION_INPUT_RESPONSE_PATTERN:
            return decoded.split("### Response:")[1].split("</s>")[0].strip()
        if self.prompt_template == LLAMA3_PATTERN:
            out = decoded.split("<|start_header_id|>assistant<|end_header_id|>")[1]
            out = out.split("<|eot_id|>")[0]
            return out.lstrip(":").strip()
        return decoded

        
class TogetherLLM(LLM):
    def _initialize(self):
        self.client = Together(api_key=get_api_key(TOGETHER_API_KEY_KEYWORD, TOGETHER_API_KEY_KEYWORD))
        self.pipeline = True

    def _setup_generation_parameters(self):
        self.generation_parameters = {
            k: self.llm_config[k]
            for k in GENERATION_PARAMETERS
            if k in self.llm_config
        }
        self.generation_parameters[MAX_NEW_TOKENS_KEY] = self.llm_config.get(MAX_NEW_TOKENS_KEY, 25)

    def _call_llm(self, messages):
        output = None
        while not output:
            try:
                resp = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=messages,
                    **self.generation_parameters,
                )
                output = resp.choices[0].message.content
            except TogetherException as e:
                time.sleep(SLEEPING_TIME_FOR_API_GENERATION_ERROR)
        return output

class OpenAILLM(LLM):
    def _initialize(self):
        openai.api_key = get_api_key(OPENAI_API_KEY_KEYWORD, OPENAI_API_KEY_KEYWORD)
        self.client = openai
        self.pipeline = True

    def _setup_generation_parameters(self):
        self.generation_parameters = {
            k: self.llm_config[k]
            for k in OPENAI_GENERATION_PARAMETERS
            if k in self.llm_config
        }
        self.generation_parameters[MAX_TOKENS_KEY] = self.llm_config.get(MAX_TOKENS_KEY, 25)
   
    def _call_llm(self, messages):
        output = None
        while not output:
            try:
                resp = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=messages,
                    # **self.generation_parameters, # commented out for now because different for generation parameters for different models
                )
                output = resp.choices[0].message.content
            except openai.OpenAIError as e:
                print(e, flush=True)
                time.sleep(SLEEPING_TIME_FOR_API_GENERATION_ERROR)
        return output

    """    
    This is not tested!

    class PipelineLLM():
        def _initialize(self):
            task = self.llm_config.get(PIPELINE_TASK_KEY)
            self.pipeline = hf_pipeline(task, self.model_name, device_map="auto")
        def _setup_generation_parameters(self):
            self.generation_parameters = {
                k: self.llm_config[k]
                for k in HUGGINGFACE_GENERATION_PARAMETERS
                if k in self.llm_config
            }
            self.generation_parameters[MAX_NEW_TOKENS_KEY] = self.llm_config.get(MAX_NEW_TOKENS_KEY, 25)

        def _call_llm(self, messages):
            outputs = self.pipeline(messages, **self.generation_parameters)
            return outputs[0][TASK2OUTPUT_FORMAT[self.llm_config.get(PIPELINE_TASK_KEY)]][-1] 
    """


    """
    This is not tested!
    
    class LocalLLM():
        @cache
        def _load_model(self):
            if os.path.isdir(self.model_name):
                cfg = AutoConfig.from_pretrained(self.model_name)
                return AutoModelForSeq2SeqLM.from_pretrained(self.model_name, config=cfg)
            return AutoModelForCausalLM.from_pretrained(self.model_name)

        @cache
        def _load_tokenizer(self):
            return AutoTokenizer.from_pretrained(self.model_name)

        def _initialize(self):
            self.model = self._load_model()
            self.model.to(self.device)
            self.model.eval()
            self.tokenizer = self._load_tokenizer()
            self.pipeline = None

        def _setup_generation_parameters(self):
            self.generation_parameters = {
                k: self.llm_config[k]
                for k in GENERATION_PARAMETERS
                if k in self.llm_config
            }
            self.generation_parameters[MAX_NEW_TOKENS_KEY] = self.llm_config.get(MAX_NEW_TOKENS_KEY, 25)
            if NUM_BEAMS_KEY in self.generation_parameters and self.generation_parameters[NUM_BEAMS_KEY] < 2:
                del self.generation_parameters[NUM_BEAMS_KEY]

        def _call_llm(self, prompt):
            inputs = self.tokenizer(prompt, return_tensors="pt").to(self.device)
            outputs = self.model.generate(**inputs, **self.generation_parameters)
            return self.tokenizer.decode(outputs[0], skip_special_tokens=False) 
    """

class OpenAI_4o(LLM):
    def _initialize(self):
        openai.api_key = get_api_key(OPENAI_API_KEY_KEYWORD, OPENAI_API_KEY_KEYWORD)
        self.client = openai
        self.pipeline = True

    def _setup_generation_parameters(self):
        self.generation_parameters = {
            k: self.llm_config[k]
            for k in OPENAI_GENERATION_PARAMETERS
            if k in self.llm_config
        }
        # self.generation_parameters[MAX_TOKENS_KEY] = self.llm_config.get(MAX_TOKENS_KEY, 25)
   
    def _call_llm(self, messages):
        output = None
        while not output:
            try:
                resp = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=messages,
                    # **self.generation_parameters, # commented out for now because different for generation parameters for different models
                )
                output = resp.choices[0].message.content
            except openai.OpenAIError as e:
                print(e, flush=True)
                time.sleep(SLEEPING_TIME_FOR_API_GENERATION_ERROR)
        return output


class OpenAI_o4_mini(LLM):
    REASONING_PROMPT = " \n To perform your role to the best of your ability, let's think about your response step-by-step. You have been given a " \
    " hidden sctrachpad where you can detail your steps / reasoning behind your response." \
    " Anything written down in this scratchpad will not be shown as output to the end user." \
    " Use this scratchpad to think about your response, and then write your final response. \n" \
    " 1. demonstrate your reasoning inside a hidden scratchpad, which will be delimited by <<< and >>>. \n" \
    " 3. Immediately after the closing >>>, anything that you write (including leading newlines and spaces) " \
    " will be part of your output response. \n" \

    def _initialize(self):
        openai.api_key = get_api_key(OPENAI_API_KEY_KEYWORD, OPENAI_API_KEY_KEYWORD)
        self.client = openai
        self.pipeline = True

    def _setup_generation_parameters(self):
        self.generation_parameters = {
            k: self.llm_config[k]
            for k in OPENAI_GENERATION_PARAMETERS
            if k in self.llm_config
        }
        self.generation_parameters[MAX_TOKENS_KEY] = self.llm_config.get(MAX_TOKENS_KEY, 25)
   
    # o4-mini specific preprocessing
    def pipeline_preprocessing(self, input_text: str, system_info: str):
        input_msg = f"{system_info} + \n + {input_text} + \n"
        reasoning_msg = {"effort" : "high", 
                         "summary" : "detailed"}
        return \
            { 
            "input": input_msg,
            "reasoning": reasoning_msg,
            }
    
    def postprocess_pipeline(self, response):
        # Assuming response is an OpenAI response object
        # Separate the output from the reasoning scratchpad and return both

        reasoning = response.output[0].summary
        content = response.output[1].content

        if reasoning == []:
            reasoning = "No reasoning provided."
        else:
            reasoning_output = ""
            for r in reasoning:
                reasoning_output += r.text.strip() + "\n"
            
        if content == []:
            content = "No output provided."
        else:
            content = content[0].text.strip()

        return \
            {
            "reasoning": reasoning,
            "output": content,
            }
    
    # General preprocessing format for most LLMs, should follow something similar.
    """ def pipeline_preprocessing(self, input_text: str, system_info: str):
            system_info += self.REASONING_PROMPT
            system_msg = [{"role": "system", "content": system_info}] if system_info else []
            return system_msg + [{"role": "user", "content": input_text}] """
    
    # Must remove the hidden scratchpad from the end output.
    # General preprocessing format for most LLMs
    """ def postprocess_pipeline(self, response):
        # Assuming response is an OpenAI response object
        # Separate the output from the reasoning scratchpad and return both

        raw_output = response
        reasoning = raw_output.split("<<<")[1].split(">>>")[0].strip() if "<<<" in raw_output and ">>>" in raw_output else ""
        if reasoning == "":
            reasoning = "No reasoning provided."

        output = raw_output.split(">>>")[-1].strip() if ">>>" in raw_output else raw_output.strip()

        return \
            {
            "reasoning": reasoning,
            "output": output,
            } """

    def _call_llm(self, messages) -> str:
        output = None
        while not output:
            try:
                resp = self.client.responses.create(
                    model=self.model_name,
                    input=messages["input"],
                    reasoning=messages["reasoning"],
                    # **self.generation_parameters, # commented out for now because different for generation parameters for different models
                )
                output = resp.model_dump_json(indent=2)
                self.logger.log("Raw LLM Output", output)
            except openai.OpenAIError as e:
                print(e, flush=True)
                time.sleep(SLEEPING_TIME_FOR_API_GENERATION_ERROR)
        return resp
    
    def generate(self, input_text: str, system_info: str = "") -> str:
        messages = self.pipeline_preprocessing(input_text, system_info)
        """ self.logger.log("Pipeline messages - System", messages[0]["content"])
        self.logger.log("Pipeline messages - User", messages[1]["content"]) """
        self.logger.log("Complete Prompt to LLM", messages["input"])
        raw = self._call_llm(messages)
        processed_output = self.postprocess_pipeline(raw)
        self.logger.log("Reasoning behind Output", processed_output["reasoning"])
        self.logger.log("Output to User", processed_output["output"])
        
        return processed_output["output"]

# Factory

def create_llm(logger, **llm_config):
    if llm_config.get(USE_TOGETHER_KEY):
        return TogetherLLM(logger, **llm_config)
    if llm_config.get(USE_OPENAI_KEY):
        return OpenAI_4o(logger, **llm_config)
    if llm_config.get(USE_PIPELINE_KEY):
        # return LLM.PipelineLLM(logger, **llm_config)
        raise NotImplementedError("Pipeline LLM is not implemented yet.")
    # return LLM.LocalLLM(logger, **llm_config)
    print(llm_config.get(USE_OPENAI_KEY))
    raise NotImplementedError("Local LLM is not implemented yet, or the model is not found/implemented.")
