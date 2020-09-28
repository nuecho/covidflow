import re
from typing import Any, Dict, List, Optional, Text, Tuple, Union

from rasa_sdk import Action, ActionExecutionRejection, Tracker
from rasa_sdk.events import EventType, SlotSet
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.forms import REQUESTED_SLOT

from covidflow.constants import (
    FIRST_NAME_SLOT,
    HAS_DIALOGUE_SLOT,
    LANGUAGE_SLOT,
    PHONE_NUMBER_SLOT,
    PRECONDITIONS_SLOT,
    SKIP_SLOT_PLACEHOLDER,
)
from covidflow.utils.persistence import ci_enroll
from covidflow.utils.phone_number_validation import (
    VALIDATION_CODE_LENGTH,
    send_validation_code,
)

from .lib.log_util import bind_logger

FORM_NAME = "daily_ci_enroll_form"
VALIDATE_ACTION_NAME = f"validate_{FORM_NAME}"

PHONE_TRY_COUNTER_SLOT = "daily_ci_enroll__phone_number_error_counter"
PHONE_TO_CHANGE_SLOT = "daily_ci_enroll__phone_number_to_change"
VALIDATION_CODE_SLOT = "daily_ci_enroll__validation_code"
VALIDATION_CODE_REFERENCE_SLOT = "daily_ci_enroll__validation_code_reference"
CODE_TRY_COUNTER_SLOT = "daily_ci_enroll__validation_code_error_counter"
NO_CODE_SOLUTION_SLOT = "daily_ci_enroll__no_code_solution"
DISPLAY_PRECONDITIONS_EXAMPLES_SLOT = "daily_ci_enroll__display_preconditions_examples"

ORDERED_FORM_SLOTS = [
    FIRST_NAME_SLOT,
    PHONE_NUMBER_SLOT,
    VALIDATION_CODE_SLOT,
    PRECONDITIONS_SLOT,
    HAS_DIALOGUE_SLOT,
]

ASK_PHONE_NUMBER_ACTION_NAME = f"action_ask_{PHONE_NUMBER_SLOT}"
ASK_VALIDATION_CODE_ACTION_NAME = f"action_ask_{VALIDATION_CODE_SLOT}"
ASK_PRECONDITIONS_ACTION_NAME = f"action_ask_{PRECONDITIONS_SLOT}"

LOCAL_ERROR_MAX = 2

NOT_DIGIT_REGEX = re.compile(r"\D")


class ActionOfferDailyCiEnrollment(Action):
    def name(self) -> Text:
        return "action_offer_daily_ci_enrollment"

    async def run(
        self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict
    ) -> List[EventType]:
        bind_logger(tracker)

        dispatcher.utter_message(template="utter_daily_ci_enroll__offer_checkin")
        dispatcher.utter_message(template="utter_daily_ci_enroll__explain_checkin_1")
        dispatcher.utter_message(template="utter_daily_ci_enroll__explain_checkin_2")
        dispatcher.utter_message(template="utter_ask_daily_ci_enroll__do_enroll")

        return []


class ActionAskPhoneNumber(Action):
    def name(self) -> Text:
        return ASK_PHONE_NUMBER_ACTION_NAME

    async def run(
        self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict
    ) -> List[EventType]:
        bind_logger(tracker)

        latest_bot_event = tracker.get_last_event_for("bot")
        latest_bot_message = (
            latest_bot_event["metadata"]["template_name"] if latest_bot_event else None
        )

        if tracker.get_slot(PHONE_TO_CHANGE_SLOT) is True:
            dispatcher.utter_message(template="utter_ask_phone_number_new")
        # Coming from cancel digression. Cannot find a better way.
        elif (
            tracker.get_slot(PHONE_TRY_COUNTER_SLOT) > 0
            or latest_bot_message == "utter_daily_ci_enroll__ok_continue"
        ):
            dispatcher.utter_message(template="utter_ask_phone_number_error")
        else:
            dispatcher.utter_message(template="utter_ask_phone_number")

        return []


class ActionAskValidationCode(Action):
    def name(self) -> Text:
        return ASK_VALIDATION_CODE_ACTION_NAME

    async def run(
        self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict
    ) -> List[EventType]:
        bind_logger(tracker)

        latest_bot_message = tracker.get_last_event_for("bot")["metadata"][
            "template_name"
        ]

        if latest_bot_message.startswith("utter_ask_daily_ci_enroll__validation_code"):
            dispatcher.utter_message(
                template="utter_ask_daily_ci_enroll__validation_code_error"
            )
        else:
            dispatcher.utter_message(
                template="utter_ask_daily_ci_enroll__validation_code"
            )

        return []


class ActionAskPreconditions(Action):
    def name(self) -> Text:
        return ASK_PRECONDITIONS_ACTION_NAME

    async def run(
        self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict
    ) -> List[EventType]:
        bind_logger(tracker)

        if tracker.get_slot(DISPLAY_PRECONDITIONS_EXAMPLES_SLOT) is True:
            dispatcher.utter_message(
                template="utter_daily_ci_enroll__explain_preconditions"
            )
            dispatcher.utter_message(
                template="utter_ask_daily_ci_enroll__preconditions_examples"
            )
        else:
            dispatcher.utter_message(template="utter_ask_preconditions")

        return []


