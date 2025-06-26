"""
Contains services related to generating reports.
"""

from typing import Any

from app.application.dtos import ReportFilterDTO
from app.domain.repositories import (
    IResultsDoneRepository,
    IResultsFailRepository,
    IResultsLastIplRepository,
)
from app.infrastructure.ingest.ipl_data_ingest import IPLDataIngestor


class ReportService:
    """
    Application service for retrieving and preparing IPL reports.
    """

    def __init__(
        self,
        results_done_repo: IResultsDoneRepository,
        results_fail_repo: IResultsFailRepository,
        results_last_ipl_repo: IResultsLastIplRepository,
        ipl_data_ingestor: IPLDataIngestor,
    ) -> None:
        """
        Initializes the ResultsProcessor class.

        Args:
            results_done_repo (IResultsDoneRepository): The repository for
                storing successful results.
            results_fail_repo (IResultsFailRepository): The repository for
                storing failed results.
            results_last_ipl_repo (IResultsLastIplRepository): The repository
                for storing the last IPL result.
            ipl_data_ingestor (IPLDataIngestor): The ingestor for retrieving
                IPL data from external sources.

        Returns:
            None
        """

        self.results_done_repo = results_done_repo
        self.results_fail_repo = results_fail_repo
        self.results_last_ipl_repo = results_last_ipl_repo
        self.ipl_data_ingestor = ipl_data_ingestor

    def get_ipl_reports(self, dto: ReportFilterDTO) -> list[dict[str, Any]]:
        """
        Get IPL reports based on the provided filter criteria.

        Parameters:
            dto (ReportFilterDTO): A data transfer object containing
                the filter criteria.

        Returns:
            list[dict[str, Any]]: A list of dictionaries representing
                the IPL reports.

                Each dictionary contains the following keys and values:
                    id (int): The unique identifier of the report.
                    sysname (str): The name of the system.
                    ipl_date (datetime): The date of the IPL.
                    log_dataset (str): The name of the log dataset.
                    pre_ipl (float): The pre-IPL load average.
                    shutdown_begin (datetime): The time when the shutdown
                        began.
                    shutdown_end (datetime): The time when the shutdown ended.
                    ipl_begin (datetime): The time when the IPL began.
                    ipl_end (datetime): The time when the IPL ended.
                    pos_ipl (float): The post-IPL load average.
                    shutdown_duration (int): The duration of the shutdown
                        in seconds.
                    poweroff_duration (int): The duration of the poweroff
                        in seconds.
                    load_ipl (float): The load average during the IPL.
                    total_duration (int): The total duration of the IPL
                        in seconds.

        """

        # 1. Ingest new raw data from CSVs
        systems_with_new_data = self.ipl_data_ingestor.ingest_raw_ipl_data()

        # 2. Process newly ingested raw data into structured tables
        flattened_sysname_list = [
            sys for sublist in systems_with_new_data for sys in sublist
        ]
        unique_sysnames = list(set(flattened_sysname_list))
        if unique_sysnames:
            self.ipl_data_ingestor.ingest_duration_data(unique_sysnames)
        results = []
        if dto.view_type == "done":
            data = self.results_done_repo.get_all()
            for item in data:
                results.append(
                    {
                        "id": item.id,
                        "sysname": item.sysname,
                        "ipl_date": item.ipl_date,
                        "log_dataset": item.log_dataset,
                        "pre_ipl": item.pre_ipl,
                        "shutdown_begin": item.shutdown_begin,
                        "shutdown_end": item.shutdown_end,
                        "ipl_begin": item.ipl_begin,
                        "ipl_end": item.ipl_end,
                        "pos_ipl": item.pos_ipl,
                        "shutdown_duration": item.shutdown_duration,
                        "poweroff_duration": item.poweroff_duration,
                        "load_ipl": item.load_ipl,
                        "total_duration": item.total_duration,
                    }
                )
        elif dto.view_type == "fail":
            data = self.results_fail_repo.get_all()
            for item in data:
                results.append(
                    {
                        "id": item.id,
                        "sysname": item.sysname,
                        "log_dataset": item.log_dataset,
                        "pre_ipl": item.pre_ipl,
                        "shutdown_begin": item.shutdown_begin,
                        "shutdown_end": item.shutdown_end,
                        "ipl_begin": item.ipl_begin,
                        "ipl_end": item.ipl_end,
                        "pos_ipl": item.pos_ipl,
                    }
                )
        elif dto.view_type == "last_ipl":
            data = self.results_last_ipl_repo.get_distinct_last_ipl_results()
            for item in data:
                results.append(
                    {
                        "sysname": item.sysname,
                        "last_ipl": item.last_ipl,
                    }
                )
        return results
