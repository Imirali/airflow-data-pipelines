import os
import paramiko
from dotenv import load_dotenv
from scripts.tools.logger_setup import logger

load_dotenv()

SFTP_HOST = os.getenv("SFTP_HOST")
SFTP_PORT = int(os.getenv("SFTP_PORT", 22))
SFTP_USERNAME = os.getenv("SFTP_USERNAME")
SFTP_PASSWORD = os.getenv("SFTP_PASSWORD")
SFTP_REMOTE_PATH = os.getenv("SFTP_REMOTE_PATH", "/")


def upload_files_to_sftp(file_list: list) -> bool:
    """
    Upload files to SFTP server
    
    Args:
        file_list: List of local file paths to upload
    
    Returns:
        bool: True if all files uploaded successfully, False otherwise
    """
    if not file_list:
        logger.warning("No files to upload")
        return False

    logger.info("=" * 60)
    logger.info("SFTP UPLOAD STARTED")
    logger.info("=" * 60)
    logger.info(f"Host: {SFTP_HOST}")
    logger.info(f"Port: {SFTP_PORT}")
    logger.info(f"User: {SFTP_USERNAME}")
    logger.info(f"Remote path: {SFTP_REMOTE_PATH}")
    logger.info(f"Files to upload: {len(file_list)}")
    logger.info("-" * 60)

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    uploaded_count = 0
    failed_files = []

    try:
        logger.info(f"Connecting to {SFTP_HOST}:{SFTP_PORT}...")
        ssh.connect(
            hostname=SFTP_HOST,
            port=SFTP_PORT,
            username=SFTP_USERNAME,
            password=SFTP_PASSWORD,
            timeout=30,
        )
        logger.success(f"Connected to {SFTP_HOST}")

        sftp = ssh.open_sftp()
        logger.info("SFTP session opened")

        
        try:
            sftp.chdir(SFTP_REMOTE_PATH)
            logger.info(f"Remote path exists: {SFTP_REMOTE_PATH}")
        except FileNotFoundError:
            logger.warning(f"Remote path does not exist: {SFTP_REMOTE_PATH}")
            try:
                sftp.mkdir(SFTP_REMOTE_PATH)
                logger.info(f"Created remote directory: {SFTP_REMOTE_PATH}")
            except Exception as e:
                logger.error(f"Failed to create remote directory: {e}")
                return False

       
        for local_file in file_list:
            try:
                
                if not os.path.exists(local_file):
                    logger.error(f"Local file not found: {local_file}")
                    failed_files.append(local_file)
                    continue

                
                file_size = os.path.getsize(local_file)
                file_size_mb = file_size / (1024 * 1024)

                
                filename = os.path.basename(local_file)
                remote_file = os.path.join(SFTP_REMOTE_PATH, filename).replace("\\", "/")

                logger.info(f"Uploading: {filename} ({file_size_mb:.2f} MB)")

                
                sftp.put(local_file, remote_file)

                
                remote_stat = sftp.stat(remote_file)
                if remote_stat.st_size == file_size:
                    logger.success(f"{filename} uploaded successfully ({remote_stat.st_size} bytes)")
                    uploaded_count += 1
                else:
                    logger.error(f"{filename} upload incomplete: {file_size} != {remote_stat.st_size}")
                    failed_files.append(local_file)

            except Exception as e:
                logger.error(f"Failed to upload {local_file}: {e}")
                failed_files.append(local_file)
                continue

        sftp.close()
        logger.info("SFTP session closed")

    except paramiko.AuthenticationException:
        logger.error("Authentication failed! Check SFTP_USERNAME and SFTP_PASSWORD in .env")
        return False

    except paramiko.SSHException as ssh_err:
        logger.error(f"SSH connection error: {ssh_err}")
        return False

    except TimeoutError:
        logger.error(f"Connection timeout to {SFTP_HOST}:{SFTP_PORT}")
        return False

    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return False

    finally:
        ssh.close()
        logger.info("SSH connection closed")

   
    logger.info("-" * 60)
    logger.info(f"Uploaded: {uploaded_count}/{len(file_list)} files")
    if failed_files:
        logger.warning(f"Failed files: {failed_files}")
    logger.info("=" * 60)

    return uploaded_count == len(file_list)

