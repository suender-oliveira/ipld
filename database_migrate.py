import sqlalchemy_sqlite
import sqlite3

database01 = "ipld_db_lpar.db"
table = "lpar"

database_connection_01 = sqlite3.connect(f"/zplatipld/Database/{database01}")
database01_cursor = database_connection_01.cursor()
result_from_database01 = database01_cursor.execute(
    f"select * from {table}"
)
for i in result_from_database01:
    lpar = i[1]
    hostname = i[2]
    dataset = i[3]
    username = i[4]
    enable = i[5]
    dict_mount = {
        "lpar": lpar,
        "hostname": hostname,
        "dataset": dataset,
        "username": username,
        "enable":enable,
    }
    # print(f"{dict_mount}")
    print(f"insert into lpar (lpar,hostname,dataset,username,enable) values('{lpar}','{hostname}','{dataset}','{username}','{enable}');")


