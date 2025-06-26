"""
Defines repository interfaces for domain entities.
"""

from abc import ABC, abstractmethod
from typing import Any, TypeVar

T = TypeVar("T")  # Define a type variable for generic repo methods


class IRepository(ABC):
    """
    An interface that defines a repository for a specific entity type.
    """

    @abstractmethod
    def create(self, entity: T) -> T:
        """
        Creates a new instance of the specified entity.

        Args:
            entity (T): The entity to be created.

        Returns:
            T: The newly created instance of the entity.
        """
        pass

    @abstractmethod
    def get_by_id(self, entity_id: int) -> T | None:
        """
        Returns the entity with the given ID.

        Args:
            entity_id (int): The ID of the entity to retrieve.

        Returns:
            T | None: The entity with the given ID, or None if no entity
                is found.
        """
        pass

    @abstractmethod
    def get_all(self) -> list[T]:
        """
        Returns a list of all entities.

        Args:
            self (Entity): The entities object.

        Returns:
            list[T]: A list containing all entities.
        """
        pass

    @abstractmethod
    def find(
        self,
        criteria: dict[str, Any],
        in_values: dict[str, list[Any]] | None = None,
    ) -> list[T]:
        """
        Finds records that match the given criteria.

        Args:
            criteria (dict): A dictionary of field names and their
                corresponding values to match against.
            in_values (dict, optional): A dictionary of field names and
                a list of values to check for inclusion. Defaults to None.

        Returns:
            list[T]: A list of matching records.
        """
        pass

    @abstractmethod
    def update(self, entity: T) -> T:
        """
        Updates the given entity in the database.

        Args:
            entity (T): The entity to be updated.

        Returns:
            T: The updated entity.
        """
        pass

    @abstractmethod
    def delete(self, entity_id: int) -> bool:
        """
        Deletes an entity from the database.

        Args:
            entity_id (int): The ID of the entity to be deleted.

        Returns:
            bool: True if the entity was successfully deleted, False otherwise.
        """
        pass


class IUserRepository(IRepository):
    """Interface for a user repository."""

    @abstractmethod
    def get_by_username(self, username: str) -> T | None:
        """
        Get a user by their username.

        Args:
            username (str): The username of the user to retrieve.

        Returns:
            Any | None: The user object if found, otherwise None.
        """
        pass


class ILparRepository(IRepository):
    """
    An interface for retrieving LPARs from a repository.
    """

    @abstractmethod
    def get_lpars(self) -> list | None:
        """
        Retrieves all LPARs from the repository.

        Returns:
            A list of LPAR objects, or None if no LPARs are found.
        """
        pass


class IVaultRepository(IRepository):
    """Interface for interacting with a vault repository.

    This interface defines methods for retrieving private keys from a vault.
    """

    @abstractmethod
    def get_private_key_by_username(self, username: str) -> str | None:
        """Retrieves the private key associated with a given username.

        Args:
            username (str): The username to retrieve the private key for.

        Returns:
            str | None: The private key associated with the username, or
            None if no key is found.
        """
        pass


class IResultsDoneRepository(IRepository):
    """
    Interface for a repository that stores and retrieves results done.
    """

    @abstractmethod
    def get_all_results_done(self) -> list[Any]:
        """
        Returns a list of all results done stored in the repository.

        Args:
            None

        Returns:
            A list of all results done stored in the repository.
        """
        pass


class IResultsFailRepository(IRepository):
    """
    Interface for a repository that provides access to results that have
    failed.
    """

    @abstractmethod
    def get_all_results_fail(self) -> list[Any]:
        """
        Returns a list of all results that have failed.

        Args:
            None

        Returns:
            A list of all results that have failed.
        """
        pass


class IResultsLastIplRepository(IRepository):
    """
    Interface for retrieving all last IPL results.
    """

    @abstractmethod
    def get_all_last_ipl_results(self) -> list[Any]:
        """
        Retrieves all last IPL results from the repository.

        Returns:
            A list of all last IPL results.
        """
        pass
