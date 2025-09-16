from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
import os


class Settings(BaseSettings):
    """
    Settings class to store the configuration settings for the application
    """
    PROJECT_NAME: str = Field("Fouray 4ay Agent", description="Name of the project")
    VERSION: str = Field("1.0.0", description="Version of the project")
    API_V1_STR: str = Field("/api/v1", description="API version")
    DESCRIPTION: str = Field("4ay Agent", description="4ay Agent")
    OPENAI_API_KEY: str = Field(..., description="OpenAI API Key")
    OPENAI_TEMP: float = Field(0.3, ge=0, le=1, description="OpenAI API Temperature")
    TOP_P: float = Field(0.9, ge=0, le=1, description="OpenAI API Top P")
    DB_STR: str = Field(..., description="Database connection string")
    SYNC_DB_STR: str = Field(..., description="Sync Database connection string")
    SCHEDULER_INTERVAL_HOURS: int = Field(48, description="Scheduler interval in hours")
    INSTRUCTIONS_AND_COMMANDS_FOLDER_NAME: str = Field(..., description="Instructions and commands folder name")
    INSTRUCTIONS_FILE_NAME: str = Field(..., description="Instructions file name")
    COMMANDS_FILE_NAME: str = Field(..., description="Commands file name")
    OPENAI_MODEL: str = Field(..., description="OpenAI model")
    OPENAI_LOWER_MODEL: str = Field(..., description="OpenAI lower model")
    NUM_HISTORY_RESPONSES: int = Field(5, description="Number of history responses")
    VECTOR_SEARCH_LIMIT: int = Field(40, description="Vector search limit")
    REDIS_URL: str = Field(..., description="Redis URL")
    CACHE_EXPIRY_SECONDS: int = Field(2629800, description="Cache expiry in seconds")
    PRODUCT_SECTIONS: str = Field(..., description="Product sections")
    ALLOWED_ORIGINS: str = Field(..., description="Allowed hosts")
    AGENT_CONFIG_FILE_NAME: str = Field(..., description="Agent config file name")
    AGENT_CONTEXT_FILE_NAME: str = Field(..., description="Agent context file name")
    AGENT_ADDITIONAL_CONTEXT_FILE_NAME: str = Field(..., description="Agent additional context file name")
    LEGAL_GV_EXPECTED_OUTPUT: str = Field("""
        {
          "function_analysis": [
            {
              "Function Name": "Mapped or new function name",
              "Function Description": "Description of the function.",
              "Parent company name will come here": "Yes/No",
              "Subsidiary company name will come here": "Yes/No",
              "Remarks": "Why Yes/No? Reference of document, document line or context.",
              "New function": true/false
            }
          ]
        }
        """, description="Prompt expected output")
    EMAIL_EXPECTED_OUTPUT: str = Field(..., description="Email Prompt expected output")
    EMAIL_FOLDERS: str = Field(..., description="Email folders")
    COHERE_API_KEY: str = Field(..., description="Cohere API Key")

    LEGAL_GV_USER_PROMPT_EXPECTED_OUTPUT: str = Field("""
        {
            "response": "generated response"
        }
        """, description="Expected output")
    BLOG_SEMANTIC_KEYWORD_CLUSTER_EXPECTED_OUTPUT: str = Field(...,
                                                               description="Blog semantic keyword cluster expected output")
    BLOG_TOPIC_GENERATION_EXPECTED_OUTPUT: str = Field(..., description="Blog topic generation expected output")
    BLOG_CONTENT_GENERATION_EXPECTED_OUTPUT: str = Field(..., description="Blog content generation expected output")

    ENV: str = os.getenv('ENV_MODE', 'dev')
    model_config = SettingsConfigDict(env_file=f".env.{ENV}", env_file_encoding="utf-8", extra="ignore")

    # class Config:
    #     env_file = ".env"
    #     extra = "ignore"


settings = Settings()
