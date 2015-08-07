import json
import logging
import datetime

import cherrypy
import os
from schematics.exceptions import ModelValidationError, ModelConversionError

from schematics.types import StringType
import re

from hqframework.framework import AbstractFramework, AbstractFrameworkAPI
from hqcodedeployer.models import Deploy, Rollback, Stage
from hqlib.sql.models import Task, TaskStatus, Job, JobStatus, JobTarget, Action
from hqframework.exceptions import LaunchTaskException, GetWorkersException
from hqcodedeployer.validators import RollbackValidator, AppTypeValidator


class Framework(AbstractFramework):
    def __init__(self):
        super(Framework, self).__init__("codedeployer-rollback", Rollback)
        self.logger = logging.getLogger("hq.framework.codedeployer.rollback")

    def config_class(self):
        config_class = super(Framework, self).config_class()

        class ConfigValidator(config_class):
            app_type_path = StringType(required=True)
            deploy_path = StringType(required=True)

        return ConfigValidator

    def registered(self):
        pass

    def process_job(self, job_id):
        with self.database.session() as session:
            rollback = session.query(Rollback).join(Job, Rollback.job_id == Job.id). \
                filter(Job.id == job_id).filter(Job.stopped_at == None).first()

            if rollback.job.status == JobStatus.PENDING:

                if self.tasks_have_status(rollback.job, TaskStatus.PENDING):
                    self.logger.info("All rollback tasks are now pending. Starting Rollback "
                                     + rollback.stage.app + " (" + str(rollback.id) + ")")
                    rollback.job.status = JobStatus.RUNNING
                    session.commit()
            elif rollback.job.status == JobStatus.RUNNING:

                # check if completed
                if self.tasks_have_status(rollback.job, TaskStatus.FINISHED):
                    self.logger.info("Rollback Completed (" + str(rollback.id) + ")")
                    rollback.job.status = JobStatus.COMPLETED
                    rollback.job.stopped_at = datetime.datetime.now()
                    session.commit()
                    return

                # check if failed
                if self.some_task_has_status(rollback.job, TaskStatus.FAILED):
                    self.logger.info("Rollback Failed (" + str(rollback.id) + ")")
                    for target_task in rollback.job.targets:
                        for task in target_task.tasks:
                            if task.status == TaskStatus.PENDING:
                                task.status = TaskStatus.KILLED
                                task.error_message = "Rollback failed"
                                task.stopped_at = datetime.datetime.now()
                                task.save()
                    rollback.job.status = JobStatus.FAILED
                    rollback.job.stopped_at = datetime.datetime.now()
                    session.commit()
                    return

                all_finished = True

                for target_task in rollback.job.targets:
                    task = target_task.tasks[rollback.job.current_task_index]

                    if task.status == TaskStatus.LOST:
                        self.logger.info("Rollback Task " + str(task.id) + " is lost. Retrying...")

                    if task.status == TaskStatus.PENDING or task.status == TaskStatus.LOST:

                        worker = target_task.worker

                        try:
                            self.logger.info("Launching Task " + task.name)
                            self.launch_task(worker, task)
                        except LaunchTaskException as e:
                            self.logger.error("Error launching rollback tasks: " + e.message)
                            task.error_message = e.message
                            task.stopped_at = datetime.datetime.now()
                            task.status = TaskStatus.FAILED
                            session.commit()

                    elif task.status == TaskStatus.RUNNING:
                        if self.unix_time_millis(datetime.datetime.now()) - \
                                self.unix_time_millis(task.updated_at) > 60000:
                            self.logger.warning("Rollback Task " + str(task.id) + " timed out. It is now lost.")
                            task.status = TaskStatus.LOST
                            session.commit()

                    if task.status != TaskStatus.FINISHED:
                        all_finished = False

                if all_finished:
                    rollback.job.current_task_index += 1

                    if rollback.job.current_task_index >= len(rollback.job.targets[0].tasks):
                        rollback.job.current_task_index = len(rollback.job.targets[0].tasks)

                    session.commit()

    def on_stop(self):
        pass

    def rollback_app(self, data):

        if data.datacenter is None:
            data.datacenter = self.config.datacenter

        with self.database.session() as session:

            rollback = session.query(Rollback).join(Job, Rollback.job_id == Job.id).filter(Rollback.app == data.app). \
                filter(Job.datacenter == data.datacenter).filter(Rollback.environment == data.env). \
                filter(Job.stopped_at == None).first()
            if rollback is not None:
                raise cherrypy.HTTPError(400, "A rollback in " + data.datacenter + " of app " + rollback.app +
                                         " is already running in environment " + rollback.environment)

            deploy = session.query(Deploy).join(Job, Deploy.job_id == Job.id).join(Stage, Deploy.stage_id == Stage.id). \
                filter(Stage.app == data.app).filter(Job.datacenter == data.datacenter).\
                filter(Deploy.environment == data.env).filter(Job.stopped_at == None).first()
            if deploy is not None:
                raise cherrypy.HTTPError(400, "A deploy in " + data.datacenter + " of app " + deploy.stage.app +
                                         " is currently running in environment " + deploy.environment)

            job = Job(name='App Rollback ' + data.app, datacenter=data.datacenter,
                      user_assignment_id=cherrypy.request.user['id'])

            session.add(job)
            session.flush()

            rollback = Rollback(app=data.app, type=data.type, job=job, environment=data.env)
            session.add(rollback)
            session.flush()

            if not os.path.isfile(self.config.app_type_path + "/" + rollback.type + "-rollback.json"):
                raise cherrypy.HTTPError(404, "Unknown app rollback type " + rollback.type)

            try:
                with open(self.config.app_type_path + "/" + rollback.type + "-rollback.json") as f:
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

            if data.rollback_tasks is not None:

                # Allow tasks to be overwritten
                for task_index, app_task in enumerate(list(app_type.tasks)):
                    for config_task in list(data.rollback_tasks):
                        if app_task.name == config_task.name \
                                and app_task.priority == config_task.priority:
                            app_type.tasks[task_index] = config_task
                            data.rollback_tasks.remove(config_task)

                app_type.tasks.extend(data.rollback_tasks)

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
                else:
                    if data.app not in worker.tags['apps']:
                        workers.remove(worker)
                        continue

            if len(workers) == 0:
                raise cherrypy.HTTPError(500, "No workers to rollback to")

            reobj = re.compile("{(.*?)}")
            variables = {
                'worker_count': str(len(workers)),
                'workers': json.dumps([worker.target for worker in workers]),
                'deploy_path': self.config.deploy_path,
                'name': data.app,
                'app_name': data.app,
                'start_date': rollback.job.created_at.strftime("%s"),
                'rollback_id': str(rollback.id),
                'environment': rollback.environment
            }
            if data.tags is not None:
                rollback.job.tags = data.tags
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

            if data.rollback_variables is not None:
                for key, value in dict(data.rollback_variables).iteritems():
                    variables[key] = value

                for key, value in data.rollback_variables.iteritems():
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
                    raise cherrypy.HTTPError(400, "Rollback has no tasks")

            session.commit()
            session.refresh(job)
            session.refresh(rollback)
            return rollback, job


