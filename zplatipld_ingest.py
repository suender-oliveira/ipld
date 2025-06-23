import os
import fnmatch
from datetime import datetime
import sqlite3
import time
import pandas as pd
from sqlalchemy_sqlite import CrudDB


# Constants Variables
ZPLATIPLD_DB = "zplatipld.sqlite3"
ZPLATIPLD_RESULTS_LAST_IPL_TABLE = "results_last_ipl"
ZPLATIPLD_RESULTS_DONE_TABLE = "results_done"
ZPLATIPLD_RESULTS_FAIL_TABLE = "results_fail"
ZPLATIPLD_RESULTS_GARB_TABLE = "results_garb"
RAW_RESULT_PATH = "/zplatipld/database"
RAW_RESULT_DB = "zplatipld-raw-results.sqlite3"
RAW_RESULT_TABLE = "raw_results"
CSV_RESULTS_PATH = "/zplatipld/results"
ZPLATIPLD_SA_DB = CrudDB(f"sqlite:///{RAW_RESULT_PATH}/{ZPLATIPLD_DB}")


def find_csv(directory):
    """
    Find CSV files in a directory and return a dictionary of full paths.
    This is useful for debugging the CSV files that are used to generate data

    @param directory - Directory to search for CSV files

    @return Dictionary of file names and full paths to CSV files
    """
    csv_files = {}
    # Add csv files to csv_files.
    for root, dirs, files in os.walk(directory):
        # Add csv files to csv_files.
        for file in files:
            # Add a file to csv_files dictionary
            if fnmatch.fnmatch(file, "*.CSV") and "resume" in file:
                full_path = os.path.join(root, file)
                csv_files[file] = full_path
    return csv_files


def is_datetime(date_str) -> bool:
    """
    Checks if date_str is a datetime.
    This is a helper function for get_date_from_string

    @param date_str - the date to check.

    @return True if date_str is a datetime False otherwise
    """
    try:
        # Return True if date_str is a valid date string.
        if date_str is not None:
            datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
            return True
    except ValueError:
        return False
    return False


def calc_time(u_timestamp):
    """
    Calculate how many hours and minutes the user passed.
    This is used to convert the time in seconds to complete time.

    @param u_timestamp - The timestamp of the user's request.

    @return A string with the number of hours and minutes the user passed
    """
    passed_hours = 0
    passed_minutes = 0
    # This function takes a timestamp in seconds and returns the number
    # of hours minutes and seconds since the epoch.
    if u_timestamp > 86400:
        # This function is used to calculate the passed hours
        while (u_timestamp / 86400) >= 1:
            u_timestamp = u_timestamp - 86400
            passed_hours += 24

        # This function is used to calculate the number of hours passed in
        # the timestamp.
        while (u_timestamp / 3600) >= 1:
            u_timestamp = u_timestamp - 3600
            passed_hours += 1

        # This function is used to calculate the amount of minutes passed
        # to the user.
        while (u_timestamp / 60) >= 1:
            u_timestamp = u_timestamp - 60
            passed_minutes += 1

    else:
        # This function is used to calculate the number of hours passed
        # in the timestamp.
        while (u_timestamp / 3600) >= 1:
            u_timestamp = u_timestamp - 3600
            passed_hours += 1

        # This function is used to calculate the amount of minutes passed
        # to the user.
        while (u_timestamp / 60) >= 1:
            u_timestamp = u_timestamp - 60
            passed_minutes += 1

    return f"{passed_hours:0>{2}}:{passed_minutes:0>{2}}:{u_timestamp:0>{2}}"


def convert_to_unix_timestamp(date_str):
    """
    Converts a date string to a unix timestamp.

    @param date_str - The date string to convert

    @return The unix timestamp of the date_str or None if the date_str is
    """
    date_object = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
    return int(date_object.timestamp())


def convert_to_last_ipl_date(date_str):
    """
    Convert date string to IPL date. This is used to generate
    the last_ipl_date field of the report.

    @param date_str - The date string to convert.
    It should be in the format YYYY - MM - DD HH : MM : SS.

    @return The date converted to IPL date format. Example 'Jan 12, 2023'
    """
    return datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S").strftime(
        "%b %d, %Y"
    )


