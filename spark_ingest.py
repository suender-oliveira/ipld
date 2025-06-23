import os
import fnmatch
from pyspark.sql.functions import (
    udf,
    col,
    datediff,
    unix_timestamp,
    from_unixtime,
)
from pyspark.sql.types import BooleanType, StringType, StructField, StructType
from spark_handler import SparkHandle
import datetime

PARQUET_PATH = "/zplatipld/parquet"
CSV_RESULTS_PATH = "/zplatipld/results"
DF_SCHEMA = StructType(
    [
        StructField("sysname", StringType(), nullable=True),
        StructField("log_dataset", StringType(), nullable=True),
        StructField("pre_ipl", StringType(), nullable=True),
        StructField("shutdown_begin", StringType(), nullable=True),
        StructField("shutdown_end", StringType(), nullable=True),
        StructField("ipl_begin", StringType(), nullable=True),
        StructField("ipl_end", StringType(), nullable=True),
        StructField("post_ipl", StringType(), nullable=True),
        StructField("last_ipl", StringType(), nullable=True),
        StructField("elapsed_before_shutdown", StringType(), nullable=True),
        StructField("elapsed_after_shutdown", StringType(), nullable=True),
        StructField("elapsed_btn_shut_ipl", StringType(), nullable=True),
        StructField("elapsed_ipl", StringType(), nullable=True),
        StructField("elapsed_after_ipl", StringType(), nullable=True),
        StructField("total_elapsed", StringType(), nullable=True),
    ]
)


def find_csv(directory):
    csv_files = {}
    for root, dirs, files in os.walk(directory):
        for file in files:
            if fnmatch.fnmatch(file, "*.CSV") and "resume" in file:
                full_path = os.path.join(root, file)
                csv_files[file] = full_path
    return csv_files


def is_datetime(date_str):
    try:
        if date_str is not None:
            datetime.datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
            return True
        else:
            return False
    except ValueError:
        return False


def calc_time(u_timestamp):
    passed_hours = 0
    passed_minutes = 0
    if u_timestamp > 86400:
        while (u_timestamp / 86400) >= 1:
            u_timestamp = u_timestamp - 86400
            passed_hours += 24

        while (u_timestamp / 3600) >= 1:
            u_timestamp = u_timestamp - 3600
            passed_hours += 1

        while (u_timestamp / 60) >= 1:
            u_timestamp = u_timestamp - 60
            passed_minutes += 1

    else:
        while (u_timestamp / 3600) >= 1:
            u_timestamp = u_timestamp - 3600
            passed_hours += 1

        while (u_timestamp / 60) >= 1:
            u_timestamp = u_timestamp - 60
            passed_minutes += 1

    return f"{passed_hours:0>{2}}:{passed_minutes:0>{2}}:{u_timestamp:0>{2}}"


