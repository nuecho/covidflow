import os
from copy import deepcopy
from datetime import datetime, time
from enum import Enum
from typing import Dict, List, NamedTuple, Optional

import backoff
import structlog
from aiohttp import ClientError, ClientSession
from geopy.point import Point

logger = structlog.get_logger()

CLINIA_ENDPOINT = "https://covid.clinia.com"
CLINIA_API_KEY = "CLINIA_API_KEY"
CLINIA_API_ROUTE = "/api/v1/indexes/covid/query"
CLINIA_TIME_FORMAT = "%H:%M:%S"

LOCATION_KEY = "aroundLatLng"
PAGE_KEY = "page"
HEADER_CLINIA_API_KEY = "x-clinia-api-key"
HITS_KEY = "hits"

DEFAULT_SEARCH_PARAMETERS = {
    "perPage": 20,
    "rankingInfo": True,
    "facetFilters": [
        ["services.en:COVID-19 testing", "services.en:COVID-19 follow up testing",]
    ],
}


class Day(Enum):
    monday = 1
    tuesday = 2
    wednesday = 3
    thursday = 4
    friday = 5
    saturday = 6
    sunday = 7


class OpeningPeriod(NamedTuple):
    start: time
    end: time


def _str_to_time(time: str) -> time:
    return datetime.strptime(time, CLINIA_TIME_FORMAT).time()


def _to_opening_hours(raw_opening_hours: List[Dict]) -> List[OpeningPeriod]:
    return [
        OpeningPeriod(_str_to_time(i["start"]), _str_to_time(i["end"]))
        for i in raw_opening_hours
    ]


class TestingLocationAddress:
    def __init__(self, raw_address_data: dict):
        self.raw_address = raw_address_data

    @property
    def street_address(self) -> Optional[str]:
        # ie: 5800 Cavendish Blvd
        return self.raw_address.get("streetAddress")

    @property
    def region_code(self) -> Optional[str]:
        # ie: QC
        return self.raw_address.get("regionCode")

    @property
    def country(self) -> Optional[str]:
        # ie: Canada
        return self.raw_address.get("country")

    @property
    def place(self) -> Optional[str]:
        # ie: Lachine
        return self.raw_address.get("place")

    def is_complete(self) -> bool:
        return self.street_address != None

    def to_formatted_address(self) -> str:
        address_parts = [
            self.street_address,
            self.place,
            self.region_code,
            self.country,
        ]
        return ", ".join(list(filter(None, address_parts)))


class TestingLocationPhone:
    def __init__(self, raw_phone_data: dict):
        self.raw_phone = raw_phone_data

    @property
    def number(self) -> str:
        return self.raw_phone["number"]

    @property
    def extension(self) -> Optional[str]:
        return self.raw_phone.get("extension")


class TestingLocation:
    def __init__(self, raw_data: dict):
        self.raw_data = deepcopy(raw_data)

        raw_address_data = raw_data.get("address")
        self.address = (
            None
            if raw_address_data is None
            else TestingLocationAddress(raw_address_data)
        )

        raw_phones_data = raw_data.get("phones", [])
        self.phones = [TestingLocationPhone(i) for i in raw_phones_data]

    @property
    def name(self) -> Optional[str]:
        return self.raw_data.get("name")

    @property
    def require_referral(self) -> Optional[bool]:
        return self.raw_data.get("requireReferral")

    @property
    def require_appointment(self) -> Optional[bool]:
        return self.raw_data.get("requireAppointment")

    # Raises if there is no geopoint because we depend on it
    @property
    def coordinates(self) -> Point:
        geo_point = self.raw_data["_geoPoint"]
        return Point([geo_point.get("lat"), geo_point.get("lon")])

    @property
    def clientele(self) -> Optional[str]:
        return self.raw_data.get("clientele")

    @property
    def websites(self) -> List[str]:
        return self.raw_data.get("websites", [])

    @property
    def description(self) -> dict:
        return self.raw_data.get("description", {})

    @property
    def opening_hours(self) -> Dict[Day, List[OpeningPeriod]]:
        raw_opening_hours = self.raw_data.get("openingHours", {})
        return {
            Day[day]: _to_opening_hours(hours)
            for (day, hours) in raw_opening_hours.items()
        }

    def __repr__(self):
        return repr(self.raw_data)


async def _fetch_testing_locations(
    session: ClientSession, coordinates: Point, page: int = 0
):
    headers = {HEADER_CLINIA_API_KEY: os.environ[CLINIA_API_KEY]}
    body = {
        **DEFAULT_SEARCH_PARAMETERS,
        LOCATION_KEY: f"{coordinates[0]},{coordinates[1]}",
        PAGE_KEY: page,
    }

    url = f"{CLINIA_ENDPOINT}{CLINIA_API_ROUTE}"
    logger.debug(f"Fetching test sites", url=url, body=body)

    result = await session.post(url, json=body, headers=headers)
    return await result.json()


@backoff.on_exception(backoff.expo, ClientError, max_time=3)
async def _fetch_testing_locations_with_backoff(
    session: ClientSession, coordinates: Point, page: int = 0
):
    return await _fetch_testing_locations(
        session=session, coordinates=coordinates, page=page
    )


async def get_testing_locations(coordinates: Point) -> List[TestingLocation]:
    async with ClientSession(raise_for_status=True) as session:
        result = await _fetch_testing_locations_with_backoff(
            session=session, coordinates=coordinates
        )

        if result is None or HITS_KEY not in result:
            logger.debug(
                f"No testing location found for coordinates {coordinates[0]},{coordinates[1]}"
            )
            return []

        hits = result[HITS_KEY]
        logger.debug(
            f"Found {len(hits)} testing location for coordinates {coordinates[0]},{coordinates[1]}"
        )
        return [TestingLocation(i) for i in hits]
