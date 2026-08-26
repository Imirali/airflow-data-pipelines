import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime
import os
from loguru import logger


def send_email_notification_triumf(success: bool, docno: str, attachment_path: str = None):
    """
    Send email notification with DBF file attachment
    
    Args:
        success: True if DBF was created successfully, False otherwise
        docno: Document number (DCODE)
        attachment_path: Path to DBF file to attach (optional)
    """
    smtp_server = "E17.ud.ru"
    smtp_port = 25
    sender = "i.bayrambekov@unident.net"
    receiver = "nakl@fktriumf.com"
    
    # CC addresses
    cc_list = [
        "akulov@unident.net",
        "l.vodostoy@unident.net",
    ]
    
    status = "SUCCESS" if success else "FAILED"
    subject = f"{docno} реализация ЗАО Юнидент"
    
    # Create multipart message
    msg = MIMEMultipart()
    msg["From"] = sender
    msg["To"] = receiver
    msg["Cc"] = ", ".join(cc_list)
    msg["Subject"] = subject
    
    # Email body
    body_lines = [
        f"{docno} реализация ЗАО Юнидент",

    ]
    
    if attachment_path and success:
        body_lines.append(f"File attached: {os.path.basename(attachment_path)}")
    
    msg.attach(MIMEText("\n".join(body_lines), "plain"))
    
    # Attach DBF file if exists and success
    if attachment_path and success and os.path.exists(attachment_path):
        try:
            with open(attachment_path, "rb") as f:
                part = MIMEBase("application", "octet-stream")
                part.set_payload(f.read())
                encoders.encode_base64(part)
                
                # Add header with filename
                filename = os.path.basename(attachment_path)
                part.add_header(
                    "Content-Disposition",
                    f"attachment; filename={filename}"
                )
                msg.attach(part)
                logger.info(f"Attached file: {filename}")
        except Exception as e:
            logger.error(f"Failed to attach file: {e}")
    
    # All recipients (To + Cc)
    recipients = [receiver] + cc_list
    
    try:
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.ehlo()
        server.sendmail(sender, recipients, msg.as_string())
        server.quit()
        logger.info(f"Email sent successfully with attachment: {os.path.basename(attachment_path) if attachment_path else 'None'}")
        logger.info(f"To: {receiver}, Cc: {', '.join(cc_list)}")
        return True
    except Exception as e:
        logger.error(f"Failed to send email: {e}")
        return False