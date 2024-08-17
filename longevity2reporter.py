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
from mako import exceptions

class Reporter(CravatReport):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.savepath = kwargs["savepath"]


    async def run(self, *args, **kwargs):
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
        self.template = Template(filename=str(Path(__file__).parent / "template.html"))


    def write_table(self, name, json_fields = [], sort_field = "", sort_revers = False):
        try:
            sort_sql = ""
            if sort_field != "":
                sort_sql = " ORDER BY " + sort_field
                if sort_revers:
                    sort_sql = sort_sql+" DESC"
                else:
                    sort_sql = sort_sql+" ASC"

            if name == "longevitymap":
                res = {}
                categories = (
                'other', 'tumor-suppressor', 'inflammation', 'genome_maintenance', 'mitochondria', 'lipids',
                'heat-shock', 'sirtuin', 'insulin', 'antioxidant', 'renin-angiotensin', 'mtor')

                for category in categories:
                    res[category]=[]

                try:
                    self.db_cursor.execute("SELECT * FROM "+name+sort_sql + ", category_name")
                except:
                    print(f"No module just_{name}")
                    return res
                
                rows = self.db_cursor.fetchall()

                for category in categories:
                    for row in rows:
                        tmp = {}
                        if category == row[18]:
                            for i, item in enumerate(self.db_cursor.description):
                                if item[0] in json_fields:
                                    lst = json.loads(row[i])
                                    if len(lst) == 0:
                                        tmp[item[0]] = ""
                                    else:
                                        tmp[item[0]] = lst
                                else:
                                    tmp[item[0]] = row[i]
                            res[category].append(tmp)
                return res

            try:
                self.db_cursor.execute("SELECT * FROM "+name+sort_sql)
            except:
                print(f"No module just_{name}")
                res = []
                return res
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
                            tmp[item[0]] = lst
                    else:
                        tmp[item[0]] = row[i]
                res.append(tmp)
            return res
        except Exception as e:
            print("Warning:", e)

    def write_data(self):
        # self.data = {"test1":[1,2,3], "test2":["aa", "bbb", "cccc"]}
        data = {}
        data["longevitymap"] = self.write_table("longevitymap", ["conflicted_rows", "description"], "weight", False)
        data["cancer"] = self.write_table("cancer", [], "id", True)
        data["coronary"] = self.write_table("coronary", [], "weight", False)
        data["drugs"] = self.write_table("drugs", [], "effect", True)
        data["cardio"] = self.write_table("cardio", [], "id", True)
        data["lipidmetabolism"] = self.write_table("lipid_metabolism", [], "weight", False)
        data["thrombophilia"] = self.write_table("thrombophilia", [], "weight", False)
        data["vo2max"] = self.write_table("vo2max", [], "weight", False)
        try:
            self.outfile.write(self.template.render(data=data))
        except:
            print(exceptions.text_error_template().render())


    def end(self):
        self.outfile.close()
        return Path(self.outfile.name).resolve()


### Don't edit anything below here ###
def main():
    reporter = Reporter(sys.argv)
    reporter.run()


if __name__ == '__main__':
    main()