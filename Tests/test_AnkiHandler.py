import pytest
from unittest.mock import patch, MagicMock, ANY
from LingqAnkiSync import AnkiHandler
from LingqAnkiSync.Models.AnkiCard import AnkiCard


@pytest.fixture
def sampleAnkiCardObject():
    return AnkiCard(
        primaryKey=12345,
        word="test_word",
        translations=["test_translation1", "test_translation2"],
        interval=5,
        level="recognized",
        tags=["tag1"],
        sentence="This is a test sentence.",
        importance=3,
        popularity=0,
    )


@pytest.fixture
def mockInternalAnkiCard():
    mock_card = MagicMock()
    mock_card.id = 789
    mock_card.interval = 10

    mock_note = MagicMock()
    note_data = {
        "LingqPK": "67890",
        "Front": "another_word",
        "Back": "1. here is a translation 2. here is another translation",
        "LingqLevel": "new",
        "Sentence": "another test sentence",
        "LingqImportance": "2",
    }
    mock_note.__getitem__.side_effect = note_data.get
    mock_note.tags = ["test", "test2"]

    # card.note()
    mock_card.note.return_value = mock_note

    return mock_card


class TestCreateNote:
    @patch("LingqAnkiSync.AnkiHandler.CreateNoteTypeIfNotExist")
    @patch("LingqAnkiSync.AnkiHandler.DoesDuplicateCardExistInDeck")
    def test_create_note_returns_false_when_duplicate_exists(
        self, mock_duplicate_check, mock_create_note_type, sampleAnkiCardObject
    ):
        mock_duplicate_check.return_value = True

        assert not AnkiHandler.CreateNote(sampleAnkiCardObject, "test_deck", "es")

        mock_duplicate_check.assert_called_once_with(sampleAnkiCardObject.primaryKey, "test_deck")
        mock_create_note_type.assert_not_called()

    @patch("LingqAnkiSync.AnkiHandler.CreateNoteTypeIfNotExist")
    @patch("LingqAnkiSync.AnkiHandler.DoesDuplicateCardExistInDeck")
    @patch("LingqAnkiSync.AnkiHandler.mw")
    def test_create_note_when_no_duplicate_exists(
        self, mock_mw, mock_duplicate_check, mock_create_note_type, sampleAnkiCardObject
    ):
        mock_duplicate_check.return_value = False

        deck_id = 123
        mock_model = MagicMock()
        mock_mw.col.models.byName.return_value = mock_model
        mock_mw.col.decks.id.return_value = deck_id

        note_id = 456
        mock_note = MagicMock()
        mock_note.id = note_id

        with patch("LingqAnkiSync.AnkiHandler.Note", return_value=mock_note):
            result = AnkiHandler.CreateNote(sampleAnkiCardObject, "test_deck", "es")

        assert result
        mock_duplicate_check.assert_called_once_with(sampleAnkiCardObject.primaryKey, "test_deck")
        mock_create_note_type.assert_called_once_with("es")
        mock_mw.col.models.byName.assert_called_once_with("lingqAnkiSync_es")
        mock_mw.col.add_note.assert_called_once_with(mock_note, deck_id)
        mock_mw.col.sched.set_due_date.assert_called_once_with(
            [note_id], str(sampleAnkiCardObject.interval)
        )

        mock_note.__setitem__.assert_any_call("LingqPK", ANY)
        mock_note.__setitem__.assert_any_call("Front", ANY)
        mock_note.__setitem__.assert_any_call("Back", ANY)
        mock_note.__setitem__.assert_any_call("LingqLevel", ANY)
        mock_note.__setitem__.assert_any_call("Sentence", ANY)
        mock_note.__setitem__.assert_any_call("LingqImportance", ANY)
        assert mock_note.tags is not None


class TestCreateAnkiCardObject:
    @patch("LingqAnkiSync.AnkiHandler.GetIntervalFromCard")
    def test_create_anki_card_object_conversion(self, mock_get_interval, mockInternalAnkiCard):
        mock_get_interval.side_effect = lambda card_id: mockInternalAnkiCard.interval

        result = AnkiHandler._CreateAnkiCardObject(mockInternalAnkiCard, mockInternalAnkiCard.id)

        assert result.primaryKey == 67890
        assert result.word == "another_word"
        # TODO eventually we want the AnkiHandler to be smarter about splitting the translations text
        assert result.translations == ["1. here is a translation 2. here is another translation"]
        # assert result.translations == mock_anki_card.note()["Back"]
        assert result.interval == 10
        assert result.level == "new"
        assert result.tags == ["test", "test2"]
        assert result.sentence == "another test sentence"
        assert result.importance == "2"

        mock_get_interval.assert_called_once_with(mockInternalAnkiCard.id)


class TestUpdateCardLevel:
    @patch("LingqAnkiSync.AnkiHandler.mw")
    @patch("LingqAnkiSync.AnkiHandler.time")
    def test_update_card_level(self, mock_time, mock_mw):
        mock_mw.col.find_cards.return_value = [123]
        mock_card = MagicMock()
        mock_mw.col.get_card.return_value = mock_card
        mock_note = MagicMock()
        mock_card.note.return_value = mock_note

        AnkiHandler.UpdateCardLevel("test_deck", 12345, "known")

        mock_mw.col.get_card.assert_called_once_with(123)
        mock_note.__setitem__.assert_called_once_with("LingqLevel", "known")
        mock_mw.col.update_note.assert_called_once_with(mock_note)