class FrameworkAPI(AbstractFrameworkAPI):
    exposed = True

    def __init__(self, framework):
        super(FrameworkAPI, self).__init__(framework, '/cd/rollback')
        self.logger = logging.getLogger("hq.framework.api.codedeployer.rollback")

    @cherrypy.tools.json_out()
    @cherrypy.tools.auth(permission="herqles.framework.cd_rollback.get")
    def GET(self, rollback_id=None, page=1, app=None):
        if rollback_id is None:

            rollbacks = []

            per_page = 10
            offset = (int(page) - 1) * per_page

            with self.framework.database.session() as session:
                rollback_objects = session.query(Rollback).join(Job, Rollback.job_id == Job.id) \
                    .order_by(Rollback.id.desc())

                if app is not None:
                    rollback_objects = rollback_objects.filter(Stage.app == app)

                rollback_objects = rollback_objects.limit(per_page).offset(offset)

                for rollback in rollback_objects:
                    data = {'id': rollback.id,
                            'job_id': rollback.job.id,
                            'app': rollback.app,
                            'environment': rollback.environment,
                            'datacenter': rollback.job.datacenter,
                            'status': rollback.job.status.value,
                            'created_at': self.framework.unix_time_millis(rollback.job.created_at),
                            'updated_at': self.framework.unix_time_millis(rollback.job.updated_at)}

                    if rollback.job.tags is not None:
                        data['tags'] = [{key: value} for key, value in rollback.job.tags.iteritems()]

                    targets = []

                    for job_target in rollback.job.targets:
                        target = {'target': job_target.worker.target}

                        if rollback.job.status == JobStatus.RUNNING:
                            target['task_id'] = job_target.tasks[rollback.job.current_task_index].id
                            target['task_name'] = job_target.tasks[rollback.job.current_task_index].name

                        if rollback.job.status == JobStatus.FAILED:
                            target['task_id'] = job_target.tasks[rollback.job.current_task_index].id
                            target['task_name'] = job_target.tasks[rollback.job.current_task_index].name
                            target['task_error'] = job_target.tasks[rollback.job.current_task_index].error_message

                        targets.append(target)

                    data['targets'] = targets

                    if rollback.job.stopped_at is not None:
                        data['stopped_at'] = self.framework.unix_time_millis(rollback.job.stopped_at)

                    rollbacks.append(data)

            return {"rollbacks": rollbacks}
        else:

            with self.framework.database.session() as session:
                rollback = session.query(Rollback).filter(Rollback.id == rollback_id).first()

                if rollback is None:
                    return {}

                data = {'id': rollback.id,
                        'job_id': rollback.job.id,
                        'app': rollback.app,
                        'environment': rollback.environment,
                        'datacenter': rollback.job.datacenter,
                        'status': rollback.job.status.value,
                        'created_at': self.framework.unix_time_millis(rollback.job.created_at),
                        'updated_at': self.framework.unix_time_millis(rollback.job.updated_at)}

                if rollback.job.tags is not None:
                    data['tags'] = [{key: value} for key, value in rollback.job.tags.iteritems()]

                targets = []

                for job_target in rollback.job.targets:
                    target = {'target': job_target.worker.target}

                    if rollback.job.status == JobStatus.RUNNING:
                        target['task_id'] = job_target.tasks[rollback.job.current_task_index].id
                        target['task_name'] = job_target.tasks[rollback.job.current_task_index].name

                    if rollback.job.status == JobStatus.FAILED:
                        target['task_id'] = job_target.tasks[rollback.job.current_task_index].id
                        target['task_name'] = job_target.tasks[rollback.job.current_task_index].name
                        target['task_error'] = job_target.tasks[rollback.job.current_task_index].error_message

                    targets.append(target)

                data['targets'] = targets

                if rollback.job.stopped_at is not None:
                    data['stopped_at'] = self.framework.unix_time_millis(rollback.job.stopped_at)

                return data

    @cherrypy.tools.json_in()
    @cherrypy.tools.json_out()
    @cherrypy.tools.auth(permission="herqles.framework.cd_rollback.create")
    def POST(self):

        data = cherrypy.request.json

        try:
            rollback_validator = RollbackValidator(data, strict=False)
        except ModelConversionError as e:
            raise cherrypy.HTTPError(400, "Invalid JSON payload " + json.dumps(e.message))

        try:
            rollback_validator.validate()
        except ModelValidationError as e:
            raise cherrypy.HTTPError(400, "Invalid JSON payload " + json.dumps(e.message))

        rollback, job = self.framework.rollback_app(rollback_validator)

        return {"rollback_id": rollback.id, "job_id": job.id}
