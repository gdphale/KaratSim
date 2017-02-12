import queue as Q
from ksim_classes import *


# takes a number of interviews and a number of emails to populate a given day with. It then returns a sorted list
# of these tasks in a schedule.
def populate_day(numbinterviews, numbemails):
    schedule = []

    # the interviews show up according to a histogram of interview times. This histogram is stored in the
    # list PROBS['IV Time Hist']. *** You can change it at the top ***
    hist_sum = sum(PROBS['IV Time Hist'])
    iv_time_prob = [0] * IV_TIME_SLOTS
    for i in range(IV_TIME_SLOTS):
        if i != 0:
            iv_time_prob[i] = PROBS['IV Time Hist'][i] / hist_sum + iv_time_prob[i - 1]
        else:
            iv_time_prob[i] = PROBS['IV Time Hist'][i] / hist_sum

    # populate the day's interviews
    R.seed()
    for i in range(numbinterviews):
        rand = R.random()
        iv_slot = 0
        # as soon as we pass the value in the array, that is the timeslot that it falls into
        for count in range(IV_TIME_SLOTS):
            if rand < iv_time_prob[count]:
                iv_slot = count
                break
        timeslot = iv_slot*6 # times 6 because there are 6 slots in each 30 minutes timeslot, and this is only populating interviews
        schedule.append(Task('Support', timeslot))

    # The emails show up with a random chance all during the day
    for i in range(numbemails):
        timeslot = M.floor(R.random() * TOTAL_TIME_SLOTS)
        schedule.append(Task('Email', timeslot))

    # sort the schedule
    schedule.sort(key=lambda x: x.start_time)
    schedule = break_down_sched(schedule)
    schedule.sort(key=lambda x: x.start_time) # just in case it got out of order.

    return schedule


# this combines support tasks that have the same start time
def break_down_sched(schedule):
    # this goes through and combines support tasks, setting support tasks that have been removed to 'None'
    support_count = 1
    for slot in range(1, len(schedule)):
        # this code looks terrible. Basically it just checks to see if we have reached an interview that is not starting at the same time as the one before, or reached
        # an email task, then we combine the previous supports into one support task
        if support_count > 1 and (schedule[slot].type == 'Email' or schedule[slot - 1].start_time != schedule[slot].start_time):
            numb_errs = 0
            combine_start_time = schedule[slot - 1].start_time
            # remove the single support tasks and count how many errors there were
            for rem in range(1, support_count + 1):
                if schedule[slot - rem].failure:
                    numb_errs += 1
                schedule[slot - rem] = None
            # combine the support tasks into groupings of 3
            numb_tasks = M.ceil(support_count / 3)
            for i in range(numb_tasks):
                combined_task = Task('Support', combine_start_time)
                if i == numb_tasks - 1:
                    if support_count % 3 == 0:
                        schedule[slot - support_count + i] = combined_task.combine_support(3, M.floor( numb_errs / numb_tasks) + numb_errs % numb_tasks)
                    else:
                        schedule[slot - support_count + i] = combined_task.combine_support(support_count % 3,
                                                                                           numb_errs % numb_tasks)
                else:
                    schedule[slot - support_count + i] = combined_task.combine_support(3, M.floor(numb_errs / numb_tasks))
            support_count = 1

        # if we hit an email and had no support tasks in a row, we just want to skip over
        elif schedule[slot].type == 'Email':
            continue
        elif schedule[slot - 1].type != 'Email' and schedule[slot].start_time == schedule[slot - 1].start_time:
            support_count += 1
    return [t for t in schedule if t is not None]


def add_tasks(sched, active_tasks, slot):
    while len(sched) > 0 and sched[0].start_time <= slot:
        active_tasks.put(sched.pop(0))


def add_ops_from_list(ops_members, starting_ops_times, ops_hours, slot):
    if len(starting_ops_times) != len(ops_hours):
        print('You must have a number of hours for each ops member working.')
        exit(1)
    while len(starting_ops_times) > 0 and starting_ops_times[0] == slot:
        ops_members.append(OpsMember(slot, ops_hours[0]))
        starting_ops_times.pop(0)
        ops_hours.pop(0)
    ops_members.sort(key=lambda x: x.task_prior)


def allocate_ops_tasks(active_tasks, ops_members):
    if not active_tasks.empty():
        lowest_task = active_tasks.get()
        lowest_prior = lowest_task.prior
        active_tasks.put(lowest_task)
    while not active_tasks.empty() and len(ops_members) != 0 and lowest_prior > ops_members[0].task_prior:
        if ops_members[0].active_task is None:
            ops_members[0].set_active_task(active_tasks.get())
        else:
            old_task = ops_members[0].switch_task(active_tasks.get())
            active_tasks.put(old_task)
        if not active_tasks.empty():
            lowest_task = active_tasks.get()
            lowest_prior = lowest_task.prior
            active_tasks.put(lowest_task)
        ops_members.sort(key=lambda x: x.task_prior)


def perform_ops_tasks(ops_members, schedule, completed_tasks, slot):
    for ops in ops_members:
        finished = ops.perform_task(slot)
        if finished:
            if ops.active_task.type == 'Support':
                schedule.append(Task('Creation', ops.active_task.start_time + SLOT_BTWN_SUP_CRE))
            if ops.active_task.type == 'Creation':
                schedule.append(Task('Publishing', slot + QC_SLOTS))
            completed_tasks.append(ops.active_task)
            ops.set_available()

    # re-sort the schedule to get those added tasks back in the right spot back in the right spot
    schedule.sort(key=lambda x: x.start_time)

def check_finished_ops(ops_members, active_tasks, finished_ops_members):
    for ops in range(len(ops_members)):
        if ops_members[ops].check_if_complete():
            if ops_members[ops].active_task is not None:
                active_tasks.put(ops_members[ops].active_task)
            ops_members[ops].set_available()
            finished_ops_members.append(ops_members[ops])
            ops_members[ops] = None
    return [o for o in ops_members if o is not None]


def update_priorities(active_tasks, ops_members):
    temp_queue = Q.PriorityQueue()
    while not active_tasks.empty():
        to_update = active_tasks.get()
        temp_queue.put(to_update.update_priority())
    for ops in ops_members:
        ops.update_active_task()
    ops_members.sort(key=lambda x: x.task_prior)
    return temp_queue

# given a schedule, this returns the minimum number of ops member we will need to cover the schedule, if everything
# goes perfectly as planned, and there is no inefficiency.
def min_ops_members(schedule):
    return M.ceil(min_ops_hours(schedule) / DAILY_OPS_MEMBER_HOURS)


# gets the number of task hours there are in one day. ie: if everyone did everything perfectly, how many hours of work
#  is there in this day?
def min_ops_hours(schedule):
    ops_slots = 0
    for task in schedule:
        ops_slots += task.slots_left
        if task.type == 'Support':
            ops_slots += (TASK_TIMES['Publishing'] + TASK_TIMES['Creation']) / 5
    # converts slots to hours
    return ops_slots * 5 / 60


