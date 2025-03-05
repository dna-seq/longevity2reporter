import json

from cravat.cravat_report import CravatReport
import sys
import datetime
import re
import csv
import zipfile
import json
from pathlib import Path
import sqlite3
from mako.template import Template
from mako import exceptions
import requests

class Reporter(CravatReport):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.savepath = kwargs["savepath"]
        self.output_dir = kwargs["output_dir"]

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

    def llm_final_call(self, list_of_summarization):
        url = "http://0.0.0.0:8088/v1/chat/completions"

        prompt = """
                    You will be provided with a texts of summarizations of different parts of the genetical report.
                    You will have to provide a final summary of the report.
                    It should be consize, underline the most important for the person infromation related to their health and longevity.
                    Also make final conclusions and recommendations. Underline the main risks that the persons carries and how the can be avoided and prevented.
                    Do not just make a list of rsids. You should summarize all the information as a text that is written in an understandable manner so
                    the people who doesn't know much about genetics understood. Do not copy the structure of summarization from the texts provided to you,
                    stick to the prompt that just provided to you. Be especially detailed on prevention measurements. Do not write big lists with genotypes
                    and small description of them. It has already been done in those small summarization. The summarization that you should do will be the final in the report.
                    It should be a summary of all the information that was provided to you. It should be relatively short, understandable for everyone.
                    Always make information clear, talk only about genes and genotypes that were provided to you, It should be clear, that you provide
                    the summarization of the information of the genotypes and genes and their significance that were provided to you in the report.
                    In your answer do not write the header of the whole text, for example, do not write "Personalized Genomic Report Analysis".
                    Do not ask follow-up questions. Do not ask if the user understood the provided information or not.
                    Also you should write your answer in HTML formatting. For small headers use tag <h3> with class="small-headers".
                    When you want to provide a link you should use html tag <a> with "href" attribute where you place the link.
                    If you want to make some of the text emphasized use <b> tag. Do not forget to divid information in different paragraphs so it looks
                    better in HTML page. Never forget to close tags. Your answer will be inserted in already existing HTML page. So make sure to format
                    it accordingly for this purpose. Everything should be wrapped in tags. If you don't know what tag to use for the main text, use <p> tag.
                    Please use the following "summ" class for the div tag that you use to wrap the whole your answer. Here is the list of texts of summarization:
                 """

        text_for_request = prompt + str(list_of_summarization)

        json_api_openai = {'model': 'gpt-4o',
                        'messages': [{'role': 'system', 'content': 'You are a helpful assistant.'},
                                        {'role': 'user', 'content': [{'type': 'text', 'text': text_for_request}]}
                                        ],
                            'stream': False,
                            'max_tokens': 50000,
                            'stop': ['[DONE]'],
                            'temperature': 0}
        try:
            answer = requests.post(url, json=json_api_openai)
        except:
            print(f"Can't make request to {url}")

        answer = answer.json()
        answer = answer["choices"][0]["message"]["content"]
        return answer

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
        data["summarization"] = {}

        summarization_file = Path(self.output_dir, "output.json")
        with open(summarization_file,"r") as file:
            items = json.load(file)
            modules_summarized = []
            list_of_summarizations = []
            for item in items[1:]:
                keys = item.keys()
                key = list(keys)[0]
                data["summarization"][key] = item[key]
                modules_summarized.append(key)
                list_of_summarizations.append(item[key])
            print("Modules that have been summarized: " + str(modules_summarized))

        data["summarization"]["final_sum"] = self.llm_final_call(list_of_summarizations)

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