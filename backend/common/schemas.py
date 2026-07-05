from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any


class TextAnalyzeRequest(BaseModel):
	text: str = Field(..., description="Email or SMS text to analyze")


class Highlight(BaseModel):
	span: str
	score: float
	start: int
	end: int


class TextAnalyzeResponse(BaseModel):
	is_phishing: bool
	confidence: float
	reasons: List[str]
	highlights: List[Highlight] = []
	model: Optional[str] = None


class UrlAnalyzeRequest(BaseModel):
	url: str


class Feature(BaseModel):
	name: str
	value: Any
	weight: Optional[float] = None


class UrlAnalyzeResponse(BaseModel):
	is_phishing: bool
	confidence: float
	features: List[Feature]
	reasons: List[str]


class ImageAnalyzeRequest(BaseModel):
	image_base64: Optional[str] = None
	image_url: Optional[str] = None


class ImageAnalyzeResponse(BaseModel):
	is_phishing: bool
	confidence: float
	reasons: List[str]
	metrics: Dict[str, Any]


class GraphCheckRequest(BaseModel):
	domain: str


class Neighbor(BaseModel):
	domain: str
	risk: float


class GraphCheckResponse(BaseModel):
	risk_score: float
	neighbors: List[Neighbor]
	reasons: List[str]
