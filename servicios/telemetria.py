"""OpenTelemetry opcional (extra `prod`): solo si OTEL_EXPORTER_OTLP_ENDPOINT está definido.

enable_sensitive_data=False: las trazas llevan tiempos, modelo, tokens y decisiones; nunca el contenido
de los mensajes (PII) ni los prompts.
"""
import os


def configurar(servicio: str) -> None:
    if not os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT"):
        return
    from agent_framework.observability import configure_otel_providers

    configure_otel_providers(service_name=servicio, enable_sensitive_data=False)
