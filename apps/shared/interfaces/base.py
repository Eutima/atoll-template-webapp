class BaseInterface:
    """Marker base class for external system integrations. Concrete
    interfaces (Helix today, and future third-party integrations) live in
    their own package under `apps/shared/interfaces/` and are the only code
    allowed to talk to that external system directly."""
