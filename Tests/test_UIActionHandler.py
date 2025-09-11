import pytest
from unittest.mock import Mock, patch
from LingqAnkiSync.UIActionHandler import ActionHandler
from LingqAnkiSync.Models.AnkiCard import AnkiCard
from LingqAnkiSync.Models.Lingq import Lingq
from LingqAnkiSync.LingqApi import LingqApi


@pytest.fixture
def mockAddonManager():
    mockManager = Mock()
    mockConfig = {"apiKey": "test_api_key", "languageCode": "es"}
    mockManager.getConfig.return_value = mockConfig
    mockManager.writeConfig.return_value = None
    return mockManager


@pytest.fixture
def sampleLevelToInterval():
    return {"new": 0, "recognized": 5, "familiar": 10, "learned": 25, "known": 50}


@pytest.fixture
def actionHandler(mockAddonManager, sampleLevelToInterval):
    handler = ActionHandler(mockAddonManager)
    with patch.object(handler.config, "GetLevelToInterval", return_value=sampleLevelToInterval):
        yield handler


@pytest.fixture
def sampleAnkiCards():
    return [
        AnkiCard(
            primaryKey=12345,
            word="test_word_1",
            translations=["test_translation_1"],
            interval=10,  # Should trigger status increase
            level="new",
            tags=["tag1"],
            sentence="Test sentence one",
            importance=3,
            popularity=5,
        ),
        AnkiCard(
            primaryKey=67890,
            word="test_word_2",
            translations=["test_translation_2"],
            interval=2,  # Should trigger downgrade
            level="recognized",
            tags=["tag2"],
            sentence="Test sentence two",
            importance=2,
            popularity=3,
        ),
        AnkiCard(
            primaryKey=11111,
            word="test_word_3",
            translations=["test_translation_3"],
            interval=300,  # Very high interval should still only trigger single status increase
            level="familiar",
            tags=["tag3"],
            sentence="Test sentence three",
            importance=4,
            popularity=7,
        ),
        AnkiCard(
            primaryKey=22222,
            word="test_word_4",
            translations=["test_translation_4"],
            interval=10,  # No status increase
            level="recognized",
            tags=["tag4"],
            sentence="Test sentence four",
            importance=3,
            popularity=8,
        ),
    ]


@pytest.fixture
def sampleLingqs():
    return [
        Lingq(
            primaryKey=1,
            word="test_lingq_1",
            translations=["test_translation_1"],
            status=1,
            extendedStatus=0,
            tags=["tag1"],
            fragment="Test fragment one",
            importance=3,
            popularity=5,
        ),
        Lingq(
            primaryKey=2,
            word="test_lingq_2",
            translations=["test_translation_2"],
            status=2,
            extendedStatus=0,
            tags=["tag2"],
            fragment="Test fragment two",
            importance=2,
            popularity=3,
        ),
    ]


