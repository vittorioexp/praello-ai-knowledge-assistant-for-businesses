"""OpenTelemetry instrumentation."""

from enterprise_ai.infrastructure.config.settings import Settings
from enterprise_ai.infrastructure.logging.setup import get_logger

logger = get_logger(__name__)


def setup_telemetry(settings: Settings) -> None:
    """Configure OpenTelemetry if enabled."""
    if not settings.otel_enabled:
        return

    try:
        from opentelemetry import trace
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter

        resource = Resource.create({"service.name": settings.otel_service_name})
        provider = TracerProvider(resource=resource)
        provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))
        trace.set_tracer_provider(provider)

        # Store instrumentor for later use in create_app
        setup_telemetry._instrumentor = FastAPIInstrumentor  # type: ignore[attr-defined]
        logger.info("opentelemetry_configured", service=settings.otel_service_name)
    except ImportError:
        logger.warning("opentelemetry_not_available")


def instrument_fastapi(app) -> None:
    """Instrument FastAPI app with OpenTelemetry."""
    instrumentor = getattr(setup_telemetry, "_instrumentor", None)
    if instrumentor:
        instrumentor.instrument_app(app)
