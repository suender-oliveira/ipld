"""
Defines database models for storing various types of results in
the application's database.
It uses SQLAlchemy as an ORM (Object-Relational Mapping) library to interact
with the database.
"""

from sqlalchemy import Column, Integer, String, Text
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class LparModel(Base):
    """
    Represents a table model for storing LPARs in the database.
    """

    __tablename__ = "lpar"
    id = Column(Integer, primary_key=True)
    lpar = Column(String)
    hostname = Column(String)
    dataset = Column(String)
    username = Column(String)
    enable = Column(Integer)
    schedule = Column(String)


class UserModel(Base):
    """
    Represents a table model for storing users in the database.
    """

    __tablename__ = "user"
    id = Column(Integer, primary_key=True)
    username = Column(String)
    password = Column(String)
    name = Column(String)
    last_name = Column(String)
    approved = Column(Integer)


class VaultModel(Base):
    """
    Represents a table model for storing encrypted secrets results in
    the database.
    """

    __tablename__ = "vault"
    id = Column(Integer, primary_key=True)
    username = Column(String)
    private_key = Column(Text)
    public_key = Column(Text)


class ResultsDoneTableModel(Base):
    """
    Represents a table model for storing completed results in the database.
    """

    __tablename__ = "results_done"
    id = Column(Integer, primary_key=True)
    sysname = Column(String)
    ipl_date = Column(String)
    log_dataset = Column(String)
    shutdown_begin = Column(String)
    shutdown_end = Column(String)
    ipl_begin = Column(String)
    ipl_end = Column(String)
    pre_ipl = Column(String)
    pos_ipl = Column(String)
    shutdown_duration = Column(String)
    poweroff_duration = Column(String)
    load_ipl = Column(String)
    total_duration = Column(String)


class ResultsFailTableModel(Base):
    """
    Represents a table model for storing failed results in the database.
    """

    __tablename__ = "results_fail"
    id = Column(Integer, primary_key=True)
    sysname = Column(String)
    log_dataset = Column(String)
    shutdown_begin = Column(String)
    shutdown_end = Column(String)
    ipl_begin = Column(String)
    ipl_end = Column(String)
    pre_ipl = Column(String)
    pos_ipl = Column(String)


class ResultsGarbTableModel(Base):
    """
    Represents a table model for storing garbaged results in the database.
    """

    __tablename__ = "results_garb"
    id = Column(Integer, primary_key=True)
    sysname = Column(String)
    log_dataset = Column(String)
    shutdown_begin = Column(String)
    shutdown_end = Column(String)
    ipl_begin = Column(String)
    ipl_end = Column(String)
    pre_ipl = Column(String)
    pos_ipl = Column(String)


class ResultsLastIplTableModel(Base):
    """
    Represents a table model for storing the last IPL results in the database.
    """

    __tablename__ = "results_last_ipl"
    id = Column(Integer, primary_key=True)
    sysname = Column(String)
    log_dataset = Column(String)
    last_ipl = Column(String)
