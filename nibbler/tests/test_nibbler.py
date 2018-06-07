import unittest
from nibbler import NibblerConfig
from nibbler import HTMLNormalizer
# python3 library
#from mock import Mock


class NibblerTestCase(unittest.TestCase):
    """Base class for all Nibbler tests."""
    arguments = {'from_email': 'from@test.com', 'to_email': 'to@test.com', 'log_dir': '/app-data/logs/nibbler-logs', 'sub_dir': '/app-bin'}

    def assertCostEqual(self, p, cost):
        """Custom assert here: `p`'s cost is equal to `cost`."""
        self.assertEqual(p.cost(), cost)


class TestNibblerConfig(NibblerTestCase):

    def setUp(self):
        self.config = NibblerConfig(**self.arguments)

    def test_log_dir(self):
        self.assertEqual(self.config.get_log_dir(), "/app-data/logs/nibbler-logs")

    def test_database_connection(self):
        self.assertEqual(self.config.get_database_connection(), "sqlite:///nibbler.db")

    def test_email_image_styles(self):
        values = self.config.get_email_image_styles()
        self.assertEqual(values["width"], 480)
        self.assertEqual(values["height"], 320)
        self.assertEqual(values["border"], 0)

    def tearDown(self):
        pass


class TestHTMLNormalizer(NibblerTestCase):

    def setUp(self):
        self.normalizer = HTMLNormalizer(NibblerConfig(**self.arguments))

    def test_clean_html(self):
        input_html = '<p>I <br/><span id="id-styles-text-to-remove">added some text </span><a class="my-class-to-remove" href="http://www.jamesaltucher.com/2017/03/matt-mullenweg/">joined in for the James Altucher<img width="480" id="id-to-remove" class=" size-full wp-image-47258 aligncenter" src="https://i1.wp.com/ma.tt/files/2017/04/ultralight.gif?resize=500%2C288&amp;ssl=1" alt="ultralight.gif"> podcast in an episode that covered a lot of ground</a>. It just needs to be two-way.</p>'
        clean_html = '<p>I added some text <a href="http://www.jamesaltucher.com/2017/03/matt-mullenweg/">joined in for the James Altucher<img src="https://i1.wp.com/ma.tt/files/2017/04/ultralight.gif?resize=500%2C288&amp;ssl=1" alt="ultralight.gif"> podcast in an episode that covered a lot of ground</a>. It just needs to be two-way.</p>'
        self.assertEqual(clean_html, self.normalizer.clean_html(input_html))

    def test_add_email_markup(self):
        clean_html = '<p>I added some text <a href="http://www.jamesaltucher.com/2017/03/matt-mullenweg/">joined in for the James Altucher<img src="https://i1.wp.com/ma.tt/files/2017/04/ultralight.gif?resize=500%2C288&amp;ssl=1" alt="ultralight.gif"> podcast in an episode that covered a lot of ground</a>. It just needs to be two-way.</p>'
        email_html = '<p>I added some text <a href="http://www.jamesaltucher.com/2017/03/matt-mullenweg/">joined in for the James Altucher<img src="https://i1.wp.com/ma.tt/files/2017/04/ultralight.gif?resize=500%2C288&amp;ssl=1" alt="ultralight.gif" width="480" height="320" border="0"> podcast in an episode that covered a lot of ground</a>. It just needs to be two-way.</p>'
        self.assertEqual(email_html, self.normalizer.add_email_markup(clean_html))

    def test_add_full_image_path(self):
        link = 'https://kottke.org/18/06/the-problem-with-action-scenes-in-dc-movies'
        input_html= '<p><img src="/plus/misc/images/ai-image-iso-02.jpg" alt="AI image in the dark"></p>'
        email_html = '<p><img src="https://kottke.org/plus/misc/images/ai-image-iso-02.jpg" alt="AI image in the dark"></p>'
        self.assertEqual(email_html, self.normalizer.add_full_image_path(input_html, link))


    def tearDown(self):
        pass

if __name__ == '__main__':
    unittest.main()