def duration_ingest_dataframe(dataframe_param):
    ############################################################################
    # Creating a dataframe for done results from ingested raw dataframe
    if os.path.exists(f"{PARQUET_PATH}/duration_ingest_done"):
        load_duration_ingested_done = spark.load_parquet(
            f"{PARQUET_PATH}/duration_ingest_done"
        )
        load_duration_ingested_done_logname = (
            load_duration_ingested_done.select("log_dataset")
            .distinct()
            .collect()
        )
        load_duration_ingested_done_logname_list = []
        for (
            load_duration_ingested_done_logname_item
        ) in load_duration_ingested_done_logname:
            load_duration_ingested_done_logname_list.append(
                load_duration_ingested_done_logname_item["log_dataset"]
            )
        dataframe_param_collect = dataframe_param.collect()
        if (
            dataframe_param_collect[0]["log_dataset"]
            not in load_duration_ingested_done_logname_list
        ):
            try:
                df_duration_ingest_done = (
                    dataframe_param.select(
                        "sysname",
                        "log_dataset",
                        "pre_ipl",
                        "shutdown_begin",
                        "shutdown_end",
                        "ipl_begin",
                        "ipl_end",
                        "post_ipl",
                    )
                    .withColumn(
                        "valid_shutdown_begin",
                        is_datetime_udf(col("shutdown_begin")),
                    )
                    .withColumn(
                        "valid_shutdown_end",
                        is_datetime_udf(col("shutdown_end")),
                    )
                    .withColumn(
                        "valid_ipl_begin", is_datetime_udf(col("ipl_begin"))
                    )
                    .withColumn(
                        "valid_ipl_end", is_datetime_udf(col("ipl_end"))
                    )
                    .filter(
                        (col("valid_shutdown_begin") == True)
                        & (col("valid_shutdown_end") == True)
                        & (col("valid_ipl_begin") == True)
                        & (col("valid_ipl_end") == True)
                    )
                    .drop("valid_shutdown_begin")
                    .drop("valid_shutdown_end")
                    .drop("valid_ipl_begin")
                    .drop("valid_ipl_end")
                    .withColumn(
                        "shutdown_begin_timestamp",
                        unix_timestamp(
                            col("shutdown_begin"), "yyyy-M-d HH:mm:ss"
                        ),
                    )
                    .withColumn(
                        "shutdown_end_timestamp",
                        unix_timestamp(
                            col("shutdown_end"), "yyyy-M-d HH:mm:ss"
                        ),
                    )
                    .withColumn(
                        "ipl_begin_timestamp",
                        unix_timestamp(col("ipl_begin"), "yyyy-M-d HH:mm:ss"),
                    )
                    .withColumn(
                        "ipl_end_timestamp",
                        unix_timestamp(col("ipl_end"), "yyyy-M-d HH:mm:ss"),
                    )
                    .withColumn(
                        "shutdown_duration",
                        calc_time_udf(
                            col("shutdown_end_timestamp")
                            - col("shutdown_begin_timestamp")
                        ),
                    )
                    .withColumn(
                        "poweroff_duration",
                        calc_time_udf(
                            col("ipl_begin_timestamp")
                            - col("shutdown_end_timestamp")
                        ),
                    )
                    .withColumn(
                        "loadipl_duration",
                        calc_time_udf(
                            col("ipl_end_timestamp")
                            - col("ipl_begin_timestamp")
                        ),
                    )
                    .withColumn(
                        "total_time",
                        calc_time_udf(
                            col("ipl_end_timestamp")
                            - col("shutdown_begin_timestamp")
                        ),
                    )
                    .drop("shutdown_begin_timestamp")
                    .drop("shutdown_end_timestamp")
                    .drop("ipl_begin_timestamp")
                    .drop("ipl_end_timestamp")
                )
                spark.append_to_parquet(
                    df_duration_ingest_done,
                    f"{PARQUET_PATH}/duration_ingest_done",
                )
            except Exception as error:
                print(str(error))
            print(
                f"{dataframe_param_collect[0]['log_dataset']} was sucessfully ingested into {PARQUET_PATH}/duration_ingest_done parquet file."
            )
        else:
            print(
                f"{dataframe_param_collect[0]['log_dataset']} already exist into {PARQUET_PATH}/duration_ingest_done parquet file."
            )
    else:
        try:
            df_duration_ingest_done = (
                dataframe_param.select(
                    "sysname",
                    "log_dataset",
                    "pre_ipl",
                    "shutdown_begin",
                    "shutdown_end",
                    "ipl_begin",
                    "ipl_end",
                    "post_ipl",
                )
                .withColumn(
                    "valid_shutdown_begin",
                    is_datetime_udf(col("shutdown_begin")),
                )
                .withColumn(
                    "valid_shutdown_end",
                    is_datetime_udf(col("shutdown_end")),
                )
                .withColumn(
                    "valid_ipl_begin", is_datetime_udf(col("ipl_begin"))
                )
                .withColumn("valid_ipl_end", is_datetime_udf(col("ipl_end")))
                .filter(
                    (col("valid_shutdown_begin") == True)
                    & (col("valid_shutdown_end") == True)
                    & (col("valid_ipl_begin") == True)
                    & (col("valid_ipl_end") == True)
                )
                .drop("valid_shutdown_begin")
                .drop("valid_shutdown_end")
                .drop("valid_ipl_begin")
                .drop("valid_ipl_end")
                .withColumn(
                    "shutdown_begin_timestamp",
                    unix_timestamp(col("shutdown_begin"), "yyyy-M-d HH:mm:ss"),
                )
                .withColumn(
                    "shutdown_end_timestamp",
                    unix_timestamp(col("shutdown_end"), "yyyy-M-d HH:mm:ss"),
                )
                .withColumn(
                    "ipl_begin_timestamp",
                    unix_timestamp(col("ipl_begin"), "yyyy-M-d HH:mm:ss"),
                )
                .withColumn(
                    "ipl_end_timestamp",
                    unix_timestamp(col("ipl_end"), "yyyy-M-d HH:mm:ss"),
                )
                .withColumn(
                    "shutdown_duration",
                    calc_time_udf(
                        col("shutdown_end_timestamp")
                        - col("shutdown_begin_timestamp")
                    ),
                )
                .withColumn(
                    "poweroff_duration",
                    calc_time_udf(
                        col("ipl_begin_timestamp")
                        - col("shutdown_end_timestamp")
                    ),
                )
                .withColumn(
                    "loadipl_duration",
                    calc_time_udf(
                        col("ipl_end_timestamp") - col("ipl_begin_timestamp")
                    ),
                )
                .withColumn(
                    "total_time",
                    calc_time_udf(
                        col("ipl_end_timestamp")
                        - col("shutdown_begin_timestamp")
                    ),
                )
                .drop("shutdown_begin_timestamp")
                .drop("shutdown_end_timestamp")
                .drop("ipl_begin_timestamp")
                .drop("ipl_end_timestamp")
            )

            spark.append_to_parquet(
                df_duration_ingest_done,
                f"{PARQUET_PATH}/duration_ingest_done",
            )
        except Exception as error:
            print(str(error))
        print(
            f"New done dataframe was sucessfully ingested into {PARQUET_PATH}/duration_ingest_done parquet file."
        )

    ############################################################################
    # Creating a dataframe for fail results from ingested raw dataframe
    if os.path.exists(f"{PARQUET_PATH}/duration_ingest_fail"):
        load_duration_ingested_fail = spark.load_parquet(
            f"{PARQUET_PATH}/duration_ingest_fail"
        )
        load_duration_ingested_fail_logname = (
            load_duration_ingested_fail.select("log_dataset")
            .distinct()
            .collect()
        )
        load_duration_ingested_fail_logname_list = []
        for (
            load_duration_ingested_fail_logname_item
        ) in load_duration_ingested_fail_logname:
            load_duration_ingested_fail_logname_list.append(
                load_duration_ingested_fail_logname_item["log_dataset"]
            )
        dataframe_param_collect = dataframe_param.collect()
        if (
            dataframe_param_collect[0]["log_dataset"]
            not in load_duration_ingested_fail_logname_list
        ):
            try:
                df_duration_ingest_fail = (
                    dataframe_param.select(
                        "sysname",
                        "log_dataset",
                        "pre_ipl",
                        "shutdown_begin",
                        "shutdown_end",
                        "ipl_begin",
                        "ipl_end",
                        "post_ipl",
                        "last_ipl",
                    )
                    .withColumn(
                        "valid_shutdown_begin",
                        is_datetime_udf(col("shutdown_begin")),
                    )
                    .withColumn(
                        "valid_shutdown_end",
                        is_datetime_udf(col("shutdown_end")),
                    )
                    .withColumn(
                        "valid_ipl_begin", is_datetime_udf(col("ipl_begin"))
                    )
                    .withColumn(
                        "valid_ipl_end", is_datetime_udf(col("ipl_end"))
                    )
                    .withColumn(
                        "valid_last_ipl", is_datetime_udf(col("last_ipl"))
                    )
                    .filter(
                        (col("valid_shutdown_begin") == False)
                        | (col("valid_shutdown_end") == False)
                        | (col("valid_ipl_begin") == False)
                        | (col("valid_ipl_end") == False)
                    )
                    .filter((col("valid_last_ipl") == False))
                    .drop("valid_shutdown_begin")
                    .drop("valid_shutdown_end")
                    .drop("valid_ipl_begin")
                    .drop("valid_ipl_end")
                    .drop("valid_last_ipl")
                )
                spark.append_to_parquet(
                    df_duration_ingest_fail,
                    f"{PARQUET_PATH}/duration_ingest_fail",
                )
            except Exception as error:
                print(str(error))
            print(
                f"{dataframe_param_collect[0]['log_dataset']} was sucessfully ingested into {PARQUET_PATH}/duration_ingest_fail parquet file."
            )
        else:
            print(
                f"{dataframe_param_collect[0]['log_dataset']} already exist into {PARQUET_PATH}/duration_ingest_fail parquet file."
            )
    else:
        try:
            df_duration_ingest_fail = (
                dataframe_param.select(
                    "sysname",
                    "log_dataset",
                    "pre_ipl",
                    "shutdown_begin",
                    "shutdown_end",
                    "ipl_begin",
                    "ipl_end",
                    "post_ipl",
                    "last_ipl",
                )
                .withColumn(
                    "valid_shutdown_begin",
                    is_datetime_udf(col("shutdown_begin")),
                )
                .withColumn(
                    "valid_shutdown_end",
                    is_datetime_udf(col("shutdown_end")),
                )
                .withColumn(
                    "valid_ipl_begin", is_datetime_udf(col("ipl_begin"))
                )
                .withColumn("valid_ipl_end", is_datetime_udf(col("ipl_end")))
                .withColumn("valid_last_ipl", is_datetime_udf(col("last_ipl")))
                .filter(
                    (col("valid_shutdown_begin") == False)
                    | (col("valid_shutdown_end") == False)
                    | (col("valid_ipl_begin") == False)
                    | (col("valid_ipl_end") == False)
                )
                .filter((col("valid_last_ipl") == False))
                .drop("valid_shutdown_begin")
                .drop("valid_shutdown_end")
                .drop("valid_ipl_begin")
                .drop("valid_ipl_end")
                .drop("valid_last_ipl")
            )

            spark.append_to_parquet(
                df_duration_ingest_fail,
                f"{PARQUET_PATH}/duration_ingest_fail",
            )
        except Exception as error:
            print(str(error))
        print(
            f"New fail dataframe was sucessfully ingested into {PARQUET_PATH}/duration_ingest_fail parquet file."
        )

    ############################################################################
    # Creating a dataframe for last IPL results from ingested raw dataframe
    if os.path.exists(f"{PARQUET_PATH}/duration_ingest_last_ipl"):
        load_duration_ingested_last_ipl = spark.load_parquet(
            f"{PARQUET_PATH}/duration_ingest_last_ipl"
        )
        load_duration_ingested_last_ipl_logname = (
            load_duration_ingested_last_ipl.select("log_dataset")
            .distinct()
            .collect()
        )
        load_duration_ingested_last_ipl_logname_list = []
        for (
            load_duration_ingested_last_ipl_logname_item
        ) in load_duration_ingested_last_ipl_logname:
            load_duration_ingested_last_ipl_logname_list.append(
                load_duration_ingested_last_ipl_logname_item["log_dataset"]
            )

        dataframe_param_collect = dataframe_param.collect()
        if (
            dataframe_param_collect[0]["log_dataset"]
            not in load_duration_ingested_last_ipl_logname_list
        ):
            try:
                df_duration_ingest_last_ipl = (
                    dataframe_param.select(
                        "sysname",
                        "log_dataset",
                        "last_ipl",
                    )
                    .withColumn(
                        "valid_last_ipl", is_datetime_udf(col("last_ipl"))
                    )
                    .filter((col("valid_last_ipl") == True))
                    .drop("valid_last_ipl")
                    .distinct()
                    .sort("sysname", "last_ipl")
                )
                spark.append_to_parquet(
                    df_duration_ingest_last_ipl,
                    f"{PARQUET_PATH}/duration_ingest_last_ipl",
                )
            except Exception as error:
                print(str(error))
            print(
                f"{dataframe_param_collect[0]['log_dataset']} was sucessfully ingested into {PARQUET_PATH}/duration_ingest_last_ipl parquet file."
            )
        else:
            print(
                f"{dataframe_param_collect[0]['log_dataset']} already exist into {PARQUET_PATH}/duration_ingest_last_ipl parquet file."
            )
    else:
        try:
            df_duration_ingest_last_ipl = (
                dataframe_param.select(
                    "sysname",
                    "log_dataset",
                    "last_ipl",
                )
                .withColumn("valid_last_ipl", is_datetime_udf(col("last_ipl")))
                .filter((col("valid_last_ipl") == True))
                .drop("valid_last_ipl")
                .distinct()
                .sort("sysname", "last_ipl")
            )

            spark.append_to_parquet(
                df_duration_ingest_last_ipl,
                f"{PARQUET_PATH}/duration_ingest_last_ipl",
            )
        except Exception as error:
            print(str(error))
        print(
            f"New last IPL dataframe was sucessfully ingested into {PARQUET_PATH}/duration_ingest_last_ipl parquet file."
        )


