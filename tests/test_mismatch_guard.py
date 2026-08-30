import types

from app.services.matching import category_match, evaluate_guard


def _fake_image(subject="red fox", confidence=0.95):
    return types.SimpleNamespace(subject=subject, confidence=confidence)


def _fake_post(title="The Secret Life of Red Foxes", body="Foxes are clever animals.", animal=None):
    return types.SimpleNamespace(title=title, body=body, animal=animal)


class TestCategoryMatch:
    def test_matching_category(self):
        img = _fake_image(subject="red fox")
        post = _fake_post(title="The Secret Life of Red Foxes", body="Foxes live in forests.")
        assert category_match(img.subject, post.title, post.body) is True

    def test_mismatch_category(self):
        img = _fake_image(subject="gray wolf")
        post = _fake_post(title="The Secret Life of Red Foxes", body="Foxes live in forests.")
        assert category_match(img.subject, post.title, post.body) is False

    def test_no_animal_words_in_post(self):
        img = _fake_image(subject="red fox")
        post = _fake_post(title="Brewing a Better Cup of Coffee", body="Coffee beans and hot water.")
        assert category_match(img.subject, post.title, post.body) is False

    def test_scientific_name_matches_common_name(self):
        img = _fake_image(subject="Vulpes vulpes")
        post = _fake_post(title="The Secret Life of Red Foxes", body="Foxes live in forests.")
        assert category_match(img.subject, post.title, post.body) is True


class TestEvaluateGuard:
    def test_category_mismatch_rejected(self):
        img = _fake_image(subject="gray wolf")
        post = _fake_post()
        all_subjects = ["gray wolf", "red fox"]
        result = evaluate_guard(img, post, similarity_score=0.85, all_image_subjects=all_subjects)
        assert result["verdict"] == "rejected"
        assert "Category mismatch" in result["reason"]
        assert "wolf" in result["reason"]

    def test_similarity_below_floor(self):
        img = _fake_image(subject="red fox")
        post = _fake_post()
        all_subjects = ["red fox"]
        result = evaluate_guard(img, post, similarity_score=0.50, all_image_subjects=all_subjects)
        assert result["verdict"] == "rejected"
        assert "Similarity" in result["reason"]

    def test_confidence_below_floor(self):
        img = _fake_image(subject="red fox", confidence=0.5)
        post = _fake_post()
        all_subjects = ["red fox"]
        result = evaluate_guard(img, post, similarity_score=0.85, all_image_subjects=all_subjects)
        assert result["verdict"] == "rejected"
        assert "confidence" in result["reason"].lower()

    def test_all_pass_accepted(self):
        img = _fake_image(subject="red fox", confidence=0.95)
        post = _fake_post()
        all_subjects = ["red fox"]
        result = evaluate_guard(img, post, similarity_score=0.85, all_image_subjects=all_subjects)
        assert result["verdict"] == "accepted"
        assert result["reason"] is None

    def test_no_animal_in_post_generic_rejection(self):
        img = _fake_image(subject="red fox")
        post = _fake_post(title="Brewing a Better Cup of Coffee", body="Coffee beans and hot water.")
        all_subjects = ["red fox"]
        result = evaluate_guard(img, post, similarity_score=0.85, all_image_subjects=all_subjects)
        assert result["verdict"] == "rejected"
        assert "Category mismatch" in result["reason"]
        assert "expected something in the post" in result["reason"]
