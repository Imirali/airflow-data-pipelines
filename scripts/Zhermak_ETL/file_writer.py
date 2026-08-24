import os
from datetime import datetime
from scripts.tools.logger_setup import logger

def save_table_to_file(table_name:str, columns:list, data: list, output_dir: str = 'data/exports/Zhermack') -> tuple:
    """
    Save table data to CSV and TXT files
    
    Args:
        table_name: Name of the table (used for filename)
        columns: List of column names
        data: List of tuples with data rows
        output_dir: Directory to save files
    
    Returns:
        tuple: (csv_filename, txt_filename)
    """

    os.makedirs(output_dir, exist_ok=True)

    date_str = datetime.now().strftime("%Y%m%d")
    base_filename = f"{table_name}_{date_str}"

    csv_filename = os.path.join(output_dir,f"{base_filename}.csv")
    txt_filename = os.path.join(output_dir,f"{base_filename}.txt")

    #csv - sep = ;
    with open(csv_filename, 'w', encoding='utf-8-sig') as f:
        f.write(';'.join(columns)+'\n')

        for row in data:

            formatted_row = []
            for value in row:
                if value is None:
                    formatted_row.append("")
                else:
                    str_value = str(value)

                    if ";" in str_value or '"' in str_value or '\n' in str_value:
                        str_value = f'"{str_value.replace('"', '""')}"'
                    formatted_row.append(str_value)

            f.write(';'.join(formatted_row)+'\n')

    # txt sep = |

    with open(txt_filename, 'w', encoding='utf-8') as f:
        f.write('|'.join(columns) + '\n')

        for row in data:
            formatted_row = [str(v) if v is not None else '' for v in row]
            f.write('|'.join(formatted_row) + '\n')

    logger.info(f"Saved {table_name}: {len(data)} rows")
    logger.info(f"  CSV: {csv_filename}")
    logger.info(f"  TXT: {txt_filename}")
    
    return csv_filename, txt_filename