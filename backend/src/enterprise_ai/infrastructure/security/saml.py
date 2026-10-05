"""SAML 2.0 service-provider integration."""

from enterprise_ai.infrastructure.config.settings import Settings


def _settings(settings: Settings) -> dict:
    return {
        "strict": True,
        "debug": settings.app_debug,
        "sp": {
            "entityId": settings.saml_sp_entity_id,
            "assertionConsumerService": {"url": settings.saml_acs_url, "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST"},
        },
        "idp": {
            "entityId": settings.saml_idp_entity_id,
            "singleSignOnService": {"url": settings.saml_idp_sso_url},
            "x509cert": settings.saml_idp_x509_cert,
        },
    }


def create_auth(request_data: dict, settings: Settings):
    if not settings.saml_enabled or not settings.saml_idp_entity_id or not settings.saml_idp_sso_url or not settings.saml_idp_x509_cert:
        raise ValueError("SAML is not configured")
    from onelogin.saml2.auth import OneLogin_Saml2_Auth

    return OneLogin_Saml2_Auth(request_data, custom_base_path="/tmp", old_settings=_settings(settings))