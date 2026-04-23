import copy
from datetime import datetime
import json
import logging
import time
import re
from enum import Enum
import traceback
from typing import Dict, List, Literal, Optional, Union, Generator
import requests
from google.api_core.exceptions import InvalidArgument
from google.cloud.aiplatform_v1beta1.types import \
    content as gapic_content_types
from google.cloud.aiplatform_v1beta1.types import tool as gapic_tool_types
from google.oauth2 import service_account
from llm_studio_integrations.utils.smart_llm_routing_utils import LLMQuotaExceededException, _get_best_project_and_region, _log_llm_call
from pydantic import Field
from vertexai import init
from vertexai.generative_models import (Content, FunctionDeclaration,
                                        GenerationResponse,
                                        GenerativeModel, Part, Tool)
from vertexai.generative_models._generative_models import ToolConfig
from vertexai.language_models import TextEmbeddingModel
from vertexai.preview.vision_models import ImageGenerationModel

import llm_studio_integrations.utils.utils_chat_history as chat_conversion_tools
from llm_studio_integrations.IntegrationBase import (IntegrationBase,
                                                     IntegrationSetupBase)
from llm_studio_integrations.utils import utils_agent_pubsub
from llm_studio_integrations.utils.agent_enums import (
    GOOGLE_MODEL_REGION_MAP, DisplayFormat, gemini_embedding_model_name,
    gemini_model_name, google_region)

from llm_studio_integrations.utils.utils_tts import get_tts_session, end_tts_session, process_final_tts_data, process_tts_agent_response

from llm_studio_integrations.utils.utils import (ImagenException, _split_json_objects, enum_to_list,
                                                 token_cost, chunk_text, process_streaming_json, get_finish_reason)

from llm_studio_integrations.utils.utils_chat_history import MemoryTechnique
from llm_studio_integrations.utils.utils_traceability import AITrace, TraceBase
from llm_studio_integrations.utils.exceptions import BlockedResponseError, MalformedFunctionCallError, InvalidInputError

class StreamTypes(str, Enum):
    no_stream = "Do Not Stream"
    stream_thinking = "Stream as Thinking Steps"
    stream_response = "Stream as Response"

class InstantLearningChunkTypes(str, Enum):
    chunk_by_paragraph = "Paragraph"
    chunk_by_details_tag = "Details Tag"

class EmbeddingOutputDimensionalityTypes(Enum):
    DIMENSIONALITY_NONE = None
    DIMENSIONALITY_768 = "768"
    DIMENSIONALITY_1536 = "1536"
    DIMENSIONALITY_3072 = "3072"

class ResponseMimeType(str, Enum):
    TEXT = "text/plain"
    JSON = "application/json"
    XENUM = "text/x.enum"

