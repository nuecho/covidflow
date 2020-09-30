from typing import Any, Dict, List, Text

from rasa_sdk import Action, Tracker
from rasa_sdk.events import ConversationPaused
from rasa_sdk.executor import CollectingDispatcher

from covidflow.constants import CANCEL_CI_SLOT, LAST_SYMPTOMS_SLOT

from .lib.log_util import bind_logger


class ActionQaGoodbye(Action):
    def name(self) -> Text:
        return "action_qa_goodbye"

    async def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:
        bind_logger(tracker)
        # Last symptoms slot tells us we are in a daily check-in conversation
        if (
            tracker.get_slot(LAST_SYMPTOMS_SLOT) is not None
            and tracker.get_slot(CANCEL_CI_SLOT) is not True
        ):
            dispatcher.utter_message(template="utter_daily_ci_qa_will_contact_tomorrow")

        dispatcher.utter_message(template="utter_goodbye")

        return [ConversationPaused()]
