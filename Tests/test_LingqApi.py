import pytest
from requests.exceptions import HTTPError
from unittest.mock import patch, MagicMock
from LingqAnkiSync.LingqApi import LingqApi
from LingqAnkiSync.Models.Lingq import Lingq


@pytest.fixture
def sampleLingqObjects():
    return [
        Lingq(
            primaryKey=1,
            word="test_word_1",
            translations=["test_translation_1a", "test_translation_1b"],
            status=1,
            extendedStatus=0,
            tags=["test_tag_1"],
            fragment="test_fragment_1",
            importance=2,
            popularity=5,
        ),
        Lingq(
            primaryKey=2,
            word="test_word_2",
            translations=["test_translation_2"],
            status=2,
            extendedStatus=0,
            tags=["test_tag_2"],
            fragment="test_fragment_2",
            importance=2,
            popularity=4,
        ),
        Lingq(
            primaryKey=3,
            word="test_word_3",
            translations=["test_translation_3"],
            status=3,
            extendedStatus=3,
            tags=["test_tag_3"],
            fragment="test_fragment_3",
            importance=3,
            popularity=5,
        ),
    ]


# Factories to simplify creating mock responses
@pytest.fixture
def lingqApiGetCardsResponse():
    def _factory(
        lingqs: list,
        count: int,
        next_url: str = None,
    ):
        results_list = []
        for lingq in lingqs:
            results_list.append(
                {
                    "pk": lingq.primaryKey,
                    "term": lingq.word,
                    "status": lingq.status,
                    "extended_status": lingq.extendedStatus,
                    "tags": lingq.tags,
                    "fragment": lingq.fragment,
                    "importance": lingq.importance,
                    "hints": [{"text": t, "popularity": 1} for t in lingq.translations],
                }
            )

        response_data = {"count": count, "next": next_url, "results": results_list}

        # Create a mock response object that behaves like requests.Response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = response_data
        mock_response.raise_for_status.return_value = None  # Default to no exception

        return mock_response

    return _factory


@pytest.fixture
def lingqApiGetLevelResponse():
    def _factory(status: int, extendedStatus: int):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": status,
            "extended_status": extendedStatus,
        }

        return mock_response

    return _factory