### Setup Configurations ###
class VertexAIIntegrationSetupConfig(IntegrationSetupBase):
    """
    VertexAI-integration setup base class for creating setup config
    """

    llm_model: Literal[tuple(enum_to_list(gemini_model_name))] = Field( #TODO: add support for custom model selection
        ...,
        description="Gemini model to be used",
        title="Gemini Model",
        provider="Google VertexAI",
        displayOnCard=True
    )
    embedding_model: Literal[tuple(enum_to_list(gemini_embedding_model_name))] = Field(
        gemini_embedding_model_name.TEXT_EMBEDDING_005.value,
        description="Google model to be used for embedding",
        title="Google Embedding Model",
        provider="Google VertexAI",
        displayOnCard =True
    )
    region: Literal[tuple(enum_to_list(google_region))] = Field(
        ..., description="Region in which the vertex API will be used", title="Region"
    )

    fallback1_model_name: Literal[tuple(enum_to_list(gemini_model_name))] = Field(
        "",
        description="The Model name to use for response generation.",
        title="Fallback-1 Model Name",
        additionalProperties=True,
    )
    fallback1_region: Literal[tuple(enum_to_list(google_region))] = Field(
        "",
        description="Region to be used for the LLM call.",
        title="Fallback-1 Region",
        additionalProperties=True,
    )

    fallback2_model_name: Literal[tuple(enum_to_list(gemini_model_name))] = Field(
        "",
        description="The Model name to use for response generation.",
        title="Fallback-2 Model Name",
        additionalProperties=True,
    )
    fallback2_region: Literal[tuple(enum_to_list(google_region))] = Field(
        "",
        description="Region to be used for the LLM call.",
        title="Fallback-2 Region",
        additionalProperties=True,
    )

    fallback3_model_name: Literal[tuple(enum_to_list(gemini_model_name))] = Field(
        "",
        description="The Model name to use for response generation.",
        title="Fallback-3 Model Name",
        additionalProperties=True,
    )
    fallback3_region: Literal[tuple(enum_to_list(google_region))] = Field(
        "",
        description="Region to be used for the LLM call.",
        title="Fallback-3 Region",
        additionalProperties=True,
    )

    retries: int = Field(
        1,
        description="The maximum number of retry attempts allowed in case of failure.",
        ge=0,
        le=5,
        additionalProperties=True,
    )
    embedding_retries: int = Field(
        1,
        description="The maximum number of retry attempts allowed in case of failure.",
        ge=0,
        le=5,
        additionalProperties=True,
    )
    project_id: str = Field(
        ...,
        description="Project ID from which the vertex API will be used",
        title="Project Id",
    )
    service_account: str = Field(
        ...,
        description="Service account credentials JSON as a string",
        title="Service Account Credentials",
        encryptionRequired=True,
    )
    memory_count: Optional[int] = Field(
        20,
        description="Number of latest messages you want to store",
        le=20,
        ge=1,
        additionalProperties=True,
    )
    memory_technique: Literal[
        tuple(enum_to_list(MemoryTechnique.MemoryTechniqueEnum))
    ] = Field(
        "last_n",
        description="Method of storing Memory in Redis",
        additionalProperties=True,
    )
    chat_history: Optional[List[Dict]] = Field(
        [], description="Previous conversation history", additionalProperties=True, doNotTrace=True
    )
    action: Literal["generate_image", "text_generation", "get_embedding"] = Field(
        ...,
        description="The VertexAI task to be performed. Must be one of: 'generate_image', 'text_generation', or 'get_embedding'.",
    )
    streaming_option: Literal[tuple(enum_to_list(StreamTypes))] = Field(
        StreamTypes.no_stream.value,
        description="Whether to stream the response directly, or as a thinking message",
        title="Stream type",
    )
    stream_from_instant_learning: Optional[bool] = Field(False,
        description="Whether to stream the response from instant learning. Note: Will only work if Instant Learning is being used.",
        title="Stream from Instant Learning",
        additionalProperties=True,
        propertyToggle="chunking_type_for_streaming_from_instant_learning"
    )
    chunking_type_for_streaming_from_instant_learning: Literal[tuple(enum_to_list(InstantLearningChunkTypes))] = Field(
        InstantLearningChunkTypes.chunk_by_paragraph.value, 
        description="How to chunk the response for streaming from instant learning", 
        additionalProperties=True, title="Chunking Type for Streaming from Instant Learning"
    )
    enable_streaming_json: Optional[bool] = Field(False, 
                                                 description="Enable streaming JSON parsing for LLM responses. When enabled, incomplete JSON responses will be completed and formatted.", 
                                                 title="Enable Streaming JSON", 
                                                 additionalProperties=True)
    imagen_safety_filter: Optional[
        Literal["block_most", "block_some", "block_few", "block_fewest"]
    ] = Field(
        "block_some",
        description="Safety filter level for image generation:\n",
        title="Safety Filter Level",
        additionalProperties=True,
    )
    imagen_person_generation_parameter: Optional[
        Literal["dont_allow", "allow_adult", "allow_all"]
    ] = Field(
        "dont_allow",
        description="person generation parameter for image generation:\n",
        title="Person Generation Parameter",
        additionalProperties=True,
    )
    tools: Optional[List[Dict]] = Field(
        [],
        description="List of tools available to the vertex AI model",
        additionalProperties=True,
    )
    temperature: Optional[float] = Field(
        0,
        description="Controls the creativity of the response (higher values yield more random output)",
        ge=0,
        le=2,
        additionalProperties=True,
    )
    top_p: Optional[float] = Field(
        1,
        description="Controls the diversity of the response (lower values yield more focused output)",
        title="Response Diversity (Top p)",
        ge=0,
        le=1,
        additionalProperties=True,
    )
    top_k: Optional[int] = Field(
        1,
        description="Controls the diversity of the response (lower values yield more focused output)",
        title="Response Diversity (Top k)",
        ge=1,
        additionalProperties=True,
    )
    max_output_tokens: Optional[int] = Field(
        8192,
        description="Limits the total number of tokens (words and symbols) in the response.",
        ge=1,
        title="Max tokens",
        additionalProperties=True,
    )
    candidate_count: Optional[int] = Field(
        1,
        description="Limits the total number of candidates to generate at a time.",
        ge=1,
        title="Candidate count",
        additionalProperties=True,
    )
    embedding_output_dimensionality: Literal[tuple(enum_to_list(EmbeddingOutputDimensionalityTypes))] = Field(
        EmbeddingOutputDimensionalityTypes.DIMENSIONALITY_NONE.value,
        description="Allows to configure the output dimensionality of embedding generation.",
        title="Embedding Dimensionality",
        additionalProperties=True,
    )
    context: Optional[str] = Field(
        None, description="system prompt for the openai task", 
        additionalProperties=True,
        raw_response=True,
    )
    is_tts_enabled: Optional[bool] = Field(
        False, 
        title="Enable Text to Speech", 
        description="Generate speech data for the generated text", 
        additionalProperties=True, propertyToggle=["tts_api_endpoint", "tts_conceirge_id", "tts_agent_id"]
    )
    tts_api_endpoint: Optional[str] = Field(
        "", 
        title="TTS API Endpoint", 
        description="The endpoint for TTS service or agent", 
        additionalProperties=True
    )
    tts_agent_id: Optional[str] = Field(
        "", 
        title="TTS Agent Id", 
        description="The Agent Id for TTS service", 
        additionalProperties=True
    )
    tts_conceirge_id: Optional[str] = Field(
        "", 
        title="TTS Conceirge Id", 
        description="The Conceirge Id for TTS Service", 
        additionalProperties=True
    )
    data: Optional[Dict] = Field(
        None, description="Additional data for the action", additionalProperties=True, doNotTrace=True
    )
    configure_stream_messages: Optional[bool] = Field(
        False,
        description="Whether to configure custom messages for streaming responses.",
        title="Configure Header Messages",
        additionalProperties=True,
        propertyToggle=["stream_start_message", "stream_end_message"]
    )
    stream_start_message: Optional[str] = Field(
        "Generating the response...",
        description="The waiting message to stream at the start of stream.",
        title="Waiting Header Message",
        additionalProperties=True,
    )
    stream_end_message: Optional[str] = Field(
        "Response generated",
        description="The waiting message to stream at the end of stream.",
        title="End Header Message",
        additionalProperties=True,
    )
    response_mime_type: Optional[Literal[tuple(enum_to_list(ResponseMimeType))]] = Field(
        ResponseMimeType.TEXT.value,
        description="MIME type for the response format. Use 'application/json' for structured JSON output or 'text/plain' for regular text.",
        title="Response MIME Type",
        additionalProperties=True,
        propertyMapping={ResponseMimeType.JSON.value: "response_schema", ResponseMimeType.TEXT.value: None, ResponseMimeType.XENUM.value: None},
    )
    response_schema: Optional[str] = Field(
        "",
        description="JSON schema to enforce structured output format. Only used when response_mime_type is 'application/json'. Should be a valid JSON schema object.",
        title="Response Schema",
        additionalProperties=True,
        longText=True
    )
    
    configure_model_thinking: Optional[bool] = Field(
        False,
        description="Whether to configure the model's thinking. If False, Model decides whether, when and how much to think",
        title="Configure Model Thinking",
        additionalProperties=True,
        propertyToggle="thinking_budget"
    )

    thinking_budget: Optional[int] = Field(
        -1,
        description="Limit tokens allocated for the model's thinking process. -1 enables dynamic thinking.",
        title="Thinking Budget",
        ge=-1,
        additionalProperties=True
    )
    seed: Optional[int] = Field(
        None,
        ge=0,
        le=1000,
        description="Seed for reproducible outputs. Must be an integer between 0 and 1000.",
        title="Seed",
        additionalProperties=True,
    )
    smart_llm_routing: Optional[bool] = Field(
        True,
        description="Whether to configure Smart LLM routing.",
        title="Smart LLM Routing",
        additionalProperties=True,
        propertyToggle="smart_llm_routing_url"
    )
    smart_llm_routing_url: Optional[str] = Field(
        "https://devllmstudio.creativeworkspace.ai/llm-load-balancer",
        description="The waiting message to stream at the end of stream.",
        title="Smart LLM Routing URL", 
        additionalProperties=True,
    )



class VertexAIIntegrationTrace(TraceBase, VertexAIIntegrationSetupConfig):
    """
    Trace class for Vertex AI integrations to log interactions and responses.
    """

    common_history: List[Dict] = Field(
        ...,
        description="Previous conversation history.",
        title="Chat History",
        displayFormat=DisplayFormat.CHAT_HISTORY.value,
    )
    finish_reason: str = Field(
        ..., description="Stopping reason for the LLM", title="Finish Reason"
    )
    stream: bool = Field(
        ..., description="Whether to stream the response.", title="Stream Response"
    )
    header_messages: dict = Field(
        ...,
        description="Header messages to be printed when streaming and non streaming responses.",
        title="Header Messages",
    )
    content: str = Field(..., description="Response from the LLM.", title="Response", raw_response=True)
    input_tokens: int = Field(
        ..., description="The number of input tokens used.", title="Input Tokens"
    )
    input_tokens_cost: float = Field(
        ...,
        description="The cost associated with the input tokens used.",
        title="Input Tokens Cost",
    )
    output_tokens: int = Field(
        ..., description="The number of output tokens generated.", title="Output Tokens"
    )
    output_tokens_cost: float = Field(
        ...,
        description="The cost associated with the output tokens and thought tokens.",
        title="Output Tokens Cost",
    )
    thinking_tokens: int = Field(
        ..., description="The number of thinking tokens used.", title="Thought Tokens"
    )
    user_query: str = Field(
        ...,
        description="This is the input query for the vertexai integration",
        title="Input Query",
        displayOnCard=True,
        raw_response=True,
    )
    result: str = Field(
        ...,
        description="A concise and accurate answer addressing the user's query effectively.",
        title="Output Response",
        displayOnCard=True,
        raw_response=True,
    )
    retry_errors: List[str] = Field(
        ..., description="Error message encountered in the last retry attempt"
    )
    embedding_query: List[str] = Field(
        ..., description="The text to be embedded by the model."
    )
    embedding: List[List[float]] = Field(
        ..., description="The embeddings generated by the model."
    )
    smart_llm_routing_time: str = Field(
        ...,
        title="Smart Routing Time (sec)",
        description="Time taken by smart LLM routing to select project and region (in seconds)",
    )
    log_llm_call_time: str = Field(
        ...,
        title="Log LLM Call time (sec)",
        description="Time taken to log the llm call"
    )


