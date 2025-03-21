import logging
from typing import Optional, Union

import psycopg2
from psycopg2.extensions import connection

logger = logging.getLogger(__name__)


class DBHandler:
    def __init__(self, config):
        self.conn = self.create_connection(config)

    @staticmethod
    def create_connection(config) -> connection:
        try:
            conn = psycopg2.connect(**config)
            logger.info(f"Connected to db {config['database']}")
        except Exception as e:
            logger.error(e)
            raise e
        return conn

    def run_sql(self, sql: str, vars: Optional[Union[dict, tuple]] = None):
        try:
            with self.conn.cursor() as c:
                c = self.conn.cursor()
                c.execute(sql + ";", vars)
                self.conn.commit()
                out = c.fetchall()
            return out
        except Exception as e:
            logger.error(e)
            raise e

    def run_sql_no_return(self, sql: str, vars: Optional[Union[dict, tuple]] = None):
        try:
            with self.conn.cursor() as c:
                c = self.conn.cursor()
                c.execute(sql + ";", vars)
                self.conn.commit()
        except Exception as e:
            logger.error(e)
            raise e

    def insert_row(self, table: str, row_dict: dict):
        query = f"""
            INSERT INTO {table}
            ({str(list(row_dict.keys())).replace("'", "")[1:-1]})
            VALUES
            {"(" + ", ".join(f"%({col})s" for col in row_dict.keys()) + ")"}
        """
        self.run_sql_no_return(query, row_dict)

    # def insert_rows(self, table: str, row_dicts: List[dict]):
    #     query = f"""
    #         INSERT INTO {table}
    #         ({str(list(row_dicts[0].keys())).replace("'", "")[1:-1]})
    #         VALUES
    #         {"(" + "), (".join(", ".join(self.adj_value(value) for value in row.values()) for row in row_dicts) + ")"}
    #     """
    #     return self.run_sql_no_return(query)

    # def adj_value(self, value):
    #     if isinstance(value, dt.datetime):
    #         return value.strftime("TIMESTAMP '%Y-%m-%d %H:%M:%S'")
    #     if isinstance(value, dt.date):
    #         return value.strftime("TIMESTAMP '%Y-%m-%d'")
    #     if isinstance(value, str):
    #         return "'" + value + "'"
    #     return str(value)