class TestLingqApi:
    @patch("requests.get")
    def test_get_lingqs_basic(self, requestsGetMock, lingqApiGetCardsResponse, sampleLingqObjects):
        page_1_response = lingqApiGetCardsResponse(
            lingqs=sampleLingqObjects,
            count=3,
        )

        requestsGetMock.return_value = page_1_response

        api = LingqApi("test_api_key", "es")
        lingqs = api.GetLingqs(includeKnowns=True)

        assert len(lingqs) == 3

        for lingq in lingqs:
            assert isinstance(lingq, Lingq)

        assert requestsGetMock.call_count == 1
        # test includeKnowns is adding a filter to the url
        assert "&status=0&status=1&status=2&status=3" not in requestsGetMock.call_args.kwargs["url"]
        api.GetLingqs(includeKnowns=False)
        assert "&status=0&status=1&status=2&status=3" in requestsGetMock.call_args.kwargs["url"]

    @patch("requests.get")
    def test_get_lingqs_paging(self, requestsGetMock, lingqApiGetCardsResponse, sampleLingqObjects):
        page_1_response = lingqApiGetCardsResponse(
            lingqs=sampleLingqObjects[:2],
            count=2,
            next_url="https://www.lingq.com/api/v3/es/cards/?page=2&page_size=2",
        )
        page_2_response = lingqApiGetCardsResponse(
            lingqs=sampleLingqObjects[2:],
            count=1,
        )

        requestsGetMock.side_effect = [page_1_response, page_2_response]

        api = LingqApi("test_api_key", "es")
        lingqs = api.GetLingqs(includeKnowns=True)

        assert len(lingqs) == 3

        for lingq in lingqs:
            assert isinstance(lingq, Lingq)

        assert requestsGetMock.call_count == 2

    @patch("time.sleep")
    @patch("requests.get")
    def test_with_retry(
        self,
        requestsGetMock,
        timeSleepMock,
        lingqApiGetCardsResponse,
        sampleLingqObjects,
    ):
        responses = [
            lingqApiGetCardsResponse(
                lingqs=sampleLingqObjects[:2],
                count=2,
                next_url="https://www.lingq.com/api/v3/es/cards/?page=2&page_size=2",
            ),
            # Will be the bad response that triggers the retry
            lingqApiGetCardsResponse(
                lingqs=[],
                count=0,
            ),
            lingqApiGetCardsResponse(
                lingqs=sampleLingqObjects[2:],
                count=1,
            ),
        ]

        # Make second response 429 and trigger retry
        retryAfterDelaySeconds = 2
        responses[1].status_code = 429
        responses[1].headers = {"Retry-After": str(retryAfterDelaySeconds)}
        responses[1].raise_for_status.side_effect = HTTPError("429 Client Error: Too Many Requests")

        requestsGetMock.side_effect = responses

        api = LingqApi("test_api_key", "es")
        lingqs = api.GetLingqs(includeKnowns=True)

        assert len(lingqs) == 3

        for lingq in lingqs:
            assert isinstance(lingq, Lingq)

        assert requestsGetMock.call_count == 3
        assert timeSleepMock.call_count == 1
        assert timeSleepMock.call_args[0][0] >= retryAfterDelaySeconds

    @patch("requests.get")
    def test_get_level(self, requestsGetMock, lingqApiGetLevelResponse):
        requestsGetMock.side_effect = [
            lingqApiGetLevelResponse(0, 0),
            lingqApiGetLevelResponse(1, 0),
            lingqApiGetLevelResponse(2, 0),
            lingqApiGetLevelResponse(3, 0),
            lingqApiGetLevelResponse(3, 3),
        ]

        api = LingqApi("test_api_key", "es")
        level = api._GetLevel(1)
        assert level == Lingq.LEVEL_1
        assert requestsGetMock.call_count == 1
        assert requestsGetMock.call_args.kwargs["url"] == "https://www.lingq.com/api/v3/es/cards/1/"

        level = api._GetLevel(2)
        assert level == Lingq.LEVEL_2
        level = api._GetLevel(3)
        assert level == Lingq.LEVEL_3
        level = api._GetLevel(4)
        assert level == Lingq.LEVEL_4
        level = api._GetLevel(5)
        assert level == Lingq.LEVEL_KNOWN

    @patch("requests.get")
    def test_should_update(self, requestsGetMock, lingqApiGetLevelResponse, sampleLingqObjects):
        requestsGetMock.side_effect = [
            lingqApiGetLevelResponse(1, 0),
            lingqApiGetLevelResponse(3, 0),
            lingqApiGetLevelResponse(3, 3),
        ]

        api = LingqApi("test_api_key", "es")
        assert not api._ShouldUpdate(sampleLingqObjects[0])
        assert api._ShouldUpdate(sampleLingqObjects[1])
        assert not api._ShouldUpdate(sampleLingqObjects[2])

    @patch("time.sleep")
    @patch("requests.patch")
    @patch("requests.get")
    def test_sync_statuses_to_lingq(
        self,
        requestsGetMock,
        requestsPatchMock,
        timeSleepMock,
        lingqApiGetLevelResponse,
        sampleLingqObjects,
    ):
        responses = [
            lingqApiGetLevelResponse(1, 0),
            # Will be the bad response that triggers the retry
            lingqApiGetLevelResponse(-1, -1),
            lingqApiGetLevelResponse(3, 0),
            lingqApiGetLevelResponse(3, 3),
        ]
        # Make second response 429 and trigger retry
        retryAfterDelaySeconds = 2
        responses[1].status_code = 429
        responses[1].headers = {"Retry-After": str(retryAfterDelaySeconds)}
        responses[1].raise_for_status.side_effect = HTTPError("429 Client Error: Too Many Requests")

        requestsGetMock.side_effect = responses

        api = LingqApi("test_api_key", "es")
        progressCallback = MagicMock()
        assert (
            api.SyncStatusesToLingq(lingqs=sampleLingqObjects, progressCallback=progressCallback)
            == 1
        )
        assert requestsGetMock.call_count == 4
        assert requestsPatchMock.call_count == 1
        assert timeSleepMock.call_count > 0
        assert progressCallback.call_count > 0
