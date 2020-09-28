from typing import List

import pytest
from rasa_sdk.events import SlotSet

from covidflow.actions.daily_ci_keep_or_cancel import (
    ActionCheckMandatoryCi,
    ActionKeepCiRecommendations,
)
from covidflow.constants import (
    AGE_OVER_65_SLOT,
    MANDATORY_CI_SLOT,
    PRECONDITIONS_SLOT,
    PROVINCE_SLOT,
    SYMPTOMS_SLOT,
    Symptoms,
)

from .action_test_helper import ActionTestCase

DOMAIN = {
    "responses": {
        "provincial_info_link_qc": [{"text": "info link qc"}],
        "provincial_info_link_bc": [{"text": "info link bc"}],
    }
}

RECOMMENDATIONS_VULNERABLE__NOT_HAS_211 = [
    "utter_daily_ci__recommendations__more_information_vulnerable_population",
    "utter_daily_ci__recommendations__tomorrow_ci",
    "utter_daily_ci__recommendations__recommendation_1",
    "utter_daily_ci__recommendations__recommendation_2",
]

RECOMMENDATIONS_GENERAL__NOT_HAS_211 = [
    "utter_daily_ci__recommendations__more_information_general",
    "utter_daily_ci__recommendations__tomorrow_ci",
    "utter_daily_ci__recommendations__recommendation_1",
    "utter_daily_ci__recommendations__recommendation_2",
]

RECOMMENDATIONS_VULNERABLE__HAS_211_OTHER = [
    "utter_daily_ci__recommendations__more_information_vulnerable_population",
    "utter_daily_ci__recommendations__211_other_provinces",
    "utter_daily_ci__recommendations__tomorrow_ci",
    "utter_daily_ci__recommendations__recommendation_1",
    "utter_daily_ci__recommendations__recommendation_2",
]

RECOMMENDATIONS_GENERAL__HAS_211_OTHER = [
    "utter_daily_ci__recommendations__more_information_general",
    "utter_daily_ci__recommendations__211_other_provinces",
    "utter_daily_ci__recommendations__tomorrow_ci",
    "utter_daily_ci__recommendations__recommendation_1",
    "utter_daily_ci__recommendations__recommendation_2",
]

RECOMMENDATIONS_VULNERABLE__HAS_211_QC = [
    "utter_daily_ci__recommendations__more_information_vulnerable_population",
    "utter_daily_ci__recommendations__211_qc",
    "utter_daily_ci__recommendations__tomorrow_ci",
    "utter_daily_ci__recommendations__recommendation_1",
    "utter_daily_ci__recommendations__recommendation_2",
]

RECOMMENDATIONS_GENERAL__HAS_211_QC = [
    "utter_daily_ci__recommendations__more_information_general",
    "utter_daily_ci__recommendations__211_qc",
    "utter_daily_ci__recommendations__tomorrow_ci",
    "utter_daily_ci__recommendations__recommendation_1",
    "utter_daily_ci__recommendations__recommendation_2",
]


class TestActionCheckMandatoryCi(ActionTestCase):
    def setUp(self):
        super().setUp()
        self.action = ActionCheckMandatoryCi()

    @pytest.mark.asyncio
    async def test_not_mandatory(self):
        tracker = self.create_tracker(
            slots={
                SYMPTOMS_SLOT: Symptoms.MILD,
                AGE_OVER_65_SLOT: False,
                PRECONDITIONS_SLOT: False,
            }
        )

        await self.run_action(tracker)

        self.assert_events([SlotSet(MANDATORY_CI_SLOT, False)])

        self.assert_templates([])

    @pytest.mark.asyncio
    async def test_moderate_symptoms(self):
        tracker = self.create_tracker(
            slots={
                SYMPTOMS_SLOT: Symptoms.MODERATE,
                AGE_OVER_65_SLOT: False,
                PRECONDITIONS_SLOT: False,
            }
        )

        await self.run_action(tracker)

        self.assert_events([SlotSet(MANDATORY_CI_SLOT, True)])

        self.assert_templates([])

    @pytest.mark.asyncio
    async def test_preconditions(self):
        tracker = self.create_tracker(
            slots={
                SYMPTOMS_SLOT: Symptoms.MILD,
                AGE_OVER_65_SLOT: False,
                PRECONDITIONS_SLOT: True,
            }
        )

        await self.run_action(tracker)

        self.assert_events([SlotSet(MANDATORY_CI_SLOT, True)])

        self.assert_templates([])

    @pytest.mark.asyncio
    async def test_age_over_65(self):
        tracker = self.create_tracker(
            slots={
                SYMPTOMS_SLOT: Symptoms.MILD,
                AGE_OVER_65_SLOT: True,
                PRECONDITIONS_SLOT: False,
            }
        )

        await self.run_action(tracker)

        self.assert_events([SlotSet(MANDATORY_CI_SLOT, True)])

        self.assert_templates([])


