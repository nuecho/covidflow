from unittest import TestCase

import pytest
from asynctest.mock import MagicMock, patch
from rasa_sdk.events import ActionExecuted, BotUttered, SlotSet
from rasa_sdk.forms import REQUESTED_SLOT

from covidflow.actions.daily_ci_enroll_form import (
    CODE_TRY_COUNTER_SLOT,
    DISPLAY_PRECONDITIONS_EXAMPLES_SLOT,
    FORM_NAME,
    NO_CODE_SOLUTION_SLOT,
    PHONE_TO_CHANGE_SLOT,
    PHONE_TRY_COUNTER_SLOT,
    VALIDATION_CODE_REFERENCE_SLOT,
    VALIDATION_CODE_SLOT,
    ActionAskPhoneNumber,
    ActionAskPreconditions,
    ActionAskValidationCode,
    ActionDailyCiEnrollFormEnded,
    ActionOfferDailyCiEnrollment,
    ValidateDailyCiEnrollForm,
    _get_first_name,
    _get_phone_number,
    _get_validation_code,
)
from covidflow.constants import (
    FIRST_NAME_SLOT,
    HAS_DIALOGUE_SLOT,
    PHONE_NUMBER_SLOT,
    PRECONDITIONS_SLOT,
    SKIP_SLOT_PLACEHOLDER,
)

from .action_test_helper import ActionTestCase
from .validate_action_test_helper import ValidateActionTestCase

FIRST_NAME = "John"
PHONE_NUMBER = "15141234567"
VALIDATION_CODE = "4567"

DOMAIN = {
    "responses": {
        "utter_ask_daily_ci_enroll__wants_cancel_error": [{"text": ""}],
        "utter_ask_daily_ci_enroll__no_code_solution_error": [{"text": ""}],
        "utter_ask_preconditions_error": [{"text": ""}],
        "utter_ask_daily_ci_enroll__preconditions_examples_error": [{"text": ""}],
    }
}


def AsyncMock(*args, **kwargs):
    mock = MagicMock(*args, **kwargs)

    async def mock_coroutine(*args, **kwargs):
        return mock(*args, **kwargs)

    mock_coroutine.mock = mock
    return mock_coroutine


class TestActionOfferDailyCiEnrollment(ActionTestCase):
    def setUp(self):
        super().setUp()
        self.action = ActionOfferDailyCiEnrollment()

    @pytest.mark.asyncio
    async def test_form_activation(self):
        await self.run_action(self.create_tracker())

        self.assert_events([])

        self.assert_templates(
            [
                "utter_daily_ci_enroll__offer_checkin",
                "utter_daily_ci_enroll__explain_checkin_1",
                "utter_daily_ci_enroll__explain_checkin_2",
                "utter_ask_daily_ci_enroll__do_enroll",
            ]
        )


class TestActionAskPhoneNumber(ActionTestCase):
    def setUp(self):
        super().setUp()
        self.action = ActionAskPhoneNumber()

    @pytest.mark.asyncio
    async def test_first_time(self):
        tracker = self.create_tracker()

        await self.run_action(tracker)

        self.assert_events([])

        self.assert_templates(["utter_ask_phone_number"])

    @pytest.mark.asyncio
    async def test_after_error(self):
        tracker = self.create_tracker(slots={PHONE_TRY_COUNTER_SLOT: 1})

        await self.run_action(tracker)

        self.assert_events([])

        self.assert_templates(["utter_ask_phone_number_error"])

    @pytest.mark.asyncio
    async def test_has_to_be_changed(self):
        tracker = self.create_tracker(
            slots={
                PHONE_TRY_COUNTER_SLOT: 1,  # change condition should prevail
                PHONE_TO_CHANGE_SLOT: True,
            }
        )

        await self.run_action(tracker)

        self.assert_events([])

        self.assert_templates(["utter_ask_phone_number_new"])

    @pytest.mark.asyncio
    async def test_after_digression(self):
        tracker = self.create_tracker(
            events=[
                BotUttered(
                    "ok?",
                    metadata={"template_name": "utter_daily_ci_enroll__ok_continue"},
                )
            ]
        )

        await self.run_action(tracker)

        self.assert_events([])

        self.assert_templates(["utter_ask_phone_number_error"])


