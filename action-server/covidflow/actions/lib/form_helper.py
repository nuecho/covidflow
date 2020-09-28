from typing import Any, Dict, List, Text

from rasa_sdk import Tracker
from rasa_sdk.events import EventType, SlotSet

from covidflow.constants import SKIP_SLOT_PLACEHOLDER


def _form_slots_to_validate(tracker: Tracker) -> Dict[Text, Any]:
    """
    Waiting for a solution to: https://github.com/RasaHQ/rasa-sdk/issues/269
    I copied the function and adapted it and replaced it where it does change something.
    Get form slots which need validation.
    You can use a custom action to validate slots which were extracted during the
    latest form execution. This method provides you all extracted candidates for
    form slots.
    Returns:
        A mapping of extracted slot candidates and their values.
    """

    slots_to_validate = {}

    # Thing I changed
    # if not self.active_loop:
    #     return slots_to_validate

    for event in reversed(tracker.events):
        # The `FormAction` in Rasa Open Source will append all slot candidates
        # at the end of the tracker events.
        if event["event"] == "slot":
            slots_to_validate[event["name"]] = event["value"]
        else:
            # Stop as soon as there is another event type as this means that we
            # checked all potential slot candidates.
            break

    return slots_to_validate


# Fills all the slots that were not yet asked. Workaround for https://github.com/RasaHQ/rasa/issues/6569
def end_form_additional_events(
    actual_slot: str, ordered_form_slots: List[str]
) -> List[EventType]:
    actual_slot_index = ordered_form_slots.index(actual_slot)
    return [
        SlotSet(slot, SKIP_SLOT_PLACEHOLDER)
        for slot in ordered_form_slots[actual_slot_index + 1 :]
    ]
