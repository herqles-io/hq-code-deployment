import logging
import json
import sys

import os.path

from hqcli.plugins import AbstractPlugin
import time


class Plugin(AbstractPlugin):
    def __init__(self):
        super(Plugin, self).__init__("cddeploy")
        self.logger = logging.getLogger("hq.cli.plugin.cddeploy")
        self.create_parser = None

    def setup_parser(self, parser):
        subparsers = parser.add_subparsers(help="codedeployer deploy command to run", dest='command')

        list_parser = subparsers.add_parser('list')
        list_parser.add_argument('-p', '--page', default=1, type=int, help='List page')
        list_parser.add_argument('-a', '--app', default=None, type=str, help='The application to filter by')
        list_parser.set_defaults(func=self.list)

        get_parser = subparsers.add_parser('get')
        get_parser.add_argument('deploy_id', type=int, help='Deploy ID')
        get_parser.set_defaults(func=self.get)

        self.create_parser = subparsers.add_parser('create')
        self.create_parser.add_argument('-sid', '--stage_id', type=int, help='The stage to deploy')
        self.create_parser.add_argument('-w', '--wait', action='store_true',
                                        help='Wait for the stage to complete before deploying')
        self.create_parser.add_argument('-e', '--env', type=str, help='The environment to deploy to')
        self.create_parser.add_argument('--tags', type=json.loads, help='Additional worker tags to filter')
        self.create_parser.add_argument('-d', '--datacenter', type=str, help='The datacenter to deploy to')
        self.create_parser.add_argument('-min', '--min_nodes', type=int,
                                        help='The minimum amount of nodes to deploy to')
        self.create_parser.add_argument('-t', '--targets', nargs='+', type=str, help='The targets to deploy to')
        self.create_parser.add_argument('-f', '--file', default=None, type=str, help='The json file to use instead')
        self.create_parser.set_defaults(func=self.create)

    def list(self, args):
        url = self.config.framework_url + "/cd/deploy?page=" + str(args.page)

        if args.app is not None:
            url += "&app=" + args.app

        r = self.api_call_get(url)

        if r.status_code != 200:
            self.logger.error(r.text)
            sys.exit(1)

        self.logger.info("Deploys\n" + json.dumps(json.loads(r.text), indent=2))

    def get(self, args):
        url = self.config.framework_url + "/cd/deploy/" + str(args.deploy_id)

        r = self.api_call_get(url)

        if r.status_code != 200:
            self.logger.error(r.text)
            sys.exit(1)

        self.logger.info("Deploy " + str(args.deploy_id) + "\n" + json.dumps(json.loads(r.text), indent=2))

    def create(self, args):

        data = {}

        if args.file is not None:

            if not os.path.isfile(args.file):
                self.logger.error("The file " + args.file + " does not exist")
                sys.exit(1)

            with open(args.file) as f:
                data = json.load(f)

        if args.stage_id is not None:
            data['stage_id'] = args.stage_id

        if args.env is not None:
            data['env'] = args.env

        if args.datacenter is not None:
            data['datacenter'] = args.datacenter

        if args.min_nodes is not None:
            data['min_nodes'] = args.min_nodes

        if args.targets is not None:
            data['targets'] = args.targets

        if args.tags is not None:
            if isinstance(args.tags, dict):
                data['tags'] = args.tags

        if 'stage_id' is not data and 'env' not in data:
            self.create_parser.print_help(sys.stderr)
            sys.exit(1)

        if 'min_nodes' not in data and 'targets' not in data:
            self.create_parser.print_help(sys.stderr)
            sys.exit(2)

        if args.wait:
            status = None

            while status != 'COMPLETED':
                self.logger.info("Waiting for stage " + str(data['stage_id']) + " to complete")

                if status == 'FAILED':
                    self.logger.error("Stage " + str(data['stage_id']) + " has failed")
                    sys.exit(1)

                r = self.api_call_get(self.config.framework_url + "/cd/stage/" + str(data['stage_id']))

                if r.status_code != 200:
                    self.logger.error(r.text)
                    sys.exit(1)

                data = json.loads(r.text)
                status = data['status']

                time.sleep(5)

            if status != 'COMPLETED':
                self.logger.error("Stage " + str(data['stage_id']) + " has not completed")
                sys.exit(1)

            self.logger.info("Stage Completed. Deploying")

        r = self.api_call_post(self.config.framework_url + "/cd/deploy", data=data)

        if r.status_code != 200:
            self.logger.error(r.text)
            sys.exit(1)

        self.logger.info(r.text)
