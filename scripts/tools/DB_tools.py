import os

import pyodbc
from dotenv import load_dotenv

from .logger_setup import logger

load_dotenv()


def get_db_conn() -> pyodbc.Connection:
    """
    Connection to DB
    args
        none
    returns
        conn.obj
    """

    driver: str = os.getenv("DB_DRIVER")
    server: str = os.getenv("DB_SERVER")
    database: str = os.getenv("DB_DATABASE")
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


def exec_the_procedure(proc_name: str, conn: pyodbc.Connection) -> tuple:
    """
    Execute stored procedure and return data
    
    args:
        proc_name: name of procedure to execute
        conn: active database connection
    
    returns:
        tuple of (columns, data)
    """
    try:
        with conn.cursor() as cursor:
            cursor.execute("SET LOCK_TIMEOUT 300000") 
            sql = f"EXEC {proc_name}"
            logger.debug(f"Executing: {sql}")
            
            cursor.execute(sql)
            
            columns = [column[0] for column in cursor.description] if cursor.description else []
            
            data = cursor.fetchall()
            
            logger.info(f"Procedure '{proc_name}' returned {len(data)} rows, {len(columns)} columns")
            
            return columns, data
            
    except pyodbc.Error as e:
        logger.error(f"Error executing procedure '{proc_name}': {e}")
        raise