class TestActionAskValidationCode(ActionTestCase):
    def setUp(self):
        super().setUp()
        self.action = ActionAskValidationCode()

    @pytest.mark.asyncio
    async def test_code_just_asked(self):
        tracker = self.create_tracker(
            events=[
                BotUttered(
                    "asking validation code",
                    metadata={
                        "template_name": "utter_ask_daily_ci_enroll__validation_code"
                    },
                )
            ]
        )

        await self.run_action(tracker)

        self.assert_events([])

        self.assert_templates(["utter_ask_daily_ci_enroll__validation_code_error"])

    @pytest.mark.asyncio
    async def test_code_just_asked_with_error(self):
        tracker = self.create_tracker(
            events=[
                BotUttered(
                    "asking validation code",
                    metadata={
                        "template_name": "utter_ask_daily_ci_enroll__validation_code_error"
                    },
                )
            ]
        )

        await self.run_action(tracker)

        self.assert_events([])

        self.assert_templates(["utter_ask_daily_ci_enroll__validation_code_error"])

    @pytest.mark.asyncio
    async def test_code_not_just_asked(self):
        tracker = self.create_tracker(
            events=[
                BotUttered(
                    "asking phone number",
                    metadata={"template_name": "utter_ask_phone_number"},
                )
            ]
        )

        await self.run_action(tracker)

        self.assert_events([])

        self.assert_templates(["utter_ask_daily_ci_enroll__validation_code"])


class TestActionAskPreconditions(ActionTestCase):
    def setUp(self):
        super().setUp()
        self.action = ActionAskPreconditions()

    @pytest.mark.asyncio
    async def test_first_time(self):
        tracker = self.create_tracker()

        await self.run_action(tracker)

        self.assert_events([])

        self.assert_templates(["utter_ask_preconditions"])

    @pytest.mark.asyncio
    async def test_need_examples(self):
        tracker = self.create_tracker(slots={DISPLAY_PRECONDITIONS_EXAMPLES_SLOT: True})

        await self.run_action(tracker)

        self.assert_events([])

        self.assert_templates(
            [
                "utter_daily_ci_enroll__explain_preconditions",
                "utter_ask_daily_ci_enroll__preconditions_examples",
            ]
        )


class TestActionDailyCiEnrollFormEnded(ActionTestCase):
    def setUp(self):
        super().setUp()
        self.action = ActionDailyCiEnrollFormEnded()

    @pytest.mark.asyncio
    async def test_does_nothing(self):
        await self.run_action(self.create_tracker())

        self.assert_templates([])

        self.assert_events([])


