import pytest
from rasa_sdk.events import SlotSet
from rasa_sdk.forms import REQUESTED_SLOT

from covidflow.actions.daily_ci_feel_worse_form import (
    FORM_NAME,
    HAS_DIFF_BREATHING_WORSENED_SLOT,
    ActionAskDailyCiFeelWorseFormHasCough,
    ActionAskDailyCiFeelWorseFormHasDiffBreathing,
    ValidateDailyCiFeelWorseForm,
)
from covidflow.constants import (
    HAS_COUGH_SLOT,
    HAS_DIFF_BREATHING_SLOT,
    HAS_FEVER_SLOT,
    LAST_HAS_COUGH_SLOT,
    LAST_HAS_DIFF_BREATHING_SLOT,
    SEVERE_SYMPTOMS_SLOT,
    SKIP_SLOT_PLACEHOLDER,
    SYMPTOMS_SLOT,
    Symptoms,
)

from .action_test_helper import ActionTestCase
from .validate_action_test_helper import ValidateActionTestCase


class TestActionAskDailyCiFeelWorseFormHasDiffBreathing(ActionTestCase):
    def setUp(self):
        super().setUp()
        self.action = ActionAskDailyCiFeelWorseFormHasDiffBreathing()

    @pytest.mark.asyncio
    async def test_did_not_have_diff_breathing(self):
        tracker = self.create_tracker(slots={LAST_HAS_DIFF_BREATHING_SLOT: False})

        await self.run_action(tracker)

        self.assert_events([])

        self.assert_templates(["utter_ask_daily_ci_feel_worse_form_has_diff_breathing"])

    @pytest.mark.asyncio
    async def test_already_had_diff_breathing(self):
        tracker = self.create_tracker(slots={LAST_HAS_DIFF_BREATHING_SLOT: True})

        await self.run_action(tracker)

        self.assert_events([])

        self.assert_templates(
            ["utter_ask_daily_ci_feel_worse_form_has_diff_breathing__still"]
        )


class TestActionAskDailyCiFeelWorseFormHasCough(ActionTestCase):
    def setUp(self):
        super().setUp()
        self.action = ActionAskDailyCiFeelWorseFormHasCough()

    @pytest.mark.asyncio
    async def test_did_not_have_cough(self):
        tracker = self.create_tracker(slots={LAST_HAS_COUGH_SLOT: False})

        await self.run_action(tracker)

        self.assert_events([])

        self.assert_templates(["utter_ask_daily_ci_feel_worse_form_has_cough"])

    @pytest.mark.asyncio
    async def test_already_had_cough(self):
        tracker = self.create_tracker(slots={LAST_HAS_COUGH_SLOT: True})

        await self.run_action(tracker)

        self.assert_events([])

        self.assert_templates(["utter_ask_daily_ci_feel_worse_form_has_cough__still"])


class TestValidateDailyCiFeelWorseForm(ValidateActionTestCase):
    def setUp(self):
        super().setUp()
        self.action = ValidateDailyCiFeelWorseForm()
        self.form_name = FORM_NAME

    @pytest.mark.asyncio
    async def test_activation(self):
        await self.check_activation()

    @pytest.mark.asyncio
    async def test_severe_symptoms(self):
        extra_events = [
            SlotSet(SYMPTOMS_SLOT, Symptoms.SEVERE),
            SlotSet(REQUESTED_SLOT, None),
            SlotSet(HAS_FEVER_SLOT, SKIP_SLOT_PLACEHOLDER),
            SlotSet(HAS_DIFF_BREATHING_SLOT, SKIP_SLOT_PLACEHOLDER),
            SlotSet(HAS_DIFF_BREATHING_WORSENED_SLOT, SKIP_SLOT_PLACEHOLDER),
            SlotSet(HAS_COUGH_SLOT, SKIP_SLOT_PLACEHOLDER),
        ]
        await self.check_slot_value_accepted(
            SEVERE_SYMPTOMS_SLOT, True, extra_events=extra_events
        )

    @pytest.mark.asyncio
    async def test_no_severe_symptoms(self):
        templates = ["utter_daily_ci_feel_worse_severe_symptoms_false"]

        await self.check_slot_value_accepted(
            SEVERE_SYMPTOMS_SLOT, False, templates=templates
        )

    @pytest.mark.asyncio
    async def test_fever(self):
        templates = [
            "utter_daily_ci_has_fever_true_1",
            "utter_daily_ci_has_fever_true_2",
            "utter_daily_ci_has_fever_true_3",
        ]

        await self.check_slot_value_accepted(HAS_FEVER_SLOT, True, templates=templates)

    @pytest.mark.asyncio
    async def test_no_fever(self):
        templates = ["utter_daily_ci_feel_worse_has_fever_false"]

        await self.check_slot_value_accepted(HAS_FEVER_SLOT, False, templates=templates)

    @pytest.mark.asyncio
    async def test_has_diff_breathing(self):
        extra_events = [SlotSet(HAS_COUGH_SLOT, SKIP_SLOT_PLACEHOLDER)]

        await self.check_slot_value_accepted(
            HAS_DIFF_BREATHING_SLOT, True, extra_events=extra_events
        )

    @pytest.mark.asyncio
    async def test_no_diff_breathing(self):
        templates = ["utter_daily_ci_feel_worse_has_diff_breathing_false"]
        extra_events = [
            SlotSet(HAS_DIFF_BREATHING_WORSENED_SLOT, SKIP_SLOT_PLACEHOLDER)
        ]

        await self.check_slot_value_accepted(
            HAS_DIFF_BREATHING_SLOT,
            False,
            templates=templates,
            extra_events=extra_events,
        )

    @pytest.mark.asyncio
    async def test_diff_breathing_worsened(self):
        templates = [
            "utter_daily_ci_feel_worse_has_diff_breathing_worsened_true_1",
            "utter_daily_ci_feel_worse_has_diff_breathing_worsened_true_2",
        ]

        await self.check_slot_value_accepted(
            HAS_DIFF_BREATHING_WORSENED_SLOT, True, templates=templates
        )

    @pytest.mark.asyncio
    async def test_diff_breathing_not_worsened(self):
        templates = [
            "utter_daily_ci_feel_worse_has_diff_breathing_worsened_false_1",
            "utter_daily_ci_feel_worse_has_diff_breathing_worsened_false_2",
        ]

        await self.check_slot_value_accepted(
            HAS_DIFF_BREATHING_WORSENED_SLOT, False, templates=templates
        )

    @pytest.mark.asyncio
    async def test_has_cough(self):
        templates = [
            "utter_daily_ci_has_cough_true_1",
            "utter_daily_ci_has_cough_true_2",
        ]

        await self.check_slot_value_accepted(HAS_COUGH_SLOT, True, templates=templates)

    @pytest.mark.asyncio
    async def test_has_no_cough(self):
        templates = [
            "utter_daily_ci_has_cough_false",
            "utter_daily_ci_feel_worse_has_cough_false",
        ]

        await self.check_slot_value_accepted(HAS_COUGH_SLOT, False, templates=templates)
