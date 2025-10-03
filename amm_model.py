from pydantic import BaseModel, Field, FilePath, DirectoryPath, model_validator, validator
from typing import List, Optional, Dict, Any
from enum import Enum
import uuid

class KnowledgeSourceType(str, Enum):
    FILE = "file"
    DIRECTORY = "directory" # Retaining for potential future use, though engine doesn't use it yet
    URL = "url"
    TEXT = "text"

class GeminiModelType(str, Enum):
    # Current Gemini models as of May 2025
    GEMINI_2_5_FLASH = "gemini-2.5-flash-preview-04-17"
    GEMINI_2_5_PRO = "gemini-2.5-pro-preview-05-06"
    GEMINI_2_0_FLASH = "gemini-2.0-flash"
    GEMINI_2_0_FLASH_IMAGE = "gemini-2.0-flash-preview-image-generation"
    GEMINI_2_0_FLASH_LITE = "gemini-2.0-flash-lite"
    GEMINI_1_5_FLASH = "gemini-1.5-flash"
    GEMINI_1_5_FLASH_8B = "gemini-1.5-flash-8b"
    GEMINI_1_5_PRO = "gemini-1.5-pro"
    
    # Embedding model
    GEMINI_EMBEDDING = "gemini-embedding-exp"
    TEXT_EMBEDDING_004 = "models/text-embedding-004"
    
    # Image and video generation models
    IMAGEN_3 = "imagen-3.0-generate-002"
    VEO_2 = "veo-2.0-generate-001"
    
    # Legacy models (kept for backward compatibility)
    GEMINI_PRO = "gemini-pro"
    GEMINI_FLASH_LATEST = "models/gemini-1.5-flash-latest"
    GEMINI_PRO_LATEST = "models/gemini-pro-latest"
    GEMINI_ULTRA_LATEST = "models/gemini-ultra-latest"

