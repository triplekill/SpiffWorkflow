# Copyright (C) 2012 Matthew Hampton
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA
from collections import deque

import logging
from SpiffWorkflow.Task import Task
from SpiffWorkflow.bpmn.specs.UnstructuredJoin import UnstructuredJoin

LOG = logging.getLogger(__name__)



class InclusiveGateway(UnstructuredJoin):
    """
    Task Spec for a bpmn:parallelGateway node.
    From the specification of BPMN (http://www.omg.org/spec/BPMN/2.0/PDF - document number:formal/2011-01-03):

    The Inclusive Gateway is activated if
     * At least one incoming Sequence Flow has at least one token and
     * For every directed path formed by sequence flow that
        * starts with a Sequence Flow f of the diagram that has a token,
        * ends with an incoming Sequence Flow of the inclusive gateway that has no token, and
        * does not visit the Inclusive Gateway.
     * There is also a directed path formed by Sequence Flow that
        * starts with f,
        * ends with an incoming Sequence Flow of the inclusive gateway that has a token, and
        * does not visit the Inclusive Gateway.

    Upon execution, a token is consumed from each incoming Sequence Flow that has a token. A token will be
    produced on some of the outgoing Sequence Flows.

    TODO: At the moment only converging Inclusive Gateways are supported.

    In order to determine the outgoing Sequence Flows that receive a token,
    all conditions on the outgoing Sequence Flows are evaluated. The evaluation
    does not have to respect a certain order.

    For every condition which evaluates to true, a token MUST be passed on
    the respective Sequence Flow.

    If and only if none of the conditions evaluates to true, the token is passed
    on the default Sequence Flow.

    In case all conditions evaluate to false and a default flow has not been
    specified, the Inclusive Gateway throws an exception.

    """

    def _try_fire_unstructured(self, my_task, force=False):
        # Look at the tree to find all ready and waiting tasks (excluding ourself).
        tasks = []
        for task in my_task.workflow.get_tasks(Task.READY | Task.WAITING):
            if task.thread_id != my_task.thread_id:
                continue
            if task.workflow != my_task.workflow:
                continue
            if task.task_spec == my_task.task_spec:
                continue
            tasks.append(task)

        # Are any of those tasks a potential ancestor to this task?
        waiting_tasks = []
        for task in tasks:
            if self._is_descendant(self, task):
                waiting_tasks.append(task)

        return force or len(waiting_tasks) == 0, waiting_tasks

    def _is_descendant(self, task_spec, task):
        q = deque()
        done = set()

        #We must skip ancestors of the task - so that loops don't make everything a descendent of everything!
        p = task.parent
        while (p != None and not p.task_spec in done and not p.task_spec==task_spec):
            done.add(p.task_spec)
            p = p.parent

        q.append(task.task_spec)
        while q:
            n = q.popleft()
            if n == task_spec:
                return True
            for child in n.outputs:
                if child not in done:
                    done.add(child)
                    q.append(child)
        return False