spark = SparkHandle("zplatipld")
################################################################################
# Register User Function on Spark
is_datetime_udf = udf(is_datetime, BooleanType())
calc_time_udf = udf(calc_time, StringType())

################################################################################
# Load all results to a raw dataframe on spark and persist it to a parquet file
if os.path.exists(f"{PARQUET_PATH}/raw_dataframe"):
    load_raw_dataframe = spark.load_parquet(f"{PARQUET_PATH}/raw_dataframe")
    load_raw_dataframe_logname = (
        load_raw_dataframe.select("log_dataset").distinct().collect()
    )

    load_raw_dataframe_logname_list = []
    for load_raw_dataframe_logname_item in load_raw_dataframe_logname:
        load_raw_dataframe_logname_list.append(
            load_raw_dataframe_logname_item["log_dataset"]
        )

    load_results_csv = find_csv(CSV_RESULTS_PATH)

    for csv_result_key, csv_result_path in load_results_csv.items():
        try:
            csv_dataframe = spark.load_csv_to_dataframe(csv_result_path)
            csv_dataframe_collect = csv_dataframe.collect()
            for csv_dataframe_collect_row in csv_dataframe_collect:
                if (
                    csv_dataframe_collect_row["log_dataset"]
                    not in load_raw_dataframe_logname_list
                ):
                    csv_dataframe_collect_row_df = spark.createRowDataFrame(
                        [csv_dataframe_collect_row], schema=DF_SCHEMA
                    )
                    spark.append_to_parquet(
                        csv_dataframe_collect_row_df,
                        f"{PARQUET_PATH}/raw_dataframe",
                    )
                    print(
                        f"{csv_dataframe_collect_row['log_dataset']} \
                            was sucessfully ingested into \
                                {PARQUET_PATH}/raw_dataframe parquet file."
                    )
                    print("- Processing dataframes:")
                    duration_ingest_dataframe(csv_dataframe_collect_row_df)
                else:
                    print(
                        f"{csv_dataframe_collect_row['log_dataset']} \
                            already exist into \
                                {PARQUET_PATH}/raw_dataframe parquet file."
                    )
        except Exception as error:
            print(str(error))


else:
    load_results_csv = find_csv(CSV_RESULTS_PATH)

    for csv_result_key, csv_result_path in load_results_csv.items():
        try:
            csv_dataframe = spark.load_csv_to_dataframe(csv_result_path)
            csv_dataframe_collect = csv_dataframe.collect()
            for csv_dataframe_collect_row in csv_dataframe_collect:
                csv_dataframe_collect_row_df = spark.createRowDataFrame(
                    [csv_dataframe_collect_row], schema=DF_SCHEMA
                )
                spark.append_to_parquet(
                    csv_dataframe_collect_row_df,
                    f"{PARQUET_PATH}/raw_dataframe",
                )
                print(
                    f"{csv_dataframe_collect_row['log_dataset']} \
                        was sucessfully ingested into \
                            {PARQUET_PATH}/raw_dataframe parquet file."
                )
                duration_ingest_dataframe(csv_dataframe_collect_row_df)

        except Exception as error:
            print(str(error))


spark.close_spark_session()
