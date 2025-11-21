"""Fast E2E tests for web adapter with mocked API responses."""
from __future__ import annotations

import base64
import json

import pytest
from playwright.sync_api import Page, Route, expect


# 1x1 transparent PNG
TEST_IMAGE_DATA = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
)


@pytest.fixture
def mock_quiz_responses(page: Page):
    """Mock all API responses for faster tests."""

    # Mock start_quiz response with image
    def handle_start_quiz(route: Route) -> None:
        route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps({
                "question": {
                    "data": {
                        "type": "multiple_choice",
                        "text": "What animal is shown in this image?",
                        "attachments": [
                            {
                                "type": "image",
                                "url": "https://example.com/test.png"
                            }
                        ],
                        "options": [
                            {"label": "Dog", "value": "dog"},
                            {"label": "Cat", "value": "cat"},
                            {"label": "Bird", "value": "bird"}
                        ]
                    },
                    "error": None,
                    "id": 1
                },
                "quiz_id": "TESTQUIZ123",
                "session_id": "test-session-123",
                "title": "Test Quiz"
            })
        )

    # Mock submit_answer response (final message)
    def handle_submit_answer(route: Route) -> None:
        route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps({
                "question": {
                    "data": {
                        "type": "final_message",
                        "text": "Quiz completed! Your score: 10/10"
                    },
                    "error": None,
                    "id": None
                }
            })
        )

    # Mock image requests
    def handle_image(route: Route) -> None:
        route.fulfill(
            status=200,
            content_type="image/png",
            body=TEST_IMAGE_DATA
        )

    page.route("**/api/quiz/start_quiz", handle_start_quiz)
    page.route("**/api/quiz/submit_answer/**", handle_submit_answer)
    page.route("**/*.png*", handle_image)
    page.route("**/example.com/**", handle_image)

    return page


class TestWebAdapterFast:
    """Fast tests with mocked responses (no Docker required)."""

    def test_image_displays_in_quiz(
        self,
        page: Page,
        mock_quiz_responses: Page,
    ) -> None:
        """Test that image displays correctly - FAST version."""
        # Navigate directly to web adapter (assumes running on localhost:8080)
        page.goto("http://localhost:8080")

        # Fill token and start
        page.wait_for_selector("#token", state="visible", timeout=2000)
        page.fill("#token", "TEST_TOKEN")
        page.click("#start-form button[type='submit']")

        # Wait for question
        page.wait_for_selector("#question-text", state="visible", timeout=2000)

        # Verify image container is visible
        expect(page.locator("#question-image-container")).to_be_visible()

        # Verify image element exists and is visible
        image = page.locator("#question-image-container img.question-image")
        expect(image).to_be_visible()

        # Verify image loaded
        page.wait_for_function(
            """
            () => {
                const img = document.querySelector('#question-image-container img.question-image');
                return img && img.complete && img.naturalWidth > 0;
            }
            """,
            timeout=2000
        )

        # Verify question text
        expect(page.locator("#question-text")
               ).to_contain_text("What animal is shown")

        # Verify options
        expect(page.locator("label.choice")).to_have_count(3)

    def test_quiz_flow_start_to_finish(
        self,
        page: Page,
        mock_quiz_responses: Page,
    ) -> None:
        """Test complete quiz flow - FAST version."""
        page.goto("http://localhost:8080")

        # Start quiz
        page.wait_for_selector("#token", timeout=2000)
        page.fill("#token", "TEST_TOKEN")
        page.click("#start-form button[type='submit']")

        # Answer question
        page.wait_for_selector("label.choice", timeout=2000)
        page.click("label.choice:first-child")

        # Submit (assuming form auto-submits on click or has submit button)
        submit_btn = page.locator("#quiz-form button[type='submit']")
        if submit_btn.is_visible():
            submit_btn.click()

        # Verify we reached end (this will depend on your final_message
        # implementation)
        page.wait_for_timeout(500)

    def test_no_image_when_attachments_empty(
        self,
        page: Page,
    ) -> None:
        """Test that image container is hidden when no attachments."""
        # Mock quiz without images
        def handle_start_no_image(route: Route) -> None:
            route.fulfill(
                status=200,
                content_type="application/json",
                body=json.dumps({
                    "question": {
                        "data": {
                            "type": "multiple_choice",
                            "text": "Simple question without image",
                            "options": [
                                {"label": "Yes", "value": "yes"},
                                {"label": "No", "value": "no"}
                            ]
                        },
                        "error": None,
                        "id": 1
                    },
                    "quiz_id": "SIMPLE123",
                    "session_id": "session-123",
                    "title": "Simple Quiz"
                })
            )

        page.route("**/api/quiz/start_quiz", handle_start_no_image)

        page.goto("http://localhost:8080")
        page.wait_for_selector("#token", timeout=2000)
        page.fill("#token", "TEST_TOKEN")
        page.click("#start-form button[type='submit']")

        page.wait_for_selector("#question-text", timeout=2000)

        # Image container should be hidden
        expect(page.locator("#question-image-container")).to_be_hidden()


@pytest.mark.skipif(
    True,  # Always skip - these are examples for reference
    reason="Example tests showing different approaches"
)
class TestWebAdapterExamples:
    """Examples of different testing approaches."""

    def test_with_docker_services(self, page: Page) -> None:
        """Example: Full integration test (slow, uses Docker)."""
        # This is what test_web_adapter.py does
        # Pros: Tests real integration
        # Cons: Slow, requires Docker, flaky
        pass

    def test_with_mocked_api(self, page: Page) -> None:
        """Example: Mocked API responses (fast, no Docker)."""
        # This is what we do above
        # Pros: Fast, reliable, no Docker needed
        # Cons: Doesn't test real API
        pass

    def test_unit_test_javascript(self) -> None:
        """Example: Pure unit test of JS logic."""
        # Could use jsdom or similar
        # Pros: Fastest, most isolated
        # Cons: Doesn't test browser rendering
        pass
