from typing import Any, Dict, List, Text

from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher

from .lib.log_util import bind_logger


class ActionSuspectNoSymptomsRecommendations(Action):
    def name(self) -> Text:
        return "action_suspect_no_symptoms_recommendations"

    async def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:
        bind_logger(tracker)
        dispatcher.utter_message(template="utter_probably_not_covid")
        dispatcher.utter_message(template="utter_social_distancing")
        dispatcher.utter_message(template="utter_checkin_if_developments")
        dispatcher.utter_message(template="utter_link_if_anxious")

        return []


class ActionSuspectMildSymptomsExposureRecommendations(Action):
    def name(self) -> Text:
        return "action_suspect_mild_symptoms_exposure_recommendations"

    async def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:
        bind_logger(tracker)
        dispatcher.utter_message(template="utter_monitor_symptoms_changes")

        return []


class ActionSuspectMildSymptomsExposureFinalRecommendations(Action):
    def name(self) -> Text:
        return "action_suspect_mild_symptoms_exposure_final_recommendations"

    async def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:
        bind_logger(tracker)
        dispatcher.utter_message(template="utter_remind_stay_home_self_isolate")
        dispatcher.utter_message(template="utter_remind_possible_checkin")

        return []


class ActionSuspectModerateSymptomsRecommendations(Action):
    def name(self) -> Text:
        return "action_suspect_moderate_symptoms_recommendations"

    async def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:
        bind_logger(tracker)
        dispatcher.utter_message(template="utter_symptoms_worsen_emergency")
        dispatcher.utter_message(template="utter_monitor_symptoms_assistance")

        return []


class ActionSuspectModerateSymptomsFinalRecommendations(Action):
    def name(self) -> Text:
        return "action_suspect_moderate_symptoms_final_recommendations"

    async def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:
        bind_logger(tracker)
        dispatcher.utter_message(template="utter_remind_stay_home_self_isolate")
        dispatcher.utter_message(template="utter_monitor_symptoms_temperature")
        dispatcher.utter_message(template="utter_remind_possible_checkin")

        return []
