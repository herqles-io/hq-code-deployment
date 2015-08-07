from hqworker.processor import ActionProcessor
import urllib
import base64


class Touch(ActionProcessor):

    def __init__(self, worker):
        super(Touch, self).__init__(worker, "file:touch", ["file"])

    def work(self):
        return self.run_command(['touch', self.args["file"]])


class Write(ActionProcessor):

    def __init__(self, worker):
        super(Write, self).__init__(worker, "file:write", ["file", "contents"])

    def work(self):
        try:
            with open(self.args['file'], "w") as f:

                contents = self.args['contents']

                if contents.startswith("B64:"):
                    contents = contents[3:]
                    contents = base64.b64decode(contents)

                f.write(contents)
        except EnvironmentError:
            return -1, "Error creating file"

        return 0, ""


class Download(ActionProcessor):

    def __init__(self, worker):
        super(Download, self).__init__(worker, "file:download", ["file", "url"])

    def work(self):
        try:
            urllib.urlretrieve(self.args['url'], self.args['file'])
        except Exception as e:
            return -1, e.message

        return 0, ""