import os
from pyspark.sql import SparkSession, Row
from dotenv import load_dotenv

load_dotenv()


class SparkHandle:
    def __init__(self, app_name):
        """
        Initialize the Spark application. This is called by : meth : ` __init__ ` to initialize the Spark application.

        @param app_name - The name of the application to be
        """
        self.spark = (
            SparkSession.builder.appName(app_name)
            .master(os.getenv("SPARK_SERVER"))
            .getOrCreate()
        )

    def createDataFrame(self, data, column):
        """
        Create a DataFrame from a list of data. This is a convenience method for Spark's createDataFrame method

        @param data - The data to be converted to a DataFrame
        @param column - The name of the column that will be used to store the data

        @return A : class : ` DataFrame ` with the data from the list of data. The column is specified by the name
        """
        return self.spark.createDataFrame(data, column)

    def createRowDataFrame(self, data, schema=None):
        """
        Create a : class : ` DataFrame ` from a sequence of data. This is equivalent to calling : meth : ` SparkContext. createDataFrame ` with

        @param data - the data to use for the DataFrame
        @param schema - the schema to use for the DataFrame

        @return a : class : ` DataFrame ` that can be used to iterate over the rows of the data in
        """
        return self.spark.createDataFrame(data, schema=schema)

    def load_csv_to_dataframe(self, csv_path):
        """
        Load CSV file into a DataFrame. This is a convenience method for loading a CSV file into a DataFrame.

        @param csv_path - Path to the CSV file. It must be a file or a directory.

        @return Dataframe that contains the CSV file as rows. The columns are the same as the columns in the DataFrame
        """
        data_frame = (
            self.spark.read.option("delimiter", ";")
            .option("header", "true")
            .csv(csv_path)
        )
        return data_frame

    def load_parquet(self, parquet_path):
        """
        Load Parquet file and return a : class : ` DataFrame `. This is a convenience method for

        @param parquet_path - Path to the Parquet file.

        @return Data frame containing the data from the Parquet file. >>> df. load_parquet ('test. txt')
        """
        data_frame = self.spark.read.parquet(parquet_path)
        return data_frame

    def append_to_parquet(self, data_frame, parquet_path):
        """
        Append data to parquet file. This method is used to append data to a data frame. The file is written to a parquet file and can be read by : meth : ` read_parquet `

        @param data_frame - Data frame to be written
        @param parquet_path - Path to the parquet
        """
        data_frame.write.mode("append").parquet(parquet_path)

    def overwrite_parquet(self, data_frame, parquet_path):
        """
        Overwrite data_frame. parquet to parquet_path. This is a destructive operation in order to avoid overwriting the file on disk.

        @param data_frame - Dataframe to be written to disk
        @param parquet_path - Path to write to
        """
        data_frame.write.mode("overwrite").parquet(parquet_path)

    def close_spark_session(self):
        """
        Close the Spark session. This is called when the session is no longer needed to perform operations on the data
        """
        self.spark.stop()
