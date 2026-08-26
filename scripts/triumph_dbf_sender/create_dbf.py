import os
from dbf import Table
from datetime import datetime, date
from decimal import Decimal
import sys
import pyodbc
from loguru import logger
import time
import re
import shutil
from dotenv import load_dotenv
from .mail_sender_triumf import send_email_notification_triumf

path = os.path.join("C:\\", "imir_docs", "airflow-data-pipelines", "logs", "triumph.log")

logger.remove()

logger.add(
    sys.stdout,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    level="INFO",
)
logger.add(
    path,
    rotation="10 MB",
    encoding="utf-8",
    level="DEBUG",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{line} - {message}",
)


def get_db_conn() -> pyodbc.Connection:
    """
    Connection to DB
    args
        none
    returns
        conn.obj
    """
    load_dotenv()
    driver: str = os.getenv("DB_DRIVER")
    server: str = os.getenv("DB_SERVER")
    database: str = 'UD'
    user: str = os.getenv("DB_USER")
    password: str = os.getenv("DB_PASSWORD")

    conn_str: str = f"DRIVER={{{driver}}}; SERVER={server}; DATABASE={database}; UID={user}; PWD={password}"

    try:
        conn: pyodbc.Connection = pyodbc.connect(conn_str)
        logger.info(
            f"Successfully connected to database '{database}' on server '{server}'"
        )
        return conn
    except pyodbc.Error as e:
        logger.error(f"Failed to connect to database: {e}")
        raise


def archive_old_files(directory: str, old_dir: str = "old"):
    """
    Moves all existing .dbf files from directory to old subdirectory
    
    Args:
        directory: Directory containing DBF files
        old_dir: Subdirectory name for old files (default: 'old')
    """
    old_path = os.path.join(directory, old_dir)
    
    # Create old directory if it doesn't exist
    os.makedirs(old_path, exist_ok=True)
    
    # Find all .dbf files in the main directory
    moved_count = 0
    for filename in os.listdir(directory):
        if filename.endswith('.dbf'):
            source_path = os.path.join(directory, filename)
            
            # Generate unique name with timestamp to avoid conflicts
            base_name = os.path.splitext(filename)[0]
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            new_filename = f"{base_name}_{timestamp}.dbf"
            dest_path = os.path.join(old_path, new_filename)
            
            try:
                shutil.move(source_path, dest_path)
                logger.info(f"Moved old file: {filename} -> old/{new_filename}")
                moved_count += 1
            except Exception as e:
                logger.error(f"Failed to move {filename}: {e}")
    
    if moved_count == 0:
        logger.info("No old DBF files found to archive")
    else:
        logger.info(f"Archived {moved_count} old file(s)")


# ============================================
# FIELD STRUCTURE (for dbf library)
# Format: 'FIELD_NAME TYPE(length,decimals)'
# ============================================
FIELDS = [
    'NZAKAZA C(20)',      # Order number
    'DCODE C(20)',        # Document number
    'DATE_DOC D',         # Document date
    'CODE C(11)',         # Supplier product code
    'PRODUCT C(100)',     # Product name (required)
    'NAME_PRO C(50)',     # Manufacturer (required)
    'COUNTRY C(50)',      # Country of origin
    'KOLVO N(10,0)',      # Quantity (required)
    'EI C(20)',           # Unit of measurement
    'KOL_PACK N(10,0)',   # Package size
    'VES N(10,3)',        # Weight
    'VOLUME N(10,8)',     # Volume
    'TEMP C(50)',         # Temperature regime
    'EAN13 C(13)',        # Manufacturer barcode
    'PRICE_NDS N(10,2)',  # Price with VAT (required)
    'CENO_Z N(10,2)',     # Price without VAT (for Vital and Essential Drugs)
    'PRPRCS C(50)',       # Price history (for Vital and Essential Drugs)
    'NDS N(2,0)',         # VAT rate % (required)
    'SUMMA N(10,2)',      # Total with VAT (required)
    'SUM_NDS N(10,2)',    # VAT amount
    'GTD C(30)',          # Customs declaration number
    'ORG_SERT C(100)',    # Certification authority
    'SERT_N C(100)',      # Certificate number
    'DAT_SERT D',         # Certificate issue date
    'DECL C(100)',        # Declarant
    'SERIES C(50)',       # Manufacturer series
    'DZ D',               # Product release date
    'SROK_S D',           # Expiration date
    'GV N(1,0)',          # Vital and Essential Drug flag (1-VED, 0-not VED)
    'MARKTAG N(1,0)',     # Marking flag (1-marked, 0-not marked)
    'PLACEID C(20)',      # Place of activity identifier (required)
    'ACCEPT N(1,0)',      # Acceptance method (0-reverse, 1-direct)
    'DTPROIZ D',          # Manufacturer sale date
    'GTIN C(14)',         # GTIN
]


