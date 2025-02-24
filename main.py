from flask_app import app
import sys
import waitress

# use the --test argument to use builtin server
if "--test" in sys.argv[1:]:
    print("Running in test mode")
    app.run(port=8080, host='0.0.0.0', debug=True)
else:
    print("Running in deployment mode")
    waitress.serve(app, port=8080, url_scheme="https")


