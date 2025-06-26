"""Provides configuration settings for the application using Pydantic settings.

Attributes:
    app_settings: A configuration class that inherits from BaseSettings and
        includes various settings for the application, such as thread count,
        database connections, secret keys, and environment variables.

"""

from dotenv import load_dotenv
from pydantic_settings import BaseSettings

# Load environment variables from a .env file
load_dotenv()


class AppSettings(BaseSettings):
    """Represents a configuration object for the application."""

    THREAD_WORKS: int = 60
    RESULT_PATH: str
    ZPLATIPLD_DB: str
    ZPLATIPLD_URL_DB: str
    PRIVATE_FILE_PATH: str
    ROOT_RESULTS: str
    ROOT_TMP_ANALYSIS: str

    SECRET_KEY: str
    ENVIRONMENT: str

    CIRRUS_API_URL: str
    CIRRUS_API_VERSION: str
    CIRRUS_ENDPOINT_TOKEN: str
    CIRRUS_ENDPOINT_FIREWALL: str
    CIRRUS_PROJECT_ID: str
    CIRRUS_CLUSTER_ID: str
    CIRRUS_USER: str
    CIRRUS_PASSWORD: str

    class Config:
        """Represents a configuration object for the application.

        Attributes:
            env_file (str): The name of the environment file to use.
            Default is ".env".

        """

        env_file = "../.env"
        env_file_encoding = "utf-8"
        case_sensitive = True


app_settings = AppSettings()