class TestUIActionHandler:
    @patch("LingqAnkiSync.UIActionHandler.AnkiHandler")
    @patch.object(LingqApi, "GetLingqs")
    @patch("LingqAnkiSync.UIActionHandler.LingqsToAnkiCards")
    def test_import_lingqs_to_anki(
        self, mockConverter, mockGetLingqs, mockAnkiHandler, actionHandler, sampleLingqs
    ):
        mockGetLingqs.return_value = sampleLingqs

        mockCards = [Mock(), Mock()]
        mockConverter.return_value = mockCards

        mockAnkiHandler.CreateNotesFromCards.return_value = 2

        result = actionHandler.ImportLingqsToAnki("TestDeck", importKnowns=True)

        assert result == 2
        mockGetLingqs.assert_called_once_with(True)
        mockConverter.assert_called_once_with(
            sampleLingqs, actionHandler.config.GetLevelToInterval()
        )
        mockAnkiHandler.CreateNotesFromCards.assert_called_once_with(mockCards, "TestDeck", "es")

    @patch("LingqAnkiSync.UIActionHandler.AnkiHandler")
    @patch.object(LingqApi, "SyncStatusesToLingq")
    def test_sync_lingq_status_with_progress_callback(
        self, mockSyncStatuses, mockAnkiHandler, actionHandler, sampleAnkiCards
    ):
        mockSyncStatuses.return_value = 5
        mockAnkiHandler.GetAllCardsInDeck.return_value = sampleAnkiCards
        progressCallback = Mock()

        actionHandler.SyncLingqStatusToLingq("TestDeck", progressCallback=progressCallback)

        mockSyncStatuses.assert_called_once()
        args = mockSyncStatuses.call_args[0]
        assert args[1] == progressCallback

    @patch("LingqAnkiSync.UIActionHandler.AnkiHandler")
    @patch.object(LingqApi, "SyncStatusesToLingq")
    @patch("LingqAnkiSync.UIActionHandler.AnkiCardsToLingqs")
    def test_sync_lingq_status_to_lingq(
        self,
        mockConverter,
        mockSyncStatuses,
        mockAnkiHandler,
        actionHandler,
        sampleAnkiCards,
    ):
        mockSyncStatuses.return_value = 3
        mockAnkiHandler.GetAllCardsInDeck.return_value = sampleAnkiCards

        mockLingqs = [Mock(), Mock()]
        mockConverter.return_value = mockLingqs
        increased, decreased, ignored, apiUpdates = actionHandler.SyncLingqStatusToLingq(
            "TestDeck", downgrade=True
        )

        assert increased == 2
        assert decreased == 1
        assert apiUpdates == 3

        mockAnkiHandler.GetAllCardsInDeck.assert_called_once_with("TestDeck")
        mockConverter.assert_called_once()
        converted_cards = mockConverter.call_args[0][0]
        assert len(converted_cards) == 3
        mockSyncStatuses.assert_called_once_with(mockLingqs, None)
        assert mockAnkiHandler.UpdateCardLevel.call_count == 3

    def test_prep_cards_for_update_only_increase(
        self, actionHandler, sampleAnkiCards, sampleLevelToInterval
    ):
        cardsToIncrease, cardsToDecrease, toIgnore = actionHandler._PrepCardsForUpdate(
            sampleAnkiCards, sampleLevelToInterval, downgrade=False
        )
        assert len(cardsToIncrease) == 2
        assert len(cardsToDecrease) == 0  # No downgrades when downgrade=False

        words = [card.word for card in cardsToIncrease]
        assert "test_word_1" in words
        assert "test_word_4" not in words

        assert "learned" in [card.level for card in cardsToIncrease if card.word == "test_word_3"]

    def test_prep_cards_for_update_increase_and_decrease(
        self, actionHandler, sampleAnkiCards, sampleLevelToInterval
    ):
        cardsToIncrease, cardsToDecrease, toIgnore = actionHandler._PrepCardsForUpdate(
            sampleAnkiCards, sampleLevelToInterval, downgrade=True
        )
        assert len(cardsToIncrease) == 2
        assert len(cardsToDecrease) == 1

        increaseWords = [card.word for card in cardsToIncrease]
        assert "test_word_1" in increaseWords
        assert "test_word_4" not in increaseWords

        decreaseWords = [card.word for card in cardsToDecrease]
        assert "test_word_2" in decreaseWords
        assert "test_word_4" not in decreaseWords

        assert "learned" in [card.level for card in cardsToIncrease if card.word == "test_word_3"]

    def test_check_language_code_valid(self, actionHandler):
        actionHandler._CheckLanguageCode("es")
        actionHandler._CheckLanguageCode("en")
        actionHandler._CheckLanguageCode("de")

    def test_check_language_code_invalid(self, actionHandler):
        with pytest.raises(ValueError) as excinfo:
            actionHandler._CheckLanguageCode("zz")

        assert 'Language code "zz" is not valid' in str(excinfo.value)
