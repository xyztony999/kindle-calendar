"""Real Pillow rendering: measured ink bounds, languages and isolated instances."""
import copy
import unittest
from unittest.mock import patch

from PIL import ImageDraw, ImageChops

from server.render.placed import paint_custom, render_placed
from server.render.regions import Rect
from server.render import style

FIELDS = ["weather.temperature", "weather.humidity", "weather.wind_speed", "sun.sunrise", "aqi.value", "weather.description"]


class DataStylesRenderTests(unittest.TestCase):
    def render_checked(self, definition, payload, size):
        calls = []
        original = ImageDraw.ImageDraw.text
        def draw_text(draw, xy, text, *args, **kwargs):
            bbox = draw.textbbox(xy, text, font=kwargs.get("font"))
            calls.append((text, bbox))
            return original(draw, xy, text, *args, **kwargs)
        with patch.object(ImageDraw.ImageDraw, "text", draw_text):
            image = paint_custom(definition, payload, Rect(0, 0, *size), "")
        self.assertEqual(image.size, size)
        for text, (left, top, right, bottom) in calls:
            with self.subTest(text=text, size=size, appearance=definition["style"]):
                self.assertGreaterEqual(left, 0)
                self.assertGreaterEqual(top, 0)
                self.assertLessEqual(right, size[0])
                self.assertLessEqual(bottom, size[1])
        return image, calls

    def test_all_styles_render_real_chinese_english_and_missing_values(self):
        for language, description in [("zh", "多云转阴"), ("en", "Partly cloudy")]:
            payload = {"ui_lang": language, "weather": {"current": {"temperature": 23, "humidity": 58, "wind_speed": 10, "description": description}}, "sun": {"sunrise": "06:27"}, "aqi": {"us_aqi": 87}}
            for appearance in ("hero", "rows", "horizontal", "grid"):
                definition = {"fields": FIELDS, "style": appearance}
                image, calls = self.render_checked(definition, payload, (480, 240))
                self.assertTrue(calls)
                self.assertLess(image.getextrema()[0], style.PAPER)
                empty, empty_calls = self.render_checked(definition, {}, (480, 240))
                self.assertTrue(any("—" in text for text, _ in empty_calls))
                self.assertNotEqual(image.tobytes(), empty.tobytes())

    def test_long_cjk_english_and_unbroken_strings_wrap_or_ellipsize(self):
        for value in ("这是一段很长的中文天气描述" * 40, "Extremely long English weather description " * 40, "X" * 1000):
            payload = {"weather": {"current": {"description": value}}, "quote": {"text": value}}
            for appearance in ("hero", "rows", "horizontal", "grid"):
                image, calls = self.render_checked({"fields": ["weather.description", "quote.text"], "style": appearance}, payload, (120, 50))
                self.assertTrue(calls)
                self.assertTrue(any("…" in text for text, _ in calls))
                self.assertLess(image.getextrema()[0], style.PAPER)

    def test_extremely_small_rectangles_have_no_outside_draws(self):
        for appearance in ("hero", "rows", "horizontal", "grid"):
            for size in ((1, 1), (2, 3), (8, 6), (21, 11), (40, 20)):
                self.render_checked({"fields": FIELDS, "style": appearance}, {}, size)

    def test_local_override_does_not_modify_definition_or_other_instances(self):
        definition = {"id": "local", "style": "rows", "fields": FIELDS[:3]}
        definitions = {"local": definition}
        page = {"page_id": "today", "layout": [
            {"widget": "custom", "id": "first", "def": "local", "style": "horizontal", "x": 0, "y": 150, "w": 300, "h": 180},
            {"widget": "custom", "id": "second", "def": "local", "style": "grid", "x": 320, "y": 150, "w": 300, "h": 180},
            {"widget": "custom", "id": "third", "def": "local", "x": 0, "y": 350, "w": 300, "h": 180}]}
        saved = copy.deepcopy((definitions, page))
        payload = {"weather": {"current": {"temperature": 23, "humidity": 58, "wind_speed": 10}}}
        images = render_placed(page, payload, 758, 1024, "", definitions, {})
        self.assertEqual((definitions, page), saved)
        self.assertIs(definitions["local"], definition)
        for key, appearance in (("first", "horizontal"), ("second", "grid"), ("third", "rows")):
            expected = paint_custom({**definition, "style": appearance}, payload, Rect(0, 0, 300, 180), "")
            self.assertIsNone(ImageChops.difference(images[key], expected).getbbox())
        self.assertIsNotNone(ImageChops.difference(images["first"], images["third"]).getbbox())

    def test_legacy_hero_long_text_and_default_rows(self):
        definition = {"fields": ["quote.text", "quote.from"], "style": "hero"}
        self.render_checked(definition, {"quote": {"text": "Legacy long hero text " * 20, "from": "An author"}}, (280, 160))
        payload = {"weather": {"current": {"temperature": 23}}}
        default = paint_custom({"fields": FIELDS[:1]}, payload, Rect(0, 0, 200, 80), "")
        rows = paint_custom({"fields": FIELDS[:1], "style": "rows"}, payload, Rect(0, 0, 200, 80), "")
        self.assertIsNone(ImageChops.difference(default, rows).getbbox())