def duration_ingest(sysname_list):
    """
    Ingest duration of a list of datasets.

    @param sysname_list - List of system names to ingestion

    @return A tuple of ( log_dataset, shutdown_begin, shutdown_end,
                       ipl_begin, ipl_end, last_ipl, pre_ipl, post_ipl )
    """

    if sysname_list:
        sysname_list_to_tuple = tuple(
            [sysname_list_values for sysname_list_values in sysname_list]
        )
        connection = sqlite3.connect(f"{RAW_RESULT_PATH}/{RAW_RESULT_DB}")
        cursor = connection.cursor()

        if len(sysname_list) == 1:
            connection_exec_list_raw = cursor.execute(
                "SELECT sysname, log_dataset, shutdown_begin, shutdown_end,"
                + "ipl_begin, ipl_end, last_ipl, pre_ipl, post_ipl FROM "
                + f"{RAW_RESULT_TABLE} WHERE "
                + f"sysname = '{sysname_list_to_tuple[0]}'"
            )
        else:
            connection_exec_list_raw = cursor.execute(
                "SELECT sysname, log_dataset, shutdown_begin, shutdown_end,"
                + " ipl_begin, ipl_end, last_ipl, pre_ipl, post_ipl FROM "
                + f"{RAW_RESULT_TABLE} WHERE sysname IN {sysname_list_to_tuple}"
            )
        dataframe_done_list = []
        dataframe_fail_list = []
        dataframe_garb_list = []
        dataframe_last_ipl_list = []

        for list_row in connection_exec_list_raw:
            if (
                is_datetime(list_row[2])
                and is_datetime(list_row[3])
                and is_datetime(list_row[4])
                and is_datetime(list_row[5])
            ):
                shutdown_duration = calc_time(
                    convert_to_unix_timestamp(list_row[3])
                    - convert_to_unix_timestamp(list_row[2])
                )
                poweroff_duration = calc_time(
                    convert_to_unix_timestamp(list_row[4])
                    - convert_to_unix_timestamp(list_row[3])
                )
                load_ipl = calc_time(
                    convert_to_unix_timestamp(list_row[5])
                    - convert_to_unix_timestamp(list_row[4])
                )
                total_duration = calc_time(
                    convert_to_unix_timestamp(list_row[5])
                    - convert_to_unix_timestamp(list_row[2])
                )

                dataframe_done = pd.DataFrame(
                    [
                        {
                            "sysname": list_row[0],
                            "ipl_date": convert_to_last_ipl_date(list_row[2]),
                            "log_dataset": list_row[1],
                            "shutdown_begin": list_row[2],
                            "shutdown_end": list_row[3],
                            "ipl_begin": list_row[4],
                            "ipl_end": list_row[5],
                            "pre_ipl": list_row[6],
                            "pos_ipl": list_row[7],
                            "shutdown_duration": shutdown_duration,
                            "poweroff_duration": poweroff_duration,
                            "load_ipl": load_ipl,
                            "total_duration": total_duration,
                        }
                    ]
                )
                dataframe_done_list.append(dataframe_done)

            elif (
                not is_datetime(list_row[2])
                or not is_datetime(list_row[3])
                or not is_datetime(list_row[4])
                or not is_datetime(list_row[5])
            ):
                dataframe_fail = pd.DataFrame(
                    [
                        {
                            "sysname": list_row[0],
                            "log_dataset": list_row[1],
                            "shutdown_begin": list_row[2],
                            "shutdown_end": list_row[3],
                            "ipl_begin": list_row[4],
                            "ipl_end": list_row[5],
                            "pre_ipl": list_row[6],
                            "pos_ipl": list_row[7],
                        }
                    ]
                )
                dataframe_fail_list.append(dataframe_fail)

            else:
                dataframe_garb = pd.DataFrame(
                    [
                        {
                            "sysname": list_row[0],
                            "log_dataset": list_row[1],
                            "shutdown_begin": list_row[2],
                            "shutdown_end": list_row[3],
                            "ipl_begin": list_row[4],
                            "ipl_end": list_row[5],
                            "pre_ipl": list_row[6],
                            "pos_ipl": list_row[7],
                        }
                    ]
                )
                dataframe_garb_list.append(dataframe_garb)

            if is_datetime(list_row[6]):
                dataframe_last_ipl = pd.DataFrame(
                    [
                        {
                            "sysname": list_row[0],
                            "log_dataset": list_row[1],
                            "last_ipl": list_row[6],
                        }
                    ]
                )
                dataframe_last_ipl_list.append(dataframe_last_ipl)

        # Returns the list of done rows.
        if "dataframe_done" in locals() or "dataframe_done" in globals():
            done_df = pd.concat(
                dataframe_done_list, ignore_index=True
            ).drop_duplicates()

            done_df.to_sql(
                ZPLATIPLD_RESULTS_DONE_TABLE,
                sqlite3.connect(f"{RAW_RESULT_PATH}/{ZPLATIPLD_DB}"),
                if_exists="append",
                index=None,
            )
        # If dataframe_fail is not in locals or dataframe_fail.
        if "dataframe_fail" in locals() or "dataframe_fail" in globals():
            fail_df = pd.concat(
                dataframe_fail_list, ignore_index=True
            ).drop_duplicates()

            fail_df.to_sql(
                ZPLATIPLD_RESULTS_FAIL_TABLE,
                sqlite3.connect(f"{RAW_RESULT_PATH}/{ZPLATIPLD_DB}"),
                if_exists="append",
                index=None,
            )
        # Returns a pandas dataframe with the results of
        # the ZPLATIPLD_RESULTS_GARB_TABLE.
        if "dataframe_garb" in locals() or "dataframe_garb" in globals():
            garb_df = pd.concat(
                dataframe_garb_list, ignore_index=True
            ).drop_duplicates()

            garb_df.to_sql(
                ZPLATIPLD_RESULTS_GARB_TABLE,
                sqlite3.connect(f"{RAW_RESULT_PATH}/{ZPLATIPLD_DB}"),
                if_exists="append",
                index=None,
            )
        # Returns the last ipl result set.
        if (
            "dataframe_last_ipl" in locals()
            or "dataframe_last_ipl" in globals()
        ):
            last_ipl_df = pd.concat(
                dataframe_last_ipl_list, ignore_index=True
            ).drop_duplicates(subset=["sysname", "last_ipl"])

            last_ipl_df.to_sql(
                ZPLATIPLD_RESULTS_LAST_IPL_TABLE,
                sqlite3.connect(f"{RAW_RESULT_PATH}/{ZPLATIPLD_DB}"),
                if_exists="append",
                index=None,
            )
        time.sleep(10)
        return sysname_list
    else:
        time.sleep(10)
        print(f"Empty list: {sysname_list}")


