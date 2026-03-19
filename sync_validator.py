"""
This script compares two lists of filename to identify missing files.
(a list of files from Excel should be uploaded
 v.s. the actual list of files uploaded to SFTP in the past 24hrs) 

Workflow:
    1. Read .txt files containing filename lists from both 'Excel' and 'SFTP' directories.
    2. Filter and format the SFTP filenames (removing date suffixes like `_DDMMYYYY123456.pdf`).
    3. Compare the two lists to output:
       - Files missing in SFTP (Present in Excel but not in SFTP)
       - Extra files in SFTP (Present in SFTP but not in Excel)
    4. Output the comparison results:
       - Missing files saved to the 'Result' directory with date&time.
       - Extra files saved to the 'Error' directory with date&time.

Directories:
    - Excel/   : Directory for the expected filename list (.txt)
    - SFTP/    : Directory for the actual uploaded SFTP filename list (.txt)
    - Result/  : Directory for the files missing from SFTP (.txt)
    - Error/   : Directory for the extra files found in SFTP (.txt)
"""

import logging
import os
from pathlib import Path
from datetime import datetime
from config import setup_logging, CURRENT_DATE_TIME, CSV_DIR, SFTP_DIR, RESULT_DIR

# Initialize shared logging
setup_logging()

# =============================================================================
# Functions
# =============================================================================


