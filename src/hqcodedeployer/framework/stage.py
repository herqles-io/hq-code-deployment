import json
import datetime
import logging
import random

import os.path
import cherrypy

from schematics.exceptions import ModelValidationError, ModelConversionError
import re

from hqframework.framework import AbstractFramework, AbstractFrameworkAPI
from hqframework.exceptions import LaunchTaskException, GetWorkersException
from hqlib.sql.models import Task, Action, TaskStatus, Job, JobStatus, JobTarget
from hqcodedeployer.models import Stage
from hqcodedeployer.validators import StageValidator, AppTypeValidator
from schematics.types import StringType


class Framework(AbstractFramework):

    def __init__(self):
        super(Framework, self).__init__("codedeployer-stage", Stage)
        self.logger = logging.getLogger("hq.framework.codedeployer.stage")

    def config_class(self):
        config_class = super(Framework, self).config_class()

        class ConfigValidator(config_class):
            app_type_path = StringType(required=True)
            build_path = StringType(required=True)

        return ConfigValidator

    def on_stop(self):
        pass

    def process_job(self, job_id):
        with self.database.session() as session:
            stage = session.query(Stage).join(Job, Stage.job_id == Job.id). \
                filter(Job.id == job_id).filter(Job.stopped_at == None).first()

            if stage is None:
                return

            if stage.job.status == JobStatus.PENDING:

                if self.tasks_have_status(stage.job, TaskStatus.PENDING):
                    self.logger.info("All stage tasks are now pending. Starting Stage "
                                     + stage.app + " (" + str(stage.id) + ")")
                    stage.job.status = JobStatus.RUNNING
                    session.commit()
                    return
            elif stage.job.status == JobStatus.RUNNING:

                # check if completed
                if self.tasks_have_status(stage.job, TaskStatus.FINISHED):
                    self.logger.info("Stage Completed (" + str(stage.id) + ")")
                    stage.job.status = JobStatus.COMPLETED
                    stage.job.stopped_at = datetime.datetime.now()
                    session.commit()
                    return

                # check if failed
                if self.some_task_has_status(stage.job, TaskStatus.FAILED):
                    self.logger.info("Stage Failed (" + str(stage.id) + ")")
                    for task in stage.job.targets[0].tasks:
                        if task.status == TaskStatus.PENDING:
                            task.status = TaskStatus.KILLED
                            task.error_message = "Stage failed"
                            task.stopped_at = datetime.datetime.now()
                    stage.job.status = JobStatus.FAILED
                    stage.job.stopped_at = datetime.datetime.now()
                    session.commit()
                    return

                all_finished = True

                task = stage.job.targets[0].tasks[stage.job.current_task_index]

                if task.status == TaskStatus.LOST:
                    self.logger.info("Stage Task " + str(task.id) + " is lost. Retrying...")

                if task.status == TaskStatus.PENDING or task.status == TaskStatus.LOST:

                    worker = stage.job.targets[0].worker

                    try:
                        self.logger.info("Launching Task " + task.name)
                        self.launch_task(worker, task)
                    except LaunchTaskException as e:
                        self.logger.error("Error launching stage tasks: " + e.message)
                        task.error_message = e.message
                        task.stopped_at = datetime.datetime.now()
                        task.status = TaskStatus.FAILED
                        session.commit()

                elif task.status == TaskStatus.RUNNING:
                    if self.unix_time_millis(datetime.datetime.now()) - self.unix_time_millis(task.updated_at) > 60000:
                        self.logger.warning("Stage Task " + str(task.id) + " timed out. It is now lost.")
                        task.status = TaskStatus.LOST
                        session.commit()

                if task.status != TaskStatus.FINISHED:
                    all_finished = False

                if all_finished:
                    stage.job.current_task_index += 1

                    if stage.job.current_task_index >= len(stage.job.targets[0].tasks):
                        stage.job.current_task_index = len(stage.job.targets[0].tasks)

                    session.commit()

    def registered(self):
        pass

    def stage_app(self, data):

        with self.database.session() as session:
            stage = session.query(Stage).join(Job, Stage.job_id == Job.id).filter(Stage.app == data.name). \
                filter(Job.stopped_at == None).first()
            if stage is not None:
                raise cherrypy.HTTPError(400, "Staging for app " + data.name + " is already running")

            job = Job(name='App Stage ' + data.name, datacenter=self.config.datacenter,
                      user_assignment_id=cherrypy.request.user['id'])
            session.add(job)
            session.flush()

            stage = Stage(app=data.name, job=job, type=data.type, branch=data.branch)
            session.add(stage)
            session.flush()

            if not os.path.isfile(self.config.app_type_path + "/" + stage.type + "-stage.json"):
                raise cherrypy.HTTPError(404, "Unknown app stage type " + stage.type)

            try:
                with open(self.config.app_type_path + "/" + stage.type + "-stage.json") as f:
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

            if data.stage_tasks is not None:

                # Allow tasks to be overwritten
                for task_index, app_task in enumerate(list(app_type.tasks)):
                    for config_task in list(data.stage_tasks):
                        if app_task.name == config_task.name \
                                and app_task.priority == config_task.priority:
                            app_type.tasks[task_index] = config_task
                            data.stage_tasks.remove(config_task)

                app_type.tasks.extend(data.stage_tasks)

            app_type.tasks.sort(key=lambda x: x.priority)

            try:
                workers = self.get_workers(job.datacenter)
            except GetWorkersException as e:
                raise cherrypy.HTTPError(500, e.message)

            for worker in workers:
                if data.tags is not None:
                    for key, value in data.tags.iteritems():
                        if key not in worker.tags:
                            workers.remove(worker)
                            continue
                        if worker.tags[key] != value:
                            workers.remove(worker)
                            continue

            if len(workers) == 0:
                raise cherrypy.HTTPError(500, "No workers to build a stage on")

            worker = random.choice(workers)
            job_target = JobTarget(job=job, worker_id=worker.id)
            session.add(job_target)

            reobj = re.compile("{(.*?)}")
            variables = {
                'target': worker.target,
                'repo': data.repo,
                'branch': data.branch,
                'build_path': self.config.build_path,
                'name': stage.app,
                'app_name': stage.app,
                'start_date': str(self.unix_time_millis(stage.job.created_at)),
                'stage_id': str(stage.id)
            }
            if data.tags is not None:
                stage.job.tags = data.tags
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

            if data.stage_variables is not None:
                for key, value in dict(data.stage_variables).iteritems():
                    variables[key] = value

                for key, value in data.stage_variables.iteritems():
                    result = reobj.findall(value)

                    for var_key in result:
                        if var_key in variables:
                            value = value.replace("{" + var_key + "}", variables[var_key])

                    variables[key] = value

            for task_index, task_data in enumerate(app_type.tasks):

                try:
                    task_data.validate()
                except ModelValidationError as e:
                    raise cherrypy.HTTPError(400, "Task validation error " + e.message)

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
                    raise cherrypy.HTTPError(400, "Stage has no tasks")

            session.commit()
            session.refresh(job)
            session.refresh(stage)
            return stage, job


