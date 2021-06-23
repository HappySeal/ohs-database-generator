import requests as rq
from bs4 import BeautifulSoup as bs
import os
from getpass import getpass
import sqlite3 as sql

true = True
false = False
null = None


class Collector:
    s = rq.Session()
    headers = {
        "Content-Type": "application/x-www-form-urlencoded"
    }
    mp = None
    a_dict = {}
    db = sql.connect("main.db")
    db_cursor = db.cursor()

    def __init__(self, uuid, password):
        self.merge_existing_databases()
        self.mp = self.login(uuid, password)
        print(self.s.cookies)

    def merge_existing_databases(self):
        self.db.execute("CREATE TABLE IF NOT EXISTS Answer_Table (question,answer,chapter)")

        dbs = [d for d in os.listdir() if len(d.split(".")) == 2]
        dbs = list(filter(lambda x: x.split(".")[1] == "db" and x.split(".")[0] != "main",dbs))
        for ddb in dbs:
            dddb = sql.connect(ddb)
            dddb_cursor = dddb.cursor()
            dddb_cursor.execute("SELECT * FROM Answer_Table")

            output = dddb_cursor.fetchall()
            for row in output:
                self.db_cursor.execute('SELECT * FROM Answer_Table WHERE (question=? AND answer=? AND chapter=?)',
                                       tuple(row))
                entry = self.db_cursor.fetchone()
                if entry is None:
                    self.db_cursor.execute("INSERT INTO Answer_Table (question,answer,chapter) VALUES (?,?,?)",
                                           tuple(row))
                    self.db.commit()

    def login(self, username, password):
        request = self.s.get("https://odtuclass.metu.edu.tr/")
        soup = bs(request.content, "html.parser")
        token = soup.find("input", {"name": "logintoken"})["value"]

        container = f"username={username}" \
                    f"&password={password}" \
                    f"&logintoken={token}"

        postRQ = self.s.post("https://odtuclass.metu.edu.tr/login/index.php", data=container, allow_redirects=False,
                             headers=self.headers)

        self.s.get(postRQ.headers["Location"], allow_redirects=False, headers=self.headers)

        mainPage = self.s.get("https://odtuclass.metu.edu.tr/course/view.php?id=4795")

        return mainPage

    def get_quizes(self):
        soup = bs(self.mp.content, "html.parser")
        return [x.a.get("href") for x in soup.find_all("li", {"class": "quiz"}) if
                x.a and (x.a.get("class") == ["aalink"])]

    def get_review_link(self, quiz):
        sp = self.s.get(quiz)
        soup = bs(sp.content, "html.parser")
        return soup.find("tr", {"class": "lastrow"}).find("td", {"class": "lastcol"}).find("a").get("href")

    def get_questions(self, rwl):
        rwp = self.s.get(rwl)
        soup = bs(rwp.content, "html.parser")
        chapter = soup.find_all("li", ({"class": "breadcrumb-item"}))[-2].text.strip("\n")
        print(chapter)

        for x in soup.find("form").find_all("div", {"class": "correct"}):
            if x.find("div", {"class": "content"}):
                question = x.find("div", {"class": "qtext"}).text
                try:
                    answer = x.find("div", {"class": "correct"}).find(class_="ml-1").text
                except AttributeError:
                    answer = x.find("select",{"class":"correct"}).find("option",{"selected":"selected"}).text

                self.a_dict[question] = answer
                self.db_cursor.execute('SELECT * FROM Answer_Table WHERE (question=? AND answer=? AND chapter=?)',
                                       (question, answer, chapter))
                entry = self.db_cursor.fetchone()
                if entry is None:
                    self.db_cursor.execute("INSERT INTO Answer_Table (question,answer,chapter) VALUES (?,?,?)",
                                           (question, answer, chapter))
                    self.db.commit()


if __name__ == "__main__":
    user_id = input("Enter your user ID: ")
    password = input("Enter your password: ")

    bot = Collector(user_id, password)

    for q in bot.get_quizes():
        print(q)
        bot.get_questions(bot.get_review_link(q))

    print(bot.a_dict)
