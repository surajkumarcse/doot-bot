# This files contains your custom actions which can be used to run
# custom Python code.
#
# See this guide on how to implement these action:
# https://rasa.com/docs/rasa/core/actions/#custom-actions/


# This is a simple example for a custom action which utters "Hello World!"

import requests
from typing import Any, Text, Dict, List

from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import SlotSet, UserUtteranceReverted

from rasa_sdk.forms import FormAction


# from rasa_core.events import (UserUtteranceReverted, UserUttered,)

# We use the medicare.gov database to find information about 3 different
# healthcare facility types, given a city name, zip code or facility ID
# the identifiers for each facility type is given by the medicare database
# xubh-q36u is for hospitals
# b27b-2uc7 is for nursing homes
# 9wzi-peqs is for home health agencies

ENDPOINTS = {
    "base": "https://data.medicare.gov/resource/{}.json",
    "xubh-q36u": {
        "city_query": "?city={}",
        "zip_code_query": "?zip_code={}",
        "id_query": "?provider_id={}"
    },
    "b27b-2uc7": {
        "city_query": "?provider_city={}",
        "zip_code_query": "?provider_zip_code={}",
        "id_query": "?federal_provider_number={}"
    },
    "9wzi-peqs": {
        "city_query": "?city={}",
        "zip_code_query": "?zip={}",
        "id_query": "?provider_number={}"
    }
}

FACILITY_TYPES = {
    "hospital":
        {
            "name": "hospital",
            "resource": "xubh-q36u"
        },
    "nursing_home":
        {
            "name": "nursing home",
            "resource": "b27b-2uc7"
        },
    "home_health":
        {
            "name": "home health agency",
            "resource": "9wzi-peqs"
        }
}

def _create_path(base: Text, resource: Text,
                 query: Text, values: Text) -> Text:
    """Creates a path to find provider using the endpoints."""

    if isinstance(values, list):
        return (base + query).format(
            resource, ', '.join('"{0}"'.format(w) for w in values))
    else:
        return (base + query).format(resource, values)


def _find_facilities(location: Text, resource: Text) -> List[Dict]:
    """Returns json of facilities matching the search criteria."""

    if str.isdigit(location):
        full_path = _create_path(ENDPOINTS["base"], resource,
                                 ENDPOINTS[resource]["zip_code_query"],
                                 location)
    else:
        full_path = _create_path(ENDPOINTS["base"], resource,
                                 ENDPOINTS[resource]["city_query"],
                                 location.upper())
    #print("Full path:")
    #print(full_path)
    results = requests.get(full_path).json()
    return results


def _resolve_name(facility_types, resource) ->Text:
    for key, value in facility_types.items():
        if value.get("resource") == resource:
            return value.get("name")
    return ""


# Invokes when facility search is done by user
# class ActionFacilitySearch(Action):

#     def name(self) -> Text:
#         return "action_facility_search"

#     def run(self, dispatcher: CollectingDispatcher,
#             tracker: Tracker,
#             domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

#         # your code runs here
#         facility = tracker.get_slot("facility_type")
#         userLocation = tracker.get_slot("location")
#         address = "300 Hyde St, San Francisco"
#         dispatcher.utter_message("Here is the address of the {}:{} and location is {}".format(facility, address, userLocation))

#         return [SlotSet("address", address)]

# Invokes as a trigger when bot_challenge intent is triggered
class ActionIsBot(Action):
    """Revertible mapped action for utter_is_bot"""

    def name(self):
        return "action_is_bot"
    
    def run(self, dispatcher, tracker, domain):
        dispatcher.utter_message(template="utter_iamabot")
        return [UserUtteranceReverted()]

