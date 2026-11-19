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

        # Target language and fallback resolution
        target_lang = getattr(lead, 'preferred_language', 'en') or 'en'
        reg_lang = getattr(lead.region, 'default_language', 'en') if (lead and lead.region) else 'en'

        # Fallback chain: lead language -> region default -> 'en'
        lang_candidates = [target_lang]
        if reg_lang not in lang_candidates:
            lang_candidates.append(reg_lang)
        if 'en' not in lang_candidates:
            lang_candidates.append('en')

        template = None
        for lang in lang_candidates:
            if lead and lead.region:
                template = MessageTemplate.objects.filter(
                    region=lead.region,
                    channel=MessageTemplate.Channel.WHATSAPP,
                    name=template_name,
                    language=lang,
                    is_active=True,
                ).first()
            if not template:
                template = MessageTemplate.objects.filter(
                    region__isnull=True,
                    channel=MessageTemplate.Channel.WHATSAPP,
                    name=template_name,
                    language=lang,
                    is_active=True,
                ).first()
            if template:
                break

        if not template:
            template = MessageTemplate.objects.filter(
                channel=MessageTemplate.Channel.WHATSAPP,
                name=template_name,
                is_active=True,
            ).first()

        # Approval status check: block if pending
        if template and template.approval_status == MessageTemplate.ApprovalStatus.PENDING:
            reason = f"Template '{template_name}' ({template.language}) is pending regulatory approval and cannot be sent."
            logger.warning(f"Blocked WhatsApp message to {phone}: {reason}")
            MessageLog.objects.create(
                channel=MessageLog.Channel.WHATSAPP,
                phone=phone,
                lead=lead,
                template_name=template_name,
                language=template.language,
                params=params,
                message_text=f"[BLOCKED] {reason}",
                status=MessageLog.Status.BLOCKED,
                error_message=reason,
            )
            return False

        used_lang = template.language if template else target_lang

        if lead and lead.region and 'opt_out_line' not in params:
            reg_trans = getattr(lead.region, 'translations', {}) or {}
            lang_trans = reg_trans.get(used_lang, {})
            params['opt_out_line'] = lang_trans.get('opt_out_text') or lead.region.opt_out_text

        if template:
            message_text = template.render(params)
        else:
            formatted_params = ", ".join(f"{k}={v}" for k, v in params.items())
            message_text = f"[{template_name}] {formatted_params}"

        logger.info(f"[ConsoleWhatsAppProvider] Sent Template '{template_name}' ({used_lang}) to {phone}: {message_text}")
        print(f"\n--- [WHATSAPP OUTBOUND ({template_name} - {used_lang})] ---")
        print(f"To: {phone}")
        print(f"Message: {message_text}")
        print("-------------------------------------------\n")

        MessageLog.objects.create(
            channel=MessageLog.Channel.WHATSAPP,
            phone=phone,
            lead=lead,
            template_name=template_name,
            language=used_lang,
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


def resolve_template_for_recipient(
    template_name: str,
    lead: Optional[Lead] = None,
    channel: str = 'whatsapp',
) -> Optional[MessageTemplate]:
    """
    Resolves the appropriate template based on the fallback chain:
    lead.preferred_language -> region.default_language -> 'en'.
    Blocks templates pending regulatory approval.
    """
    target_lang = getattr(lead, 'preferred_language', 'en') or 'en'
    reg_lang = getattr(lead.region, 'default_language', 'en') if (lead and lead.region) else 'en'

    lang_candidates = [target_lang]
    if reg_lang not in lang_candidates:
        lang_candidates.append(reg_lang)
    if 'en' not in lang_candidates:
        lang_candidates.append('en')

    template = None
    for lang in lang_candidates:
        if lead and lead.region:
            template = MessageTemplate.objects.filter(
                region=lead.region,
                channel=channel,
                name=template_name,
                language=lang,
                is_active=True,
            ).first()
        if not template:
            template = MessageTemplate.objects.filter(
                region__isnull=True,
                channel=channel,
                name=template_name,
                language=lang,
                is_active=True,
            ).first()
        if template:
            break

    if not template:
        template = MessageTemplate.objects.filter(
            channel=channel,
            name=template_name,
            is_active=True,
        ).first()

    if template and template.approval_status == MessageTemplate.ApprovalStatus.PENDING:
        raise ValueError(f"Template '{template_name}' is pending approval and cannot be sent.")

    return template

