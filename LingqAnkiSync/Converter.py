import random
from typing import List, Dict, Tuple
from .Models.Lingq import Lingq
from .Models.AnkiCard import AnkiCard


def AnkiCardsToLingqs(
    ankiCards: List[AnkiCard], levelToInterval: Dict[str, int]
) -> List[Lingq]:
    lingqs = []
    for card in ankiCards:
        status, extendedStatus = _IntervalToLingqStatus(card.interval, levelToInterval)
        lingqs.append(
            Lingq(
                primaryKey=card.primaryKey,
                word=card.word,
                translations=card.translations,
                status=status,
                extendedStatus=extendedStatus,
                tags=card.tags,
                fragment=card.sentence,
                importance=card.importance,
                popularity=card.popularity,
            )
        )
    return lingqs


def LingqsToAnkiCards(lingqs: List[Lingq], levelToInterval: Dict[str, int]) -> List[AnkiCard]:
    ankiCards = []
    for lingq in lingqs:
        ankiCards.append(
            AnkiCard(
                primaryKey=lingq.primaryKey,
                word=lingq.word,
                translations=lingq.translations,
                interval=_LingqStatusToInterval(
                    lingq.status, lingq.extendedStatus, levelToInterval
                ),
                level=LingqStatusToLevel(lingq.status, lingq.extendedStatus),
                tags=lingq.tags,
                sentence=lingq.fragment,
                importance=lingq.importance,
                popularity=lingq.popularity,
            )
        )
    return ankiCards


def CardCanIncreaseLevel(ankiCard: AnkiCard, levelToInterval: Dict[str, int]):
    return ankiCard.interval > levelToInterval[ankiCard.level]


def _LingqStatusToInterval(
    status: int, extendedStatus: int, levelToInterval: Dict[str, int]
) -> int:
    level = LingqStatusToLevel(status, extendedStatus)
    intervalRange = (0, 0)

    if level == Lingq.LEVEL_1:
        intervalRange = (0, levelToInterval[level])
    elif level == Lingq.LEVEL_2:
        intervalRange = (levelToInterval[level], levelToInterval[Lingq.LEVEL_3])
    elif level == Lingq.LEVEL_3:
        intervalRange = (levelToInterval[level], levelToInterval[Lingq.LEVEL_4])
    elif level == Lingq.LEVEL_4:
        intervalRange = (levelToInterval[level], levelToInterval[Lingq.LEVEL_KNOWN])
    elif level == Lingq.LEVEL_KNOWN:
        # If a card is known, how long should the range be? Double?
        intervalRange = (levelToInterval[level], levelToInterval[level] * 2)

    return random.randint(intervalRange[0], intervalRange[1]) # nosec


def _IntervalToLingqStatus(interval: int, levelToInterval: Dict[str, int]) -> Tuple[int, int]:
    level = _IntervalToLevel(interval, levelToInterval)
    return LevelToLingqStatus(level)


def _IntervalToLevel(interval: int, levelToInterval: Dict[str, int]) -> str:
    if interval > levelToInterval[Lingq.LEVEL_KNOWN]:
        lingqLevel = Lingq.LEVEL_KNOWN
    else:
        lingqLevel = Lingq.LEVEL_1
        for level in Lingq.LEVELS:
            if interval > levelToInterval[level]:
                lingqLevel = level

    return lingqLevel


def LingqStatusToLevel(status: int, extendedStatus: int) -> str:
    if status not in (0, 1, 2, 3):
        raise ValueError(
            f"""Lingq api status outside of accepted range
            Status: {status}
            Extended Status: {extendedStatus}
        """
        )

    if extendedStatus == 3:
        return Lingq.LEVEL_KNOWN

    return Lingq.LEVELS[status]



def LevelToLingqStatus(level: str) -> Tuple[int, int]:
    if level not in Lingq.LEVELS:
        raise ValueError(f'No such level "{level}". Should be one of {Lingq.LEVELS}')

    extendedStatus = 0
    if level == Lingq.LEVEL_KNOWN:
        status = 3
        extendedStatus = 3
    else:
        status = Lingq.LEVELS.index(level)

    return status, extendedStatus