class FacilityForm(FormAction):
    def name(self) -> Text:
        return "facility_form"

    @staticmethod
    def required_slots(tracker: Tracker) -> List[Text]:
        return ["facility_type", "location"]

    def slot_mappings(self) -> Dict[Text, Any]:
        return {"facility_type": self.from_entity(entity="facility_type", 
                                                  intent=["inform", "search_provider"]), 
                "location": self.from_entity(entity="location", intent=["inform", "search_provider"])}

    def submit(self,
                dispatcher:CollectingDispatcher,
                tracker: Tracker,
                domain: Dict[Text, Any]
                ) -> List[Dict]:

        """Once required slots are filled, print buttons for found facilities"""

        location = tracker.get_slot('location')
        facility_type = tracker.get_slot('facility_type')

        results = _find_facilities(location, facility_type)
        button_name = _resolve_name(FACILITY_TYPES, facility_type)
        if len(results) == 0:
            dispatcher.utter_message(
                "Sorry, we could not find a {} in {}.".format(button_name,
                                                              location.title()))
            return []

        buttons = []
        # limit number of results to 3 for clear presentation purposes
        for r in results[:3]:
            if facility_type == FACILITY_TYPES["hospital"]["resource"]:
                facility_id = r.get("provider_id")
                name = r["hospital_name"]
            elif facility_type == FACILITY_TYPES["nursing_home"]["resource"]:
                facility_id = r["federal_provider_number"]
                name = r["provider_name"]
            else:
                facility_id = r["provider_number"]
                name = r["provider_name"]

            payload = "/inform{\"facility_id\":\"" + facility_id + "\"}"
            buttons.append(
                {"title": "{}".format(name.title()), "payload": payload})

        if len(buttons) == 1:
            message = "Here is a {} near you:".format(button_name)
        else:
            if button_name == "home health agency":
                button_name = "home health agencie"
            message = "Here are {} {}s near you:".format(len(buttons),
                                                         button_name)

        # TODO: update rasa core version for configurable `button_type`
        dispatcher.utter_button_message(message, buttons)

        return []

class FindHealthCareAddress(Action):
    """This action class retrieves the address of the user's
    healthcare facility choice to display it to the user."""

    def name(self) -> Text:
        """Unique identifier of the action"""

        return "find_healthcare_address"

    def run(self,
            dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict]:

        facility_type = tracker.get_slot("facility_type")
        healthcare_id = tracker.get_slot("facility_id")
        full_path = _create_path(ENDPOINTS["base"], facility_type,
                                 ENDPOINTS[facility_type]["id_query"],
                                 healthcare_id)
        results = requests.get(full_path).json()
        if results:
            selected = results[0]
            if facility_type == FACILITY_TYPES["hospital"]["resource"]:
                address = "{}, {}, {} {}".format(selected["address"].title(),
                                                 selected["city"].title(),
                                                 selected["state"].upper(),
                                                 selected["zip_code"].title())
            elif facility_type == FACILITY_TYPES["nursing_home"]["resource"]:
                address = "{}, {}, {} {}".format(selected["provider_address"].title(),
                                                 selected["provider_city"].title(),
                                                 selected["provider_state"].upper(),
                                                 selected["provider_zip_code"].title())
            else:
                address = "{}, {}, {} {}".format(selected["address"].title(),
                                                 selected["city"].title(),
                                                 selected["state"].upper(),
                                                 selected["zip"].title())

            return [SlotSet("facility_address", address)]
        else:
            print("No address found. Most likely this action was executed "
                  "before the user choose a healthcare facility from the "
                  "provided list. "
                  "If this is a common problem in your dialogue flow,"
                  "using a form instead for this action might be appropriate.")

            return [SlotSet("facility_address", "not found")]

class FindFacilityTypes(Action):
    """This action class allows to display buttons for each facility type
    for the user to chose from to fill the facility_type entity slot."""

    def name(self) -> Text:
        """Unique identifier of the action"""

        return "find_facility_types"

    def run(self,
            dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List:

        buttons = []
        for t in FACILITY_TYPES:
            facility_type = FACILITY_TYPES[t]
            payload = "/inform{\"facility_type\": \"" + facility_type.get(
                "resource") + "\"}"

            buttons.append(
                {"title": "{}".format(facility_type.get("name").title()),
                 "payload": payload})

        # TODO: update rasa core version for configurable `button_type`
        dispatcher.utter_button_template("utter_greet", buttons, tracker)
        return []
