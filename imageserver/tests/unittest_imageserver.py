import unittest
from imageserver import ImageServer


class TestImageServer(unittest.TestCase):
    # No Azure storage so below call will return nothing
    def test_get_image(self):
        image_server = ImageServer()
        blob = image_server.do_get_image("noimageexpected.png")
        # Check blob is none
        self.assertIsNone(blob)


if __name__ == "__main__":
    unittest.main()