class FrameworkAPI(AbstractFrameworkAPI):

    exposed = True

    def __init__(self, framework):
        super(FrameworkAPI, self).__init__(framework, '/cd/stage')
        self.logger = logging.getLogger("hq.framework.api.codedeployer.stage")

    @cherrypy.tools.json_out()
    @cherrypy.tools.auth(permission="herqles.framework.cd_stage.get")
    def GET(self, stage_id=None, app=None, branch=None, page=1):
        if stage_id is None:

            stages = []

            per_page = 10
            offset = (int(page) - 1) * per_page

            with self.framework.database.session() as session:
                stage_objects = session.query(Stage).join(Job, Stage.job_id == Job.id).order_by(Stage.id.desc())

                if app is not None:
                    stage_objects = stage_objects.filter(Stage.app == app)

                if branch is not None:
                    stage_objects = stage_objects.filter(Stage.branch == branch)

                stage_objects = stage_objects.limit(per_page).offset(offset)

                for stage in stage_objects:
                    data = {'id': stage.id,
                            'job_id': stage.job.id,
                            'app': stage.app,
                            'branch': stage.branch,
                            'status': stage.job.status.value,
                            'created_at': self.framework.unix_time_millis(stage.job.created_at),
                            'updated_at': self.framework.unix_time_millis(stage.job.updated_at)}

                    if stage.job.tags is not None:
                        data['tags'] = [{key: value} for key, value in stage.job.tags.iteritems()]

                    if stage.job.stopped_at is not None:
                        data['stopped_at'] = self.framework.unix_time_millis(stage.job.stopped_at)

                    targets = []

                    for job_target in stage.job.targets:
                        target = {'target': job_target.worker.target}

                        if stage.job.status == JobStatus.RUNNING:
                            target['task_id'] = job_target.tasks[stage.job.current_task_index].id
                            target['task_name'] = job_target.tasks[stage.job.current_task_index].name

                        if stage.job.status == JobStatus.FAILED:
                            target['task_id'] = job_target.tasks[stage.job.current_task_index].id
                            target['task_name'] = job_target.tasks[stage.job.current_task_index].name
                            target['task_error'] = job_target.tasks[stage.job.current_task_index].error_message

                        targets.append(target)

                    data['targets'] = targets

                    stages.append(data)

            return {"stages": stages}
        else:

            with self.framework.database.session() as session:
                stage = session.query(Stage).filter(Stage.id == stage_id).first()

                if stage is None:
                    raise cherrypy.HTTPError(400, "Unknown Stage "+str(stage_id))

                data = {'id': stage.id,
                        'job_id': stage.job.id,
                        'app': stage.app,
                        'branch': stage.branch,
                        'status': stage.job.status.value,
                        'created_at': self.framework.unix_time_millis(stage.job.created_at),
                        'updated_at': self.framework.unix_time_millis(stage.job.updated_at)}

                if stage.job.tags is not None:
                    data['tags'] = [{key: value} for key, value in stage.job.tags.iteritems()]

                if stage.job.stopped_at is not None:
                    data['stopped_at'] = self.framework.unix_time_millis(stage.job.stopped_at)

                targets = []

                for job_target in stage.job.targets:
                    target = {'target': job_target.worker.target}

                    if stage.job.status == JobStatus.RUNNING:
                        target['task_id'] = job_target.tasks[stage.job.current_task_index].id
                        target['task_name'] = job_target.tasks[stage.job.current_task_index].name

                    if stage.job.status == JobStatus.FAILED:
                        target['task_id'] = job_target.tasks[stage.job.current_task_index].id
                        target['task_name'] = job_target.tasks[stage.job.current_task_index].name
                        target['task_error'] = job_target.tasks[stage.job.current_task_index].error_message

                    targets.append(target)
                data['targets'] = targets

                return data

    @cherrypy.tools.json_in()
    @cherrypy.tools.json_out()
    @cherrypy.tools.auth(permission="herqles.framework.cd_stage.create")
    def POST(self):

        data = cherrypy.request.json

        try:
            stage_validator = StageValidator(data, strict=False)
        except ModelConversionError as e:
            raise cherrypy.HTTPError(400, "Invalid JSON payload " + json.dumps(e.message))

        try:
            stage_validator.validate()
        except ModelValidationError as e:
            raise cherrypy.HTTPError(400, "Invalid JSON payload " + json.dumps(e.message))

        stage, job = self.framework.stage_app(stage_validator)

        return {"stage_id": stage.id, "job_id": job.id}