class TestValidateDailyCiEnrollForm(ValidateActionTestCase):
    def setUp(self):
        super().setUp()
        self.action = ValidateDailyCiEnrollForm()
        self.form_name = FORM_NAME

    @pytest.mark.asyncio
    async def test_activation(self):
        await self.check_activation()

    @pytest.mark.asyncio
    async def test_provide_first_name(self):
        templates = [
            "utter_daily_ci_enroll__thanks_first_name",
            "utter_daily_ci_enroll__text_message_checkin",
        ]

        await self.check_slot_value_accepted(
            FIRST_NAME_SLOT, FIRST_NAME, templates=templates
        )

    @pytest.mark.asyncio
    async def test_provide_invalid_first_name(self):
        await self.check_slot_value_rejected(FIRST_NAME_SLOT, " ")

    @pytest.mark.asyncio
    @patch(
        "covidflow.actions.daily_ci_enroll_form.send_validation_code",
        new=AsyncMock(return_value=VALIDATION_CODE),
    )
    async def test_provide_phone_number(self):
        templates = ["utter_daily_ci_enroll__acknowledge"]
        extra_events = [
            SlotSet(PHONE_TO_CHANGE_SLOT, False),
            SlotSet(VALIDATION_CODE_REFERENCE_SLOT, VALIDATION_CODE),
        ]

        await self.check_slot_value_accepted(
            PHONE_NUMBER_SLOT,
            PHONE_NUMBER,
            templates=templates,
            extra_events=extra_events,
        )

    @pytest.mark.asyncio
    @patch(
        "covidflow.actions.daily_ci_enroll_form.send_validation_code",
        new=AsyncMock(return_value=None),
    )
    async def test_provide_phone_number_sms_error(self):
        templates = [
            "utter_daily_ci_enroll__acknowledge",
            "utter_daily_ci_enroll__validation_code_not_sent_1",
            "utter_daily_ci_enroll__validation_code_not_sent_2",
            "utter_daily_ci_enroll__continue",
        ]
        extra_events = [
            SlotSet(PHONE_TO_CHANGE_SLOT, False),
            SlotSet(REQUESTED_SLOT, None),
            SlotSet(VALIDATION_CODE_SLOT, SKIP_SLOT_PLACEHOLDER),
            SlotSet(PRECONDITIONS_SLOT, SKIP_SLOT_PLACEHOLDER),
            SlotSet(HAS_DIALOGUE_SLOT, SKIP_SLOT_PLACEHOLDER),
        ]

        await self.check_slot_value_accepted(
            PHONE_NUMBER_SLOT,
            PHONE_NUMBER,
            templates=templates,
            extra_events=extra_events,
        )

    @pytest.mark.asyncio
    async def test_provide_first_invalid_phone_number(self):
        templates = ["utter_daily_ci_enroll__invalid_phone_number"]
        extra_events = [
            SlotSet(PHONE_TO_CHANGE_SLOT, False),
            SlotSet(PHONE_TRY_COUNTER_SLOT, 1),
        ]

        await self.check_slot_value_rejected(
            PHONE_NUMBER_SLOT,
            "1nval1d ph0n3 numb3r",
            templates=templates,
            extra_events=extra_events,
        )

    @pytest.mark.asyncio
    async def test_provide_second_invalid_phone_number(self):
        previous_slots = {PHONE_TRY_COUNTER_SLOT: 1}
        templates = ["utter_daily_ci_enroll__invalid_phone_number"]
        extra_events = [
            SlotSet(PHONE_TO_CHANGE_SLOT, False),
            SlotSet(PHONE_TRY_COUNTER_SLOT, 2),
        ]

        await self.check_slot_value_rejected(
            PHONE_NUMBER_SLOT,
            "1nval1d ph0n3 numb3r",
            templates=templates,
            extra_events=extra_events,
            previous_slots=previous_slots,
        )

    @pytest.mark.asyncio
    async def test_provide_third_invalid_phone_number(self):
        previous_slots = {PHONE_TRY_COUNTER_SLOT: 2}
        templates = ["utter_daily_ci_enroll__invalid_phone_no_checkin"]
        extra_events = [
            SlotSet(REQUESTED_SLOT, None),
            SlotSet(VALIDATION_CODE_SLOT, SKIP_SLOT_PLACEHOLDER),
            SlotSet(PRECONDITIONS_SLOT, SKIP_SLOT_PLACEHOLDER),
            SlotSet(HAS_DIALOGUE_SLOT, SKIP_SLOT_PLACEHOLDER),
        ]

        await self.check_slot_value_stored(
            PHONE_NUMBER_SLOT,
            "1nval1d ph0n3 numb3r",
            SKIP_SLOT_PLACEHOLDER,
            templates=templates,
            extra_events=extra_events,
            previous_slots=previous_slots,
        )

    @pytest.mark.asyncio
    async def test_provide_validation_code(self):
        previous_slots = {VALIDATION_CODE_REFERENCE_SLOT: VALIDATION_CODE}
        templates = ["utter_daily_ci_enroll__thanks"]

        await self.check_slot_value_accepted(
            VALIDATION_CODE_SLOT,
            VALIDATION_CODE,
            templates=templates,
            previous_slots=previous_slots,
        )

    @pytest.mark.asyncio
    async def test_provide_first_invalid_validation_code(self):
        previous_slots = {VALIDATION_CODE_REFERENCE_SLOT: VALIDATION_CODE}
        extra_events = [SlotSet(CODE_TRY_COUNTER_SLOT, 1)]

        await self.check_slot_value_rejected(
            VALIDATION_CODE_SLOT,
            "4321",
            extra_events=extra_events,
            previous_slots=previous_slots,
        )

    @pytest.mark.asyncio
    async def test_provide_second_invalid_validation_code(self):
        previous_slots = {
            VALIDATION_CODE_REFERENCE_SLOT: VALIDATION_CODE,
            CODE_TRY_COUNTER_SLOT: 1,
        }
        extra_events = [SlotSet(CODE_TRY_COUNTER_SLOT, 2)]

        await self.check_slot_value_rejected(
            VALIDATION_CODE_SLOT,
            "4321",
            extra_events=extra_events,
            previous_slots=previous_slots,
        )

    @pytest.mark.asyncio
    async def test_provide_third_invalid_validation_code(self):
        previous_slots = {
            VALIDATION_CODE_REFERENCE_SLOT: VALIDATION_CODE,
            CODE_TRY_COUNTER_SLOT: 2,
        }
        extra_events = [
            SlotSet(REQUESTED_SLOT, None),
            SlotSet(PRECONDITIONS_SLOT, SKIP_SLOT_PLACEHOLDER),
            SlotSet(HAS_DIALOGUE_SLOT, SKIP_SLOT_PLACEHOLDER),
        ]
        templates = ["utter_daily_ci_enroll__invalid_phone_no_checkin"]

        await self.check_slot_value_stored(
            VALIDATION_CODE_SLOT,
            "4321",
            SKIP_SLOT_PLACEHOLDER,
            extra_events=extra_events,
            previous_slots=previous_slots,
            templates=templates,
        )

    @pytest.mark.asyncio
    async def test_provide_validation_code_change_phone(self):
        extra_events = [
            SlotSet(PHONE_NUMBER_SLOT, None),
            SlotSet(PHONE_TO_CHANGE_SLOT, True),
        ]
        await self.check_slot_value_rejected(
            VALIDATION_CODE_SLOT, "change_phone", extra_events
        )

    @pytest.mark.asyncio
    @patch(
        "covidflow.actions.daily_ci_enroll_form.send_validation_code",
        new=AsyncMock(return_value=VALIDATION_CODE),
    )
    async def test_provide_validation_code_phone_number(self):
        tracker = self.create_tracker(
            events=[
                ActionExecuted(self.form_name),
                SlotSet(VALIDATION_CODE_SLOT, PHONE_NUMBER),
            ],
            slots={VALIDATION_CODE_REFERENCE_SLOT: VALIDATION_CODE},
            intent="change_phone",
            text=PHONE_NUMBER,
        )

        await self.run_action(tracker)

        self.assert_events(
            [
                SlotSet(VALIDATION_CODE_SLOT, None),
                SlotSet(PHONE_NUMBER_SLOT, PHONE_NUMBER),
                SlotSet(VALIDATION_CODE_REFERENCE_SLOT, VALIDATION_CODE),
            ]
        )

        self.assert_templates(["utter_daily_ci_enroll__acknowledge_new_phone_number"])

    @pytest.mark.asyncio
    @patch(
        "covidflow.actions.daily_ci_enroll_form.send_validation_code",
        new=AsyncMock(return_value=VALIDATION_CODE),
    )
    async def test_provide_validation_code_change_phone_with_new(self):
        tracker = self.create_tracker(
            events=[
                ActionExecuted(self.form_name),
                SlotSet(VALIDATION_CODE_SLOT, "change_phone"),
            ],
            slots={VALIDATION_CODE_REFERENCE_SLOT: VALIDATION_CODE},
            intent="change_phone",
            text=PHONE_NUMBER,
        )

        await self.run_action(tracker)

        self.assert_events(
            [
                SlotSet(VALIDATION_CODE_SLOT, None),
                SlotSet(PHONE_NUMBER_SLOT, PHONE_NUMBER),
                SlotSet(VALIDATION_CODE_REFERENCE_SLOT, VALIDATION_CODE),
            ]
        )

        self.assert_templates(["utter_daily_ci_enroll__acknowledge_new_phone_number"])

    @pytest.mark.asyncio
    async def test_provide_validation_code_did_not_get_code_first_time(self):
        extra_events = [
            SlotSet(CODE_TRY_COUNTER_SLOT, 1),
            SlotSet(NO_CODE_SOLUTION_SLOT, None),
        ]
        await self.check_slot_value_rejected(
            VALIDATION_CODE_SLOT, "did_not_get_code", extra_events=extra_events
        )

    @pytest.mark.asyncio
    async def test_provide_validation_code_did_not_get_code_second_time(self):
        previous_slots = {CODE_TRY_COUNTER_SLOT: 1}
        extra_events = [
            SlotSet(CODE_TRY_COUNTER_SLOT, 2),
            SlotSet(NO_CODE_SOLUTION_SLOT, None),
        ]
        await self.check_slot_value_rejected(
            VALIDATION_CODE_SLOT,
            "did_not_get_code",
            extra_events=extra_events,
            previous_slots=previous_slots,
        )

    @pytest.mark.asyncio
    async def test_provide_validation_code_did_not_get_code_third_time(self):
        previous_slots = {CODE_TRY_COUNTER_SLOT: 2}
        templates = ["utter_daily_ci_enroll__invalid_phone_no_checkin"]
        extra_events = [
            SlotSet(REQUESTED_SLOT, None),
            SlotSet(PRECONDITIONS_SLOT, SKIP_SLOT_PLACEHOLDER),
            SlotSet(HAS_DIALOGUE_SLOT, SKIP_SLOT_PLACEHOLDER),
        ]
        await self.check_slot_value_stored(
            VALIDATION_CODE_SLOT,
            "did_not_get_code",
            SKIP_SLOT_PLACEHOLDER,
            extra_events=extra_events,
            previous_slots=previous_slots,
            templates=templates,
        )

    @pytest.mark.asyncio
    @patch(
        "covidflow.actions.daily_ci_enroll_form.send_validation_code",
        new=AsyncMock(return_value=VALIDATION_CODE),
    )
    async def test_provide_no_code_solution_new_code(self):
        extra_events = [SlotSet(VALIDATION_CODE_REFERENCE_SLOT, VALIDATION_CODE)]

        await self.check_slot_value_accepted(
            NO_CODE_SOLUTION_SLOT, "new_code", extra_events
        )

    @pytest.mark.asyncio
    @patch(
        "covidflow.actions.daily_ci_enroll_form.send_validation_code",
        new=AsyncMock(return_value=None),
    )
    async def test_provide_no_code_solution_new_code_sms_error(self):
        templates = [
            "utter_daily_ci_enroll__validation_code_not_sent_1",
            "utter_daily_ci_enroll__validation_code_not_sent_2",
            "utter_daily_ci_enroll__continue",
        ]
        extra_events = [
            SlotSet(REQUESTED_SLOT, None),
            SlotSet(VALIDATION_CODE_SLOT, SKIP_SLOT_PLACEHOLDER),
            SlotSet(PRECONDITIONS_SLOT, SKIP_SLOT_PLACEHOLDER),
            SlotSet(HAS_DIALOGUE_SLOT, SKIP_SLOT_PLACEHOLDER),
        ]

        await self.check_slot_value_accepted(
            NO_CODE_SOLUTION_SLOT,
            "new_code",
            templates=templates,
            extra_events=extra_events,
        )

    @pytest.mark.asyncio
    async def test_provide_no_code_solution_change_phone(self):
        extra_events = [
            SlotSet(PHONE_NUMBER_SLOT, None),
            SlotSet(PHONE_TO_CHANGE_SLOT, True),
        ]
        await self.check_slot_value_accepted(
            NO_CODE_SOLUTION_SLOT, "change_phone", extra_events
        )

    @pytest.mark.asyncio
    @patch(
        "covidflow.actions.daily_ci_enroll_form.send_validation_code",
        new=AsyncMock(return_value=VALIDATION_CODE),
    )
    async def test_provide_no_code_solution_phone_number(self):
        tracker = self.create_tracker(
            events=[
                ActionExecuted(self.form_name),
                SlotSet(NO_CODE_SOLUTION_SLOT, PHONE_NUMBER),
            ],
            slots={VALIDATION_CODE_REFERENCE_SLOT: VALIDATION_CODE},
            intent="change_phone",
            text=PHONE_NUMBER,
        )

        await self.run_action(tracker)

        self.assert_events(
            [
                SlotSet(NO_CODE_SOLUTION_SLOT, "change_phone"),
                SlotSet(PHONE_NUMBER_SLOT, PHONE_NUMBER),
                SlotSet(VALIDATION_CODE_REFERENCE_SLOT, VALIDATION_CODE),
            ]
        )

        self.assert_templates(["utter_daily_ci_enroll__acknowledge_new_phone_number"])

    @pytest.mark.asyncio
    async def test_provide_preconditions_affirm(self):
        templates = ["utter_daily_ci_enroll__acknowledge"]

        await self.check_slot_value_accepted(
            PRECONDITIONS_SLOT, True, templates=templates
        )

    @pytest.mark.asyncio
    async def test_provide_preconditions_false(self):
        templates = ["utter_daily_ci_enroll__acknowledge"]

        await self.check_slot_value_accepted(
            PRECONDITIONS_SLOT, False, templates=templates
        )

    @pytest.mark.asyncio
    async def test_provide_preconditions_dont_know(self):
        extra_events = [SlotSet(DISPLAY_PRECONDITIONS_EXAMPLES_SLOT, True)]

        await self.check_slot_value_rejected(
            PRECONDITIONS_SLOT, "dont_know", extra_events=extra_events
        )

    @pytest.mark.asyncio
    async def test_provide_preconditions_dont_know_second_time(self):
        previous_slots = {DISPLAY_PRECONDITIONS_EXAMPLES_SLOT: True}
        templates = ["utter_daily_ci_enroll__note_preconditions"]

        await self.check_slot_value_stored(
            PRECONDITIONS_SLOT,
            "dont_know",
            True,
            previous_slots=previous_slots,
            templates=templates,
        )

    @pytest.mark.asyncio
    @patch("covidflow.actions.daily_ci_enroll_form.ci_enroll")
    async def test_provide_has_dialogue_true(self, mock_ci_enroll):
        previous_slots = {
            REQUESTED_SLOT: HAS_DIALOGUE_SLOT,
            FIRST_NAME_SLOT: FIRST_NAME,
            PHONE_NUMBER_SLOT: PHONE_NUMBER,
            VALIDATION_CODE_SLOT: VALIDATION_CODE,
            PRECONDITIONS_SLOT: True,
        }
        templates = [
            "utter_daily_ci_enroll__enroll_done_1",
            "utter_daily_ci_enroll__enroll_done_2",
            "utter_daily_ci_enroll__enroll_done_3",
        ]

        await self.check_slot_value_accepted(
            HAS_DIALOGUE_SLOT, True, previous_slots=previous_slots, templates=templates
        )

        mock_ci_enroll.assert_called()

    @pytest.mark.asyncio
    @patch("covidflow.actions.daily_ci_enroll_form.ci_enroll")
    async def test_provide_has_dialogue_false(self, mock_ci_enroll):
        previous_slots = {
            REQUESTED_SLOT: HAS_DIALOGUE_SLOT,
            FIRST_NAME_SLOT: FIRST_NAME,
            PHONE_NUMBER_SLOT: PHONE_NUMBER,
            VALIDATION_CODE_SLOT: VALIDATION_CODE,
            PRECONDITIONS_SLOT: True,
        }
        templates = [
            "utter_daily_ci_enroll__enroll_done_1",
            "utter_daily_ci_enroll__enroll_done_2",
            "utter_daily_ci_enroll__enroll_done_3",
        ]

        await self.check_slot_value_accepted(
            HAS_DIALOGUE_SLOT, False, previous_slots=previous_slots, templates=templates
        )

        mock_ci_enroll.assert_called()

    @pytest.mark.asyncio
    @patch("covidflow.actions.daily_ci_enroll_form.ci_enroll", side_effect=Exception)
    async def test_provide_has_dialogue_enrollment_failed(self, mock_ci_enroll):
        previous_slots = {
            REQUESTED_SLOT: HAS_DIALOGUE_SLOT,
            FIRST_NAME_SLOT: FIRST_NAME,
            PHONE_NUMBER_SLOT: PHONE_NUMBER,
            VALIDATION_CODE_SLOT: VALIDATION_CODE,
            PRECONDITIONS_SLOT: True,
        }
        templates = [
            "utter_daily_ci_enroll__enroll_fail_1",
            "utter_daily_ci_enroll__enroll_fail_2",
            "utter_daily_ci_enroll__enroll_fail_3",
        ]

        await self.check_slot_value_accepted(
            HAS_DIALOGUE_SLOT, False, previous_slots=previous_slots, templates=templates
        )

        mock_ci_enroll.assert_called()


