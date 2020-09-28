import pytest
from asynctest.mock import patch
from rasa_sdk.events import SlotSet

from covidflow.actions.action_daily_ci_cancel_ci import ActionDailyCiCancelCi
from covidflow.constants import CANCEL_CI_SLOT

from .action_test_helper import ActionTestCase


class ActionDailyCiCancelCiTest(ActionTestCase):
    def setUp(self):
        super().setUp()
        self.action = ActionDailyCiCancelCi()

    @pytest.mark.asyncio
    @patch("covidflow.actions.action_daily_ci_cancel_ci.cancel_reminder")
    async def test_early_opt_out(self, mock_cancel_reminder):
        tracker = self.create_tracker()

        await self.run_action(tracker)

        self.assert_events([SlotSet(CANCEL_CI_SLOT, True)])

        self.assert_templates(
            [
                "utter_daily_ci__acknowledge_cancel_ci",
                "utter_daily_ci__cancel_ci_recommendation",
            ]
        )

        mock_cancel_reminder.assert_called()
