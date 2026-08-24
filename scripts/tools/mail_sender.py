import smtplib
from email.mime.text import MIMEText
from datetime import datetime
import os


def send_email_notification(success: bool, files: list = None):
    """
    Отправляет email с результатами выгрузки Zhermack ETL
    
    Args:
        success: True если всё успешно, False если ошибка
        files: Список загруженных файлов (опционально)
    """
    

    smtp_server = "E17.ud.ru"
    smtp_port = 25
    sender = "i.bayrambekov@unident.net"
    receiver = "i.bayrambekov@unident.net"
    
  
    today = datetime.now().strftime("%Y-%m-%d")
    log_file = "logs/logs.log"
    logs = ""
    
    try:
        if os.path.exists(log_file):
            with open(log_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            # Фильтруем только строки с SUCCESS или ERROR
            today_lines = []
            for line in lines:
                if line.startswith(today):
                    if "SUCCESS" in line or "ERROR" in line:
                        today_lines.append(line.strip())
            
            logs = "\n".join(today_lines) if today_lines else f"No SUCCESS/ERROR logs for {today}"
        else:
            logs = f"Log file not found: {log_file}"
    except Exception as e:
        logs = f"Error reading logs: {e}"
    

    status = "SUCCESS" if success else "FAILED"
    subject = f"Zhermack ETL: {status} - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    
    body_lines = [
        "=" * 60,
        "ZHERMACK ETL EXPORT REPORT",
        "=" * 60,
        f"Status: {status}",
        f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "=" * 60,
    ]
    
    if files:
        body_lines.append(f"\nFiles uploaded ({len(files)}):")
        body_lines.extend([f"  - {f}" for f in files])
    
    if logs:
        body_lines.extend([
            "\n" + "=" * 60,
            "LOGS (SUCCESS/ERROR only):",
            "=" * 60,
            logs
        ])
    
    msg = MIMEText("\n".join(body_lines))
    msg["From"] = sender
    msg["To"] = receiver
    msg["Subject"] = subject
    
    try:
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.ehlo()
        server.sendmail(sender, [receiver], msg.as_string())
        server.quit()
        #print("Email sent successfully!")
        return True
    except Exception as e:
        #print(f"Failed to send email: {e}")
        return False