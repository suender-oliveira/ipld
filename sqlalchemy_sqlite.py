from sqlalchemy import create_engine, Column, Integer, String, Text, and_
from sqlalchemy.orm import sessionmaker, declarative_base, load_only
from sqlalchemy.sql import text, column

Base = declarative_base()


class Lpar(Base):
    __tablename__ = "lpar"
    id = Column(Integer, primary_key=True)
    lpar = Column(String)
    hostname = Column(String)
    dataset = Column(String)
    username = Column(String)
    enable = Column(Integer)
    schedule = Column(String)


class Users(Base):
    __tablename__ = "user"
    id = Column(Integer, primary_key=True)
    username = Column(String)
    password = Column(String)
    name = Column(String)
    last_name = Column(String)
    approved = Column(Integer)


class Vault(Base):
    __tablename__ = "vault"
    id = Column(Integer, primary_key=True)
    username = Column(String)
    private_key = Column(Text)
    public_key = Column(Text)


class ResultsDoneTable(Base):
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


class ResultsFailTable(Base):
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


class ResultsGarbTable(Base):
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


class ResultsLastIplTable(Base):
    __tablename__ = "results_last_ipl"
    id = Column(Integer, primary_key=True)
    sysname = Column(String)
    log_dataset = Column(String)
    last_ipl = Column(String)


class CrudDB:
    def __init__(self, db_url) -> None:
        self.engine = create_engine(db_url)
        Base.metadata.create_all(self.engine)
        session_obj = sessionmaker(bind=self.engine)
        self.session = session_obj()

    def init_database(self):
        Base.metadata.create_all(self.engine)
        return True

    def create_table(self, table_name, columns, with_id=None):
        class DynamicTable(Base):
            __tablename__ = table_name
            if with_id:
                id = Column(Integer, primary_key=True)
            for column_name, column_type in columns.items():
                locals()[column_name] = Column(column_type)

        Base.metadata.create_all(self.engine)
        return DynamicTable

    def create(self, table, data):
        record = table(**data)
        self.session.add(record)
        self.session.commit()
        return record

    def read(self, table, distinct=None, condition=None, in_values=None):
        if distinct:
            return (
                self.session.query(table)
                .distinct()
                .group_by(text(distinct))
                .all()
            )
        elif distinct and condition:
            return (
                self.session.query(table).distinct().filter_by(condition).all()
            )
        elif condition:
            filter_conditions = [
                getattr(table, field) == value
                for field, value in condition.items()
            ]
            return (
                self.session.query(table).filter(and_(*filter_conditions)).all()
            )
        elif in_values:
            for field, values in in_values.items():
                filter_condition = getattr(table, field).in_(values)
            return self.session.query(table).filter(filter_condition).all()
        else:
            return self.session.query(table).all()

    def update(self, table, record_id, data):
        record = self.read(table, condition=record_id)
        if record:
            for key, value in data.items():
                setattr(record[0], key, value)
            self.session.commit()
            return record[0]
        return None

    def delete(self, table, record_id):
        record = self.read(table, f"id={record_id}")
        if record:
            self.session.delete(record)
            self.session.commit()
            return True
        return False
