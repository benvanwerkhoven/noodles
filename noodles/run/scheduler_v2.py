from .coroutines import (Connection)
from .job_keeper import (JobKeeper)

from ..workflow import (
    is_workflow, get_workflow, Empty, invert_links, insert_result,
    is_node_ready, Workflow)
import uuid
import sys


def run_job(node):
    return node.foo(*node.bound_args.args,
                    **node.bound_args.kwargs)


class Job:
    def __init__(self, workflow, node_id):
        self.workflow = workflow
        self.node_id = node_id

    def __iter__(self):
        return iter((self.workflow, self.node_id))

    @property
    def node(self):
        return self.workflow.nodes[self.node_id]


class Result:
    def __init__(self, key, status, value, msg):
        self.key = key
        self.status = status
        self.value = value
        self.msg = msg

    def __iter__(self):
        return iter((self.key, self.status, self.value, self.msg))


class DynamicLink:
    def __init__(self, source, target, node):
        self.source = source
        self.target = target
        self.node = node

    def __iter__(self):
        return iter((self.source, self.target, self.node))


class Scheduler:
    """
    Schedules jobs, recieves results, then schedules more jobs as they
    become ready to compute. This class communicates with a pool of workers
    by means of coroutines.
    """
    def __init__(self, verbose=False, error_handler=None, job_keeper=None):
        self.dynamic_links = {}
        self.jobs = job_keeper if job_keeper is not None else JobKeeper()
        # I'd rather say: self.jobs = job_keeper or {}
        # but Python thruthiness of {} is False
        self.count = 0
        self.key_map = {}
        self.verbose = verbose
        self.handle_error = error_handler

    def run(self, connection: Connection, master: Workflow):
        """Run a workflow.

        :param connection:
            A connection giving a sink to the job-queue and a source yielding
            results.
        :type connection: Connection

        :param master:
            The workflow.
        :type master: Workflow
        """
        # initiate worker slave army and take up reins ...
        source, sink = connection.setup()

        # schedule work
        self.add_workflow(master, master, master.root, sink)
        graceful_exit = False

        # process results
        for job_key, status, result, err_msg in source:
            if status == 'error':
                if self.handle_error:
                    wf, n = self.jobs[job_key]
                    self.handle_error(wf.nodes[n], err_msg)
                    graceful_exit = True
                else:
                    raise err_msg

            if self.verbose:
                print("sched result [{0}]: ".format(self.key_map[job_key]),
                      result,
                      file=sys.stderr, flush=True)
            wf, n = self.jobs[job_key]

            del self.jobs[job_key]
            if len(self.jobs) == 0 and graceful_exit:
                return

            # if we retrieve a workflow, push a child
            if is_workflow(result):
                child_wf = get_workflow(result)
                self.add_workflow(child_wf, wf, n, sink)
                continue

            # if this result is the root of a workflow, pop to parent
            while n == wf.root:
                _, wf, n = self.dynamic_links[id(wf)]
                if wf == master and n == master.root:
                    return result

            # and insert it in the nodes that need it
            for (tgt, address) in wf.links[n]:
                insert_result(wf.nodes[tgt], address, result)
                if is_node_ready(wf.nodes[tgt]) and not graceful_exit:
                    self.schedule(Job(workflow=wf, node_id=tgt), sink)

            # see if we're done
            if wf == master and n == master.root:
                return result

        print("Seventh circle of HELL")

    def schedule(self, job, sink):
        sink.send(self.jobs.register(job))

    def add_workflow(self, wf, target, node, sink):
        self.dynamic_links[id(wf)] = DynamicLink(
            source=wf, target=target, node=node)

        for n in wf.nodes:
            if is_node_ready(wf.nodes[n]):
                self.schedule(Job(workflow=wf, node_id=n), sink)

