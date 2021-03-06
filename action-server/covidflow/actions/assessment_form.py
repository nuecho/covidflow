from typing import Any, Dict, List, Text

import structlog
from rasa_sdk import Action, Tracker
from rasa_sdk.events import EventType, SlotSet
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.forms import REQUESTED_SLOT

from covidflow.constants import (
    AGE_OVER_65_SLOT,
    ASSESSMENT_TYPE_SLOT,
    HAS_COUGH_SLOT,
    HAS_FEVER_SLOT,
    MODERATE_SYMPTOMS_SLOT,
    PROVINCE_SLOT,
    PROVINCES,
    PROVINCIAL_811_SLOT,
    SELF_ASSESS_DONE_SLOT,
    SEVERE_SYMPTOMS_SLOT,
    SYMPTOMS_SLOT,
    AssessmentType,
    Symptoms,
)

from .lib.form_helper import _form_slots_to_validate, end_form_additional_events
from .lib.log_util import bind_logger
from .lib.provincial_811 import get_provincial_811

logger = structlog.get_logger()

FORM_NAME = "assessment_form"
VALIDATE_ACTION_NAME = f"validate_{FORM_NAME}"
ASK_PROVINCE_ACTION_NAME = "action_ask_province_code"

ORDERED_FORM_SLOTS = [
    SEVERE_SYMPTOMS_SLOT,
    PROVINCE_SLOT,
    AGE_OVER_65_SLOT,
    HAS_FEVER_SLOT,
    MODERATE_SYMPTOMS_SLOT,
    HAS_COUGH_SLOT,
]


class ActionAskProvinceCode(Action):
    def name(self) -> Text:
        return ASK_PROVINCE_ACTION_NAME

    async def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:
        bind_logger(tracker)
        dispatcher.utter_message(template="utter_pre_ask_province_code")
        dispatcher.utter_message(template="utter_ask_province_code")

        return []


class ValidateNewAssessmentForm(Action):
    def name(self) -> Text:
        return VALIDATE_ACTION_NAME

    async def run(
        self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict
    ) -> List[EventType]:
        bind_logger(tracker)

        extracted_slots: Dict[Text, Any] = _form_slots_to_validate(
            tracker
        )  # https://github.com/RasaHQ/rasa-sdk/issues/269

        validation_events: List[EventType] = []

        for slot_name, slot_value in extracted_slots.items():
            slot_events = [SlotSet(slot_name, slot_value)]

            if slot_name == ASSESSMENT_TYPE_SLOT:
                slot_events = validate_assessment_type(slot_value, tracker)
            elif slot_name == PROVINCE_SLOT:
                slot_events = validate_province(slot_value, domain)
            elif slot_name == SEVERE_SYMPTOMS_SLOT and slot_value is True:
                slot_events += set_symptoms(Symptoms.SEVERE, slot_name)
            elif slot_name == MODERATE_SYMPTOMS_SLOT and slot_value is True:
                slot_events += set_symptoms(Symptoms.MODERATE, slot_name)
            elif slot_name == MODERATE_SYMPTOMS_SLOT:
                dispatcher.utter_message(template="utter_moderate_symptoms_false")
            elif slot_name == HAS_COUGH_SLOT and (
                slot_value is True or tracker.get_slot(HAS_FEVER_SLOT) is True
            ):
                slot_events += set_symptoms(Symptoms.MILD, slot_name)
            elif slot_name == HAS_COUGH_SLOT:
                slot_events += set_symptoms(Symptoms.NONE, slot_name)

            validation_events.extend(slot_events)

        return validation_events


def validate_assessment_type(value: str, tracker: Tracker) -> List[EventType]:
    applied_intents = [
        event["parse_data"]["intent"]["name"]
        for event in tracker.applied_events()
        if event["event"] == "user"
    ]

    if applied_intents[-2:] == ["tested_positive", "affirm"]:
        return [SlotSet(ASSESSMENT_TYPE_SLOT, AssessmentType.TESTED_POSITIVE)]
    return [SlotSet(ASSESSMENT_TYPE_SLOT, value)]


def validate_province(value: str, domain: Dict) -> List[EventType]:
    if value not in PROVINCES:
        return [SlotSet(PROVINCE_SLOT, None)]
    else:
        provincial_811 = get_provincial_811(value, domain)

        return [
            SlotSet(PROVINCE_SLOT, value),
            SlotSet(PROVINCIAL_811_SLOT, provincial_811),
        ]


def set_symptoms(symptoms_value: str, end_form_slot: str) -> List[EventType]:
    return [
        SlotSet(SYMPTOMS_SLOT, symptoms_value),
        SlotSet(SELF_ASSESS_DONE_SLOT, True),
        SlotSet(REQUESTED_SLOT, None),
    ] + end_form_additional_events(end_form_slot, ORDERED_FORM_SLOTS)
