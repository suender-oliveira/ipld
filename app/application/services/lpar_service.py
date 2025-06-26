"""
Provides services related to managing logical partitions (LPARs).

Classes:
    LparService: Responsible for creating, updating, and retrieving LPAR data.
"""

from app.application.dtos import LparCreateDTO, LparUpdateDTO
from app.domain.entities import Lpar
from app.domain.repositories import ILparRepository


class LparService:
    """
    Class responsible for managing logical partitions (LPARs) in a system.
    """

    def __init__(self, lpar_repo: ILparRepository) -> None:
        """
        Initializes the LparService class with a reference to
            an ILparRepository object.

        Args:
            lpar_repo (ILparRepository): The repository responsible for
                storing and retrieving LPAR data.
        """
        self.lpar_repo = lpar_repo

    def create_lpar(self, dto: LparCreateDTO) -> Lpar | None:
        """
        Creates a new logical partition (LPAR) based on the provided DTO.

        Args:
            dto (LparCreateDTO): The data transfer object containing
                the information to create the LPAR.

        Returns:
            Lpar | None: The created LPAR, or None if an existing LPAR with
                the same hostname already exists.
        """

        existing_lpar = self.lpar_repo.find(
            criteria={"hostname": dto.hostname}
        )

        if existing_lpar:
            return None

        new_lpar = Lpar(
            id=None,
            lpar=dto.lpar,
            hostname=dto.hostname,
            dataset=dto.dataset,
            username=dto.username,
            enable=1,
            schedule=None,
        )

        return self.lpar_repo.create(new_lpar)

    def get_all_lpars(self) -> list[Lpar]:
        """
        Returns a list of all LPARs in the system.

        Args:
            self (LparRepository): The instance of the LparRepository class.

        Returns:
            list[Lpar]: A list of Lpar objects representing all LPARs in
                the system.
        """

        return self.lpar_repo.get_all()

    def get_enabled_lpars(self) -> list[Lpar]:
        """
        Returns a list of enabled LPARs.

        Parameters:
        - None

        Returns:
        - A list of LPAR objects that are currently enabled.
        """

        return self.lpar_repo.find(criteria={"enable": 1})

    def get_lpar_by_id(self, lpar_id: int) -> Lpar | None:
        """
        Returns an LPAR object from the repository based on the provided ID.

        Parameters:
            lpar_id (int): The unique identifier of the LPAR to retrieve.

        Returns:
            Lpar | None: The LPAR object with the matching ID, or None if
                no LPAR is found.
        """

        return self.lpar_repo.get_by_id(lpar_id)

    def update_lpar(self, dto: LparUpdateDTO) -> Lpar | None:
        """
        Updates an existing LPAR with the provided DTO.

        Args:
            dto (LparUpdateDTO): The DTO containing the updated
                LPAR information.

        Returns:
            Lpar | None: The updated LPAR object if successful, otherwise None.
        """

        lpar_to_update = self.lpar_repo.get_by_id(dto.id)

        if not lpar_to_update:
            return None

        lpar_to_update.lpar = dto.lpar
        lpar_to_update.hostname = dto.hostname
        lpar_to_update.dataset = dto.dataset
        lpar_to_update.username = dto.username
        lpar_to_update.enable = dto.enable
        lpar_to_update.schedule = dto.schedule

        return self.lpar_repo.update()