class TestActionKeepCiRecommendations(ActionTestCase):
    def setUp(self):
        super().setUp()
        self.action = ActionKeepCiRecommendations()

    @pytest.mark.asyncio
    async def test_preconditions_not_has_211(self):
        await self._test_recommendations(
            province="nu",
            age_over_65=False,
            preconditions=True,
            recommendations=RECOMMENDATIONS_VULNERABLE__NOT_HAS_211,
        )

    @pytest.mark.asyncio
    async def test_preconditions_has_211_other(self):
        await self._test_recommendations(
            province="bc",
            age_over_65=False,
            preconditions=True,
            recommendations=RECOMMENDATIONS_VULNERABLE__HAS_211_OTHER,
        )

    @pytest.mark.asyncio
    async def test_preconditions_has_211_qc(self):
        await self._test_recommendations(
            province="qc",
            age_over_65=False,
            preconditions=True,
            recommendations=RECOMMENDATIONS_VULNERABLE__HAS_211_QC,
        )

    @pytest.mark.asyncio
    async def test_over_65_not_has_211(self):
        await self._test_recommendations(
            province="nu",
            age_over_65=True,
            preconditions=False,
            recommendations=RECOMMENDATIONS_VULNERABLE__NOT_HAS_211,
        )

    @pytest.mark.asyncio
    async def test_over_65_has_211_other(self):
        await self._test_recommendations(
            province="bc",
            age_over_65=True,
            preconditions=False,
            recommendations=RECOMMENDATIONS_VULNERABLE__HAS_211_OTHER,
        )

    @pytest.mark.asyncio
    async def test_over_65_has_211_qc(self):
        await self._test_recommendations(
            province="qc",
            age_over_65=True,
            preconditions=False,
            recommendations=RECOMMENDATIONS_VULNERABLE__HAS_211_QC,
        )

    @pytest.mark.asyncio
    async def test_general_not_has_211(self):
        await self._test_recommendations(
            province="nu",
            age_over_65=False,
            preconditions=False,
            recommendations=RECOMMENDATIONS_GENERAL__NOT_HAS_211,
        )

    @pytest.mark.asyncio
    async def test_general_has_211_other(self):
        await self._test_recommendations(
            province="bc",
            age_over_65=False,
            preconditions=False,
            recommendations=RECOMMENDATIONS_GENERAL__HAS_211_OTHER,
        )

    @pytest.mark.asyncio
    async def test_general_has_211_qc(self):
        await self._test_recommendations(
            province="qc",
            age_over_65=False,
            preconditions=False,
            recommendations=RECOMMENDATIONS_GENERAL__HAS_211_QC,
        )

    async def _test_recommendations(
        self,
        province: str,
        age_over_65: bool,
        preconditions: bool,
        recommendations: List[str],
    ):
        tracker = self.create_tracker(
            slots={
                PROVINCE_SLOT: province,
                AGE_OVER_65_SLOT: age_over_65,
                PRECONDITIONS_SLOT: preconditions,
            }
        )

        await self.run_action(tracker, DOMAIN)

        self.assert_events([])

        self.assert_templates(recommendations)