class VertexAIIntegration(IntegrationBase):
    """
    An integration to setup and initialize the vertexai client
    """

    CONFIG_CLASS = VertexAIIntegrationSetupConfig

    def setup(
        self, config: dict, header_messages: Optional[dict] = {}
    ):
        
        """
        Initializes the VertexAI client with the provided configuration
        """
        super().setup(config=config)

        self.data = self.config.data or {}
           
        self.logging_context = {
            "concierge_id": self.data.get("concierge_id", "unknown_concierge_id"),
            "concierge_name": self.data.get("concierge_name", "unknown_concierge"),
            "request_id": self.data.get("request_id", "default_request_id"),
            "agent_name": self.data.get("agent_name", "unknown_agent"),
            "agent_id": self.data.get("agent_id", "unknown_agent_id"),
            "llm_process_id": self.data.get("llm_process_id", None)         # For traceability of processes with LLM calls in the logs
        }

        self.region = self.config.region
        self.llm_model = config.get("model") or self.config.llm_model
        if config.get("stream") is False:
            self.config.streaming_option = StreamTypes.no_stream.value
        elif config.get("stream") is True:
            self.config.streaming_option = StreamTypes.stream_thinking.value

        self.stream = self.config.streaming_option != StreamTypes.no_stream
        self.stream_from_instant_learning = self.config.stream_from_instant_learning
        self.chunking_type_for_streaming_from_instant_learning = self.config.chunking_type_for_streaming_from_instant_learning
        self.header_messages = header_messages
        if self.config.configure_stream_messages or (not self.header_messages):
            self.header_messages = {
                "header_message_start": self.config.stream_start_message,
                "header_message_end": self.config.stream_end_message,
            }

        parameters = {
            "temperature": self.config.temperature,
            "max_output_tokens": self.config.max_output_tokens,
            "top_k": self.config.top_k,
            "top_p": self.config.top_p,
        }
        
        if self.config.response_mime_type != ResponseMimeType.TEXT.value:
            parameters["response_mime_type"] = self.config.response_mime_type
        
        if self.config.response_schema and self.config.response_mime_type == ResponseMimeType.JSON.value:
            try:
                response_json_schema = json.loads(self.config.response_schema)
                parameters["response_json_schema"] = response_json_schema
                logging.info(f"Response JSON schema applied: {response_json_schema}")
            except json.JSONDecodeError as e:
                logging.error(f"Invalid JSON schema provided : {e}")
                raise ValueError(f"response_schema must be valid JSON: {e}")
        
        if self.config.seed is not None:
            parameters["seed"] = self.config.seed

        if self.config.configure_model_thinking :
            parameters["thinking_config"] = {"thinking_budget" : self.config.thinking_budget}

        self.generation_config = gapic_content_types.GenerationConfig(
            **parameters,
            candidate_count=self.config.candidate_count,  # it will generate only one candidate at a time
        )
        self.tool_config = ToolConfig(
            function_calling_config=ToolConfig.FunctionCallingConfig(
                # mode=ToolConfig.FunctionCallingConfig.Mode.ANY # one tool call will be made for sure
                mode=ToolConfig.FunctionCallingConfig.Mode.AUTO
            )
        )
        self.memory_technique_func = MemoryTechnique.MEMORY_TECHNIQUE_MAP.get(
            self.config.memory_technique
        )
        self.vertex_history = []
        self.len_past_history = 0
        self.full_chat_history = []
        self.stream_response = None
        self.vertex_tools = self.prepare_tools(self.config.tools)
        self.chat_history = self.config.chat_history if self.config.chat_history else []
        self.common_history = self.config.chat_history
        self.chat_history = []
        self.initial_response = True
        self.retry_errors = []
        self.tts_session_details = {}

        if self.config.is_tts_enabled:
            self.tts_api_endpoint = self.config.tts_api_endpoint
            self.tts_agent_id = self.config.tts_agent_id
            self.tts_conceirge_id = self.config.tts_conceirge_id
        
        self.streaming_json_lexer = None
        if self.config.enable_streaming_json:
            try:
                import streamingjson
                self.streaming_json_lexer = streamingjson.Lexer()
                logging.info(f"streamingjson version: {streamingjson.__version__}")
            except ImportError:
                self.enable_streaming_json = False
                self.streaming_json_lexer = None
                logging.error("streamingjson library not found. Streaming JSON will be disabled.")

        self.smart_llm_routing = self.config.smart_llm_routing
        self.service_accounts_config = {}
        if self.smart_llm_routing:
            try:
                self.available_projects = []
                self._setup_smart_routing()
                logging.info(
                    f"Vertex AI Integration setup completed with model: {self.llm_model}"
                )
                return  # Exit early if smart routing succeeds
            except Exception as e:
                logging.warning(f"Smart LLM routing failed: {e}. Falling back to single service account.")
        #else:

        # Single service account flow (fallback or default)
        self.google_application_credentials = (
            service_account.Credentials.from_service_account_info(
                json.loads(self.config.service_account)
            )
        )
        init(
            project=self.config.project_id,
            location=self.region,
            credentials=self.google_application_credentials,
        )

        self.chat_model = GenerativeModel(
            self.llm_model,
            system_instruction=self.config.context,
            tool_config=self.tool_config,
        )
        self.chat = self.chat_model.start_chat()


        logging.info(f"Vertex AI Integraion setup completed with modeL: {self.llm_model}")
        
    def preprocess_history(self):
        # Apply memory technique
        if self.memory_technique_func:
            self.full_chat_history = copy.deepcopy(
                self.common_history
            )  # Keep full history
            transformed_memory = self.memory_technique_func(
                self.common_history, self.config.memory_count
            )
        else:
            raise ValueError(
                f"Invalid memory technique: {self.config.memory_technique}. Supported memory techniques are: {', '.join([e.value for e in MemoryTechnique])}."
            )
        self.chat_history, self.len_past_history = (
            chat_conversion_tools.convert_common_to_vertex_chathistory(
                transformed_memory
            )
        )

    def postprocess_history(self):
        # Retrieve the new messages from the chat session
        current_session_chat_history = self.chat.history
        new_chat_others = [
            chat_conversion_tools.VertexAIMessage(
                role=(
                    "assistant"
                    if msg.to_dict()["role"] == "model"
                    else msg.to_dict()["role"]
                ),
                parts=msg.to_dict().get("parts", []),
            )
            for msg in current_session_chat_history[self.len_past_history :]
        ]
        self.common_history = (
            chat_conversion_tools.convert_vertex_to_common_chathistory(
                old_chat=self.full_chat_history, new_chat=new_chat_others
            )
        )

    def prepare_tools(self, tools: List[Dict]) -> List[Tool]:
        """
        Prepares tools in the required format for Vertex AI Gemini model.

        Args:
            tools (list[dict]): List of tool definitions to prepare.

        Returns:
            list[Tool]: List containing a single Tool object with all function declarations.
        """

        if tools:
            function_declarations = []
            for tool in tools:
                tool_function = tool.get("function", {})
                tool_function.get("parameters", {}).pop(
                    "additionalProperties", None
                )  # Remove 'additionalProperties' from parameters
                function_declarations.append(
                    FunctionDeclaration(
                        name=tool_function["name"],
                        description=tool_function["description"],
                        parameters=tool_function["parameters"],
                    )
                )
            # Converted each tool into a FunctionDeclaration object, and Return a single Tool object with all function declarations
            return [Tool(function_declarations=function_declarations)]
        return []

    @AITrace(VertexAIIntegrationTrace)
    def run(self, query: str,aspect_ratio: Optional[str] = None):
        """
        Executes either response generation, or image generation based on the action provided during setup.
        """
        if self.common_history and self.initial_response:
            self.preprocess_history()
        self.user_query = query
        if self.config.action == "text_generation":
            if self.smart_llm_routing:
                self.result = self.text_generation_with_sllmr(query=query)
            else:
                self.result = self.text_generation(query=query)
        elif self.config.action == "generate_image":
            return self.generate_image(aspect_ratio=aspect_ratio, query=query)
        elif self.config.action == "get_embedding":
            if self.smart_llm_routing:
                self.result = self.get_embedding_with_sllmr(query)
            else:
                self.result = self.get_embedding(query)
        else:
            raise ValueError(
                f"Invalid action: {self.config.action}. Supported actions are 'embedding', 'generate_response', and 'generate_image'."
            )
        
        self.chat_history = self.chat.history
        self.postprocess_history()
        return self.result
    
    @AITrace(VertexAIIntegrationTrace)
    def run_stream_response_for_instant_learning(self, query: str, next_trace=None, trace=None) -> Generator[Dict, None, None]:
        """
        Yields responses from the streaming mode of text_generation,
        and runs cleanup after the stream ends.
        """
        logging.info(f"Streaming from instant learning {self.stream_from_instant_learning}")
        if self.common_history and self.initial_response:
            self.preprocess_history()
        self.user_query = query

        if self.smart_llm_routing:
            func = self.text_generation_with_sllmr
        else:
            func = self.text_generation

        try:
            yield from func(query=query)
        finally:
            self.chat_history = self.chat.history
            self.postprocess_history()

    def text_generation(self, query: str) -> Dict:
        """
        Generates text response using the Vertex AI language model.

        Args:
            query (str): User query for text generation.
            system_prompt (str): System prompt to guide the model's response.

        Returns:
            dict: Generated response content, finish reason, and tool calls.
        """
        regions = set(
            [
                self.region,
                *GOOGLE_MODEL_REGION_MAP.get(
                    self.llm_model, [google_region.US_CENTRAL1.value]
                ),
            ]
        )
        regions = sorted(
            regions, key=lambda x: x != self.region  # Prioritize user-specified region
        )
        logging.info(f"Available Regions for {self.llm_model}: {regions}")

        self.chat_model._system_instruction = self.config.context
        messages = self.prepare_messages() or self.chat_history
        self.chat = self.chat_model.start_chat(
            history=messages, response_validation=False
        )
                     
        base_delay = 1
        # TODO: still need to check on region switching for VertexAI

        for retry in range(self.config.retries + 1):
            for location in regions:
                starttime = str(datetime.utcnow())
                try:
                    logging.info(
                        f"Attempt {retry + 1}/{self.config.retries}: Using model {self.llm_model}, in region: {location}"
                    )
                    init(
                        project=self.config.project_id,
                        location=location,
                        credentials=self.google_application_credentials,
                    )
                    if query:
                        try:
                            response = self.chat.send_message(
                                content=query,
                                generation_config=self.generation_config,
                                stream=self.stream,
                                tools=self.vertex_tools,
                            )
                        except IndexError as e:
                            raise BlockedResponseError(
                            block_reason="PROHIBITED_CONTENT",
                            message="VertexAI blocked or returned an empty response after all retries (possible prohibited content).",
                        )
                    elif self.vertex_history:
                        response = self.chat.send_message(
                            content=Part.from_function_response(
                                **self.vertex_history[-1]["tool_results"]
                            ),
                            generation_config=self.generation_config,
                            stream=self.stream,
                            tools=self.vertex_tools,
                        )
                    else:
                        raise InvalidInputError(f"The query to vertexAI integration is invalid. query={query}")
                    
                    if self.stream_from_instant_learning:
                        result = self.process_text_response_yield_chunk(response)
                    else:
                        result = self.process_text_response(response)
                    

                    if getattr(self, "finish_reason", None) in ["UNEXPECTED_TOOL_CALL"]:
                        raise Exception(
                            f"Tool call failed with finish reason: {self.finish_reason}"
                        )
                    
                    if getattr(self, "finish_reason", None) == "MALFORMED_FUNCTION_CALL":
                        raise MalformedFunctionCallError(
                            message=f"Function call failed with finish reason: {self.finish_reason}"
                        )

                    if hasattr(self, "input_tokens"):
                        self.logging_context["input_tokens"] = self.input_tokens
                    if hasattr(self,"output_tokens"):
                        self.logging_context["output_tokens"] = self.output_tokens + (self.thinking_tokens if hasattr(self,"thinking_tokens") else 0)
                    self.log_llm_call_time = _log_llm_call(self.config.smart_llm_routing_url, self.config.action, self.logging_context, self.config.project_id, self.llm_model, location, status="success", start_time=starttime, end_time=str(datetime.utcnow()), increment_counter=True)
                    return result
                        

                except (BlockedResponseError, MalformedFunctionCallError, InvalidInputError) as e:
                    raise

                except Exception as e:
                    sleep_time = base_delay * (2**retry)
                    tb_str = traceback.format_exc()
                    if hasattr(self,"input_tokens"):
                        self.logging_context["input_tokens"] = self.input_tokens
                    if hasattr(self,"output_tokens"):
                        self.logging_context["output_tokens"] = self.output_tokens + (self.thinking_tokens if hasattr(self,"thinking_tokens") else 0)
                    self.log_llm_call_time = _log_llm_call(self.config.smart_llm_routing_url, self.config.action, self.logging_context, self.config.project_id, self.llm_model, location, status="error", start_time=starttime, end_time=str(datetime.utcnow()), error_message=f"{str(e)}\nTraceback:\n{tb_str}", increment_counter=True)
                    time.sleep(sleep_time)
                    error = f"Vertex AI error in retry {retry + 1}/{self.config.retries}: {str(e)}"
                    logging.error(
                        f"Vertex AI error in retry {retry + 1}/{self.config.retries}: {str(e)}"
                    )
                    self.retry_errors.append(error)  # Store error for tracing

        # If all retries fail, raise an error
        raise Exception(
            f"All retries failed for {self.llm_model}. Last error: {self.retry_errors}"
        )
    
    def text_generation_with_sllmr(self, query: str) -> Dict:
        """
        Generates text response using the Vertex AI language model.

        Args:
            query (str): User query for text generation.
            system_prompt (str): System prompt to guide the model's response.

        Returns:
            dict: Generated response content, finish reason, and tool calls.
        """
        regions = set(
            [
                self.region,
                *GOOGLE_MODEL_REGION_MAP.get(
                    self.llm_model, [google_region.US_CENTRAL1.value]
                ),
            ]
        )
        regions = sorted(
            regions, key=lambda x: x != self.region  # Prioritize user-specified region
        )
                    
        base_delay = 1
        # TODO: still need to check on region switching for VertexAI

        for retry in range(self.config.retries + 1):
            for location in regions:
                starttime = str(datetime.utcnow())
                routing_start_time = datetime.utcnow()
                try:
                    best_project, best_region = _get_best_project_and_region(
                        self.config.smart_llm_routing_url, 
                        self.logging_context,
                        self.available_projects, 
                        self.llm_model, 
                        self.config.project_id, 
                        location
                    )
                    routing_end_time = datetime.utcnow()
                    self.smart_llm_routing_time = str((routing_end_time - routing_start_time).total_seconds())
                    logging.info(
                        f"Attempt {retry + 1}/{self.config.retries}: Using model {self.llm_model}, in region: {best_region}"
                    )
                    # Tracing info
                    self.project_id = best_project
                    self.region = best_region
                    credentials = self.service_accounts_config.get(best_project, {}).get('credentials')
                    if not credentials:
                        raise ValueError(f"No credentials found for project {best_project}")
                    
                    starttime = str(datetime.utcnow())
                    self._initialize_vertex_ai_session(best_project, best_region, credentials, history_changes_needed=True)
                    logging.info(f"Smart routing selected --> Project: {best_project}, Region: {best_region}")

                    if query:
                        response = self.chat.send_message(
                            content=query,
                            generation_config=self.generation_config,
                            stream=self.stream,
                            tools=self.vertex_tools,
                        )
                    elif self.vertex_history:
                        response = self.chat.send_message(
                            content=Part.from_function_response(
                                **self.vertex_history[-1]["tool_results"]
                            ),
                            generation_config=self.generation_config,
                            stream=self.stream,
                            tools=self.vertex_tools,
                        )
                    else:
                        raise InvalidInputError(f"The query to vertexAI integration is invalid. query={query}")

                    if self.stream_from_instant_learning:
                        result = self.process_text_response_yield_chunk(response)
                    else:
                        result = self.process_text_response(response)
                        
                    if getattr(self, "finish_reason", None) in ["UNEXPECTED_TOOL_CALL"]:
                        raise Exception(
                            f"Tool call failed with finish reason: {self.finish_reason}"
                        )
                    
                    if getattr(self, "finish_reason", None) == "MALFORMED_FUNCTION_CALL":
                        raise MalformedFunctionCallError(
                            message=f"Function call failed with finish reason: {self.finish_reason}"
                        )

                    if hasattr(self, "input_tokens"):
                        self.logging_context["input_tokens"] = self.input_tokens
                    if hasattr(self,"output_tokens"):
                        self.logging_context["output_tokens"] = self.output_tokens + (self.thinking_tokens if hasattr(self,"thinking_tokens") else 0)
                    self.log_llm_call_time = _log_llm_call(self.config.smart_llm_routing_url, self.config.action, self.logging_context, best_project, self.llm_model, best_region, status="success", start_time=starttime, end_time=str(datetime.utcnow()), increment_counter=False)
                    return result
                

                except LLMQuotaExceededException as e:
                    # Log the quota exceeded scenario and exit immediately
                    logging.critical(f"🚫 LLM Quota Exceeded: {str(e)}")
                    if hasattr(self,"input_tokens"):
                        self.logging_context["input_tokens"] = self.input_tokens
                    if hasattr(self,"output_tokens"):
                        self.logging_context["output_tokens"] = self.output_tokens + (self.thinking_tokens if hasattr(self,"thinking_tokens") else 0)
                    self.log_llm_call_time = _log_llm_call(
                        self.config.smart_llm_routing_url, 
                        self.config.action, 
                        self.logging_context, 
                        self.config.project_id,  # Use original project since routing failed
                        self.llm_model, 
                        location, 
                        status="error", 
                        start_time=starttime, 
                        end_time=str(datetime.utcnow()), 
                        error_message=str(e), 
                        increment_counter=False
                    )
                    # Re-raise to propagate to higher-level error handling
                    raise

                except Exception as e:
                    tb_str = traceback.format_exc()
                    if hasattr(self,"input_tokens"):
                        self.logging_context["input_tokens"] = self.input_tokens
                    if hasattr(self,"output_tokens"):
                        self.logging_context["output_tokens"] = self.output_tokens + (self.thinking_tokens if hasattr(self,"thinking_tokens") else 0)
                    self.log_llm_call_time = _log_llm_call(self.config.smart_llm_routing_url, self.config.action, self.logging_context, best_project, self.llm_model, best_region, status="error", start_time=starttime, end_time=str(datetime.utcnow()), error_message=f"{str(e)}\nTraceback:\n{tb_str}", increment_counter=False)
                    sleep_time = base_delay * (2**retry)
                    time.sleep(sleep_time)
                    error = f"Vertex AI error in retry {retry + 1}/{self.config.retries}: {str(e)}"
                    logging.error(
                        f"Vertex AI error in retry {retry + 1}/{self.config.retries}: {str(e)}"
                    )
                    self.retry_errors.append(error)  # Store error for tracing

                    if isinstance(e, (BlockedResponseError, MalformedFunctionCallError, InvalidInputError)):
                        raise

        # If all retries fail, raise an error
        raise Exception(
            f"All retries failed for {self.llm_model}. Last error: {self.retry_errors}"
        )

    def prepare_messages(self) -> list[Content]:
        """Prepares chat messages for the Vertex AI emini language model.

        Returns:
            list[Content]: List of chat message objects.
        """

        chat_history = self.chat.history

        if chat_history:
            is_match = False
            if self.stream:
                msg_obj = []
                msg = self.stream_response
                parts = []
                role_ = msg["role"]
                parts_ = msg["parts"]

                if "text" in parts_:
                    if parts_["text"].strip():
                        if (
                            chat_history[-1].parts[0].text.strip()
                            == parts_["text"].strip()
                        ):
                            is_match = True
                        parts.append(Part.from_text(parts_["text"]))
                if "function_call" in parts_:
                    for function_call in parts_["function_call"]:
                        parts.append(
                            Part._from_gapic(
                                raw_part=gapic_content_types.Part(
                                    function_call=gapic_tool_types.FunctionCall(
                                        function_call
                                    )
                                )
                            )
                        )

                msg_obj = Content(
                    parts=tuple(parts),
                    role=role_,
                )
                if is_match:
                    chat_history[-1] = msg_obj
            return chat_history

    def process_text_response(self, response: GenerationResponse) -> Dict:
        """
        Processes the response from the Vertex AI models.

        Args:
            response (GenerationResponse): Raw response from the model.

        Returns:
            dict: Processed content, finish reason, and tool calls.
        """
        self.input_tokens = 0
        self.output_tokens = 0
        self.thinking_tokens = 0
        if self.stream:
            self.tts_session_details = {}
            if self.config.is_tts_enabled:
                self.tts_session_details = get_tts_session(
                    agent_url=self.tts_api_endpoint,
                    agent_id=self.tts_agent_id,
                    concierge_id=self.tts_conceirge_id
                )
            (
                content,
                chat_history,
                finish_reason,
                response_list,
                self.input_tokens,
                self.output_tokens,
                self.thinking_tokens,
                final_speech_data
            ) = self.process_stream_response_vertex_ai(
                response,
                self.config.data,
                explainability_id=self.explainability_id,
                stream_response_directly=(
                    self.config.streaming_option == StreamTypes.stream_response
                ),
                tts_session_details=self.tts_session_details,
                streaming_json_lexer=self.streaming_json_lexer,
                header_message=self.header_messages
            )
            tool_calls = self.extract_tool_calls(response_list)
            self.stream_response = chat_history
            self.total_tokens = self.input_tokens + self.output_tokens + self.thinking_tokens
            self.finish_reason = finish_reason

            if self.tts_session_details:
                tts_agent_data, tts_traceability_structure, tts_trace_root = end_tts_session(speech_data=final_speech_data)
        else:
            parts = response.candidates[0].content.parts
            content = ""
            for part in parts:
                if hasattr(part, "text"):
                    content += part.text
            finish_reason = get_finish_reason(response.candidates[0].finish_reason) if response.candidates[0].finish_reason else None
            self.finish_reason = finish_reason
            tool_calls = self.extract_tool_calls(response)
            self.input_tokens = response.usage_metadata.prompt_token_count
            self.output_tokens = response.usage_metadata.candidates_token_count
            self.total_tokens = response.usage_metadata.total_token_count
            self.thinking_tokens = getattr(
                response.usage_metadata, "thoughts_token_count", 0
            )
        
        # Calculate total tokens
        self.input_tokens_cost, self.output_tokens_cost, self.total_tokens_cost = (
            token_cost(
                self.llm_model,
                self.input_tokens,
                self.output_tokens + self.thinking_tokens,
            )
        )

        self.content = content
        return {
            "content": content,
            "finish_reason": finish_reason,
            "tool_calls": tool_calls,
        }

    def process_text_response_yield_chunk(self, response: GenerationResponse) -> Union[Dict, Generator[Dict, None, None]]:
        """
        Yields back the streaming response from the Vertex AI models.

        Args:
            response (GenerationResponse): Raw response from the model.

        Returns:
            Generator[Dict, None, None]: Yields processed content, finish reason, and tool calls.
        """
        self.input_tokens = 0
        self.output_tokens = 0
        self.thinking_tokens = 0
        final_metadata = None
        for chunk in self.process_stream_response_vertex_ai_yield(response, chunking_method=self.chunking_type_for_streaming_from_instant_learning):
            if chunk.get("is_stream_end"):
                final_metadata = chunk
            else:
                yield chunk
        
        if final_metadata:
            content = final_metadata.get("final_response_text")
            chat_history = final_metadata.get("chat_history")
            finish_reason = final_metadata.get("finish_reason")
            response_list = final_metadata.get("response_list")
            self.finish_reason = finish_reason
            self.input_tokens = final_metadata.get("tokens", {}).get("input")
            self.output_tokens = final_metadata.get("tokens", {}).get("output")
            tool_calls = self.extract_tool_calls(response_list)
            self.stream_response = chat_history
            self.total_tokens = self.input_tokens + self.output_tokens 

        # Calculate total tokens
        self.input_tokens_cost, self.output_tokens_cost, self.total_tokens_cost = token_cost(self.llm_model, 
                                                                                            self.input_tokens, 
                                                                                            self.output_tokens + self.thinking_tokens
                                                                                            )
        self.content = content
        yield {
            "content": content,
            "finish_reason": finish_reason,
            "tool_calls": tool_calls,
            "is_stream_end": True,
        }

    def generate_image(self, aspect_ratio: str, query: str):
        if aspect_ratio not in ["1:1", "3:4", "4:3", "16:9", "9:16"]:
            raise ValueError(
                f'Invalid aspect ratio:({aspect_ratio}), supported aspect ratios are: "1:1", "3:4", "4:3", "16:9", "9:16"'
            )
        generation_model = ImageGenerationModel.from_pretrained(self.llm_model)

        try:
            attempt = 0
            while attempt < 6:
                try:

                    images = generation_model.generate_images(
                            prompt=query,
                            number_of_images=1,
                            aspect_ratio=aspect_ratio,
                            safety_filter_level=self.config.imagen_safety_filter,
                            person_generation=self.config.imagen_person_generation_parameter,
                            seed = 11267,
                            add_watermark=False,
                            guidance_scale=23
                        )

                    if not list(images):
                        logging.error("vertexai_integration: No image generated")
                        raise ImagenException(
                "This query did not produce any images because it violates the 'person_generation' parameter. Try rephrasing the query,")

                    else:
                        logging.info("vertexai_integration: image generated")

                    return images

                except Exception as e:

                    images={}
                    logging.info(f'vertexai_integration: Error generating image for aspect ratio {aspect_ratio}, attempt {attempt}. Retrying in 10 seconds... Error: {e}')

                    attempt += 1
                    time.sleep(10)

        except InvalidArgument as e:
            self.error = f"Vertex AI Integration error: {str(e)}"
            if "sensitive words" in str(e):
                raise ImagenException(
                    "This query contains sensitive words that violate the safety filter settings. Try rephrasing the query.")
            else:
                logging.error(self.error)
                raise Exception(self.error)
        except Exception as e:
            logging.error(f"vertexai_integration: Error in imagen:{str(e)}")
            raise Exception(self.error)

        if not list(images):
            self.error = f"vertexai_integration: No image generated"
            logging.error(self.error)
            raise ImagenException(
                "This query did not produce any images because it violates the 'person_generation' parameter. Try rephrasing the query,"
            )
        else:
            logging.info("vertexai_integration: image generated")
        return images

    def get_embedding(self, query: Union[str, List]) -> List[float]:
        try:
            is_query_list = isinstance(query, list)
            starttime = str(datetime.utcnow())
            self.embedding_query = query if is_query_list else [query]
            model = TextEmbeddingModel.from_pretrained(self.config.embedding_model)
            if self.config.embedding_output_dimensionality:
                self.embeddings = [
                    embedding.values
                    for embedding in model.get_embeddings(self.embedding_query, output_dimensionality = int(self.config.embedding_output_dimensionality))
                ]
            else:
                self.embeddings = [
                    embedding.values
                    for embedding in model.get_embeddings(self.embedding_query)
                ]
            self.log_llm_call_time = _log_llm_call(self.config.smart_llm_routing_url, self.config.action, self.logging_context, self.config.project_id, self.config.embedding_model, self.region, status="success", start_time=starttime, end_time=str(datetime.utcnow()), increment_counter=True)
            return self.embeddings if is_query_list else self.embeddings[0]
        except Exception as e:
            self.error = f"Error in generating Embeddings via VertexAI: {e}"
            self.log_llm_call_time = _log_llm_call(self.config.smart_llm_routing_url, self.config.action, self.logging_context, self.config.project_id, self.config.embedding_model, self.region, status="error", start_time=starttime, end_time=str(datetime.utcnow()), error_message=str(e), increment_counter=True)
            logging.error(self.error)
            raise Exception(self.error)
        
    def get_embedding_with_sllmr(self, query: Union[str, List]) -> List[float]:
        max_retries = self.config.embedding_retries + 1
        base_delay = 1  # seconds
        max_delay = 30  # seconds

        is_query_list = isinstance(query, list)
        self.embedding_query = query if is_query_list else [query]
     
        for attempt in range(max_retries):
            starttime = str(datetime.utcnow())
            try:
                logging.info(f"Attempt {attempt + 1}/{max_retries} for embedding generation")
                best_project, best_region = _get_best_project_and_region(
                    self.config.smart_llm_routing_url, 
                    self.logging_context,
                    self.available_projects, 
                    self.config.embedding_model, 
                    self.config.project_id, 
                    self.region
                )
                credentials = self.service_accounts_config.get(best_project, {}).get('credentials')
                self._initialize_vertex_ai_session(best_project, best_region, credentials)
                logging.info(f"Using Project: {best_project}, Region: {best_region} for embedding generation") 
                
                model = TextEmbeddingModel.from_pretrained(self.config.embedding_model)
                if self.config.embedding_output_dimensionality:
                    self.embeddings = [
                        embedding.values
                        for embedding in model.get_embeddings(
                            self.embedding_query, 
                            output_dimensionality=int(self.config.embedding_output_dimensionality)
                        )
                    ]
                else:
                    self.embeddings = [
                        embedding.values
                        for embedding in model.get_embeddings(self.embedding_query)
                    ]
                self.log_llm_call_time = _log_llm_call(
                    self.config.smart_llm_routing_url, 
                    self.config.action, 
                    self.logging_context, 
                    best_project, 
                    self.config.embedding_model, 
                    best_region, 
                    status="success", 
                    start_time=starttime, 
                    end_time=str(datetime.utcnow()), 
                    increment_counter=False
                )
                return self.embeddings if is_query_list else self.embeddings[0]
            
            except LLMQuotaExceededException as e:
                # Log the quota exceeded scenario and exit immediately
                logging.critical(f"🚫 Embedding Quota Exceeded: {str(e)}")
                self.log_llm_call_time = _log_llm_call(
                    self.config.smart_llm_routing_url, 
                    self.config.action, 
                    self.logging_context, 
                    self.config.project_id,  # Use original project since routing failed
                    self.config.embedding_model, 
                    self.region, 
                    status="error", 
                    start_time=starttime, 
                    end_time=str(datetime.utcnow()), 
                    error_message=str(e), 
                    increment_counter=False
                )
                # Re-raise to propagate to higher-level error handling
                raise
                
            except Exception as e:
                if attempt == max_retries - 1:
                    # Last attempt failed, raise the exception
                    error = f"Error in generating Embeddings via VertexAI after {max_retries} attempts: {e}"
                    logging.error(error)
                    self.retry_errors.append(error)
                # Calculate exponential backoff delay
                self.log_llm_call_time = _log_llm_call(self.config.smart_llm_routing_url, self.config.action, self.logging_context, best_project, self.config.embedding_model, best_region, status="error", start_time=starttime, end_time=str(datetime.utcnow()), error_message=str(e), increment_counter=False)
                delay = min(base_delay * (2 ** attempt), max_delay)
                logging.warning(
                    f"Attempt {attempt + 1}/{max_retries} failed: {e}. "
                    f"Retrying in {delay} seconds..."
                )
                time.sleep(delay)
        raise Exception(
            f"All retries failed for generating embeddings via VertexAI. Last errors: {self.retry_errors}"
        )

    def extract_tool_calls(self, response_list) -> List[Dict]:
        """
        Extracts tool calls from the Vertex AI model's response.

        Returns:
            list[dict]: Extracted tool call details.
        """

        if not self.stream:
            return [
                {call.name: {key: value for key, value in call.args.items()}}
                for call in response_list.candidates[0].function_calls or []
            ]

        else:
            temp = []
            for response in response_list:
                functions_ = response.candidates[0].function_calls
                temp.extend(
                    [
                        {call.name: {key: value for key, value in call.args.items()}}
                        for call in functions_ or []
                    ]
                )
            return temp
        
    @staticmethod
    def process_stream_response_vertex_ai(
        response,
        data,
        header_message={},
        explainability_id=None,
        stream_response_directly=False,
        tts_session_details = {},
        streaming_json_lexer=None
    ):
        response_text = ""
        is_stream_end = False
        thinking_break = False
        response_list = []
        finish_reason = None
        input_tokens = 0
        output_tokens = 0
        thinking_tokens = 0
        chat_history = []
        candidate_obj = {}

        sentence_chunk_buffer = ""
        accumulated_speech_data = []
        final_speech_data = {}

        if tts_session_details:
            trace_full = tts_session_details.get("trace_full")

        for message in response:
            if message.usage_metadata:
                token_usage = message.usage_metadata
                input_tokens = token_usage.prompt_token_count
                output_tokens = token_usage.candidates_token_count
                thinking_tokens = getattr(token_usage, "thoughts_token_count", 0)

            for candidate_ in message.candidates:
                if "role" not in candidate_obj:
                    candidate_obj["role"] = candidate_.content.role

                if "parts" not in candidate_obj:
                    candidate_obj["parts"] = {"text": "", "function_call": []}

                for parts_ in candidate_.content.parts:
                    parts_ = parts_.to_dict()
                    if "text" in parts_:
                        candidate_obj["parts"]["text"] += parts_.get("text", "")
                    if "function_call" in parts_:
                        candidate_obj["parts"]["function_call"].append(
                            parts_.get("function_call", {})
                        )

                # Check the finish reason
                if get_finish_reason(candidate_.finish_reason) == "STOP":
                    chat_history = candidate_obj
                    candidate_obj = {}  # Reset after appending to chat_history

            candidate = message.candidates[0]
            tool_calls = candidate.content.parts[-1].function_call if candidate.content.parts else None

            if not tool_calls:
                content = candidate.content.parts[-1].text
                response_text += content
                
                text_to_send = process_streaming_json(streaming_json_lexer, content, response_text) if streaming_json_lexer else response_text
                tts_agent_data = {}
                if tts_session_details:
                    tts_agent_data, sentence_chunk_buffer = process_tts_agent_response(content, sentence_chunk_buffer, tts_session_details, trace_full, accumulated_speech_data)

                utils_agent_pubsub.send_streaming_response_to_pubsub(
                    data=data,
                    text=text_to_send,
                    is_stream_end=is_stream_end,
                    thinking_break=thinking_break,
                    header_message=header_message.get(
                        "header_message_start", "Processing..."
                    ),
                    explainability_id=explainability_id,
                    is_orchestrator=stream_response_directly,
                    speech_data=tts_agent_data
                )
            else:
                response_list.append(message)

            if candidate.finish_reason:
                finish_reason = get_finish_reason(candidate.finish_reason)
                if finish_reason in {"STOP", "MAX_TOKENS"}:
                    break
        
        final_text_to_send = process_streaming_json(streaming_json_lexer, content, response_text) if streaming_json_lexer else response_text
        
        if tts_session_details:
            final_speech_data, tts_agent_data = process_final_tts_data(response_text, sentence_chunk_buffer, tts_session_details, trace_full, accumulated_speech_data)
            utils_agent_pubsub.send_streaming_response_to_pubsub(
                data=data, 
                text=final_text_to_send,
                is_stream_end=is_stream_end,
                thinking_break=thinking_break,
                header_message=header_message.get('header_message_start', "Processing..."),
                explainability_id=explainability_id,
                is_orchestrator=stream_response_directly,
                speech_data=tts_agent_data
            )

        if response_text and not stream_response_directly:
            thinking_break = True
            utils_agent_pubsub.send_streaming_response_to_pubsub(
                data=data,
                text=response_text,
                is_stream_end=is_stream_end,
                thinking_break=thinking_break,
                header_message=header_message.get(
                    "header_message_end", "Processed! 👍"
                ),
                explainability_id=explainability_id,
                is_orchestrator=stream_response_directly,
            )

        return (
            response_text,
            chat_history,
            finish_reason,
            response_list,
            input_tokens,
            output_tokens,
            thinking_tokens,
            final_speech_data
        )

    @staticmethod
    def process_stream_response_vertex_ai_yield(response, chunking_method="Paragraph"):
        response_text = ""
        buffer = ""
        response_list = []
        input_tokens = 0
        output_tokens = 0
        chat_history = []
        candidate_obj = {}

        for message in response:
            if message.usage_metadata:
                token_usage = message.usage_metadata
                input_tokens = token_usage.prompt_token_count
                output_tokens = token_usage.candidates_token_count

            for candidate_ in message.candidates:
                if "role" not in candidate_obj:
                    candidate_obj["role"] = candidate_.content.role
                if "parts" not in candidate_obj:
                    candidate_obj["parts"] = {"text": "", "function_call": []}

                for parts_ in candidate_.content.parts:
                    parts_ = parts_.to_dict()
                    if "text" in parts_:
                        candidate_obj["parts"]["text"] += parts_["text"]
                    if "function_call" in parts_:
                        candidate_obj["parts"]["function_call"].append(parts_["function_call"])

                if get_finish_reason(candidate_.finish_reason) == "STOP":
                    chat_history = candidate_obj
                    candidate_obj = {}

            candidate = message.candidates[0]
            tool_calls = candidate.content.parts[-1].function_call

            if not tool_calls:
                chunk = candidate.content.parts[-1].text
                buffer += chunk
                response_text += chunk

                chunks, buffer = chunk_text(buffer, chunking_method)
                for i, para in enumerate(chunks):
                    yield {
                        "chunk": para,
                        "is_stream_end": False,
                        "last_chunk": False,
                        "tokens": {"input": input_tokens, "output": output_tokens}
                    }

            else:
                response_list.append(message)

        # Final leftover buffer
        yield {
            "chunk": buffer if buffer else "",
            "is_stream_end": False,
            "last_chunk": True,
            "tokens": {"input": input_tokens, "output": output_tokens}
        }

        yield {
            "paragraph": None,
            "is_stream_end": True,
            "final_response_text": response_text,
            "chat_history": chat_history,
            "finish_reason": get_finish_reason(candidate.finish_reason) if candidate.finish_reason else None,
            "response_list": response_list,
            "tokens": {"input": input_tokens, "output": output_tokens}
        }

    def _setup_smart_routing(self):
        """Setup Smart LLM Routing with multiple service accounts"""
        try:
            # Parse comma-separated service accounts
            service_accounts_list = _split_json_objects(self.config.service_account)
            
            for sa_json_str in service_accounts_list:
                try:
                    sa_info = json.loads(sa_json_str)
                    project_id = sa_info.get('project_id')
                    # Only add if project_id exists in rate_limit_config
                    if project_id:
                        credentials = service_account.Credentials.from_service_account_info(sa_info)
                        
                        self.service_accounts_config[project_id] = {
                            'project_id': project_id,
                            'credentials': credentials,
                        }
                        self.available_projects.append(project_id)
                        
                except json.JSONDecodeError as e:
                    logging.error(f"Failed to parse service account JSON: {e}")
                    continue        
            
            # For image generation, disable smart routing as it's not supported
            if self.config.action == "image_generation":
                self.smart_llm_routing = False
                logging.info("Disabling Smart LLM Routing for image generation (not supported)")
                raise ValueError("Smart LLM Routing is not supported for image generation.")

            if not self.service_accounts_config:
                raise ValueError("No valid service accounts found for Smart LLM Routing.")
            if not self.available_projects:
                raise ValueError("No available projects found for Smart LLM Routing.")

            user_selected_project = self.config.project_id
            if user_selected_project not in self.service_accounts_config:
                raise ValueError(f"Configured project_id {user_selected_project} not found in provided service accounts.")
            
        except Exception as e:
            logging.error(f"Failed to setup Smart LLM Routing: {e}")
            raise
    

    def _initialize_vertex_ai_session(self, project_id: str, region: str, credentials, history_changes_needed: bool = False):
        """
        Re-initializes Vertex AI with the specified project and region, and recreates the chat session.
        
        Args:
            project_id (str): Google Cloud project ID
            region (str): Region to use for the session
            credentials: Service account credentials
            messages (list): Chat history messages for the session
            
        Raises:
            ValueError: If required parameters are missing or invalid
            Exception: If Vertex AI initialization fails
        """
        try:
            # Validate input parameters
            if not project_id or not isinstance(project_id, str):
                raise ValueError("Project ID must be a non-empty string")
            
            if not region or not isinstance(region, str):
                raise ValueError("Region must be a non-empty string")
            
            if credentials is None:
                raise ValueError("Credentials cannot be None")
                        
            logging.info(f"initializing Vertex AI session with Project: {project_id}, Region: {region}, credentials: {credentials.service_account_email}")
            
            try:
                init(project=project_id, location=region, credentials=credentials)
                logging.debug("Vertex AI initialization successful.")
            except Exception as e:
                logging.error(f"Vertex AI initialization failed: {e}")
                raise Exception(
                    f"Failed to initialize Vertex AI with project '{project_id}' in region '{region}': {e}"
                )
            
            # RE-CREATE the chat model with the new context
            try:
                
                self.chat_model = GenerativeModel(
                    self.llm_model,
                    system_instruction=self.config.context,
                    tool_config=self.tool_config,
                )
                self.chat = self.chat_model.start_chat()
                logging.debug("Chat model creation successful")
            except Exception as e:
                logging.error(f"Chat model creation failed: {str(e)}")
                raise Exception(f"Failed to create chat model {self.llm_model}: {str(e)}")
            
            # RE-CREATE the chat session
            if history_changes_needed:
                try:
                    self.chat_model._system_instruction = self.config.context
                    messages = self.prepare_messages() or self.chat_history
                    self.chat = self.chat_model.start_chat(
                        history=messages, response_validation=False
                    )
                    logging.debug("Chat session creation successful")
                except Exception as e:
                    logging.error(f"Chat session creation failed: {str(e)}")
                    raise Exception(f"Failed to create chat session: {str(e)}")
                
                logging.info("Vertex AI session reinitialized successfully")
            
        except ValueError as ve:
            logging.error(f"Validation error in Vertex AI session reinitialization: {str(ve)}")
            raise
        except Exception as e:
            logging.error(f"Unexpected error in Vertex AI session reinitialization: {str(e)}")
            raise


