"""
Contains repositories for interacting with various data models
in the application's database.
"""

from typing import Any

from sqlalchemy import and_, create_engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import text

from app.infrastructure.persistence.models import (
    Base,
    LparModel,
    ResultsDoneTableModel,
    ResultsFailTableModel,
    ResultsGarbTableModel,
    ResultsLastIplTableModel,
    UserModel,
    VaultModel,
)


class SQLAlchemyRepository:
    """
    A class that provides a high-level interface for interacting with
    a database using SQLAlchemy.
    """

    def __init__(self, db_url: str) -> None:
        """
        Initializes a new instance of the Database class.

        Args:
            db_url (str): The URL of the database.

        Returns:
            None
        """
        self.engine = create_engine(db_url)
        session = sessionmaker(bind=self.engine)
        self.session = session()

    def init_database(self) -> bool:
        """Initializes the database.

        Args:
            self (class instance): The class instance calling the method.

        Returns:
            bool: True if the database was successfully initialized,
                False otherwise.
        """

        try:
            Base.metadata.create_all(self.engine)
        except SQLAlchemyError as sa_error:
            print(f"Error creating tables: {sa_error}")
            return False
        else:
            return True

    def create(self, model: type[Base], data: dict[str, Any]) -> Base:
        """
        Creates a new record in the database.

        Args:
            model (type[Base]): The SQLAlchemy declarative base
                class for the table.
            data (dict[str, Any]): A dictionary of column names and values to
                insert into the table.

        Returns:
            Base: The created record as a SQLAlchemy declarative
                base class instance.
        """

        record = model(**data)
        self.session.add(record)
        self.session.commit()
        return record

    def read(
        self,
        model: type[Base],
        distinct: str | None = None,
        criteria: dict[str, Any] | None = None,
        in_values: dict[str, list[Any]] | None = None,
    ) -> list[Base]:
        """
        Reads records from the database based on the provided parameters.

        Args:
            model (type[Base]): The model class to query.
            distinct (str | None): An optional field name to use for DISTINCT.
            condition (dict[str, Any] | None): A dictionary of field names and
                values to filter by.
            in_values (dict[str, list[Any]] | None): A dictionary of field
                names and lists of values to filter by IN.

        Returns:
            list[Base]: A list of records that match the provided
                parameters.
        """

        query = self.session.query(model)

        if distinct:
            query = query.distinct().group_by(text(distinct))
        if criteria:
            filter_conditions = [
                getattr(model, field) == value
                for field, value in criteria.items()
            ]
            query = query.filter(and_(*filter_conditions))
        if in_values:
            for field, values in in_values.items():
                query = query.filter(getattr(model, field).in_(values))
        return query.all()

    def update(
        self,
        model: type[Base],
        record_id: dict[str, Any],
        data: dict[str, Any],
    ) -> Base | None:
        """
        Updates a record in the database based on the provided record ID and
        data.

        Args:
            model (type[Base]): The SQLAlchemy declarative base
                class for the table to update.
            record_id (dict[str, Any]): A dictionary of column names and values
                that identify the record to update.
            data (dict[str, Any]): A dictionary of column names and new values
            to update the record with.

        Returns:
            Base | None: The updated record as a SQLAlchemy
                declarative base class instance, or None if the record was
                not found.
        """

        record = self.read(model, condition=record_id)

        if record:
            for key, value in data.items():
                setattr(record[0], key, value)
            self.session.commit()
            return record[0]
        return None

    def delete(
        self, model: type[Base], record_id: dict[str, Any]
    ) -> bool | None:
        """Delete a record from the database.

        Args:
            model (type[Base]): The SQLAlchemy declarative base
                class for the table to be deleted.
            record_id (dict[str, Any]): A dictionary containing the primary key
                values for the record to be deleted.

        Returns:
            bool | None: True if the record was successfully deleted, False
            otherwise.
        """

        record = self.read(model, condition=record_id)

        if record:
            self.session.delete(record[0])
            self.session.commit()
            return True
        return False


# For dependency injection
class LparRepository(SQLAlchemyRepository):
    """
    Responsible for managing lpar-related data stored in the 'lpar' table.
    """

    def __init__(self, db_url: str) -> None:
        super().__init__(db_url)
        self.model = LparModel


class UserRepository(SQLAlchemyRepository):
    """
    Responsible for managing user-related data stored in the 'lpar' table.
    """

    def __init__(self, db_url: str) -> None:
        super().__init__(db_url)
        self.model = UserModel

    def find(
        self,
        criteria: dict[str, Any] | None = None,
        in_values: dict[str, list[Any]] | None = None,
    ) -> list[Base]:
        return self.read(self.model, criteria=criteria, in_values=in_values)

    def get_by_id(
        self,
        user_id: int,
    ) -> list[Base]:
        return self.read(self.model, criteria={"id": user_id})

    def get_by_username(
        self,
        username: str,
    ) -> list[Base]:
        return self.read(self.model, criteria={"username": username})

    def get_all(self) -> list:
        return self.read(self.model)


class VaultRepository(SQLAlchemyRepository):
    """
    Responsible for managing user-related data stored in the 'vault' table.
    """

    def __init__(self, db_url: str) -> None:
        super().__init__(db_url)
        self.model = VaultModel


class ResultsDoneRepository(SQLAlchemyRepository):
    """
    Responsible for managing completed results stored in
    the 'results_done' table.
    """

    def __init__(self, db_url: str) -> None:
        super().__init__(db_url)
        self.model = ResultsDoneTableModel


class ResultsFailRepository(SQLAlchemyRepository):
    """
    Responsible for managing failed results stored in
    the 'results_fail' table.
    """

    def __init__(self, db_url: str) -> None:
        super().__init__(db_url)
        self.model = ResultsFailTableModel


class ResultsLastIplRepository(SQLAlchemyRepository):
    """
    Responsible for managing last IPL results stored in
    the 'results_last_ipl' table.
    """

    def __init__(self, db_url: str) -> None:
        super().__init__(db_url)
        self.model = ResultsLastIplTableModel


class ResultsGarbRepository(SQLAlchemyRepository):
    """
    Responsible for managing results stored in
    the 'results_garb' table.
    """

    def __init__(self, db_url: str) -> None:
        super().__init__(db_url)
        self.model = ResultsGarbTableModel
