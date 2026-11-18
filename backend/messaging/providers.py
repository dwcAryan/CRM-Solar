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
        # Check do_not_contact and opt_out_whatsapp
        if lead and (lead.do_not_contact or lead.opt_out_whatsapp):
            reason = "Lead has do_not_contact=True" if lead.do_not_contact else "Lead has opted out of WhatsApp messages"
            logger.warning(f"Blocked WhatsApp message to {phone}: {reason}")
            MessageLog.objects.create(
                channel=MessageLog.Channel.WHATSAPP,
                phone=phone,
                lead=lead,
                template_name=template_name,
                params=params,
                message_text=f"[BLOCKED] {reason}",
                status=MessageLog.Status.BLOCKED,
                error_message=reason,
            )
            return False

        # Find region-specific template or global fallback
        template = None
        if lead and lead.region:
            template = MessageTemplate.objects.filter(
                region=lead.region,
                channel=MessageTemplate.Channel.WHATSAPP,
                name=template_name,
                is_active=True,
            ).first()
            if 'opt_out_line' not in params:
                params['opt_out_line'] = lead.region.opt_out_text

        if not template:
            template = MessageTemplate.objects.filter(
                name=template_name,
                channel=MessageTemplate.Channel.WHATSAPP,
                is_active=True,
            ).first()

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
            channel=MessageLog.Channel.WHATSAPP,
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
        if lead and (lead.do_not_contact or lead.opt_out_whatsapp):
            reason = "Lead has do_not_contact=True" if lead.do_not_contact else "Lead has opted out of WhatsApp messages"
            logger.warning(f"Blocked WhatsApp text to {phone}: {reason}")
            MessageLog.objects.create(
                channel=MessageLog.Channel.WHATSAPP,
                phone=phone,
                lead=lead,
                message_text=f"[BLOCKED] {text}",
                status=MessageLog.Status.BLOCKED,
                error_message=reason,
            )
            return False

        logger.info(f"[ConsoleWhatsAppProvider] Sent Text to {phone}: {text}")
        print("\n--- [WHATSAPP OUTBOUND (TEXT)] ---")
        print(f"To: {phone}")
        print(f"Message: {text}")
        print("----------------------------------\n")

        MessageLog.objects.create(
            channel=MessageLog.Channel.WHATSAPP,
            phone=phone,
            lead=lead,
            message_text=text,
            status=MessageLog.Status.SENT,
        )
        return True


class SMSProvider(ABC):
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
    def send_sms(
        self,
        phone: str,
        text: str,
        lead: Optional[Lead] = None,
    ) -> bool:
        pass


class ConsoleSMSProvider(SMSProvider):
    def send_template(
        self,
        phone: str,
        template_name: str,
        params: Dict[str, Any],
        lead: Optional[Lead] = None,
    ) -> bool:
        # Check do_not_contact and opt_out_sms
        if lead and (lead.do_not_contact or lead.opt_out_sms):
            reason = "Lead has do_not_contact=True" if lead.do_not_contact else "Lead has opted out of SMS messages"
            logger.warning(f"Blocked SMS template to {phone}: {reason}")
            MessageLog.objects.create(
                channel=MessageLog.Channel.SMS,
                phone=phone,
                lead=lead,
                template_name=template_name,
                params=params,
                message_text=f"[BLOCKED] {reason}",
                status=MessageLog.Status.BLOCKED,
                error_message=reason,
            )
            return False

        template = None
        if lead and lead.region:
            template = MessageTemplate.objects.filter(
                region=lead.region,
                channel=MessageTemplate.Channel.SMS,
                name=template_name,
                is_active=True,
            ).first()
            if 'opt_out_line' not in params:
                params['opt_out_line'] = lead.region.opt_out_text

        if not template:
            template = MessageTemplate.objects.filter(
                name=template_name,
                channel=MessageTemplate.Channel.SMS,
                is_active=True,
            ).first()

        if template:
            message_text = template.render(params)
        else:
            formatted_params = ", ".join(f"{k}={v}" for k, v in params.items())
            opt = lead.region.opt_out_text if lead and lead.region else "Reply STOP to opt out"
            message_text = f"[{template_name}] {formatted_params}. {opt}"

        logger.info(f"[ConsoleSMSProvider] Sent SMS Template '{template_name}' to {phone}: {message_text}")
        print(f"\n--- [SMS OUTBOUND ({template_name})] ---")
        print(f"To: {phone}")
        print(f"Message: {message_text}")
        print("---------------------------------------\n")

        MessageLog.objects.create(
            channel=MessageLog.Channel.SMS,
            phone=phone,
            lead=lead,
            template_name=template_name,
            params=params,
            message_text=message_text,
            status=MessageLog.Status.SENT,
        )
        return True

    def send_sms(
        self,
        phone: str,
        text: str,
        lead: Optional[Lead] = None,
    ) -> bool:
        if lead and (lead.do_not_contact or lead.opt_out_sms):
            reason = "Lead has do_not_contact=True" if lead.do_not_contact else "Lead has opted out of SMS messages"
            logger.warning(f"Blocked SMS to {phone}: {reason}")
            MessageLog.objects.create(
                channel=MessageLog.Channel.SMS,
                phone=phone,
                lead=lead,
                message_text=f"[BLOCKED] {text}",
                status=MessageLog.Status.BLOCKED,
                error_message=reason,
            )
            return False

        opt_line = f" {lead.region.opt_out_text}" if lead and lead.region and lead.region.opt_out_text not in text else ""
        final_text = f"{text}{opt_line}"

        logger.info(f"[ConsoleSMSProvider] Sent SMS to {phone}: {final_text}")
        print("\n--- [SMS OUTBOUND (TEXT)] ---")
        print(f"To: {phone}")
        print(f"Message: {final_text}")
        print("-----------------------------\n")

        MessageLog.objects.create(
            channel=MessageLog.Channel.SMS,
            phone=phone,
            lead=lead,
            message_text=final_text,
            status=MessageLog.Status.SENT,
        )
        return True


def get_whatsapp_provider() -> WhatsAppProvider:
    provider_name = os.getenv('WHATSAPP_PROVIDER', 'console').strip().lower()
    if provider_name == 'console':
        return ConsoleWhatsAppProvider()
    return ConsoleWhatsAppProvider()


def get_sms_provider() -> SMSProvider:
    provider_name = os.getenv('SMS_PROVIDER', 'console').strip().lower()
    if provider_name == 'console':
        return ConsoleSMSProvider()
    return ConsoleSMSProvider()

