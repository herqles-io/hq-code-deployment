import json
import datetime
import logging

import os.path
import cherrypy

from schematics.exceptions import ModelValidationError, ModelConversionError
import re

from schematics.types import StringType

from hqframework.framework import AbstractFramework, AbstractFrameworkAPI
from hqlib.sql.models import Task, TaskStatus, Action, Job, JobTarget, JobStatus
from hqcodedeployer.models import Deploy, Stage, Rollback
from hqframework.exceptions import LaunchTaskException, GetWorkersException
from hqcodedeployer.validators import DeployValidator, AppTypeValidator


class Framework(AbstractFramework):
    def __init__(self):
        super(Framework, self).__init__("codedeployer-deploy", Deploy)
        self.logger = logging.getLogger("hq.framework.codedeployer.deploy")

    def config_class(self):
        config_class = super(Framework, self).config_class()

        class ConfigValidator(config_class):
            app_type_path = StringType(required=True)
            deploy_path = StringType(required=True)

        return ConfigValidator

    def on_stop(self):
        pass

    def process_job(self, job_id):
        with self.database.session() as session:
            deploy = session.query(Deploy).join(Job, Deploy.job_id == Job.id). \
                filter(Job.id == job_id).filter(Job.stopped_at == None).first()

            if deploy.job.status == JobStatus.PENDING:

                if self.tasks_have_status(deploy.job, TaskStatus.PENDING):
                    self.logger.info("All deploy tasks are now pending. Starting Deploy "
                                     + deploy.stage.app + " (" + str(deploy.id) + ")")
                    deploy.job.status = JobStatus.RUNNING
                    session.commit()
            elif deploy.job.status == JobStatus.RUNNING:

                # check if completed
                if self.tasks_have_status(deploy.job, TaskStatus.FINISHED):
                    self.logger.info("Deploy Completed (" + str(deploy.id) + ")")
                    deploy.job.status = JobStatus.COMPLETED
                    deploy.job.stopped_at = datetime.datetime.now()
                    session.commit()
                    return

                # check if failed
                if self.some_task_has_status(deploy.job, TaskStatus.FAILED):
                    self.logger.info("Deploy Failed (" + str(deploy.id) + ")")
                    for target_task in deploy.job.targets:
                        for task in target_task.tasks:
                            if task.status == TaskStatus.PENDING:
                                task.status = TaskStatus.KILLED
                                task.error_message = "Deploy failed"
                                task.stopped_at = datetime.datetime.now()
                    deploy.job.status = JobStatus.FAILED
                    deploy.job.stopped_at = datetime.datetime.now()
                    session.commit()
                    return

                all_finished = True

                for target_task in deploy.job.targets:
                    task = target_task.tasks[deploy.job.current_task_index]

                    if task.status == TaskStatus.LOST:
                        self.logger.info("Deploy Task " + str(task.id) + " is lost. Retrying...")

                    if task.status == TaskStatus.PENDING or task.status == TaskStatus.LOST:

                        worker = target_task.worker

                        try:
                            self.logger.info("Launching Task " + task.name)
                            self.launch_task(worker, task)
                        except LaunchTaskException as e:
                            self.logger.error("Error launching deploy tasks: " + e.message)
                            task.error_message = e.message
                            task.stopped_at = datetime.datetime.now()
                            task.status = TaskStatus.FAILED
                            session.commit()

                    elif task.status == TaskStatus.RUNNING:
                        if self.unix_time_millis(datetime.datetime.now()) - \
                                self.unix_time_millis(task.updated_at) > 60000:
                            self.logger.warning("Deploy Task " + str(task.id) + " timed out. It is now lost.")
                            task.status = TaskStatus.LOST
                            session.commit()

                    if task.status != TaskStatus.FINISHED:
                        all_finished = False

                if all_finished:
                    deploy.job.current_task_index += 1

                    if deploy.job.current_task_index >= len(deploy.job.targets[0].tasks):
                        deploy.job.current_task_index = len(deploy.job.targets[0].tasks)

                    session.commit()

    def registered(self):
        pass

    def deploy_app(self, data):

        if data.datacenter is None:
            data.datacenter = self.config.datacenter

        with self.database.session() as session:
            stage = session.query(Stage).filter(Stage.id == data.stage_id).first()

            if stage is None:
                raise cherrypy.HTTPError(404, "Unknown stage id")

            if stage.job.status != JobStatus.COMPLETED:
                raise cherrypy.HTTPError(400, "Stage does not have a completed status")

            rollback = session.query(Rollback).join(Job, Rollback.job_id == Job.id).filter(Rollback.app == stage.app). \
                filter(Rollback.environment == data.env).filter(Job.stopped_at == None).first()
            if rollback is not None:
                raise cherrypy.HTTPError(400, "A rollback in " + data.datacenter + " of app " + rollback.app +
                                         " is currently running in environment " + rollback.environment)

            deploy = session.query(Deploy).join(Job, Deploy.job_id == Job.id).join(Stage, Deploy.stage_id == Stage.id). \
                filter(Stage.app == stage.app).filter(Job.datacenter == data.datacenter). \
                filter(Deploy.environment == data.env).filter(Job.stopped_at == None).first()
            if deploy is not None:
                raise cherrypy.HTTPError(400, "A deploy in " + data.datacenter + " of app " + deploy.stage.app +
                                         " is already running in environment " + deploy.environment)

            job = Job(name='App Deploy ' + stage.app, datacenter=data.datacenter,
                      user_assignment_id=cherrypy.request.user['id'])

            session.add(job)
            session.flush()

            deploy = Deploy(stage=stage, job=job, environment=data.env)
            session.add(deploy)
            session.flush()

            if not os.path.isfile(self.config.app_type_path + "/" + stage.type + "-deploy.json"):
                raise cherrypy.HTTPError(404, "Unknown app deploy type " + stage.type)

            try:
                with open(self.config.app_type_path + "/" + stage.type + "-deploy.json") as f:
                    app_json = json.load(f)

            except IOError as e:
                raise cherrypy.HTTPError(500, "Error opening app type file " + e.message)
            except ValueError as e:
                raise cherrypy.HTTPError(500, "Error loading app type json " + e.message)

            try:
                app_type = AppTypeValidator(app_json)
            except ModelConversionError as e:
                raise cherrypy.HTTPError(400, "App Type JSON Error " + json.dumps(e.message))

            try:
                app_type.validate()
            except ModelValidationError as e:
                raise cherrypy.HTTPError(400, "App Type JSON Error " + json.dumps(e.message))

            if data.deploy_tasks is not None:

                # Allow tasks to be overwritten
                for task_index, app_task in enumerate(list(app_type.tasks)):
                    for config_task in list(data.deploy_tasks):
                        if app_task.name == config_task.name \
                                and app_task.priority == config_task.priority:
                            app_type.tasks[task_index] = config_task
                            data.deploy_tasks.remove(config_task)

                app_type.tasks.extend(data.deploy_tasks)

            app_type.tasks.sort(key=lambda x: x.priority)

            try:
                workers = self.get_workers(job.datacenter)
            except GetWorkersException as e:
                raise cherrypy.HTTPError(500, e.message)

            for worker in list(workers):
                if worker.tags['environment'] != data.env:
                    workers.remove(worker)
                    continue
                if data.tags is not None:
                    for key, value in data.tags.iteritems():
                        if key not in worker.tags:
                            workers.remove(worker)
                            continue
                        if worker.tags[key] != value:
                            workers.remove(worker)
                            continue
                if data.targets is not None:
                    if worker.target not in data.targets:
                        workers.remove(worker)
                        continue
                    else:
                        if stage.app in worker.tags['apps']:
                            raise cherrypy.HTTPError(400, "Worker " + worker.target + " already has app "
                                                     + stage.app + " deployed. Cannot bootstrap worker.")
                else:
                    if stage.app not in worker.tags['apps']:
                        workers.remove(worker)
                        continue

            if len(workers) == 0:
                raise cherrypy.HTTPError(500, "No workers to deploy to")

            if data.targets is None and len(workers) < data.min_nodes:
                raise cherrypy.HTTPError(500, "Not enough nodes to deploy to")

            if data.targets is not None and len(workers) < len(data.targets):
                raise cherrypy.HTTPError(500, "Could not find all targets to deploy to")

            reobj = re.compile("{(.*?)}")
            variables = {
                'worker_count': str(len(workers)),
                'workers': json.dumps([worker.target for worker in workers]),
                'deploy_path': self.config.deploy_path,
                'name': stage.app,
                'app_name': stage.app,
                'start_date': deploy.job.created_at.strftime("%s"),
                'stage_id': str(stage.id),
                'deploy_id': str(deploy.id),
                'environment': deploy.environment
            }
            if data.tags is not None:
                deploy.job.tags = data.tags
                variables = variables.copy()
                variables.update(data.tags)

            if app_type.variables is not None:
                for key, value in dict(app_type.variables).iteritems():
                    variables[key] = value

                for key, value in app_type.variables.iteritems():
                    result = reobj.findall(value)

                    for var_key in result:
                        if var_key in variables:
                            value = value.replace("{" + var_key + "}", variables[var_key])

                    variables[key] = value

            if data.deploy_variables is not None:
                for key, value in dict(data.deploy_variables).iteritems():
                    variables[key] = value

                for key, value in data.deploy_variables.iteritems():
                    result = reobj.findall(value)

                    for var_key in result:
                        if var_key in variables:
                            value = value.replace("{" + var_key + "}", variables[var_key])

                    variables[key] = value

            for worker in workers:

                job_target = JobTarget(job=job, worker_id=worker.id)
                session.add(job_target)

                for task_index, task_data in enumerate(app_type.tasks):

                    try:
                        task_data.validate()
                    except ModelValidationError as e:
                        raise cherrypy.HTTPError(400, "Task validation error " + json.dumps(e.message))

                    task = Task(name=task_data.name, order=task_index, job_target=job_target)
                    session.add(task)
                    job_target.tasks.append(task)

                    for action_index, action in enumerate(task_data.actions):
                        action_obj = Action(processor=action.processor, order=action_index)
                        session.add(action_obj)
                        task.actions.append(action_obj)

                        if action.arguments is not None:
                            for key in action.arguments:
                                argument = action.arguments[key]

                                result = reobj.findall(argument)

                                for var_key in result:
                                    if var_key in variables:
                                        argument = argument.replace("{" + var_key + "}", variables[var_key])

                                action.arguments[key] = argument

                            action_obj.arguments = action.arguments

                if len(job_target.tasks) == 0:
                    raise cherrypy.HTTPError(400, "Deploy has no tasks")

            session.commit()
            session.refresh(job)
            session.refresh(deploy)
            return deploy, job