class FileComparator:
    """
    This script comparing shipment reference with internal format, figure
    out which files is missing in another server.
    """

    def __init__(self, csv_dir: Path = CSV_DIR, sftp_dir: Path = SFTP_DIR,
                result_dir: Path = RESULT_DIR):

        self.csv_dir = csv_dir
        self.sftp_dir = sftp_dir
        self.result_dir = result_dir

        # Store comparison result
        self.file_missing_in_sftp = []
        self.extra_file_in_sftp = []
        self.ship_ref_in_sftp = []


    def read_latest_txt(self, dir_path: Path, sftp: bool = False) -> list:
        """
        Read the latest modified text file in directory provided. Run
        'csv_extractor.py' to generate csv text file, manual create & paste
        data in sftp text file.

        Args:
            dir_path  : Directory to search for .txt files.
            file_type : Label used in log messages (e.g. 'csv', 'sftp').
            compare   : If True, read the TWO latest files and return lines
                        present in the newest (A) but absent in the previous
                        one (B) — i.e. the A - B set difference.
                        Default False keeps the original single-file behaviour.
        """
        logging.debug(f"Reading directory {dir_path}")
        file_type = "sftp" if sftp else "csv"

        # Ensure the path exists & is a directory
        if not dir_path.exists() or not dir_path.is_dir():
            raise FileNotFoundError("Directory not found")

        txt_files = list(dir_path.glob("*.txt"))
        logging.debug(f"{len(txt_files)} .txt files found")

        # Nothing inside the directory
        if not txt_files:
            raise FileNotFoundError("Didn't find any .txt files")

        # If only one file, everything is considered "new added"
        if sftp and len(txt_files) < 2:
            logging.warning("All sftp in past 10days are new uploaded.")

        files_dict = {}
        for file in txt_files:

            # Get file modification timestamp and convert to Datetime object
            timestamp = os.path.getmtime(file)
            datestamp = datetime.fromtimestamp(timestamp)

            # Utilise setdefault() to ensure datestamp didnt overwrite
            files_dict.setdefault(file, datestamp)

        # Sort in descending order based on value(datestamp)
        files_sorted = sorted(files_dict.items(), key=lambda item: item[1], reverse=True)

        logging.info(f"Latest {file_type} file found: {files_sorted[0][0].name}")

        # For csv, return one list
        if not sftp:
            try:
                with open(files_sorted[0][0], 'r', encoding='utf-8') as data:
                    # Remove '\n' in list()
                    return data.read().splitlines()
                
            except Exception as e:
                raise SystemExit(f"Couldn't read {files_sorted[0][0].name} | {e}")

        # For sftp, get new data upload
        if sftp:
            logging.info(f"Second {file_type} file found: {files_sorted[1][0].name}")
            
            try:
                with open(files_sorted[0][0], 'r', encoding='utf-8') as data:
                    new_list = data.read().splitlines()
            except Exception as e:
                raise SystemExit(f"Couldn't read {files_sorted[0][0].name} | {e}")

            try:
                with open(files_sorted[1][0], 'r', encoding='utf-8') as data:
                    old_list = data.read().splitlines()
            except Exception as e:
                raise SystemExit(f"Couldn't read {files_sorted[1][0].name} | {e}")

            new_data = [line for line in new_list if line not in set(old_list)]
            logging.info(f"{len(new_data)} new ship_ref found compared to previous file")

            return new_data


    def filter_parent_path(self, sftp_path: Path) -> list:
        """        
        Iterates through all files listed in SFTP, remove directory paths 
        (/opt/sftp/...) and unnecessary suffixes like '_DDMMYYYY123456.pdf'
        """

        sftp_data = self.read_latest_txt(sftp_path, True)

        cleaned_data = []

        for ship_ref in sftp_data:

            # Remove directory path to get file name
            filename = Path(ship_ref).name

            # Use string slicing to remove date suffix
            index = filename.find("_")

            if index != -1:
                cleaned_data.append(filename[:index])
            
            else:
                # Add file name directly if no '_' found
                cleaned_data.append(filename)

        if not cleaned_data:
            raise SystemExit("None valid ship_ref is read")

        return cleaned_data
    

    def get_sftp(self, sftp_path: Path) -> list:
        """
        Return new SFTP data since the last snapshot (A - B set difference).
        Delegates to read_latest_txt() with compare=True.
        """
        return self.read_latest_txt(sftp_path, file_type="sftp", compare=True)




    def matching_process(self):
        """
        Compare excel_data and sftp_data to find missing and extra data.

        Excel_data is the base, use sftp_data deduct it
        """

        csv_data = self.read_latest_txt(self.csv_dir, "csv")
        sftp_data = self.filter_parent_path(self.sftp_dir)

        # FIX 4: Was `self.sftp_data` (non-existent attribute), corrected to local variable `sftp_data`
        logging.debug(f"{len(set(sftp_data))} files uploaded in SFTP past 24hrs")

        logging.info("Comparison started")
        
        # Convert to sets for efficient O(1) lookups
        # FIX 5: Was `self.file_listed_in_excel` (non-existent attribute), corrected to local variable `csv_data`
        excel_set = set(csv_data)
        # FIX 6: Was `self.sftp_data` (non-existent attribute), corrected to local variable `sftp_data`
        sftp_set = set(sftp_data)

        # Files haven't uploaded to SFTP
        # FIX 7: Was `self.file_listed_in_excel`, corrected to `csv_data`
        missing_files = [f for f in csv_data if f not in sftp_set]
        # Use dictionary to remove duplicates (key is unique), then convert back to list
        self.file_missing_in_sftp = list(dict.fromkeys(missing_files))

        # Files not listed in Excel
        # FIX 8: Was `self.sftp_data`, corrected to `sftp_data`
        extra_files = [f for f in sftp_data if f not in excel_set]
        self.extra_file_in_sftp = list(dict.fromkeys(extra_files))

        logging.info("Comparison completed")

        logging.info(f"{len(self.file_missing_in_sftp)} SFTP's files failed to match Excel's files")
        print(f"Files missing from SFTP: {len(self.file_missing_in_sftp)} files")

        logging.info(f"{len(self.extra_file_in_sftp)} SFTP's files not listed in Excel")
        print(f"Extra files found in SFTP: {len(self.extra_file_in_sftp)} files")
        

    def upload_results(self):
        """
        Write result and rename with current date time.
        """

        # Define output path for both
        file_missing_path = self.result_path / f"{CURRENT_DATE_TIME}.txt"

        # Writing results
        with open(file_missing_path, 'w', encoding='utf-8') as file:
            for fileName in self.file_missing_in_sftp:
                file.write(f"{fileName}\n")

        logging.info(f"Results have been uploaded and renamed: {CURRENT_DATE_TIME}.txt")
        print(f"Results named: {CURRENT_DATE_TIME}.txt")


# -------------------------------------------------
# Main Entry Point
# -------------------------------------------------

if __name__ == "__main__":

    logging.info("sync_validator.py program started")

    try:        
        comparator = FileComparator()
        comparator.matching_process()
        # comparator.upload_results()
        
    except FileNotFoundError as e:
        logging.error(e)
        print(e)

    except SystemExit as e:
        logging.error(e)
        print(e)

    except Exception as e:
        logging.error(e)
        print(e)

    finally:
        logging.info("sync_validator.py program ended")