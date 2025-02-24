from stored_data import DiaryRecord, CalendarEvent, DayMeal, Child, User, Expense
from user_graph import Graph
import itertools
import sqlite3
import json
import time
import datetime

# for demo purposes only, entirely disables write to database
READONLY_DEMO_MODE = 0


def sql_query(query, db="nub.db"):
    print("SQL running", query)
    conn = sqlite3.connect(db)
    cursor = conn.cursor()
    cursor.execute(query)
    rows = cursor.fetchall()
    conn.commit()
    conn.close()
    print("SQL result", rows)
    return rows


class DBHandler:
    def __init__(self, dbname):
        self.__dbname = dbname
        self.__graph = Graph()

    def new_diary_record(self, record, childID, nannyID):
        # insert a new diary record
        query = f"INSERT INTO diary (date, data, childID, nannyID) VALUES ({time.time()}, {record}, {childID}, {nannyID});"
        sql_query(query, self.__dbname)

    def get_diary_record(self, key=0, time_range=None, child_id=0, nanny_id=0):

        if time_range is None:
            time_range = [0, 0]
        if key != 0:
            query = f"SELECT * FROM diary WHERE _id = {key}"
        elif time_range != [0, 0]:
            query = f"SELECT * FROM diary WHERE date BETWEEN {min(time_range)} AND {max(time_range)}"
        elif child_id != 0:
            query = f"SELECT * FROM diary WHERE childID = {child_id}"
        elif nanny_id != 0:
            query = f"SELECT * FROM diary WHERE nannyID = {nanny_id}"
        else:
            return []

        records_read = sql_query(query, self.__dbname)

        records = []

        for raw in records_read:
            timestamp = raw[2]
            record_childID = raw[3]
            record_nannyID = raw[4]
            record_json = raw[1]
            record_id = raw[0]

            record_dict = json.loads(record_json)

            record_data = DiaryRecord(record_dict["activity"], record_dict["food"], record_dict["wow"],
                                      record_dict["health"], record_dict["naps"], record_id, time_created=timestamp)

            records.append([timestamp, record_data, record_childID, record_nannyID])

        return records

    def new_calendar_event(self, event, user_id):
        # use a dictionary, and then convert to json
        calendar_dict = {
            "title": event.title,
            "note": event.note
        }
        calendar_json = "'" + json.dumps(calendar_dict) + "'"

        query = f"INSERT INTO calendar (startDate, endDate, data, userID) values ({event.timestamp}, {event.timestamp_end}, {calendar_json}, {user_id});"
        print(query)
        sql_query(query, self.__dbname)

    def get_calendar_event(self, key=0, datestamp=0, user_id=0):
        query = ""
        if key != 0:
            query = f"SELECT * FROM calendar WHERE _id = {key}"
        if datestamp != 0 or user_id != 0:
            if type(user_id) == list:
                user_id = user_id[0]
            query = f"SELECT * FROM calendar WHERE startDate BETWEEN {datestamp} AND {int(datestamp + 86400)} AND userID = {user_id}"
        events_raw = sql_query(query, self.__dbname)
        print("Events fetched:", events_raw)

        events = []
        for raw in events_raw:
            data_json = raw[1]
            data_dict = json.loads(data_json)

            event = CalendarEvent(data_dict["title"], data_dict["note"], int(raw[2]), raw[3], event_id=raw[0])
            events.append(event)

        return events

    def edit_meal_plan(self, meal):
        if READONLY_DEMO_MODE:
            return

        # delete the old meal plan for the child on the day
        query = f"DELETE FROM meals WHERE childID = {meal.child_id} AND date = {meal.datestamp}"
        sql_query(query, self.__dbname)

        # and create a new one with the updated info
        query = (f"INSERT INTO meals (childID, date, breakfast, lunch, dinner, ingredients)"
                 f" VALUES('{meal.child_id}', '{meal.datestamp}', '{meal.breakfast}', '{meal.lunch}', '{meal.dinner}', '{meal.ingredients}')")

        print(query)
        sql_query(query, self.__dbname)

    def get_meal_plan(self, child_id, datestamp):
        query = f"SELECT * FROM meals WHERE childID = {child_id} AND date = {datestamp}"
        daymeal_raw = sql_query(query, self.__dbname)

        if len(daymeal_raw) > 0:
            daymeal_raw = daymeal_raw[0]
            daymeal = DayMeal(daymeal_raw[3], daymeal_raw[4], daymeal_raw[5], daymeal_raw[6], daymeal_raw[2],
                              daymeal_raw[1], daymeal_raw[0])
            return daymeal
        else:
            # return empty daymeal if there is none present
            return DayMeal("", "", "", "")

    def remove_ingredient(self, ingredient, daymeal_id):
        # get the meal first
        query = f"SELECT * FROM meals WHERE _id = {daymeal_id}"
        daymeal_raw = sql_query(query, self.__dbname)

        # create the meal object
        daymeal_raw = daymeal_raw[0]
        daymeal = DayMeal(daymeal_raw[3], daymeal_raw[4], daymeal_raw[5], daymeal_raw[6], daymeal_raw[2],
                          daymeal_raw[1], daymeal_raw[0])

        # remove the ingredient
        daymeal.remove_ingredient(ingredient)

        # save the meal again
        self.edit_meal_plan(daymeal)

    def get_child(self, child_id):
        query = f"SELECT * FROM children WHERE childID = {child_id}"
        return sql_query(query, self.__dbname)[0]  # get the only record out the list

    def get_relation_id_from_parent(self, parent_id):
        query = (f"SELECT _id FROM relations WHERE parentIDs LIKE '[{parent_id}]'"
                 f" OR parentIDs LIKE '%, {parent_id}%'"
                 f" OR parentIDs LIKE '{parent_id},'")
        result = sql_query(query, self.__dbname)
        if len(result) > 0:
            return result[0][0]
        else:
            return None

    def get_user_id_from_email(self, email):
        query = f"SELECT _id FROM users WHERE email = '{email}'"
        result = sql_query(query, self.__dbname)
        if len(result) > 0:
            return result[0][0]
        else:
            return None

    def add_parent(self, user):
        if user.is_nanny:
            print("Nanny sign up should NOT use the add_parent() function, consider fixing this")

        # make sure the user's details are rewritten if they already exist
        query = f"SELECT * FROM users WHERE email = '{user.email}'"
        result = sql_query(query, self.__dbname)
        if len(result) > 0:
            query = f"UPDATE users SET name = '{user.name}', isNanny = {user.is_nanny} WHERE email = '{user.email}'"
            sql_query(query, self.__dbname)
            return
        query = f"INSERT OR IGNORE INTO users (name, email, isNanny) VALUES('{user.name}', '{user.email}', {user.is_nanny})"
        sql_query(query, self.__dbname)

    def get_relation(self, relation_id):
        query = f"SELECT * FROM relations WHERE _id = {relation_id}"
        return sql_query(query, self.__dbname)[0]

    def add_child(self, child, parent_emails, nanny_id):
        if READONLY_DEMO_MODE:
            return

        datestamp = time.mktime(datetime.datetime.strptime(child.birth_date, "%Y-%m-%d").timetuple())
        query = f"INSERT INTO children (firstname, lastname, birthDate, notes) VALUES ('{child.firstname}', '{child.lastname}',{datestamp}, '{child.notes}');"
        sql_query(query, self.__dbname)

        # add into relations table

        # get id(s) of parent
        parent_ids = []
        for email in parent_emails:
            parent_id = self.get_user_id_from_email(email)
            if parent_id == None:
                self.add_parent(User("unregistered", email, False))
                parent_id = self.get_user_id_from_email(email)
                parent_ids.append(parent_id)
            else:
                parent_ids.append(parent_id
                                  )

        print("Parent ids: ", parent_ids)

        # get autoincrement id of last insert
        last_child_id = sql_query("SELECT _id FROM children",
                                  self.__dbname)[-1][0]

        relation_id = self.get_relation_id_from_parent(parent_ids)
        print("Relation id: ", relation_id)

        # add child to existing relation
        if relation_id is not None:
            relation = self.get_relation(relation_id)

            # use json list serialisation
            print("Existing relation: ", relation)
            print("Last child id: ", last_child_id)

            print(relation[1])
            child_ids = json.loads(relation[1])

            child_ids.append(last_child_id)
            child_ids_serialised = json.dumps(child_ids)
            query = f"UPDATE relations SET childIDs='{child_ids_serialised}' WHERE _id = {relation_id}"
            sql_query(query, self.__dbname)

        # no relation set up with these parents before
        else:
            print("Adding new relation with parents: ", parent_ids)
            query = f"INSERT INTO relations (childIDs, parentIDs, nannyIDs) VALUES ('{[last_child_id]}', '{parent_ids}', '{[nanny_id]}')"
            sql_query(query, self.__dbname)

    def get_child_ids_by_nanny_id(self, nanny_id):
        query = f"SELECT _id, childIDs FROM relations WHERE nannyIDs LIKE '%{nanny_id}%'"
        rows = sql_query(query, self.__dbname)

        child_ids = []  # a 2d list of relations' child ids
        for row in rows:
            child_ids.append(
                [row[0], json.loads(row[1])])  # first column is _id, second is child ids for that relationship
        return child_ids

    def get_child_name_by_id(self, child_id):
        query = f"SELECT firstname, lastname FROM children WHERE _id = {child_id}"
        result = sql_query(query, self.__dbname)[0]  # get the only row
        return result[0] + " " + result[1]  # first column is firstname, second is lastname

    def get_child_ids_by_parent_id(self, parent_id):
        query = (f"SELECT _id, childIDs FROM relations WHERE parentIDs LIKE '[{parent_id}]'"
                 f" OR parentIDs LIKE '%, {parent_id}%'"
                 f" OR parentIDs LIKE '{parent_id},'")
        rows = sql_query(query, self.__dbname)

        child_ids = []  # a 2d list of relations' child ids
        for row in rows:
            child_ids.append(
                [row[0], json.loads(row[1])])  # first column is _id, second is child ids for that relationship
        return child_ids[0]

    def get_nanny_ids_by_parent(self, parent_id):
        query = (f"SELECT parentIDs FROM relations WHERE parentIDs LIKE '[{parent_id}]'"
                 f" OR parentIDs LIKE '%, {parent_id}%'"
                 f" OR parentIDs LIKE '{parent_id},'")
        result = sql_query(query, self.__dbname)[0][0]  # there would only be one relationship for each parent
        return json.loads(result)

    def log_expense(self, expense):
        # extract data
        description = expense.description
        amount = expense.amount
        datestamp = expense.datestamp
        nanny_id = expense.nanny_id
        relation_id = expense.relation_id

        # save
        query = f"INSERT INTO expense (description, amount, date, nannyID, relationID) VALUES ('{description}', '{amount}', {datestamp}, {nanny_id}, {relation_id})"
        sql_query(query, self.__dbname)

    def get_expenses(self, date_range, relation_id):
        query = f"SELECT * FROM expense WHERE date BETWEEN {date_range[0]} AND {date_range[1]} AND relationID = {relation_id}"
        rows = sql_query(query, self.__dbname)
        expenses = []
        for row in rows:
            expenses.append(Expense(row[2], row[1], row[4], row[5], datestamp=row[3]))
        return expenses

    def user_is_nanny(self, email):
        query = f"SELECT isNanny FROM users WHERE email = '{email}'"
        return sql_query(query, self.__dbname)[0][0]

    def get_secure_notes(self, relation_id):
        query = f"SELECT secureNotes FROM relations WHERE _id = {relation_id}"
        result = sql_query(query, self.__dbname)[0]
        if len(result) == 0:
            return ""
        else:
            return result[0]

    def save_secure_notes(self, relation_id, notes):
        query = f"UPDATE relations SET secureNotes=\"{notes}\" WHERE _id = {relation_id}"
        sql_query(query, self.__dbname)

    def set_connect_address(self, addr_lines, user_email):
        user_id = self.get_user_id_from_email(user_email)
        query = f"""insert into addresses(userID, address) 
values({user_id}, "{json.dumps(addr_lines).replace("\"", "$").replace("\'", "£")}")"""

