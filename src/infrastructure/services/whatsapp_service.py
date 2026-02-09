"""
WhatsApp service for sending messages via Twilio
"""
import logging
from typing import Optional

from src.infrastructure.config.settings import get_settings

logger = logging.getLogger(__name__)


class WhatsAppService:
    """Service to send WhatsApp messages via Twilio"""
    
    def __init__(self):
        settings = get_settings()
        self.account_sid = settings.TWILIO_ACCOUNT_SID
        self.auth_token = settings.TWILIO_AUTH_TOKEN
        self.whatsapp_from = settings.TWILIO_WHATSAPP_FROM  # e.g., "whatsapp:+237xxxxxxxxx"
        
        # Only initialize Twilio if credentials are provided
        if self.account_sid and self.auth_token:
            from twilio.rest import Client
            self.client = Client(self.account_sid, self.auth_token)
            self.enabled = True
        else:
            self.client = None
            self.enabled = False
            logger.warning("WhatsApp service not configured - messages will not be sent")
    
    async def send_invitation_code(
        self, 
        phone_number: str, 
        code: str,
        parent_name: str = "Parent"
    ) -> bool:
        """
        Send invitation code via WhatsApp
        
        Args:
            phone_number: Phone number with country code (e.g., "+237xxxxxxxxx")
            code: Invitation code (e.g., "INV-ABC123XYZ")
            parent_name: Name of the parent
        
        Returns:
            True if sent successfully, False otherwise
        """
        if not self.enabled or not self.client:
            logger.warning(f"WhatsApp not configured, skipping send to {phone_number}")
            return False
        
        try:
            # Format phone number for WhatsApp
            whatsapp_to = f"whatsapp:{phone_number}"
            
            # Create message
            message_body = (
                f"Bonjour {parent_name},\n\n"
                f"Vous êtes invité(e) à rejoindre ServantAssist.\n\n"
                f"Votre code d'accès: {code}\n\n"
                f"Utilisez ce code pour vous enregistrer sur l'application.\n\n"
                f"Cordialement,\n"
                f"L'équipe ServantAssist"
            )
            
            # Send via Twilio
            message = self.client.messages.create(
                from_=self.whatsapp_from,
                to=whatsapp_to,
                body=message_body
            )
            
            logger.info(f"WhatsApp message sent successfully to {phone_number} (SID: {message.sid})")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send WhatsApp message to {phone_number}: {str(e)}")
            return False
    
    async def send_login_otp(
        self,
        phone_number: str,
        otp_code: str
    ) -> bool:
        """
        Send OTP code via WhatsApp for login verification
        
        Args:
            phone_number: Phone number with country code
            otp_code: One-time password (e.g., "123456")
        
        Returns:
            True if sent successfully, False otherwise
        """
        if not self.enabled or not self.client:
            logger.warning(f"WhatsApp not configured, skipping OTP to {phone_number}")
            return False
        
        try:
            whatsapp_to = f"whatsapp:{phone_number}"
            
            message_body = (
                f"Votre code de vérification ServantAssist: {otp_code}\n\n"
                f"Ce code expire dans 10 minutes."
            )
            
            message = self.client.messages.create(
                from_=self.whatsapp_from,
                to=whatsapp_to,
                body=message_body
            )
            
            logger.info(f"WhatsApp OTP sent to {phone_number} (SID: {message.sid})")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send WhatsApp OTP to {phone_number}: {str(e)}")
            return False
    
    async def send_admin_notification(
        self,
        phone_number: str,
        admin_name: str,
        message_text: str
    ) -> bool:
        """
        Send admin notification via WhatsApp
        
        Args:
            phone_number: Admin phone number
            admin_name: Admin name
            message_text: Custom message text
        
        Returns:
            True if sent successfully, False otherwise
        """
        if not self.enabled or not self.client:
            return False
        
        try:
            whatsapp_to = f"whatsapp:{phone_number}"
            
            message = self.client.messages.create(
                from_=self.whatsapp_from,
                to=whatsapp_to,
                body=message_text
            )
            
            logger.info(f"WhatsApp notification sent to {phone_number} (SID: {message.sid})")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send WhatsApp notification to {phone_number}: {str(e)}")
            return False
