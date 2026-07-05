import os
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
	# Service URLs (for gateway to call microservices)
	TEXT_SERVICE_URL: str = os.getenv("TEXT_SERVICE_URL", "http://localhost:8001")
	URL_SERVICE_URL: str = os.getenv("URL_SERVICE_URL", "http://localhost:8002")
	IMAGE_SERVICE_URL: str = os.getenv("IMAGE_SERVICE_URL", "http://localhost:8003")
	GRAPH_SERVICE_URL: str = os.getenv("GRAPH_SERVICE_URL", "http://localhost:8004")

	# Threat intel API keys (placeholders)
	OTX_API_KEY: str | None = os.getenv("OTX_API_KEY")
	PHISHTANK_API_KEY: str | None = os.getenv("PHISHTANK_API_KEY")
	MISP_API_KEY: str | None = os.getenv("MISP_API_KEY")
	MISP_URL: str | None = os.getenv("MISP_URL")

	# Service model configuration (evaluation-only HF model)
	SERVICE_MODEL_ID: str = os.getenv(
		"SERVICE_MODEL_ID",
		"cybersectony/phishing-email-detection-distilbert_v2.4.1",
	)
	SERVICE_FALLBACK_MODEL_ID: str = os.getenv(
		"SERVICE_FALLBACK_MODEL_ID",
		"/models/text/model",
	)
	SERVICE_USE_EXTERNAL_THRESHOLD: bool = (os.getenv("SERVICE_USE_EXTERNAL_THRESHOLD", "true").strip().lower() in {"1","true","yes","y"})

	# Pydantic v2 settings config: ignore extra env vars and load from .env
	model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
