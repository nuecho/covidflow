import pytest
from rasa_sdk.events import ConversationPaused

from covidflow.actions.action_qa_goodbye import ActionQaGoodbye
from covidflow.constants import CANCEL_CI_SLOT, LAST_SYMPTOMS_SLOT, Symptoms

from .action_test_helper import ActionTestCase


class ActionQAGoodbyeTest(ActionTestCase):
    def setUp(self):
        super().setUp()
        self.action = ActionQaGoodbye()

    @pytest.mark.asyncio
    async def test_continue_ci(self):
        tracker = self.create_tracker(slots={LAST_SYMPTOMS_SLOT: Symptoms.MILD})

        await self.run_action(tracker)

        self.assert_events([ConversationPaused()])

        self.assert_templates(
            ["utter_daily_ci_qa_will_contact_tomorrow", "utter_goodbye"]
        )

    @pytest.mark.asyncio
    async def test_cancel_ci(self):
        tracker = self.create_tracker(
            slots={LAST_SYMPTOMS_SLOT: Symptoms.MILD, CANCEL_CI_SLOT: True}
        )

        await self.run_action(tracker)

        self.assert_events([ConversationPaused()])

        self.assert_templates(["utter_goodbye"])

    @pytest.mark.asyncio
    async def test_not_in_ci(self):
        tracker = self.create_tracker()

        await self.run_action(tracker)

        self.assert_events([ConversationPaused()])

        self.assert_templates(["utter_goodbye"])
