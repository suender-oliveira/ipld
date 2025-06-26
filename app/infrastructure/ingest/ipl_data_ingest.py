"""
Provides functionality for ingesting and processing IPL data.
"""

import fnmatch
import os
import sqlite3
from datetime import datetime

import pandas as pd

from app.infrastructure.config.settings import app_settings
from app.infrastructure.persistence.models import (
    ResultsDoneTableModel,
    ResultsFailTableModel,
    ResultsGarbTableModel,
    ResultsLastIplTableModel,
)


class IPLDataIngestor:
    """
    Responsible for ingesting and processing IPL data.
    """

    def __init__(self, db_url: str) -> None:
        self.db_url = db_url
        self.raw_db_path = (
            f"{app_settings.RESULT_PATH}/{app_settings.ZPLATIPLD_DB}"
        )
        self.raw_result_table = "raw_results"

    def _get_connection(self) -> sqlite3.Connection:
        """
        Returns a SQLite connection object to the database file specified
        by self.raw_db_path.

        Args:
            None

        Returns:
            sqlite3.Connection: A connection object to the database file.

        Raises:
            None
        """
        return sqlite3.connect(self.raw_db_path)

    def _find_csv_files(self, directory: str) -> dict[str, str]:
        """
        Finds all CSV files in a given directory that contain the word "resume"

        Args:
            directory (str): The directory to search for CSV files.

        Returns:
            dict[str, str]: A dictionary mapping the file names to their
                full paths.
        """
        csv_files = {}
        for root, _, files in os.walk(directory):
            for file in files:
                if fnmatch.fnmatch(file, "*.CSV") and "resume" in file:
                    full_path = os.path.join(root, file)
                    csv_files[file] = full_path
        return csv_files

    def _is_datetime(self, date_str: str | None) -> bool:
        """Check if a string is a valid datetime.

        Args:
            date_str (str | None): The string to check.

        Returns:
            bool: True if the string is a valid datetime, False otherwise.
        """
        if date_str is None:
            return False
        try:
            datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            return False
        else:
            return True

    def _calc_time_duration(self, u_timestamp: int) -> str:
        """Calculate the time duration from a given timestamp.

        Args:
            u_timestamp (int): The timestamp to calculate the duration from.

        Returns:
            str: A string representing the time duration in the
                format "HH:MM:SS".
        """

        passed_hours = 0
        passed_minutes = 0

        if u_timestamp >= 86400:
            days = u_timestamp // 86400
            u_timestamp %= 86400
            passed_hours += days * 24

        passed_hours += u_timestamp // 3600
        u_timestamp %= 3600

        passed_minutes += u_timestamp // 60
        u_timestamp %= 60

        return f"{passed_hours:02}:{passed_minutes:02}:{u_timestamp:02}"

    def _convert_to_unix_timestamp(self, date_str: str) -> int:
        """Convert a date string to a Unix timestamp.

        Args:
            date_str (str): A date string in the format "YYYY-MM-DD HH:MM:SS".

        Returns:
            int: The corresponding Unix timestamp.
        """

        date_object = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
        return int(date_object.timestamp())

    def _convert_to_last_ipl_date_format(self, date_str: str) -> str:
        """
        Convert a date string in the format "YYYY-MM-DD HH:MM:SS" to
        the last IPL date format "MMM DD, YYYY".

        Args:
            date_str (str): The input date string in the
                format "YYYY-MM-DD HH:MM:SS".

        Returns:
            str: The converted date string in the last IPL date
                format "MMM DD, YYYY".
        """

        return datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S").strftime(
            "%b %d, %Y"
        )

    def ingest_duration_data(self, sysname_list: list[str]) -> None:
        """
        Ingest duration data from a database table.

        Parameters:
            - self (class instance): The class instance.
            - sysname_list (list[str]): A list of system names to query.

        Returns:
            None
        """

        if not sysname_list:
            print("Empty system name list for duration ingest")
            return

        sysname_tuple = tuple(sysname_list)

        with self._get_connection() as connection:
            cursor = connection.cursor()
            if len(sysname_list) == 1:
                query = (
                    "SELECT sysname, log_dataset, shutdown_begin, shutdown_end"
                    " ipl_begin, ipld_end, pre_ipl, pos_ipl_last_ipl from %s"
                    " WHERE sysname = '%s'",
                    self.raw_result_table,
                    sysname_tuple[0],
                )
            else:
                query = (
                    "SELECT sysname, log_dataset, shutdown_begin, shutdown_end"
                    " ipl_begin, ipld_end, pre_ipl, pos_ipl_last_ipl from %s"
                    " WHERE sysname = '%s'",
                    self.raw_result_table,
                    sysname_tuple,
                )

            connection_exec_list_row = cursor.execute(query).fetchall()

            done_data_list = []
            fail_data_list = []
            garb_data_list = []
            last_ipl_data_list = []

            for row in connection_exec_list_row:
                (
                    sysname,
                    log_dataset,
                    shutdown_begin,
                    shutdown_end,
                    ipl_begin,
                    ipl_end,
                    pre_ipl,
                    pos_ipl,
                    last_ipl,
                ) = row

                is_valid_ipl_times = (
                    self._is_datetime(shutdown_begin)
                    and self._is_datetime(shutdown_end)
                    and self._is_datetime(ipl_begin)
                    and self._is_datetime(ipl_end)
                )

                if is_valid_ipl_times:
                    shutdown_duration = self._calc_time_duration(
                        self._convert_to_unix_timestamp(shutdown_end)
                        - self._convert_to_unix_timestamp(shutdown_begin)
                    )

                    poweroff_duration = self._calc_time_duration(
                        self._convert_to_unix_timestamp(ipl_begin)
                        - self._convert_to_unix_timestamp(shutdown_end)
                    )

                    load_ipl = self._calc_time_duration(
                        self._convert_to_unix_timestamp(ipl_end)
                        - self._convert_to_unix_timestamp(ipl_begin)
                    )

                    total_duration = self._calc_time_duration(
                        self._convert_to_unix_timestamp(ipl_end)
                        - self._convert_to_unix_timestamp(shutdown_begin)
                    )

                    done_data_list.append(
                        {
                            "sysname": sysname,
                            "ipl_date": self._convert_to_last_ipl_date_format(
                                shutdown_begin
                            ),
                            "log_dataset": log_dataset,
                            "shutdown_begin": shutdown_begin,
                            "shutdown_end": shutdown_end,
                            "ipl_begin": ipl_begin,
                            "ipl_end": ipl_end,
                            "pre_ipl": pre_ipl,
                            "pos_ipl": pos_ipl,
                            "shutdown_duration": shutdown_duration,
                            "poweroff_duration": poweroff_duration,
                            "load_ipl": load_ipl,
                            "total_duration": total_duration,
                        }
                    )
                elif not is_valid_ipl_times and (
                    shutdown_begin or shutdown_end or ipl_begin or ipl_end
                ):
                    fail_data_list.append(
                        {
                            "sysname": sysname,
                            "log_dataset": log_dataset,
                            "shutdown_begin": shutdown_begin,
                            "shutdown_end": shutdown_end,
                            "ipl_begin": ipl_begin,
                            "ipl_end": ipl_end,
                            "pre_ipl": pre_ipl,
                            "pos_ipl": pos_ipl,
                        }
                    )
                else:
                    garb_data_list.append(
                        {
                            "sysname": sysname,
                            "log_dataset": log_dataset,
                            "shutdown_begin": shutdown_begin,
                            "shutdown_end": shutdown_end,
                            "ipl_begin": ipl_begin,
                            "ipl_end": ipl_end,
                            "pre_ipl": pre_ipl,
                            "pos_ipl": pos_ipl,
                        }
                    )

                if self._is_datetime(last_ipl):
                    last_ipl_data_list.append(
                        {
                            "sysname": sysname,
                            "log_dataset": log_dataset,
                            "last_ipl": last_ipl,
                        }
                    )

            if done_data_list:
                done_dataframe = pd.DataFrame(done_data_list).drop_duplicates()
                done_dataframe.to_sql(
                    ResultsDoneTableModel.__tablename__,
                    connection,
                    if_exists="append",
                    index=None,
                )

            if fail_data_list:
                fail_dataframe = pd.DataFrame(fail_data_list).drop_duplicates()
                fail_dataframe.to_sql(
                    ResultsFailTableModel.__tablename__,
                    connection,
                    if_exists="append",
                    index=None,
                )

            if garb_data_list:
                garbage_dataframe = pd.DataFrame(
                    garb_data_list
                ).drop_duplicates()
                garbage_dataframe.to_sql(
                    ResultsGarbTableModel.__tablename__,
                    connection,
                    if_exists="append",
                    index=None,
                )

            if last_ipl_data_list:
                last_ipl_dataframe = pd.DataFrame(
                    last_ipl_data_list
                ).drop_duplicates()
                last_ipl_dataframe.to_sql(
                    ResultsLastIplTableModel.__tablename__,
                    connection,
                    if_exists="append",
                    index=None,
                )

    def ingest_raw_ipl_data(self) -> list[list[str]]:
        systems_with_new_data = []
        with self._get_connection() as connection:
            cursor = connection.cursor()

            cursor.execute(f"""
                CREATE TABLE IF NOT EXISTS {self.raw_result_table} (
                    log_name TEXT, log_id TEXT, date TEXT, time TEXT, sysname TEXT,
                    type TEXT, error TEXT, last_ipl TEXT, msg TEXT,
                    pre_ipl TEXT, ipl_end TEXT, pos_ipl TEXT)
            """)

            connection.commit()