# ============================================
# DATA CONVERSION FUNCTION
# ============================================
def convert_db_row_to_dict(columns, row):
    """
    Converts a database row to a dictionary with proper types for DBF
    """
    result = {}
    
    for i, col_name in enumerate(columns):
        value = row[i]
        
        # Mapping from DB column names to DBF field names
        dbf_field = col_name.upper()
        
        # Handle None values
        if value is None:
            result[dbf_field] = None
            continue
        
        # Handle date values
        if isinstance(value, (datetime, date)):
            result[dbf_field] = value
            continue
        
        # Handle numeric values
        if isinstance(value, (int, float, Decimal)):
            result[dbf_field] = value
            continue
        
        # Handle string values (truncate to max length)
        if isinstance(value, str):
            # Find the maximum field length
            for field_spec in FIELDS:
                field_name = field_spec.split()[0]
                if field_name == dbf_field:
                    # Extract length from spec like 'C(20)' or 'N(10,2)'
                    match = re.search(r'\((\d+)', field_spec)
                    if match:
                        max_len = int(match.group(1))
                        if len(value) > max_len:
                            logger.warning(f"Truncated field {dbf_field}: {len(value)} -> {max_len}")
                            value = value[:max_len]
                    break
            result[dbf_field] = value
            continue
        
        # Everything else - convert to string
        result[dbf_field] = str(value)
    
    return result


def get_sql_query_from_file(sql_file_path: str) -> str:
    """
    Reads SQL from file and returns only the SELECT statement
    """
    with open(sql_file_path, 'r', encoding='utf-8') as f:
        sql_content = f.read()
    
    # Split by GO statements
    statements = []
    current = []
    
    for line in sql_content.split('\n'):
        line = line.strip()
        if line.upper() == 'GO':
            if current:
                statements.append('\n'.join(current))
                current = []
        else:
            current.append(line)
    
    if current:
        statements.append('\n'.join(current))
    
    # Find the last statement that contains SELECT
    for stmt in reversed(statements):
        if 'SELECT' in stmt.upper():
            logger.info("Found SELECT statement")
            return stmt
    
    logger.warning("No SELECT statement found, using entire file")
    return sql_content