class ActionDailyCiEnrollFormEnded(Action):
    def name(self) -> Text:
        return "action_daily_ci_enroll_form_ended"

    async def run(
        self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict
    ) -> List[EventType]:
        bind_logger(tracker)

        return []


class ValidateDailyCiEnrollForm(Action):
    def name(self) -> Text:
        return VALIDATE_ACTION_NAME

    async def run(
        self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict
    ) -> List[EventType]:
        bind_logger(tracker)

        extracted_slots: Dict[Text, Any] = tracker.form_slots_to_validate()

        validation_events: List[EventType] = []
        for slot_name, slot_value in extracted_slots.items():
            slot_events = [SlotSet(slot_name, slot_value)]

            if slot_name == FIRST_NAME_SLOT:
                slot_events = _validate_first_name(slot_value, dispatcher)
            elif slot_name == PHONE_NUMBER_SLOT:
                slot_events = await _validate_phone_number(
                    slot_value, dispatcher, tracker
                )
            elif slot_name == VALIDATION_CODE_SLOT:
                slot_events = await _validate_validation_code(
                    slot_value, dispatcher, tracker
                )
            elif slot_name == NO_CODE_SOLUTION_SLOT:
                slot_events = await _validate_no_code_solution(
                    slot_value, dispatcher, tracker
                )
            elif slot_name == PRECONDITIONS_SLOT:
                slot_events = _validate_preconditions(slot_value, dispatcher, tracker)
            elif slot_name == HAS_DIALOGUE_SLOT:  # last slot, enrollment completed
                try:
                    ci_enroll(tracker.current_slot_values())

                    dispatcher.utter_message(
                        template="utter_daily_ci_enroll__enroll_done_1"
                    )
                    dispatcher.utter_message(
                        template="utter_daily_ci_enroll__enroll_done_2"
                    )
                    dispatcher.utter_message(
                        template="utter_daily_ci_enroll__enroll_done_3"
                    )
                except:
                    dispatcher.utter_message(
                        template="utter_daily_ci_enroll__enroll_fail_1"
                    )
                    dispatcher.utter_message(
                        template="utter_daily_ci_enroll__enroll_fail_2"
                    )
                    dispatcher.utter_message(
                        template="utter_daily_ci_enroll__enroll_fail_3"
                    )

            validation_events.extend(slot_events)

        return validation_events


def _validate_first_name(
    value: Text, dispatcher: CollectingDispatcher
) -> List[EventType]:
    first_name = _get_first_name(value)

    if first_name:
        dispatcher.utter_message(
            template="utter_daily_ci_enroll__thanks_first_name", first_name=first_name,
        )
        dispatcher.utter_message(template="utter_daily_ci_enroll__text_message_checkin")

    return [SlotSet(FIRST_NAME_SLOT, first_name)]


async def _validate_phone_number(
    value: Text, dispatcher: CollectingDispatcher, tracker: Tracker,
) -> List[EventType]:

    phone_number = _get_phone_number(value)
    slots = [
        SlotSet(PHONE_NUMBER_SLOT, phone_number),
        SlotSet(PHONE_TO_CHANGE_SLOT, False),
    ]

    if phone_number is not None:
        dispatcher.utter_message(template="utter_daily_ci_enroll__acknowledge")

        return slots + await _send_validation_code(tracker, dispatcher, phone_number)

    (reached_max_errors, error_events) = _check_error_counter(
        PHONE_NUMBER_SLOT, PHONE_TRY_COUNTER_SLOT, tracker, dispatcher
    )

    if reached_max_errors:
        return error_events

    dispatcher.utter_message(template="utter_daily_ci_enroll__invalid_phone_number")
    return error_events + [SlotSet(PHONE_TO_CHANGE_SLOT, False)]


async def _validate_validation_code(
    value: Text, dispatcher: CollectingDispatcher, tracker: Tracker,
) -> List[EventType]:

    # User corrects phone number
    phone_number_in_message = _get_phone_number(tracker.latest_message.get("text", ""))
    if phone_number_in_message is not None:
        dispatcher.utter_message(
            template="utter_daily_ci_enroll__acknowledge_new_phone_number"
        )
        return [
            SlotSet(VALIDATION_CODE_SLOT, None),
            SlotSet(PHONE_NUMBER_SLOT, phone_number_in_message),
        ] + await _send_validation_code(tracker, dispatcher, phone_number_in_message)

    if value == "change_phone":
        return [
            SlotSet(VALIDATION_CODE_SLOT, None),
            SlotSet(PHONE_NUMBER_SLOT, None),
            SlotSet(PHONE_TO_CHANGE_SLOT, True),
        ]

    validation_code = _get_validation_code(value)
    if validation_code == tracker.get_slot(VALIDATION_CODE_REFERENCE_SLOT):
        dispatcher.utter_message(template="utter_daily_ci_enroll__thanks")
        return [SlotSet(VALIDATION_CODE_SLOT, validation_code)]

    (reached_max_errors, error_events) = _check_error_counter(
        VALIDATION_CODE_SLOT, CODE_TRY_COUNTER_SLOT, tracker, dispatcher
    )

    if value == "did_not_get_code":
        return (
            error_events
            if reached_max_errors
            else error_events + [SlotSet(NO_CODE_SOLUTION_SLOT, None)]
        )

    return error_events


