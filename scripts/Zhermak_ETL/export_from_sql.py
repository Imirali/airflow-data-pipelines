from scripts.tools.DB_tools import get_db_conn, exec_the_procedure
from scripts.Zhermak_ETL.file_writer import save_table_to_file
from scripts.tools.sftp_conn import upload_files_to_sftp
import os
from datetime import datetime, timedelta
import shutil
from scripts.tools.logger_setup import logger
from scripts.tools.mail_sender import send_email_notification

def get_previous_business_day():
    today = datetime.now().date()
    if today.weekday() == 0:  
        return today - timedelta(days=3) 
    else:
        return today - timedelta(days=1)

today_str = datetime.now().strftime("%Y%m%d")

yesterday = get_previous_business_day()
yesterday_str = yesterday.strftime('%Y-%m-%d')
yesterday_num = yesterday.strftime('%Y%m%d')

dir_path = os.path.join('data','exports','Zhermack')
old_path = os.path.join('data','exports','Zhermack','old')

archive_dir = os.path.join(old_path, yesterday_str)
os.makedirs(archive_dir, exist_ok=True)

moved_count = 0
for filename in os.listdir(dir_path):
    if filename.endswith(('.csv', '.txt')):
        if yesterday_num in filename:
            src = os.path.join(dir_path, filename)
            dst = os.path.join(archive_dir, filename)
            
            if os.path.exists(src):
                shutil.move(src, dst)
                logger.info(f"Moved: {filename} -> {archive_dir}") 
                moved_count += 1

if moved_count == 0:
    logger.info(f"No files found for {yesterday_str}")
else:
    logger.info(f"Moved {moved_count} files")

tables = ['Customer', 'LegalEntity', 'Product', 'SellOut', 'Purchase', 'WarehouseStock']
exported_files = []
export_success = False
upload_success = False

try:
    with get_db_conn() as conn:
        try:
            with conn.cursor() as cursor:
                cursor.execute("""exec ZHE_create_table45""")
            logger.info("ZHE_create_table45 OK")
        except Exception as e:
            logger.error(e)

        try:
            for table in tables:
                columns, data = exec_the_procedure(f'ZHE_{table}', conn)
                files = save_table_to_file(table, columns, data)
                logger.info(f"{table} created")
                txt_files = [f for f in files if f.endswith('.txt')]
                exported_files.extend(txt_files)
            export_success = True
        except Exception as e:
            logger.error(e)
            export_success = False
            
except Exception as e:
    logger.error(e)
    export_success = False

if exported_files:
    logger.info("=" * 60)
    logger.info(f"Starting SFTP upload of {len(exported_files)} files...")
    logger.info("=" * 60)
    
    upload_success = upload_files_to_sftp(exported_files)
    
    if upload_success:
        logger.success("All files uploaded to SFTP successfully!")
    else:
        logger.error("Some files failed to upload to SFTP")
else:
    logger.warning("No files to upload to SFTP")
    upload_success = False

# Итоговый результат и email
overall_success = export_success and upload_success

if overall_success:
    logger.success("=" * 60)
    logger.success("PIPELINE COMPLETED SUCCESSFULLY!")
    logger.info("=" * 60)
else:
    logger.error("=" * 60)
    logger.error("PIPELINE COMPLETED WITH ERRORS")
    logger.info("=" * 60)

send_email_notification(overall_success, exported_files)