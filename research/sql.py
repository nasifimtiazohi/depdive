import pymysql

database = "updatereview"
import sqlalchemy as db
import pandas as pd
import datetime

engine = db.create_engine("mysql+pymysql://root:@localhost:3306/{}".format(database))


PYMYSQL_DUPLICATE_ERROR = 1062

global_conn = pymysql.connect(
    host="localhost",
    user="root",
    db=database,
    charset="utf8mb4",
    cursorclass=pymysql.cursors.DictCursor,
    autocommit=True,
    local_infile=True,
)


def create_db_connection():
    new_conn = pymysql.connect(
        host="localhost",
        user="root",
        db=database,
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=True,
        local_infile=True,
    )
    return new_conn


def execute(query, arguments=(), get_affected_rowcount=False, connection=global_conn):
    if not connection:  # if no connection has been passed
        connection = global_conn
    with connection.cursor() as cursor:
        cursor.execute(query, arguments)
        results = cursor.fetchall()
        affected_rows = cursor.rowcount
    if get_affected_rowcount:
        return results, affected_rows
    return results


def pd_read_sql(query, connection=global_conn):
    return pd.read_sql(query, connection)


def load_df(table, df):
    cols = get_table_columns(table)
    df = df[cols]  # check if column names are in order, if not rearrange
    df.to_sql(table, engine, if_exists="append", index=False, schema=database)


def get_primary_key_name(table):
    # asserting table name is valid without a space and doesn't already come with ticks around
    assert "`" not in table or " " not in table

    q = "show keys from `{}` where Key_name='Primary';".format(table)
    results = execute(q)
    cols = []
    for item in results:
        cols.append(item["Column_name"])
    return cols


def update_df(table, df, updateColumns):
    cols = get_table_columns(table)
    primaryKeys = get_primary_key_name(table)

    # check if df and updateColumns are valid
    df = df[cols]
    for col in updateColumns:
        if col not in cols:
            raise Exception("columns names to update not valid", col)
    cols = updateColumns
    # make sure primary key is not in cols ->
    cols = [e for e in cols if e not in primaryKeys]

    # construct update query
    q = "update {} set ".format(table)
    for col in cols:
        q += "{} = %s ".format(col)
        if col != cols[-1]:
            q += ", "
    q += "where "
    for col in primaryKeys:
        q += "{} = %s ".format(col)
        if col != primaryKeys[-1]:
            q += "and "
    q += ";"

    totalUpdates = 0  # keep track fof total affected updates

    def update(row):
        nonlocal cols, primaryKeys, q, totalUpdates
        args = []
        for col in cols:
            if pd.isna(row[col]):
                args.append(None)
            else:
                args.append(row[col])
        for col in primaryKeys:
            args.append(row[col])
        args = tuple(args)
        affected_rows = execute(q, args, get_affected_rowcount=True)[1]
        totalUpdates += affected_rows

    df.apply(lambda row: update(row), axis=1)
    return totalUpdates


def get_table_columns(table):
    q = "SHOW COLUMNS FROM {}.{};".format(database, table)
    r = execute(q)
    cols = []
    for row in r:
        cols.append(row["Field"])
    return cols


def convert_datetime_to_sql_format(s):
    return datetime.datetime.strptime(s, "%m/%d/%y").strftime("%y/%m/%d")


if __name__ == "__main__":
    pass
