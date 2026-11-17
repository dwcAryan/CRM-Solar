import logging
import os
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from leads.models import Lead

from .models import MessageLog, MessageTemplate

logger = logging.getLogger(__name__)


class WhatsAppProvider(ABC):
    @abstractmethod
    def send_template(
        self,
        phone: str,
        template_name: str,
        params: Dict[str, Any],
        lead: Optional[Lead] = None,
    ) -> bool:
        pass

    @abstractmethod
    def send_text(
        self,
        phone: str,
        text: str,
        lead: Optional[Lead] = None,
    ) -> bool:
        pass


class ConsoleWhatsAppProvider(WhatsAppProvider):
    def send_template(
        self,
        phone: str,
        template_name: str,
        params: Dict[str, Any],
        lead: Optional[Lead] = None,
    ) -> bool:
        # Check do_not_contact
        if lead and lead.do_not_contact:
            logger.warning(f"Blocked WhatsApp message to {phone}: Lead has do_not_contact=True")
            MessageLog.objects.create(
                phone=phone,
                lead=lead,
                template_name=template_name,
                params=params,
                message_text=f"[BLOCKED] Lead #{lead.id} requested Do Not Contact",
                status=MessageLog.Status.BLOCKED,
                error_message="Lead has do_not_contact=True",
            )
            return False

        template = MessageTemplate.objects.filter(name=template_name, is_active=True).first()
        if template:
            message_text = template.render(params)
        else:
            formatted_params = ", ".join(f"{k}={v}" for k, v in params.items())
            message_text = f"[{template_name}] {formatted_params}"

        logger.info(f"[ConsoleWhatsAppProvider] Sent Template '{template_name}' to {phone}: {message_text}")
        print(f"\n--- [WHATSAPP OUTBOUND ({template_name})] ---")
        print(f"To: {phone}")
        print(f"Message: {message_text}")
        print("-------------------------------------------\n")

        MessageLog.objects.create(
            phone=phone,
            lead=lead,
            template_name=template_name,
            params=params,
            message_text=message_text,
            status=MessageLog.Status.SENT,
        )
        return True

    def send_text(
        self,
        phone: str,
        text: str,
        lead: Optional[Lead] = None,
    ) -> bool:
        if lead and lead.do_not_contact:
            logger.warning(f"Blocked WhatsApp text to {phone}: Lead has do_not_contact=True")
            MessageLog.objects.create(
                phone=phone,
                lead=lead,
                message_text=f"[BLOCKED] {text}",
                status=MessageLog.Status.BLOCKED,
                error_message="Lead has do_not_contact=True",
            )
            return False

        logger.info(f"[ConsoleWhatsAppProvider] Sent Text to {phone}: {text}")
        print("\n--- [WHATSAPP OUTBOUND (TEXT)] ---")
        print(f"To: {phone}")
        print(f"Message: {text}")
        print("----------------------------------\n")

        MessageLog.objects.create(
            phone=phone,
            lead=lead,
            message_text=text,
            status=MessageLog.Status.SENT,
        )
        return True


def get_whatsapp_provider() -> WhatsAppProvider:
    provider_name = os.getenv('WHATSAPP_PROVIDER', 'console').strip().lower()
    if provider_name == 'console':
        return ConsoleWhatsAppProvider()
    # Default fallback
    return ConsoleWhatsAppProvider()