class FrameworkAPI(AbstractFrameworkAPI):
    exposed = True

    def __init__(self, framework):
        super(FrameworkAPI, self).__init__(framework, '/cd/deploy')
        self.logger = logging.getLogger("hq.framework.api.codedeployer.deploy")

    @cherrypy.tools.json_out()
    @cherrypy.tools.auth(permission="herqles.framework.cd_deploy.get")
    def GET(self, deploy_id=None, page=1, app=None):
        if deploy_id is None:

            deploys = []

            per_page = 10
            offset = (int(page) - 1) * per_page

            with self.framework.database.session() as session:
                deploy_objects = session.query(Deploy).join(Job, Deploy.job_id == Job.id). \
                    join(Stage, Deploy.stage_id == Stage.id).order_by(Deploy.id.desc())

                if app is not None:
                    deploy_objects = deploy_objects.filter(Stage.app == app)

                deploy_objects = deploy_objects.limit(per_page).offset(offset)

                for deploy in deploy_objects:
                    data = {'id': deploy.id,
                            'job_id': deploy.job.id,
                            'stage_id': deploy.stage_id,
                            'environment': deploy.environment,
                            'datacenter': deploy.job.datacenter,
                            'status': deploy.job.status.value,
                            'created_at': self.framework.unix_time_millis(deploy.job.created_at),
                            'updated_at': self.framework.unix_time_millis(deploy.job.updated_at)}

                    if deploy.job.tags is not None:
                        data['tags'] = [{key: value} for key, value in deploy.job.tags.iteritems()]

                    if deploy.job.stopped_at is not None:
                        data['stopped_at'] = self.framework.unix_time_millis(deploy.job.stopped_at)

                    targets = []

                    for job_target in deploy.job.targets:
                        target = {'target': job_target.worker.target}

                        if deploy.job.status == JobStatus.RUNNING:
                            target['task_id'] = job_target.tasks[deploy.job.current_task_index].id
                            target['task_name'] = job_target.tasks[deploy.job.current_task_index].name

                        if deploy.job.status == JobStatus.FAILED:
                            target['task_id'] = job_target.tasks[deploy.job.current_task_index].id
                            target['task_name'] = job_target.tasks[deploy.job.current_task_index].name
                            target['task_error'] = job_target.tasks[deploy.job.current_task_index].error_message

                        targets.append(target)

                    data['targets'] = targets

                    deploys.append(data)

            return {"deploys": deploys}
        else:

            with self.framework.database.session() as session:
                deploy = session.query(Deploy).filter(Deploy.id == deploy_id).first()

                if deploy is None:
                    return {}

                data = {'id': deploy.id,
                        'job_id': deploy.job.id,
                        'stage_id': deploy.stage_id,
                        'environment': deploy.environment,
                        'datacenter': deploy.job.datacenter,
                        'status': deploy.job.status.value,
                        'created_at': self.framework.unix_time_millis(deploy.job.created_at),
                        'updated_at': self.framework.unix_time_millis(deploy.job.updated_at)}

                if deploy.job.tags is not None:
                    data['tags'] = [{key: value} for key, value in deploy.job.tags.iteritems()]

                if deploy.job.stopped_at is not None:
                    data['stopped_at'] = self.framework.unix_time_millis(deploy.job.stopped_at)

                targets = []

                for job_target in deploy.job.targets:
                    target = {'target': job_target.worker.target}

                    if deploy.job.status == JobStatus.RUNNING:
                        target['task_id'] = job_target.tasks[deploy.job.current_task_index].id
                        target['task_name'] = job_target.tasks[deploy.job.current_task_index].name

                    if deploy.job.status == JobStatus.FAILED:
                        target['task_id'] = job_target.tasks[deploy.job.current_task_index].id
                        target['task_name'] = job_target.tasks[deploy.job.current_task_index].name
                        target['task_error'] = job_target.tasks[deploy.job.current_task_index].error_message

                    targets.append(target)

                data['targets'] = targets

                return data

    @cherrypy.tools.json_in()
    @cherrypy.tools.json_out()
    @cherrypy.tools.auth(permission="herqles.framework.cd_deploy.create")
    def POST(self):

        data = cherrypy.request.json

        try:
            deploy_validator = DeployValidator(data, strict=False)
        except ModelConversionError as e:
            raise cherrypy.HTTPError(400, "Invalid JSON payload " + json.dumps(e.message))

        try:
            deploy_validator.validate()
        except ModelValidationError as e:
            raise cherrypy.HTTPError(400, "Invalid JSON payload " + json.dumps(e.message))

        deploy, job = self.framework.deploy_app(deploy_validator)

        return {"deploy_id": deploy.id, "job_id": job.id}