# """
# on conflict(userID) do
# update
# set address=\"excluded.address\"
# where excluded.userID=userID;"""

        sql_query(query, self.__dbname)

    def update_all_connect_users(self):
        query = f"""
SELECT users.email, addresses.address
FROM users
INNER JOIN addresses ON users._id = addresses.userID;
    """
        rows = sql_query(query, self.__dbname)
        for row in rows:
            node_email, node_address = row

            # check if we need to add this to the graph
            if not self.__graph.check_node(node_email):
                self.__graph.new_node(json.loads(node_address.replace("$", "\"").replace("£", "\'")), node_email)

            self.__graph.build_adjacency_lists()

    def get_nearby_connect_users(self, email):
        self.populate_demo_connect_list()
        self.update_all_connect_users()
        all_connect_users = self.__graph.nearby_nodes(email)
        if len(all_connect_users) > 10:
            nearby = dict(itertools.islice(all_connect_users.items, 10))
        else:
            nearby = all_connect_users
        return nearby

    def populate_demo_connect_list(self):

        self.__graph.new_node(["51 New Road", "Harlington", "UB3 5BQ", "United Kingdom"], "test5@example.com")

        self.__graph.new_node(["90 End Lane", "Harlington", "UB3 5LU", "United Kingdom"], "test3@example.com")
        self.__graph.new_node(["246 Wincolmlee", "Hull", "HU2 0PZ", "United Kingdom"], "test4@example.com")
        self.__graph.new_node(["945 Barbara Ave", "Mountain View", "CA 94040", "United States"], "test2@example.com")

    def nub_connect_check(self, email):
        query = f"""SELECT * FROM users 
INNER JOIN addresses ON users._id=addresses.userID
 WHERE users.email = "{email}" """
        result = sql_query(query, self.__dbname)
        return len(result) > 0
