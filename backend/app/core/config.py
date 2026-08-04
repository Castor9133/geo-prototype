"""
全局配置 — 从环境变量 / .env 文件加载
"""
from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings
from sqlalchemy.engine import URL
from typing import List
import hashlib
import base64
from urllib.parse import urlparse


class Settings(BaseSettings):
    # ----- 基础 -----
    APP_NAME: str = "GEOrank"
    DEBUG: bool = False
    SECRET_KEY: str = "change-me-in-production"
    SETTINGS_ENCRYPTION_KEY: str = ""
    PUBLIC_BASE_URL: str = "http://localhost:3009"
    TRUSTED_HOSTS: List[str] = [
        "localhost",
        "127.0.0.1",
        "testserver",
        "api",
        "app.georank.com",
        "*.georank.com",
    ]

    # ----- CORS -----
    CORS_ORIGINS: List[str] = ["http://localhost:8899", "http://localhost:80", "http://localhost", "http://127.0.0.1"]

    # ----- PostgreSQL -----
    # 裸跑本机时设 POSTGRES_HOST=127.0.0.1；Compose 内默认 hostname=postgres
    POSTGRES_HOST: str = "postgres"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "georank"
    POSTGRES_USER: str = "georank"
    POSTGRES_PASSWORD: str = "change-me-postgres-password"
    TEST_DATABASE_URL: str = ""

    # ----- 内容后端模式（M1：统一 Python / F2 双轨）-----
    # native-python：知识库/任务/分发走 Rank 原生；legacy-flow：Suite 仍 handoff 到 GEOFlow
    CONTENT_BACKEND_MODE: str = "native-python"

    @property
    def DATABASE_URL(self) -> str:
        return URL.create(
            "postgresql+asyncpg",
            username=self.POSTGRES_USER,
            password=self.POSTGRES_PASSWORD,
            host=self.POSTGRES_HOST,
            port=self.POSTGRES_PORT,
            database=self.POSTGRES_DB,
        ).render_as_string(hide_password=False)

    # ----- Redis -----
    REDIS_HOST: str = "redis"
    REDIS_PORT: int = 6379

    @property
    def REDIS_URL(self) -> str:
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/0"

    @property
    def CELERY_BROKER_URL(self) -> str:
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/1"

    # ----- Qdrant 向量数据库 -----
    QDRANT_HOST: str = "qdrant"
    QDRANT_PORT: int = 6333
    QDRANT_COLLECTION: str = "companies"

    # ----- Neo4j 知识图谱 -----
    NEO4J_URI: str = "bolt://neo4j:7687"
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str = "change-me-neo4j-password"

    # ----- MinIO 对象存储 -----
    MINIO_ENDPOINT: str = "minio:9000"
    MINIO_ACCESS_KEY: str = Field(
        default="change-me-minio-access-key",
        validation_alias=AliasChoices("MINIO_ACCESS_KEY", "MINIO_USER"),
    )
    MINIO_SECRET_KEY: str = Field(
        default="change-me-minio-secret-key",
        validation_alias=AliasChoices("MINIO_SECRET_KEY", "MINIO_PASSWORD"),
    )
    MINIO_BUCKET: str = "georank-assets"
    # 裸跑无 MinIO 时落盘目录（诊断 HTML 等）
    LOCAL_OBJECT_STORE_DIR: str = r"C:\georank-runtime\object-store"

    # ----- AI / LLM -----
    # 主 LLM 服务（兼容 OpenAI API 格式的服务均可）
    LLM_API_KEY: str = ""
    LLM_BASE_URL: str = "https://api.deepseek.com/v1"
    LLM_MODEL: str = "deepseek-v4-flash"
    LLM_FALLBACK_MODEL: str = ""
    ALLOW_PRIVATE_LLM_PROVIDER_URLS: bool = False

    CODEX_API_KEY: str = ""
    CODEX_BASE_URL: str = ""
    CODEX_MODEL: str = "gpt-5.3-codex-spark"

    # 向后兼容旧字段（ai_client 内部使用 LLM_* 前缀）
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "deepseek-v4-flash"

    # Embedding：默认 Qwen3-Embedding 系列（DashScope OpenAI 兼容 text-embedding-v4）
    # 勿与 DeepSeek 等仅 Chat 的 Key 混用；未配置时内容引擎降级本地哈希向量。
    EMBEDDING_API_KEY: str = ""
    DASHSCOPE_API_KEY: str = ""  # 可与 EMBEDDING_API_KEY 二选一
    EMBEDDING_BASE_URL: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    EMBEDDING_MODEL: str = "text-embedding-v4"
    EMBEDDING_DIMENSIONS: int = 1024

    # 本地 / Suite 演示：允许未登录调用诊断、拓词、问答等 AI 接口
    GEORANK_ALLOW_ANONYMOUS_AI: bool = False

    # ----- GEO Suite / GEOFlow 集成 -----
    GEOFLOW_ENABLED: bool = False
    GEOFLOW_BASE_URL: str = "http://host.docker.internal:18080"
    GEOFLOW_PUBLIC_BASE_URL: str = "http://localhost:18080"
    GEOFLOW_API_TOKEN: str = ""
    # Phase1/2：SSO 换票与发布回写共用 HMAC 密钥（两边 .env 保持一致）
    GEOSUITE_SSO_SECRET: str = ""
    GEOSUITE_CALLBACK_SECRET: str = ""
    GEOSUITE_PUBLIC_URL: str = "http://localhost:3009"

    @property
    def effective_llm_key(self) -> str:
        """优先使用 LLM_API_KEY，否则回退到 OPENAI_API_KEY"""
        return self.LLM_API_KEY or self.OPENAI_API_KEY

    @property
    def effective_embedding_key(self) -> str:
        """Embedding 仅用专用 Key（或 DashScope），绝不回退到 DeepSeek/LLM Key。"""
        return self.EMBEDDING_API_KEY or self.DASHSCOPE_API_KEY

    # ----- JWT -----
    JWT_SECRET: str = "change-me-jwt-secret"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60  # 1小时；生产环境建议 15-30 分钟
    JWT_PERSIST_DAYS: int = 365

    @property
    def settings_encryption_key_bytes(self) -> bytes:
        """
        生成 32 字节设置加密密钥。
        未单独配置时回退到 SECRET_KEY，保证本地开发可用。
        """
        material = (self.SETTINGS_ENCRYPTION_KEY or self.SECRET_KEY).encode("utf-8")
        return hashlib.sha256(material).digest()

    @property
    def settings_encryption_key_b64(self) -> str:
        return base64.urlsafe_b64encode(self.settings_encryption_key_bytes).decode("ascii")

    def validate_production_security(self) -> None:
        """Fail closed when production is started with development secrets/origin."""
        if self.DEBUG:
            return

        weak_values = {"", "change-me-in-production", "change-me-jwt-secret"}
        problems: list[str] = []
        if self.SECRET_KEY in weak_values or len(self.SECRET_KEY) < 32:
            problems.append("SECRET_KEY 必须使用至少 32 字符的随机值")
        if self.JWT_SECRET in weak_values or len(self.JWT_SECRET) < 32:
            problems.append("JWT_SECRET 必须使用至少 32 字符的独立随机值")
        if (
            not self.SETTINGS_ENCRYPTION_KEY
            or self.SETTINGS_ENCRYPTION_KEY.startswith("change-me")
            or len(self.SETTINGS_ENCRYPTION_KEY) < 32
            or self.SETTINGS_ENCRYPTION_KEY in {self.SECRET_KEY, self.JWT_SECRET}
        ):
            problems.append("SETTINGS_ENCRYPTION_KEY 必须使用至少 32 字符的独立随机值")

        public_origin = urlparse(self.PUBLIC_BASE_URL)
        if public_origin.scheme != "https" or not public_origin.hostname:
            problems.append("PUBLIC_BASE_URL 在生产环境必须是完整的 HTTPS 地址")
        if problems:
            raise RuntimeError("生产环境安全配置无效：" + "；".join(problems))

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
