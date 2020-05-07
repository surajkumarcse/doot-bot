# This files contains your custom actions which can be used to run
# custom Python code.
#
# See this guide on how to implement these action:
# https://rasa.com/docs/rasa/core/actions/#custom-actions/


# This is a simple example for a custom action which utters "Hello World!"

from typing import Any, Text, Dict, List

from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import SlotSet, UserUtteranceReverted

# from rasa_core.events import (UserUtteranceReverted, UserUttered,)

# Invokes when facility search is done by user
class ActionFacilitySearch(Action):

    def name(self) -> Text:
        return "action_facility_search"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        # your code runs here
        facility = tracker.get_slot("facility_type")
        userLocation = tracker.get_slot("location")
        address = "300 Hyde St, San Francisco"
        dispatcher.utter_message("Here is the address of the {}:{} and location is {}".format(facility, address, userLocation))

        return [SlotSet("address", address)]

# Invokes as a trigger when bot_challenge intent is triggered
class ActionIsBot(Action):
    """Revertible mapped action for utter_is_bot"""

    def name(self):
        return "action_is_bot"
    
    def run(self, dispatcher, tracker, domain):
        dispatcher.utter_message(template="utter_iamabot")
        return [UserUtteranceReverted()]
