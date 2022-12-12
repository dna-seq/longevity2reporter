import json

from cravat.cravat_report import CravatReport
import sys
import datetime
import re
import csv
import zipfile
from pathlib import Path
import sqlite3
from mako.template import Template

class Reporter(CravatReport):

    def __init__(self, args):
        super().__init__(args)
        self.savepath = args['savepath']


    async def run(self):
        self.setup()
        self.write_data()
        self.end()
        pass


    def setup(self):
        self.input_database_path = f'{self.savepath}_longevity.sqlite'
        self.db_conn = sqlite3.connect(self.input_database_path)
        self.db_cursor = self.db_conn.cursor()
        outpath = f'{self.savepath}.longevity2.html'
        self.outfile = open(outpath, 'w', encoding='utf-8')
        cur_path = str(Path(__file__).parent)
        self.template = Template(filename=str(Path(__file__).parent)+"/template.html")


    def write_table(self, name, json_fields = [], sort_field = "", sort_revers = False):
        try:
            sort_sql = ""
            if sort_field != "":
                sort_sql = " ORDER BY " + sort_field
                if sort_revers:
                    sort_sql = sort_sql+" DESC"
                else:
                    sort_sql = sort_sql+" ASC"

            self.db_cursor.execute("SELECT * FROM "+name+sort_sql)
            rows = self.db_cursor.fetchall()
            res = []

            for row in rows:
                tmp = {}
                for i, item in enumerate(self.db_cursor.description):
                    if item[0] in json_fields:
                        lst = json.loads(row[i])
                        if len(lst) == 0:
                            tmp[item[0]] = ""
                        else:
                            tmp[item[0]] = lst[0]
                    else:
                        tmp[item[0]] = row[i]
                res.append(tmp)
            self.data[name] = res
        except Exception as e:
            print("Warning:", e)


    def write_data(self):
        # self.data = {"test1":[1,2,3], "test2":["aa", "bbb", "cccc"]}
        self.data = {}
        self.write_table("prs", [], "id", True)
        self.write_table("longevitymap", ["conflicted_rows", "description"], "weight", False)
        self.write_table("cancer", [], "id", True)
        self.write_table("coronary", [], "weight", False)
        self.write_table("drugs", [], "id", True)


    def end(self):
        self.outfile.write(self.template.render(data=self.data))
        self.outfile.close()
        return Path(self.outfile.name).resolve()


### Don't edit anything below here ###
def main():
    reporter = Reporter(sys.argv)
    reporter.run()


if __name__ == '__main__':
    main()