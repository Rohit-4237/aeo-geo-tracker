from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text, ForeignKey, JSON
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from database import Base


class BrandConfig(Base):
    __tablename__ = "brand_configs"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    url = Column(String, nullable=False)
    is_primary = Column(Boolean, default=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class Prompt(Base):
    __tablename__ = "prompts"
    id = Column(Integer, primary_key=True)
    text = Column(Text, nullable=False)
    category = Column(String, nullable=True)
    order_index = Column(Integer, default=0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class TrackingRun(Base):
    __tablename__ = "tracking_runs"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    platforms = Column(JSON, nullable=False)   # list of platform keys
    status = Column(String, default="pending")  # pending | running | completed | failed
    total_prompts = Column(Integer, default=0)
    completed_prompts = Column(Integer, default=0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    completed_at = Column(DateTime, nullable=True)
    results = relationship("PromptResult", back_populates="run", cascade="all, delete-orphan")


class PromptResult(Base):
    __tablename__ = "prompt_results"
    id = Column(Integer, primary_key=True)
    run_id = Column(Integer, ForeignKey("tracking_runs.id"), nullable=False)
    prompt_id = Column(Integer, ForeignKey("prompts.id"), nullable=False)
    platform = Column(String, nullable=False)  # chatgpt | gemini | perplexity | google_aio | google_aim
    raw_response = Column(Text, nullable=True)
    available = Column(Boolean, default=True)   # False when platform blocked/unavailable
    brand_mentions = Column(JSON, default=dict)  # {brand_name: count}
    cited_urls = Column(JSON, default=dict)      # {brand_name: [urls]}
    sentiment = Column(String, nullable=True)    # positive | negative | neutral
    sentiment_score = Column(Float, nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    run = relationship("TrackingRun", back_populates="results")


class AppSettings(Base):
    __tablename__ = "app_settings"
    id = Column(Integer, primary_key=True, default=1)
    api_mode = Column(String, default="byok")   # byok | platform
    openai_key = Column(String, nullable=True)
    gemini_key = Column(String, nullable=True)
    perplexity_key = Column(String, nullable=True)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
