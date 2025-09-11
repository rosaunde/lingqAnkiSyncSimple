import LingqAnkiSync.Converter as Converter
from LingqAnkiSync.Models import Lingq, AnkiCard
import pytest


@pytest.fixture
def levelToInterval():
    return {"new": 100, "recognized": 200, "familiar": 300, "learned": 400, "known": 500}


class TestIntervalToStatus:
    def test_convert_anki_interval_to_lingq_level(self, levelToInterval):
        testInterval = 225
        resultLevel = Converter._IntervalToLevel(testInterval, levelToInterval)
        assert resultLevel == "recognized"

    def test_should_return_max_level_if_interval_is_greater_than_max_interval(
        self, levelToInterval
    ):
        testInterval = 600
        resultLevel = Converter._IntervalToLevel(testInterval, levelToInterval)
        assert resultLevel == "known"

    def test_should_return_min_level_if_interval_is_less_than_min_interval(
        self, levelToInterval
    ):
        testInterval = 50
        resultLevel = Converter._IntervalToLevel(testInterval, levelToInterval)
        assert resultLevel == "new"

    def test_should_return_min_level_if_interval_is_equal_to_min_interval(
        self, levelToInterval
    ):
        testInterval = 100
        resultLevel = Converter._IntervalToLevel(testInterval, levelToInterval)
        assert resultLevel == "new"


class TestlevelToInterval:
    def test_convert_lingq_status_to_anki_interval(self, levelToInterval):
        testStatus = 2
        testExtendedStatus = 0
        resultStatus = Converter._LingqStatusToInterval(
            testStatus, testExtendedStatus, levelToInterval
        )
        assert resultStatus >= 300
        assert resultStatus <= 400

    def test_should_return_max_interval_plus_other_intervals_if_status_is_max_status(
        self, levelToInterval
    ):
        testStatus = 3
        testExtendedStatus = 3
        resultStatus = Converter._LingqStatusToInterval(
            testStatus, testExtendedStatus, levelToInterval
        )
        assert resultStatus >= 500

    def test_should_return_min_interval_if_status_min_status(self, levelToInterval):
        testStatus = 0
        testExtendedStatus = 0
        resultStatus = Converter._LingqStatusToInterval(
            testStatus, testExtendedStatus, levelToInterval
        )
        assert resultStatus >= 0
        assert resultStatus <= 100


class TestLingqStatusConversion:
    def test_convert_lingq_status_to_level(self):
        resultStatus = Converter.LingqStatusToLevel(
            status=0, extendedStatus=None
        )
        assert resultStatus == "new"

        resultStatus2 = Converter.LingqStatusToLevel(
            status=2, extendedStatus=0
        )
        assert resultStatus2 == "familiar"

        resultStatus3 = Converter.LingqStatusToLevel(
            status=3, extendedStatus=3
        )
        assert resultStatus3 == "known"

        with pytest.raises(ValueError, match="accepted range"):
            Converter.LingqStatusToLevel(status=9, extendedStatus=2)

    def test_convert_level_to_lingq_status(self, levelToInterval):
        resultStatus, resultExternalStatus = Converter.LevelToLingqStatus(
            level="new"
        )
        assert resultStatus == 0
        assert resultExternalStatus in (0, None)

        (
            resultStatus2,
            resultExternalStatus2,
        ) = Converter.LevelToLingqStatus(level="familiar")
        assert resultStatus2 == 2
        assert resultExternalStatus2 == 0

        (
            resultStatus3,
            resultExternalStatus3,
        ) = Converter.LevelToLingqStatus(level="known")
        assert resultStatus3 == 3
        assert resultExternalStatus3 == 3

        with pytest.raises(ValueError, match="No such level"):
            Converter.LevelToLingqStatus(level="understood")

        with pytest.raises(ValueError, match="No such level"):
            Converter.LevelToLingqStatus(level=1)


@pytest.fixture
def modelCard():
    return AnkiCard.AnkiCard(
        1, "word", ["translation", "translation2"], 100, "new", ["tag1", "tag2"], "sentence", 0
    )


@pytest.fixture
def modelLingq():
    return Lingq.Lingq(
        1, "word", ["translation", "translation2"], 0, None, ["tag1", "tag2"], "sentence", 0
    )


class TestConvertAnkiToLingq:
    def test_convert_anki_card_to_lingq(self, levelToInterval, modelCard):
        resultLingq = Converter.AnkiCardsToLingqs([modelCard], levelToInterval)[0]
        assert resultLingq.primaryKey == modelCard.primaryKey
        assert resultLingq.word == modelCard.word
        assert resultLingq.translations == modelCard.translations
        assert resultLingq.status == 0
        assert resultLingq.extendedStatus == 0
        assert resultLingq.tags == modelCard.tags
        assert resultLingq.fragment == modelCard.sentence
        assert resultLingq.importance == modelCard.importance


class TestConvertLingqToAnki:
    def test_convert_lingq_to_anki_card(self, levelToInterval, modelLingq):
        resultAnkiCard = Converter.LingqsToAnkiCards([modelLingq], levelToInterval)[0]
        assert resultAnkiCard.primaryKey == modelLingq.primaryKey
        assert resultAnkiCard.word == modelLingq.word
        assert resultAnkiCard.translations == modelLingq.translations
        assert resultAnkiCard.interval >= 0
        assert resultAnkiCard.interval <= 100
        assert resultAnkiCard.level == "new"
        assert resultAnkiCard.tags == modelLingq.tags
        assert resultAnkiCard.sentence == modelLingq.fragment
        assert resultAnkiCard.importance == modelLingq.importance


class TestCardCanIncreaseStatus:
    def test_should_return_true_if_interval_is_greater_than_threshold(
        self, levelToInterval, modelCard
    ):
        modelCard.interval = 250
        modelCard.level = "recognized"
        result = Converter.CardCanIncreaseLevel(modelCard, levelToInterval)
        assert result

    def test_should_return_false_if_interval_is_equal_to_threshold(
        self, levelToInterval, modelCard
    ):
        modelCard.interval = 200
        modelCard.level = "recognized"
        result = Converter.CardCanIncreaseLevel(modelCard, levelToInterval)
        assert not result

    def test_should_return_false_if_interval_is_less_than_threshold(
        self, levelToInterval, modelCard
    ):
        modelCard.interval = 150
        modelCard.level = "recognized"
        result = Converter.CardCanIncreaseLevel(modelCard, levelToInterval)
        assert not result

    def test_should_return_false_for_new_card(self, modelCard, levelToInterval):
        modelCard.interval = 0
        modelCard.level = "new"
        result = Converter.CardCanIncreaseLevel(modelCard, levelToInterval)
        assert not result

    def test_should_return_true_for_known_card_with_high_interval(
        self, modelCard, levelToInterval
    ):
        modelCard.interval = 1000
        modelCard.level = "known"
        result = Converter.CardCanIncreaseLevel(modelCard, levelToInterval)
        assert result