# ============================================
# MAIN DBF CREATION FUNCTION (FROM SQL FILE)
# ============================================
def create_dbf_from_sql_file(
    sql_file_path: str,
    output_dir: str = "data/exports/triumph",
    query_timeout: int = 600,
    connection_timeout: int = 60,
    archive_old: bool = True  # ← ДОБАВЛЕНО!
):
    """
    Creates a DBF file in CP866 (DOS) encoding
    from data retrieved by executing SQL from a file
    
    Args:
        sql_file_path: Path to SQL file with query
        output_dir: Directory where DBF file will be saved
        query_timeout: Query execution timeout in seconds
        connection_timeout: Connection timeout in seconds
        archive_old: Whether to archive existing DBF files (default: True)
    """
    start_time = time.time()
    
    try:
        # 1. Archive old files if enabled
        if archive_old:
            logger.info("Checking for old DBF files to archive...")
            archive_old_files(output_dir)
        
        # 2. Read and parse SQL from file
        logger.info(f"Reading SQL from file: {sql_file_path}")
        sql_query = get_sql_query_from_file(sql_file_path)
        
        # 3. Add SET NOCOUNT ON if not present
        if 'SET NOCOUNT ON' not in sql_query.upper():
            sql_query = 'SET NOCOUNT ON;\n' + sql_query
            logger.info("Added SET NOCOUNT ON to query")
        
        # 4. Connect to database
        logger.info(f"Connecting to database (timeout: {connection_timeout}s)...")
        conn = get_db_conn()
        logger.info("Database connection established")
        
        # 5. Execute SQL query
        logger.info(f"Executing SQL query (timeout: {query_timeout}s)...")
        logger.info("This may take some time. Please wait...")
        
        cursor = conn.cursor()
        cursor.execute(sql_query)
        
        # 6. Get column names
        columns = [column[0] for column in cursor.description] if cursor.description else []
        
        if len(columns) == 0:
            logger.error("Query returned no columns")
            conn.close()
            return False
        
        # 7. Fetch all data
        logger.info("Fetching data from database...")
        data = cursor.fetchall()
        
        if not data:
            logger.warning("No data to write to DBF")
            conn.close()
            return False
        
        elapsed = time.time() - start_time
        logger.info(f"Retrieved {len(data)} records, {len(columns)} columns in {elapsed:.2f}s")
        
        # 8. Convert data to dictionaries
        logger.info("Converting data...")
        records = []
        for row in data:
            record = convert_db_row_to_dict(columns, row)
            records.append(record)
        
        # 9. Determine output filename
        dcode = str(records[0].get('DCODE', 'unknown')) if records else 'unknown'
        date_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{dcode}_{date_str}.dbf"
        
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, filename)
        
        # 10. Create DBF file
        logger.info(f"Creating DBF file: {output_path}")
        table = Table(output_path, FIELDS, codepage='cp866')
        
        from dbf import READ_WRITE
        with table.open(mode=READ_WRITE) as dbf:
            for record in records:
                # Clean record: keep only fields from structure
                clean_record = {}
                for field_spec in FIELDS:
                    field_name = field_spec.split()[0]
                    clean_record[field_name] = record.get(field_name, None)
                
                dbf.append(clean_record)
        
        # 11. Verify result
        file_size = os.path.getsize(output_path)
        total_time = time.time() - start_time
        logger.info(f"DBF file created: {output_path}")
        logger.info(f"File size: {file_size} bytes")
        logger.info(f"Records: {len(records)}")
        logger.info(f"Total execution time: {total_time:.2f} seconds")
        
        # 12. Show file version
        with open(output_path, 'rb') as f:
            version_byte = f.read(1)[0]
            logger.info(f"DBF version: 0x{version_byte:02X} (dBASE III PLUS)")
        
        # 13. Close connection
        conn.close()
        
        logger.info("="*60)
        logger.info(f"COMPLETED: File is ready: {output_path}")
        logger.info("="*60)
        
        return True
        
    except pyodbc.Error as e:
        if "timeout" in str(e).lower() or "timed out" in str(e).lower():
            logger.error(f"Query timeout exceeded ({query_timeout}s): {e}")
            logger.error("Try increasing query_timeout in configuration")
        else:
            logger.error(f"Database error: {e}")
        return False
    except Exception as e:
        logger.error(f"Error creating DBF: {e}")
        import traceback
        traceback.print_exc()
        return False


# ============================================
# ENTRY POINT
# ============================================
if __name__ == "__main__":

    # ===== CONFIGURATION =====
    SQL_FILE_PATH = "sql/Triumph.sql"
    OUTPUT_DIR = "data/exports/triumph"
    QUERY_TIMEOUT = 600      # 10 minutes
    CONNECTION_TIMEOUT = 60  # 1 minute
    ARCHIVE_OLD = True       # Archive old DBF files to old/ subdirectory
    # =========================
    
    if not os.path.exists(SQL_FILE_PATH):
        logger.error(f"SQL file not found: {SQL_FILE_PATH}")
        sys.exit(1)
    
    success = create_dbf_from_sql_file(
        sql_file_path=SQL_FILE_PATH,
        output_dir=OUTPUT_DIR,
        query_timeout=QUERY_TIMEOUT,
        connection_timeout=CONNECTION_TIMEOUT,
        archive_old=ARCHIVE_OLD
    )
    
    if success:
        sys.exit(0)
    else:
        sys.exit(1)