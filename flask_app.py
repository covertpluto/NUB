from flask import Flask, render_template, request, redirect, send_file, abort, make_response
from flask_login import LoginManager, login_user, login_required, logout_user, current_user, UserMixin
from flask_sqlalchemy import SQLAlchemy
from backend import DBHandler
from stored_data import DiaryRecord, CalendarEvent, DayMeal, User, Child, Expense
from http import HTTPStatus
from user_graph import GeolocationError
import json
import time
import bcrypt
import sqlalchemy
import datetime
import utils
import re

demo_mode = True

dbhandler = DBHandler("nub.db")
app = Flask(__name__)

# flask login config
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///db.sqlite"
app.config["SECRET_KEY"] = "secretkey"
auth_db = SQLAlchemy()
login_manager = LoginManager()
login_manager.init_app(app)


class Users(UserMixin, auth_db.Model):
    id = auth_db.Column(auth_db.Integer, primary_key=True)
    name = auth_db.Column(auth_db.String(100))
    email = auth_db.Column(auth_db.String(100), unique=True)
    password = auth_db.Column(auth_db.String(100))


auth_db.init_app(app)
with app.app_context():
    auth_db.create_all()


# Get the user object from its id
@login_manager.user_loader
def load_user(user_id):
    return Users.query.get(int(user_id))


