import datetime
import time
import json


class DiaryRecord:
    def __init__(self, activity, food, wow, health, naps, diary_id=0, time_created=time.time()):
        self.activity = activity
        self.food = food
        self.wow = wow
        self.health = health
        self.naps = naps
        self.diary_id = diary_id
        self.time_created = int(time_created) - (int(time_created) % 60)  # only want the minutes
        self.datetime_str = str(datetime.datetime.fromtimestamp(self.time_created)) # store the time created

    def to_json(self):
        diary_data_dict = {
            "activity": self.activity,
            "food": self.food,
            "wow": self.wow,
            "health": self.health,
            "naps": self.naps
        }

        diary_data_json = "'" + json.dumps(diary_data_dict) + "'"
        return diary_data_json


class CalendarEvent:
    def __init__(self, title, note, timestamp, user_id, timestamp_end=0, recurring_period=0, event_id=0):
        self.title = title
        self.note = note
        self.timestamp = timestamp
        self.datetime_str = str(datetime.datetime.fromtimestamp(self.timestamp))

        self.timestamp_end = timestamp_end
        self.datetime_str_end = str(datetime.datetime.fromtimestamp(self.timestamp_end))
        self.recurring_period = recurring_period

        self.user_id = user_id
        self.time_created = time.time()
        self.event_id = event_id

    def get_due(self):
        # it will be "due" for a minute
        return time.time() - self.timestamp < 60

    def get_next_recurring_event(self):
        if self.recurring_period == 0:
            return None
        else:
            return CalendarEvent(self.title, self.note, self.timestamp + self.recurring_period, self.user_id, self.timestamp_end + self.recurring_period, self.recurring_period, self.event_id)


class DayMeal:
    def __init__(self, breakfast, lunch, dinner, ingredients, datestamp=0, child_id=0, meal_id=0):
        self.breakfast = breakfast
        self.lunch = lunch
        self.dinner = dinner
        self.ingredients = ingredients  # items in the list split by newlines
        self.datestamp = datestamp
        self.child_id = child_id
        self.meal_id = meal_id

    def ingredients_list(self):
        if self.ingredients == "\n":
            return []  # leftover new line from the last entry
        else:
            return self.ingredients.split("\n")

    def remove_ingredient(self, ingredient):
        self.ingredients = self.ingredients.replace(ingredient, "")
        self.ingredients = self.ingredients.replace("\n\n", "\n")


class Child:
    def __init__(self, firstname, lastname, birth_date, notes=""):
        self.firstname = firstname
        self.lastname = lastname
        self.birth_date = birth_date
        self.parents = []
        self.notes = notes

    def add_parent(self, parent_id):
        self.parents.append(parent_id)


class User:
    def __init__(self, name, email, is_nanny=False):
        self.email = email
        self.is_nanny = is_nanny
        self.name = name


class Expense:
    def __init__(self, amount, description, nanny_id, relation_id, datestamp=0):
        self.amount = amount
        self.description = description
        if datestamp == 0:
            self.datestamp = int(time.time())
        else:
            self.datestamp = datestamp

        self.datetime_str = str(datetime.datetime.fromtimestamp(self.datestamp))
        self.nanny_id = nanny_id
        self.relation_id = relation_id