class KnowledgeSourceConfig(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str = Field(..., description="User-defined name for the knowledge source.")
    type: KnowledgeSourceType
    path: Optional[str] = None # Path to file, directory, or URL
    content: Optional[str] = None # Direct text content
    encoding: Optional[str] = Field(default='utf-8', description="Encoding for file-based sources")
    description: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata for the source.")

    @model_validator(mode='after') # Changed from before to after for Pydantic v2 for checking fields
    def check_path_and_content_based_on_type(cls, values: Any) -> Any:
        # In Pydantic V2, the first argument to a model_validator (mode='after') is the model instance itself.
        # So, we access fields directly from 'values' (the model instance).
        source_type = values.type
        path = values.path
        content = values.content

        if source_type in [KnowledgeSourceType.FILE, KnowledgeSourceType.URL]:
            if not path:
                raise ValueError(f"'path' is required for knowledge source type '{source_type.value}'")
            if content is not None:
                # Optionally, you could clear content or just warn
                # print(f"Warning: 'content' field is ignored for type '{source_type.value}'")
                values.content = None # Example: Clear content if path is primary
        elif source_type == KnowledgeSourceType.TEXT:
            if not content:
                raise ValueError(f"'content' is required for knowledge source type '{source_type.value}'")
            if path is not None:
                # Optionally, you could clear path or just warn
                # print(f"Warning: 'path' field is ignored for type '{source_type.value}'")
                values.path = None # Example: Clear path if content is primary
        elif source_type == KnowledgeSourceType.DIRECTORY:
            if not path:
                raise ValueError(f"'path' is required for knowledge source type '{source_type.value}'")
        return values

class AdaptiveMemoryConfig(BaseModel):
    enabled: bool = True
    db_name_prefix: str = Field("adaptive_memory_cache", description="Prefix for the SQLite DB name.")
    # Maximum number of recent interactions to retrieve for context
    retrieval_limit: int = 10 
    # Future: strategy: str = "recent" # e.g., recent, relevant (requires embeddings)
    retention_policy_days: Optional[int] = Field(None, description="How long to retain adaptive memories in days. None for indefinite.")

class DynamicContextFunction(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str = Field(..., description="Name of the Python function to call for dynamic context.")
    description: Optional[str] = None
    # For PoC, we might assume function is in a specific module or defined in a string.
    # Future: module_path: Optional[FilePath] = None 
    # Future: function_code_str: Optional[str] = None 
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Parameters to pass to the function, or expected schema.")

class GeminiConfig(BaseModel):
    model_name: GeminiModelType = GeminiModelType.GEMINI_2_5_FLASH  # Default to latest flash model
    embedding_model_name: GeminiModelType = GeminiModelType.TEXT_EMBEDDING_004  # Default embedding model
    api_key_env_var: str = Field("GEMINI_API_KEY", description="Environment variable holding the Gemini API Key.")
    # Generation parameters
    temperature: Optional[float] = Field(0.7, ge=0.0, le=1.0)
    top_p: Optional[float] = Field(None, ge=0.0, le=1.0)
    top_k: Optional[int] = Field(None, ge=0)
    max_output_tokens: Optional[int] = Field(2048)

class AgentPrompts(BaseModel):
    system_instruction: str = Field("You are a helpful AI assistant.", description="Core instruction for the agent.")
    welcome_message: Optional[str] = Field("Hello! How can I assist you today?", description="Initial message from the agent.")
    # Future: error_handler_prompt, clarification_prompt, etc.

class AMMDesign(BaseModel):
    design_id: str = Field(default_factory=lambda: f"amm_design_{uuid.uuid4()}")
    name: str = Field(..., description="User-defined name for this AMM design.")
    description: Optional[str] = None
    version: str = "0.1.0"

    knowledge_sources: List[KnowledgeSourceConfig] = Field(default_factory=list)
    adaptive_memory: AdaptiveMemoryConfig = Field(default_factory=AdaptiveMemoryConfig)
    dynamic_context_functions: List[DynamicContextFunction] = Field(default_factory=list)
    gemini_config: GeminiConfig = Field(default_factory=GeminiConfig)
    agent_prompts: AgentPrompts = Field(default_factory=AgentPrompts)

    # Metadata for GUI or builder
    ui_metadata: Dict[str, Any] = Field(default_factory=dict, description="Metadata for UI rendering or other purposes.")
    created_at: Optional[str] = None # Timestamp, can be auto-set
    updated_at: Optional[str] = None # Timestamp, can be auto-set

# Example Usage (for testing purposes, can be removed or moved to a test file later)
if __name__ == "__main__":
    example_design = AMMDesign(
        name="My First AMM",
        description="A test AMM for general queries.",
        knowledge_sources=[
            KnowledgeSourceConfig(
                name="Project README",
                type=KnowledgeSourceType.FILE,
                path="/path/to/your/project/README.md",
                description="Main readme file for the project."
            )
        ],
        dynamic_context_functions=[
            DynamicContextFunction(
                name="get_current_weather",
                description="Fetches current weather for a given location.",
                parameters={"location_api_param": "city"}
            )
        ]
    )
    print(example_design.model_dump_json(indent=2))

    # Test validation
    try:
        invalid_gemini_config = GeminiConfig(temperature=2.0) # Should fail
    except ValueError as e:
        print(f"\nSuccessfully caught validation error: {e}")

    try:
        amm_design_no_name = AMMDesign() # Should fail due to missing name
    except ValueError as e:
        print(f"\nSuccessfully caught validation error for AMMDesign: {e}")



 memory_module.py
 import datetime
from typing import Optional, Dict, Any
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, JSON
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker
from pydantic import BaseModel, Field, ConfigDict

# --- Pydantic Models for API/Logic Layer ---

class InteractionRecordPydantic(BaseModel):
    id: Optional[int] = None # Will be set by DB
    session_id: Optional[str] = Field(None, description="Optional session identifier.")
    user_id: Optional[str] = Field(None, description="Optional user identifier.")
    query: str
    response: str
    timestamp: datetime.datetime = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc))
    additional_metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional metadata.") # Renamed from metadata

    model_config = ConfigDict(from_attributes=True)


class InteractionRecordUpdatePydantic(BaseModel):
    """Pydantic model for updating an interaction record. All fields are optional."""
    session_id: Optional[str] = None
    user_id: Optional[str] = None
    query: Optional[str] = None
    response: Optional[str] = None
    # timestamp: Optional[datetime] = None # Usually, timestamp is not updated, but kept as original.
    additional_metadata: Optional[Dict[str, Any]] = None
    # No need for id or timestamp in an update model usually, or make timestamp explicitly updatable if needed.


# --- SQLAlchemy ORM Models ---

Base = declarative_base()

class InteractionRecordORM(Base):
    __tablename__ = "interaction_records"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    session_id = Column(String, index=True, nullable=True)
    user_id = Column(String, index=True, nullable=True)
    query = Column(Text, nullable=False)
    response = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc), nullable=False)
    additional_metadata = Column(JSON, nullable=True) # Renamed from 'metadata'

    def __repr__(self):
        return f"<InteractionRecordORM(id={self.id}, query='{self.query[:30]}...', response='{self.response[:30]}...')>"

# --- Database Utility Functions (can be expanded) ---

def create_db_engine_and_tables(db_url: str):
    engine = create_engine(db_url)
    Base.metadata.create_all(bind=engine)
    return engine

def get_session_local(engine):
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return SessionLocal       