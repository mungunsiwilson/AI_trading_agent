"""Email Service Module

Sends PDF reports via email to a list of recipients.
Supports Gmail, Outlook, and custom SMTP servers.
"""

import smtplib
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from typing import List, Optional
from pathlib import Path


class EmailService:
    """Send email reports with PDF attachments."""
    
    def __init__(
        self,
        smtp_server: str,
        smtp_port: int,
        username: str,
        password: str,
        from_email: str,
        use_tls: bool = True
    ):
        """
        Initialize email service.
        
        Args:
            smtp_server: SMTP server address (e.g., smtp.gmail.com)
            smtp_port: SMTP port (587 for TLS, 465 for SSL)
            username: SMTP username (usually your email)
            password: SMTP password or app password
            from_email: Sender email address
            use_tls: Whether to use TLS (default True)
        """
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.username = username
        self.password = password
        self.from_email = from_email
        self.use_tls = use_tls
    
    def send_report(
        self,
        to_emails: List[str],
        subject: str,
        body: str,
        pdf_path: str,
        html_body: Optional[str] = None
    ) -> bool:
        """
        Send email with PDF attachment.
        
        Args:
            to_emails: List of recipient email addresses
            subject: Email subject
            body: Plain text email body
            pdf_path: Path to PDF file to attach
            html_body: Optional HTML version of email body
            
        Returns:
            True if sent successfully, False otherwise
        """
        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = self.from_email
            msg['To'] = ', '.join(to_emails)
            
            # Attach plain text body
            msg.attach(MIMEText(body, 'plain'))
            
            # Attach HTML body if provided
            if html_body:
                msg.attach(MIMEText(html_body, 'html'))
            
            # Attach PDF
            if pdf_path and os.path.exists(pdf_path):
                with open(pdf_path, 'rb') as f:
                    part = MIMEBase('application', 'octet-stream')
                    part.set_payload(f.read())
                
                encoders.encode_base64(part)
                filename = os.path.basename(pdf_path)
                part.add_header(
                    'Content-Disposition',
                    f'attachment; filename="{filename}"'
                )
                msg.attach(part)
            else:
                print(f"Warning: PDF file not found at {pdf_path}")
            
            # Connect to SMTP server and send
            if self.use_tls:
                server = smtplib.SMTP(self.smtp_server, self.smtp_port)
                server.starttls()
            else:
                server = smtplib.SMTP_SSL(self.smtp_server, self.smtp_port)
            
            server.login(self.username, self.password)
            server.sendmail(self.from_email, to_emails, msg.as_string())
            server.quit()
            
            print(f"✓ Email sent successfully to {len(to_emails)} recipient(s)")
            return True
            
        except Exception as e:
            print(f"✗ Failed to send email: {str(e)}")
            return False
    
    def send_test_email(self, to_email: str) -> bool:
        """
        Send a test email to verify configuration.
        
        Args:
            to_email: Recipient email address
            
        Returns:
            True if sent successfully
        """
        subject = "Douyin Opportunity Finder - Test Email"
        body = """
This is a test email from the Douyin Opportunity Finder system.

If you received this, your email configuration is working correctly!

The system will send daily PDF reports to this address at 9:00 AM China Time.

Best regards,
Douyin Opportunity Finder
        """
        
        return self.send_report(
            to_emails=[to_email],
            subject=subject,
            body=body,
            pdf_path=None  # No attachment for test
        )


def create_email_service_from_env() -> Optional[EmailService]:
    """
    Create EmailService instance from environment variables.
    
    Returns:
        EmailService instance or None if configuration is missing
    """
    smtp_server = os.getenv('SMTP_SERVER')
    smtp_port = int(os.getenv('SMTP_PORT', 587))
    username = os.getenv('SMTP_USERNAME')
    password = os.getenv('SMTP_PASSWORD')
    from_email = os.getenv('EMAIL_FROM')
    
    if not all([smtp_server, username, password, from_email]):
        print("Warning: Email configuration incomplete. Email reports disabled.")
        return None
    
    return EmailService(
        smtp_server=smtp_server,
        smtp_port=smtp_port,
        username=username,
        password=password,
        from_email=from_email
    )


def parse_email_list(email_string: str) -> List[str]:
    """
    Parse comma-separated email string into list.
    
    Args:
        email_string: Comma-separated email addresses
        
    Returns:
        List of email addresses
    """
    if not email_string:
        return []
    
    emails = [email.strip() for email in email_string.split(',')]
    return [email for email in emails if email and '@' in email]


if __name__ == "__main__":
    # Test email sending (requires .env configuration)
    from dotenv import load_dotenv
    load_dotenv()
    
    email_service = create_email_service_from_env()
    
    if email_service:
        # Get test recipient from env or use default
        test_email = os.getenv('EMAIL_FROM', 'test@example.com')
        print(f"Sending test email to: {test_email}")
        
        success = email_service.send_test_email(test_email)
        if success:
            print("Test email sent successfully!")
        else:
            print("Failed to send test email.")
    else:
        print("Email service not configured. Please set up .env file.")