class TestExtractors(TestCase):
    def test_get_first_name(self):
        self.assertEqual(_get_first_name("john"), "john")
        self.assertEqual(_get_first_name("John"), "John")
        self.assertEqual(_get_first_name("john john"), "john john")

        # At the moment, we can't extract the name
        self.assertEqual(_get_first_name("it's John!"), "it's John!")

    def test_get_phone_number(self):
        self.assertEqual(_get_phone_number("5145554567"), "15145554567")
        self.assertEqual(_get_phone_number("15145554567"), "15145554567")
        self.assertEqual(_get_phone_number("514-555-4567"), "15145554567")
        self.assertEqual(_get_phone_number("1 (514)-555-4567"), "15145554567")
        self.assertEqual(_get_phone_number("it's 514-555-4567!"), "15145554567")
        self.assertEqual(_get_phone_number("it's 1 514 555 4567"), "15145554567")
        self.assertEqual(_get_phone_number("145554567"), None)
        self.assertEqual(_get_phone_number("25145554567"), None)

    def test_get_validation_code(self):
        self.assertEqual(_get_validation_code("its 4567"), "4567")
        self.assertEqual(_get_validation_code("4567"), "4567")

        self.assertEqual(_get_validation_code("45678"), None)
        self.assertEqual(_get_validation_code("514"), None)
