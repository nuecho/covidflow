from typing import Any, Dict, List, Text

from rasa_sdk import Action, Tracker
from rasa_sdk.events import EventType, SlotSet
from rasa_sdk.executor import CollectingDispatcher

from covidflow.constants import (
    AGE_OVER_65_SLOT,
    MANDATORY_CI_SLOT,
    PRECONDITIONS_SLOT,
    PROVINCE_SLOT,
    PROVINCES_WITH_211,
    SYMPTOMS_SLOT,
    Symptoms,
)

from .lib.log_util import bind_logger

DEFAULT_INFO_LINK = "https://covid19.dialogue.co/#/info?id=common"


class ActionCheckMandatoryCi(Action):
    def name(self) -> Text:

        return "action_check_mandatory_ci"

    async def run(
        self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict
    ) -> List[EventType]:
        bind_logger(tracker)

        mandatory_ci = (
            tracker.get_slot(SYMPTOMS_SLOT) == Symptoms.MODERATE
            or tracker.get_slot(PRECONDITIONS_SLOT) is True
            or tracker.get_slot(AGE_OVER_65_SLOT) is True
        )

        return [SlotSet(MANDATORY_CI_SLOT, mandatory_ci)]


class ActionKeepCiRecommendations(Action):
    def name(self) -> Text:

        return "action_keep_ci_recommendations"

    async def run(
        self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict
    ) -> List[EventType]:
        bind_logger(tracker)

        provincial_link = _get_provincial__info_link(tracker, domain)
        if (
            tracker.get_slot(AGE_OVER_65_SLOT) is True
            or tracker.get_slot(PRECONDITIONS_SLOT) is True
        ):
            dispatcher.utter_message(
                template="utter_daily_ci__recommendations__more_information_vulnerable_population",
                provincial_link=provincial_link,
            )
        else:
            dispatcher.utter_message(
                template="utter_daily_ci__recommendations__more_information_general",
                provincial_link=provincial_link,
            )

        if tracker.get_slot(PROVINCE_SLOT) in PROVINCES_WITH_211:
            if tracker.get_slot(PROVINCE_SLOT) == "qc":
                dispatcher.utter_message(
                    template="utter_daily_ci__recommendations__211_qc"
                )
            else:
                dispatcher.utter_message(
                    template="utter_daily_ci__recommendations__211_other_provinces"
                )

        dispatcher.utter_message(
            template="utter_daily_ci__recommendations__tomorrow_ci"
        )

        dispatcher.utter_message(
            template="utter_daily_ci__recommendations__recommendation_1"
        )

        dispatcher.utter_message(
            template="utter_daily_ci__recommendations__recommendation_2"
        )

        return []


def _get_provincial__info_link(tracker: Tracker, domain: Dict[Text, Any]) -> str:
    province = tracker.get_slot(PROVINCE_SLOT)
    response = domain.get("responses", {}).get(
        f"provincial_info_link_{province}", [{"text": DEFAULT_INFO_LINK}]
    )
    return response[0].get("text", DEFAULT_INFO_LINK)
