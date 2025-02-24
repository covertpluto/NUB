import requests
import json


class AddressToCoords:
    def __init__(self, service=""):
        match service:
            # can add more services here
            case "nominatim":
                self._endpoint = "https://nominatim.openstreetmap.org/search"
            case _:
                raise ValueError("A service is needed!")

    def convert_address(self, lines):
        req_args = "?q="
        for line in lines:
            # address spaces convert to +
            line = line.replace(" ", "+")
            # separate lines can be separated using a comma to improve accuracy
            req_args += line + ","

        # remove extra comma
        req_args = req_args[:-1]

        # add this to get a JSON response instead of a whole HTML page
        req_args += "&format=json"
        # print("Requesting: \n", self._endpoint + req_args)
        response = requests.get(self._endpoint + req_args)
        print(response.text)
        # get the top result and return the relevant details
        top_result = json.loads(response.text)[0]
        lat_long = [float(top_result["lat"]), float(top_result["lon"])]
        display = top_result["display_name"]
        return lat_long, display




