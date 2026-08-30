import pytest
from pydantic import ValidationError

from app.schemas.image_tag import ImageTag


def test_valid_image_tag():
    tag = ImageTag(
        subject="red fox",
        category="animal",
        attributes=["ears", "fur"],
        caption="A red fox in the forest",
        confidence=0.95,
    )
    assert tag.subject == "red fox"
    assert tag.category == "animal"
    assert tag.confidence == 0.95


def test_confidence_above_one_raises():
    with pytest.raises(ValidationError):
        ImageTag(
            subject="fox",
            category="animal",
            attributes=[],
            caption="a fox",
            confidence=1.1,
        )


def test_confidence_below_zero_raises():
    with pytest.raises(ValidationError):
        ImageTag(
            subject="fox",
            category="animal",
            attributes=[],
            caption="a fox",
            confidence=-0.1,
        )


def test_confidence_string_raises():
    with pytest.raises(ValidationError):
        ImageTag(
            subject="fox",
            category="animal",
            attributes=[],
            caption="a fox",
            confidence="0.9",
        )


def test_non_animal_category_raises():
    with pytest.raises(ValidationError):
        ImageTag(
            subject="fox",
            category="plant",
            attributes=[],
            caption="a fox",
            confidence=0.9,
        )


def test_missing_caption_raises():
    with pytest.raises(ValidationError):
        ImageTag(
            subject="fox",
            category="animal",
            attributes=[],
            confidence=0.9,
        )


def test_missing_subject_raises():
    with pytest.raises(ValidationError):
        ImageTag(
            category="animal",
            attributes=[],
            caption="a fox",
            confidence=0.9,
        )


def test_boundary_confidence_zero():
    tag = ImageTag(
        subject="fox",
        category="animal",
        attributes=[],
        caption="a fox",
        confidence=0.0,
    )
    assert tag.confidence == 0.0


def test_boundary_confidence_one():
    tag = ImageTag(
        subject="fox",
        category="animal",
        attributes=[],
        caption="a fox",
        confidence=1.0,
    )
    assert tag.confidence == 1.0
