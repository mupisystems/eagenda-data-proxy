import os
import re
from functools import lru_cache
from pathlib import Path

import yaml
from pydantic import Field
from pydantic_settings import BaseSettings


def _substitute_env_vars(raw: str) -> str:
    """Replace ${VAR_NAME} patterns with environment variable values."""
    def replacer(match):
        var_name = match.group(1)
        return os.getenv(var_name, "")
    return re.sub(r"\$\{(\w+)}", replacer, raw)


def _load_yaml_config(path: str = "data_proxy_config.yml") -> dict:
    """Load YAML config file with environment variable substitution."""
    config_path = Path(path)
    if not config_path.exists():
        return {}
    raw = config_path.read_text(encoding="utf-8")
    resolved = _substitute_env_vars(raw)
    return yaml.safe_load(resolved) or {}


class Settings(BaseSettings):
    # eagendas cloud
    eagendas_base_url: str = "https://app.eagendas.com.br/api/v3"
    eagendas_api_token: str = ""
    eagendas_timeout: int = 30
    eagendas_retry_attempts: int = 3
    eagendas_retry_backoff: float = 2.0

    # Database
    database_url: str = "postgresql+asyncpg://proxy:proxy@localhost:5432/eagendas_pii"
    database_url_sync: str = "postgresql+psycopg2://proxy:proxy@localhost:5432/eagendas_pii"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # PII
    pii_pseudonym_prefix: str = "Cidadao"
    pii_redacted_placeholder: str = "[REDACTED]"
    pii_questionnaire_pii_types: list[str] = Field(default_factory=lambda: ["text", "short-text", "paragraph"])

    # Notifications
    email_enabled: bool = True
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from_address: str = ""
    smtp_from_name: str = "Sistema de Agendamento"

    # Webhook relay
    webhook_relay_target_url: str = ""
    webhook_relay_auth_header: str = ""
    webhook_relay_retry_max: int = 5
    webhook_relay_retry_delay: int = 60

    # Admin
    admin_enabled: bool = True
    admin_secret_key: str = "change-me"

    # Audit
    audit_retention_days: int = 365

    # Debug
    debug: bool = False
    log_level: str = "INFO"

    @classmethod
    def from_yaml(cls, path: str = "data_proxy_config.yml") -> "Settings":
        """Create Settings by merging YAML config with env vars."""
        cfg = _load_yaml_config(path)
        flat = {}

        # Flatten nested YAML into Settings field names
        eagendas = cfg.get("eagendas", {})
        flat["eagendas_base_url"] = eagendas.get("base_url", "")
        flat["eagendas_api_token"] = eagendas.get("api_token", "")
        flat["eagendas_timeout"] = eagendas.get("timeout", 30)
        flat["eagendas_retry_attempts"] = eagendas.get("retry_attempts", 3)
        flat["eagendas_retry_backoff"] = eagendas.get("retry_backoff", 2.0)

        db = cfg.get("database", {})
        if db.get("url"):
            flat["database_url"] = db["url"]
        if db.get("url_sync"):
            flat["database_url_sync"] = db["url_sync"]

        flat["redis_url"] = cfg.get("redis", {}).get("url", "")

        pii = cfg.get("pii", {})
        flat["pii_pseudonym_prefix"] = pii.get("pseudonym_prefix", "Cidadao")
        questionnaire = pii.get("questionnaire", {})
        if questionnaire.get("pii_types"):
            flat["pii_questionnaire_pii_types"] = questionnaire["pii_types"]
        if questionnaire.get("redacted_placeholder"):
            flat["pii_redacted_placeholder"] = questionnaire["redacted_placeholder"]

        notif = cfg.get("notifications", {})
        email = notif.get("email", {})
        flat["email_enabled"] = email.get("enabled", True)
        flat["smtp_host"] = email.get("smtp_host", "")
        flat["smtp_port"] = email.get("smtp_port", 587)
        flat["smtp_user"] = email.get("smtp_user", "")
        flat["smtp_password"] = email.get("smtp_password", "")
        flat["smtp_from_address"] = email.get("from_address", "")
        flat["smtp_from_name"] = email.get("from_name", "Sistema de Agendamento")

        wh = cfg.get("webhook_relay", {})
        flat["webhook_relay_target_url"] = wh.get("target_url", "")
        flat["webhook_relay_auth_header"] = wh.get("auth_header", "")
        flat["webhook_relay_retry_max"] = wh.get("retry_max", 5)
        flat["webhook_relay_retry_delay"] = wh.get("retry_delay", 60)

        admin = cfg.get("admin", {})
        flat["admin_enabled"] = admin.get("enabled", True)
        flat["admin_secret_key"] = admin.get("secret_key", "change-me")

        audit = cfg.get("audit", {})
        flat["audit_retention_days"] = audit.get("retention_days", 365)

        proxy = cfg.get("proxy", {})
        flat["debug"] = proxy.get("debug", False)
        flat["log_level"] = proxy.get("log_level", "INFO")

        # Remove empty strings so env vars can take precedence
        flat = {k: v for k, v in flat.items() if v not in ("", None)}

        return cls(**flat)


@lru_cache
def get_settings() -> Settings:
    return Settings.from_yaml()