async def _validate_no_code_solution(
    value: Text, dispatcher: CollectingDispatcher, tracker: Tracker
) -> List[EventType]:
    slots = [SlotSet(NO_CODE_SOLUTION_SLOT, value)]

    # User corrects phone number
    phone_number_in_message = _get_phone_number(tracker.latest_message.get("text", ""))
    if phone_number_in_message is not None:
        dispatcher.utter_message(
            template="utter_daily_ci_enroll__acknowledge_new_phone_number"
        )
        return [
            SlotSet(NO_CODE_SOLUTION_SLOT, "change_phone"),
            SlotSet(PHONE_NUMBER_SLOT, phone_number_in_message),
        ] + await _send_validation_code(tracker, dispatcher, phone_number_in_message)

    if value == "change_phone":
        return [
            SlotSet(NO_CODE_SOLUTION_SLOT, "change_phone"),
            SlotSet(PHONE_NUMBER_SLOT, None),
            SlotSet(PHONE_TO_CHANGE_SLOT, True),
        ]

    if value == "new_code":
        return slots + await _send_validation_code(tracker, dispatcher)

    raise ActionExecutionRejection(VALIDATE_ACTION_NAME)


def _validate_preconditions(
    value: Union[bool, Text], dispatcher: CollectingDispatcher, tracker: Tracker
) -> List[EventType]:

    if value == "dont_know":
        if tracker.get_slot(DISPLAY_PRECONDITIONS_EXAMPLES_SLOT) is True:
            dispatcher.utter_message(
                template="utter_daily_ci_enroll__note_preconditions"
            )
            return [SlotSet(PRECONDITIONS_SLOT, True)]
        else:
            return [
                SlotSet(PRECONDITIONS_SLOT, None),
                SlotSet(DISPLAY_PRECONDITIONS_EXAMPLES_SLOT, True),
            ]

    dispatcher.utter_message(template="utter_daily_ci_enroll__acknowledge")
    return [SlotSet(PRECONDITIONS_SLOT, value)]


def _get_first_name(text: Text) -> Optional[Text]:
    first_name = text.rstrip()

    return first_name if first_name else None


def _get_phone_number(text: Text) -> Optional[Text]:
    digits = NOT_DIGIT_REGEX.sub("", text)
    if len(digits) == 11 and digits[0] == "1":
        return digits
    if len(digits) == 10:
        return f"1{digits}"

    return None


def _get_validation_code(text: Text) -> Optional[Text]:
    digits = NOT_DIGIT_REGEX.sub("", text)
    valid_length = len(digits) == VALIDATION_CODE_LENGTH

    return digits if valid_length else None


async def _send_validation_code(
    tracker: Tracker,
    dispatcher: CollectingDispatcher,
    phone_number: Optional[str] = None,
) -> List[EventType]:
    if phone_number is None:
        phone_number = tracker.get_slot(PHONE_NUMBER_SLOT)

    first_name = tracker.get_slot(FIRST_NAME_SLOT)
    language = tracker.get_slot(LANGUAGE_SLOT)

    validation_code = await send_validation_code(phone_number, language, first_name)
    if validation_code is None:
        dispatcher.utter_message(
            template="utter_daily_ci_enroll__validation_code_not_sent_1"
        )
        dispatcher.utter_message(
            template="utter_daily_ci_enroll__validation_code_not_sent_2"
        )
        dispatcher.utter_message(template="utter_daily_ci_enroll__continue")

        return end_form_events(PHONE_NUMBER_SLOT)

    return [SlotSet(VALIDATION_CODE_REFERENCE_SLOT, validation_code)]


def _check_error_counter(
    slot_name: str,
    counter_slot_name: str,
    tracker: Tracker,
    dispatcher: CollectingDispatcher,
) -> Tuple[bool, List[EventType]]:
    try_counter = tracker.get_slot(counter_slot_name)

    if try_counter >= LOCAL_ERROR_MAX:
        dispatcher.utter_message(
            template="utter_daily_ci_enroll__invalid_phone_no_checkin"
        )
        return (
            True,
            [SlotSet(slot_name, SKIP_SLOT_PLACEHOLDER)] + end_form_events(slot_name),
        )

    return (
        False,
        [SlotSet(slot_name, None), SlotSet(counter_slot_name, try_counter + 1),],
    )


# Fills all the slots that were not yet asked. Workaround for https://github.com/RasaHQ/rasa/issues/6569
def end_form_events(actual_slot: str) -> List[EventType]:
    actual_slot_index = ORDERED_FORM_SLOTS.index(actual_slot)
    return [SlotSet(REQUESTED_SLOT, None)] + [
        SlotSet(slot, SKIP_SLOT_PLACEHOLDER)
        for slot in ORDERED_FORM_SLOTS[actual_slot_index + 1 :]
    ]