@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        name = request.form["name"]
        email = request.form["email"]
        password = request.form["password"]

        # Apply password strength checking
        searched = re.search("^(?=.*[A-Z])(?=.*[a-z])(?=.*[0-9])(?=.*[!@£$%^&*]).{8,}$", password)
        if searched is None:  # 0 matches
            return render_template("signup.html", error="Password is not strong enough")

        is_nanny = False
        if request.form.get("is_nanny") == "on":
            is_nanny = True

        # hash the password
        password_hashed = bcrypt.hashpw(bytes(password, "utf-8"), bcrypt.gensalt(rounds=12))

        try:
            user = Users(name=name, email=email.lower(), password=password_hashed)
            auth_db.session.add(user)
            auth_db.session.commit()

            user_entry = User(name=name, email=email, is_nanny=is_nanny)
            dbhandler.add_parent(user_entry)
        except sqlalchemy.exc.IntegrityError:
            # user already exists
            return render_template("signup.html", error="User with this email already exists")
        return redirect("/login")
    # is a get request, therefore show the page
    return render_template("signup.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user = Users.query.filter_by(email=request.form["email"]).first()
        if user is None:
            # invalid email
            return render_template("login.html", error="Email or password invalid. Please try again")

        # check the password against the hashed pasword
        if bcrypt.checkpw(bytes(request.form.get("password"), "utf-8"), user.password):
            login_user(user)
            # login success
            user_is_nanny = dbhandler.user_is_nanny(request.form["email"])
            if not user_is_nanny:
                user_relations = dbhandler.get_relation_id_from_parent(
                    dbhandler.get_user_id_from_email(request.form["email"]))
                if user_relations is None:
                    logout_user()
                    # the user is not in any relations (account wasn't setup properly)
                    return render_template("login.html", error="Your account hasn't been set up by a nanny yet")

            return redirect("/")
        else:  # invalid password
            return render_template("login.html", error="Email or password invalid. Please try again")
    # Load the login page because it is a GET request
    return render_template("login.html")


# route for all unauthorised clients, go straight to login
@login_manager.unauthorized_handler
def unauthorised():
    print("unauthorised")
    if request.blueprint == 'api':
        abort(HTTPStatus.UNAUTHORIZED)
    return redirect("/login")


# logout user and go to login page
@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect("/login")


# # for test purposes only
# @app.route("/whoami")
# @login_required
# def whoami():
#     return current_user.email


# default route
@app.route("/")
@login_required
def index():
    # display relevant welcome screen
    datestring = datetime.datetime.now().strftime("%a, %d %b %Y")

    current_userid = dbhandler.get_user_id_from_email(current_user.email)

    upcoming_events = dbhandler.get_calendar_event(datestamp=int(time.time()), user_id=current_userid)
    print(upcoming_events)

    user_is_nanny = dbhandler.user_is_nanny(current_user.email)

    # get user event or nanny events
    if not user_is_nanny:
        my_nannies = dbhandler.get_nanny_ids_by_parent(dbhandler.get_user_id_from_email(current_user.email))
        nanny_events = dbhandler.get_calendar_event(datestamp=int(time.time()), user_id=my_nannies)
        my_relation_id = dbhandler.get_relation_id_from_parent(dbhandler.get_user_id_from_email(current_user.email))
    else:
        nanny_events = []
        my_child_ids_relationships = dbhandler.get_child_ids_by_nanny_id(
            dbhandler.get_user_id_from_email(current_user.email))

        my_relation_id = [relation[0] for relation in my_child_ids_relationships]
        if len(my_relation_id) == 0:  # nanny new and no relation set up, send straight to set up page
            return (redirect("/child-new"))
        else:
            my_relation_id = my_relation_id[0]  # default to the first relation

    home_path = "home.html" if not demo_mode else "home_demo.html"
    resp = make_response(render_template(
        home_path,
        name=current_user.name,
        date_formatted=datestring,
        events=upcoming_events,
        nanny_events=nanny_events,
        user_is_nanny=user_is_nanny
    ))
    # set them to the first relation if there is one. if they're the parent set them to the only relation id they have
    resp.set_cookie("relationid", str(my_relation_id))
    return resp


@app.route("/menu")
@login_required
def menu():
    is_nanny = dbhandler.user_is_nanny(current_user.email)

    if is_nanny:
        # get all relations

        my_child_ids_relationships = dbhandler.get_child_ids_by_nanny_id(
            dbhandler.get_user_id_from_email(current_user.email))
        #print(my_child_ids_relationships)
        my_children_names = []
        for relation in my_child_ids_relationships:
            relation_names = []
            for child_id in relation[1]:
                child_name = dbhandler.get_child_name_by_id(child_id)
                relation_names.append(child_name)
            my_children_names.append([relation[0], relation_names])
    else:
        # nothing to display
        my_children_names = []
    return render_template("menu.html", name=current_user.name, relations=my_children_names)


@app.route("/diary-new", methods=["GET"])
@login_required
def diarynew():
    return render_template("diary_new.html", errormsg="")


@app.route("/diary-new", methods=["POST"])
@login_required
def diarynew_post():
    # Get the data from the diary form
    data = request.form
    activity = data.get("what-we-did")
    food = data.get("what-we-ate")
    wow = data.get("wow-moment")
    health = data.get("healthcare")

    naps_start_hours = data.getlist("start_hours")
    naps_start_minutes = data.getlist("start_minutes")

    naps_end_hours = data.getlist("end_hours")
    naps_end_minutes = data.getlist("end_minutes")

    # Organise nap times
    nap_times = []
    for nap in zip(naps_start_hours, naps_start_minutes, naps_end_hours, naps_end_minutes):
        try:
            nap = [int(t) for t in nap]
            # if same hour, check whether minutes are greater than start minutes
            if nap[0] == nap[2]:
                assert nap[1] < nap[3]
            else:
                # otherwise the start hours must be before end hours
                assert nap[0] < nap[2]
        # don't need to catch the string -> int error since it's a dropdown with no possible empty values
        except AssertionError:
            errormsg = "Start time must be after end time"
            return render_template("diarynew.html", errormsg=errormsg)

        nap_times.append(nap)
    print(nap_times)

    # Create diary object
    diary_record = DiaryRecord(activity, food, wow, health, nap_times)

    # Store the diary
    dbhandler.new_diary_record(diary_record.to_json(), 1, 1)

    # Point the user back
    return redirect("/")


@app.route("/diary")
@login_required
def diary_view():
    data = request.args
    # search page
    if "diary_id" not in data.keys():  # No specific diary is selected, show all in date range

        if "date" not in data.keys():  # no date specified, default to showing today
            timenow = datetime.datetime.now()
            years = utils.pad_number(timenow.year, 4)
            month = utils.pad_number(timenow.month, 2)
            day = utils.pad_number(timenow.day, 2)
            return redirect(f"/diary?date={years}-{month}-{day}")
        else:
            # date is present, generate time range for this day
            date = data["date"]
            date_range = [
                time.mktime(datetime.datetime.strptime(date, "%Y-%m-%d").timetuple()),
                time.mktime(datetime.datetime.strptime(date, "%Y-%m-%d").timetuple()) + 86400
            ]
            # get the records
            records = dbhandler.get_diary_record(time_range=date_range)
            years = utils.pad_number(datetime.datetime.strptime(date, "%Y-%m-%d").timetuple().tm_year, 4)
            month = utils.pad_number(datetime.datetime.strptime(date, "%Y-%m-%d").timetuple().tm_mon, 2)
            day = utils.pad_number(datetime.datetime.strptime(date, "%Y-%m-%d").timetuple().tm_mday, 2)

        # return the screen with all the relevant diary records
        return render_template("diary.html",
                               records=records,
                               years=years,
                               month=month,
                               day=day,
                               is_nanny=dbhandler.user_is_nanny(current_user.email)
                               )
    else:
        # diary record selected, show details of that diary record
        record = dbhandler.get_diary_record(key=data["diary_id"])[0]
        return render_template("diary_record.html", record=record)


@app.route("/calendar-new", methods=["GET"])
@login_required
def calendar_new():
    # get current time as default placeholder time
    timenow = datetime.datetime.now()
    return render_template("calendar_new.html",
                           hours=utils.pad_number(timenow.hour + 1, 2),
                           minutes=utils.pad_number(timenow.minute, 2),
                           years=utils.pad_number(timenow.year, 4),
                           month=utils.pad_number(timenow.month, 2),
                           day=utils.pad_number(timenow.day, 2)
                           )


@app.route("/calendar-new", methods=["POST"])
@login_required
def calendar_new_post():
    # get data from form
    data = request.form
    title = data.get("title")
    note = data.get("note")
    event_time = data.get("time")
    event_date = data.get("date")

    event_time_end = data.get("time_end")
    event_date_end = data.get("date_end")

    # convert to timestamps
    timestamp = time.mktime(datetime.datetime.strptime(event_time + " " + event_date, "%H:%M %Y-%m-%d").timetuple())
    timestamp_end = time.mktime(
        datetime.datetime.strptime(event_time_end + " " + event_date_end, "%H:%M %Y-%m-%d").timetuple())

    print("Creating new event from", timestamp, "to", timestamp_end)

    # check valid dates
    if timestamp_end < timestamp:
        return render_template("calendar_new.html", error="End time cannot be before start time")

    # get current user details
    current_user_id = dbhandler.get_user_id_from_email(current_user.email)

    # create the calendar event, and stores it
    event = CalendarEvent(title, note, timestamp, current_user_id, timestamp_end=timestamp_end)
    dbhandler.new_calendar_event(event, current_user_id)

    # back to calendar screen
    return redirect("/calendar")


@app.route("/calendar")
@login_required
def calendar_view():
    data = request.args
    # search page
    if "event_id" not in data.keys():
        if "date" not in data.keys():  # no date specified
            # redirect to current day
            timenow = datetime.datetime.now()
            years = utils.pad_number(timenow.year, 4)
            month = utils.pad_number(timenow.month, 2)
            day = utils.pad_number(timenow.day, 2)
            return redirect(f"/calendar?date={years}-{month}-{day}")
        else:
            # display all for current day
            date = time.mktime(datetime.datetime.strptime(data["date"], "%Y-%m-%d").timetuple())
            current_user_id = dbhandler.get_user_id_from_email(current_user.email)
            events = dbhandler.get_calendar_event(datestamp=date, user_id=current_user_id)

            years = utils.pad_number(datetime.datetime.strptime(data["date"], "%Y-%m-%d").timetuple().tm_year, 4)
            month = utils.pad_number(datetime.datetime.strptime(data["date"], "%Y-%m-%d").timetuple().tm_mon, 2)
            day = utils.pad_number(datetime.datetime.strptime(data["date"], "%Y-%m-%d").timetuple().tm_mday, 2)

        return render_template("calendar.html",
                               events=events,
                               years=years,
                               month=month,
                               day=day,
                               is_nanny=dbhandler.user_is_nanny(current_user.email)
                               )
    else:
        # show individual event
        event = dbhandler.get_calendar_event(key=data["event_id"])[0]
        print("Found event", event)
        return render_template("calendar_event.html", event=event)


@app.route("/edit-food-plan", methods=["GET"])
@login_required
def edit_food_plan():
    data = request.args
    datetime.datetime.now()

    if "date" not in data.keys():  # no date specified
        # show food plan for today
        timenow = datetime.datetime.now()
        years = utils.pad_number(timenow.year, 4)
        month = utils.pad_number(timenow.month, 2)
        day = utils.pad_number(timenow.day, 2)
        return redirect(f"/edit-food-plan?date={years}-{month}-{day}")
    else:
        # show food plan for searched day
        date_editing = data["date"]
        datestamp = time.mktime(datetime.datetime.strptime(date_editing, "%Y-%m-%d").timetuple())
        relation = request.cookies.get("relationid")
        child_ids = json.loads(dbhandler.get_relation(relation)[1])

        # placeholder with existing plans if any

        today_meal = dbhandler.get_meal_plan(child_ids[0], datestamp)

        return render_template("food_plan_edit.html",
                               child_id=child_ids[0],
                               date=datestamp,
                               date_editing=date_editing,
                               day_meal=today_meal)


@app.route("/edit-food-plan", methods=["POST"])
@login_required
def edit_food_plan_post():
    data = request.form
    breakfast = data["breakfast"]
    lunch = data["lunch"]
    dinner = data["dinner"]
    ingredients = data["ingredients"].replace("\r", "")  # remove extra characters inserted by browsers
    print(ingredients)
    meal_datestamp = data["editdate"]
    child_id = data["childID"]

    # Create object, save, return user to edit page
    day_meal = DayMeal(breakfast, lunch, dinner, ingredients, datestamp=meal_datestamp, child_id=child_id)
    dbhandler.edit_meal_plan(day_meal)
    return redirect("/edit-food-plan")


@app.route("/food-plan", methods=["GET"])
@login_required
def food_plan_view():
    data = request.args

    if "date" not in data.keys() or "relationid" not in request.cookies:
        # no date specified, take them to today's food plan
        timenow = datetime.datetime.now()
        years = utils.pad_number(timenow.year, 4)
        month = utils.pad_number(timenow.month, 2)
        day = utils.pad_number(timenow.day, 2)
        return redirect(f"/food-plan?date={years}-{month}-{day}")

    else:
        date_viewing = data["date"]
        datestamp = time.mktime(datetime.datetime.strptime(date_viewing, "%Y-%m-%d").timetuple())

        is_nanny = dbhandler.user_is_nanny(current_user.email)
        relation_id = request.cookies.get('relationid')

        child_in_relation = json.loads(dbhandler.get_relation(relation_id)[1])[0]
        meal = dbhandler.get_meal_plan(child_in_relation, datestamp)

        return render_template("food_plan.html",
                               child_id=child_in_relation,
                               date=datestamp,
                               date_viewing=date_viewing,
                               day_meal=meal,
                               is_nanny=is_nanny)


@app.route("/removeingredient")
@login_required
def remove_ingredient():
    # get clicked items
    data = request.args

    item = data["item_name"]
    daymeal_id = data["meal_id"]

    # remove the item
    dbhandler.remove_ingredient(item, daymeal_id)

    # redirect to previous page
    return redirect(f"/food-plan?date={data["date_viewing"]}&child_id={data["child_id"]}")


@app.route("/child-new", methods=["GET"])
@login_required
def new_child():
    return render_template("add_child.html")


@app.route("/child-new", methods=["POST"])
@login_required
def new_child_post():
    data = request.form
    firstname = data["firstname"]
    lastname = data["lastname"]
    notes = data["notes"]
    date = data["date"]
    parents = data["parents"]

    # split parents by \n\r
    parents = parents.split("\r\n")
    print(parents)

    child = Child(firstname, lastname, date, notes)
    email_passwords = dbhandler.add_child(child, parents, nanny_id=1)
    print("email_passwords", email_passwords)
    return render_template("add_child_done.html", email_passwords=email_passwords)


@app.route("/log-expense", methods=["GET"])
@login_required
def log_expense():
    return render_template("log_expense.html")


@app.route("/log-expense", methods=["POST"])
@login_required
def log_expense_post():
    # get the data from the request body
    data = request.form

    nanny_id = dbhandler.get_user_id_from_email(current_user.email)

    # input validation for a float. Return to that page with an error message if fail
    try:
        assert float(data["amount"]) > 0
    except ValueError:
        return render_template("log_expense.html", errormsg="Amount must be a decimal number. Do not include currency")
    except AssertionError:
        return render_template("log_expense.html",
                               errormsg="Amount must be a positive non zero number. Do not include currency")

    # request object contains cookies, use that to get which relation the user is selecting
    expense = Expense(data["amount"], data["description"], nanny_id, request.cookies.get('relationid'))
    dbhandler.log_expense(expense)
    return redirect("/log-expense")


@app.route("/expenses")
@login_required
def expenses():
    data = request.args

    if "date_start" not in data.keys() or "date_end" not in data.keys():  # no date specified
        timenow = datetime.datetime.now()
        years = utils.pad_number(timenow.year, 4)
        month = utils.pad_number(timenow.month, 2)
        day = utils.pad_number(timenow.day, 2)
        # print("here")
        return redirect(f"/expenses?date_start={years}-{month}-{day}&date_end={years}-{month}-{day}")

    else:
        date_range = [data["date_start"], data["date_end"]]
        # print(date_range)
        datestamp_range = [time.mktime(datetime.datetime.strptime(date, "%Y-%m-%d").timetuple()) for date in date_range]
        datestamp_range[1] = datestamp_range[1] + 86400  # add a day onto it, since the end date is exclusive

        relation_id = request.cookies.get('relationid')

        # get the data
        expenses = dbhandler.get_expenses(datestamp_range, relation_id)

        # sum expenses
        total = sum([float(expense.amount) for expense in expenses])

        return render_template("expenses.html", expenses=expenses, total=total, date_start_viewing=date_range[0],
                               date_end_viewing=date_range[1], is_nanny=dbhandler.user_is_nanny(current_user.email))


# routes for secure note sections
@app.route("/secure-notes", methods=["GET"])
@login_required
def secure_notes():
    relation_id = request.cookies.get('relationid')
    notes = dbhandler.get_secure_notes(relation_id)

    return render_template("secure_notes.html", notes=notes)


@app.route("/secure-notes", methods=["POST"])
@login_required
def secure_notes_post():
    relation_id = request.cookies.get('relationid')
    notes = request.form.get("notes")
    dbhandler.save_secure_notes(relation_id, notes)
    return redirect("/secure-notes")


@app.route("/connect", methods=["GET"])
@login_required
def connect():
    email = current_user.email

    # user has not signed up
    if not dbhandler.nub_connect_check(email):
        return redirect("/connect_signup")

    # Catch any problems with the API
    try:
        # get nearby users and display
        nearby = dbhandler.get_nearby_connect_users(email)
    except GeolocationError:
        return render_template("connect.html",
                               errormsg="There has been an error. Please check whether your address is correct")
    return render_template("connect.html", users=list(zip(nearby.values(), nearby.keys())))


# signup routes for connect
@app.route("/connect_signup", methods=["GET"])
@login_required
def connect_signup():
    email = current_user.email
    return render_template("connect_signup.html", eml=email)


@app.route("/connect_signup", methods=["POST"])
@login_required
def connect_signup_post():
    # get form data
    data = request.form

    # save details
    dbhandler.set_connect_address([data.get("addr1"), data.get("addr2"), data.get("addr3"), data.get("addr4")],
                                  data.get("eml"))
    return redirect("/connect")


@app.route("/populate_demo")
def populate_demo():
    dbhandler.populate_demo_connect_list()
    return redirect("/connect")


# following needed for PWA functinality


@app.route('/manifest.json')
def serve_manifest():
    return send_file('manifest.json', mimetype='application/manifest+json')


@app.route('/sw.js')
def serve_sw():
    return send_file('sw.js', mimetype='application/javascript')


@app.route("/getdata")
def getdata():
    return ""

#
# if __name__ == "__main__":
#     app.run(port=8080, host="0.0.0.0")