def zplatipld_ingest():
    """
    Ingest ZPLATIPLD data from CSV's and normalizes data. It will return
    a list of systems to duration ingested.

    @return list of systems to duration ingested or None if
    """
    try:
        connection = sqlite3.connect(f"{RAW_RESULT_PATH}/{RAW_RESULT_DB}")
        cursor = connection.cursor()
        connection_exec_list_table = cursor.execute(
            "select tbl_name from sqlite_master"
        ).fetchall()
        table_list = [no_tuple[0] for no_tuple in connection_exec_list_table]
        if RAW_RESULT_TABLE in table_list:
            ingested_datasets = [
                no_tuple[0]
                for no_tuple in cursor.execute(
                    f"SELECT DISTINCT log_dataset from {RAW_RESULT_TABLE}"
                )
            ]
            systems_to_duration_ingest = []
            for csv_result_keys, csv_result_path in find_csv(
                CSV_RESULTS_PATH
            ).items():
                if os.stat(csv_result_path).st_size > 205:
                    data = pd.read_csv(csv_result_path, delimiter=";")
                    data.head()
                    select_df_column_log_dataset = (
                        data["log_dataset"].drop_duplicates().tolist()
                    )
                    select_df_column_sysname = (
                        data["sysname"].drop_duplicates().to_list()
                    )
                    for column_row in select_df_column_log_dataset:
                        if column_row not in ingested_datasets:
                            data.to_sql(
                                RAW_RESULT_TABLE,
                                connection,
                                if_exists="append",
                                index=False,
                            )
                            if len(select_df_column_sysname) != 0:
                                systems_to_duration_ingest.append(
                                    select_df_column_sysname
                                )
                            print(
                                f"The {column_row} / {select_df_column_sysname}"
                                + "was successfully ingested."
                            )

            return systems_to_duration_ingest
        else:
            systems_to_duration_ingest = []
            for csv_result_keys, csv_result_path in find_csv(
                CSV_RESULTS_PATH
            ).items():
                if os.stat(csv_result_path).st_size > 800:
                    data = pd.read_csv(csv_result_path, delimiter=";")
                    data.head()
                    select_df_column_sysname = (
                        data["sysname"].drop_duplicates().to_list()
                    )
                    data.to_sql(
                        RAW_RESULT_TABLE,
                        connection,
                        if_exists="append",
                        index=False,
                    )
                    # print(len(select_df_column_sysname))
                    if len(select_df_column_sysname) != 0:
                        systems_to_duration_ingest.append(
                            select_df_column_sysname
                        )

            return systems_to_duration_ingest

    except ValueError as error:
        print(str(error))


if __name__ == "__main__":
    system_to_duration_ingest = zplatipld_ingest()
    if system_to_duration_ingest:
        system_to_duration_ingest_uncompressed = []
        for uncompress_list in system_to_duration_ingest:
            system_to_duration_ingest_uncompressed.append(uncompress_list[0])
        system_to_duration_ingest_uncompressed = list(
            set(system_to_duration_ingest_uncompressed)
        )
        duration_ingest(system_to_duration_ingest_uncompressed)
