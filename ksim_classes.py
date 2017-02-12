import random as R
import math as M

# constants
IV_TIME_SLOTS = 48 # simply 24 * 2
TOTAL_TIME_SLOTS = 288
DAILY_OPS_MEMBER_HOURS = 7.25
SLOT_TIME = 5
SLOT_BTWN_SUP_CRE = 21 # this is the amount of time that passes between support and creation, currently set to 1 hour and 45 minutes
QC_SLOTS = 6 # takes 30 minutes to do QC, this needs to be expanded to change based on the probability of being code only, requires further, etc
DAILY_OPS_MEMBER_SLOTS = DAILY_OPS_MEMBER_HOURS * 60 / SLOT_TIME # the amount of timeslots one ops member works

# ***************************** #
# Amount of time tasks take     #     - eventually expand these into intervals. This will be implemented once we get the day to be simulated with static task-times
# ***************************** #

TASK_TIMES = {'Support':
                  {'No Issue': 5, 'Issue': 15},
              'Creation': 15,
              'Publishing': 20,
              'Email': 20}



# ***************************** #
# Probabilities                 #
# ***************************** #
# the different probabilities we have stored on issues, and other things like interview times
# ------------------------------------------------------------------------------------#
PROBS = {'Support Issue': 0.1,
         'IV Time Hist': [3,3,3,3,3,3,7,3,3,4,5,6,10,5,10,20,22,5,35,22,25,44,33,8,47,30,13,25,27,13,35,12,21,21,20,2,18,5,10,5,22,15,8,10,3,3,2,2]}


# time penalty in minutes for switching a task in the middle of it
# ------------------------------------------------------------------------------------#
SWITCH_PEN = 1


# ***************************** #
# Priority Level of Tasks       #
# ***************************** #

# priority level that a support task starts out at - priority only grows
# ------------------------------------------------------------------------------------#
PRIORS = {'Support': 100,
          'Creation': 60,
          'Publishing': 40,
          'Email': 30}


# ***************************** #
# Priority growth rates         #
# ***************************** #

# Priority level growth rate of the different tasks. units/ 5 minutes (may seem weird, but the model increments by 5 mins)
# ------------------------------------------------------------------------------------#
GROWTH_RATES = {'Support': 5,
                'Creation': 7,
                'Publishing': 3,
                'Email': 4}


# ----------------- here ends constant declarations and definitions -------------------------------

# toString function for a timeslot
def timeslot_to_time(timeslot):
    # 12 hours on a clock
    hour = M.floor( ( timeslot%(TOTAL_TIME_SLOTS/2) ) / 12 )
    minute = M.floor( (timeslot%(TOTAL_TIME_SLOTS/2)% 12)*5 )
    am = timeslot < (TOTAL_TIME_SLOTS/2)
    time = ''
    if hour == 0:
        time = time + '12:'
    else:
        time = time + str(hour) + ':'
    if minute < 10:
        time = time + str(minute) + '0 '
    else:
        time = time + str(minute) + ' '
    if am:
        time = time + 'am'
    else:
        time = time + 'pm'
    return time



# A class which encompasses all the tasks that support members must do. Things such as support,
# creation, etc. are all children of this class
class Task:
    # makes a new task of the given type
    def __init__(self, tasktype, time_slot):
        self.type = tasktype
        self.start_time = time_slot
        self.end_time = -1
        self.numb_supports = 0  # this is only for support tasks, lets us squish them together
        self.failure = False

        # random seed for getting whether or not the interview has an issue
        R.seed()

        # need to see which task it is and initiate it accordingly
        self.prior = PRIORS[tasktype]
        self.growth_rate = GROWTH_RATES[tasktype]

        # if it is a support task then check to see if there is an issue
        if tasktype == 'Support' and R.random() < PROBS['Support Issue']:
            self.slots_left = TASK_TIMES['Support']['Issue'] / SLOT_TIME # time_left is in units of time_slots
            self.numb_supports = 1
            self.failure = True
        elif tasktype == 'Support':
            self.slots_left = TASK_TIMES['Support']['No Issue'] / SLOT_TIME
            self.numb_supports = 1
        else:
            self.slots_left = TASK_TIMES[tasktype] / SLOT_TIME

    # updates the priority of the task, updating it the same amount of priority as being active for
    # one time slot (5 minutes)
    def update_priority(self):
        if self.prior + self.growth_rate >= 100 and self.type == 'Support':
            self.prior = 100
        elif self.prior + self.growth_rate >= 99:
            self.prior = 99
        else:
            self.prior += self.growth_rate
        return self

    # the task is worked on for 5 minutes. Returns whether or not the task is finished.
    def work_on_task(self, timeslot):
        self.slots_left -= 1
        if self.slots_left == 0:
            self.end_time = timeslot
        return self.slots_left == 0

    # combines support tasks into one. This increases the time of the current support task based on how many supports it now contains,
    # and based on how many errors there were in the support tasks it took over
    def combine_support(self, num, numb_errs):
        self.numb_supports = num
        new_time = 1 + numb_errs * (TASK_TIMES['Support']['Issue'] / SLOT_TIME)
        if num > 3:
            new_time += 1
        self.slots_left = new_time
        return self

    # the overriding toString method (in java talk)
    def __str__(self):
        if self.type == 'Support' and self.numb_supports != 1:
            return str(self.numb_supports) + ' ' + self.type + ' tasks happening at ' + timeslot_to_time(
                self.start_time)
        return self.type + ' task happening at ' + timeslot_to_time(self.start_time)

    # less than method, necessary for priority queue sorting
    def __lt__(self, other):
        return self.prior > other.prior

    # compare to, possibly unnecessary as the less than is all that priority queues need
    def __cmp__(self, other):
        return __cmp__(self.prior, other.prior)


# An ops person. What limitations do ops people have? They can only work 8 hours in a day. They should not
# have more than hours of spread in their day.
class OpsMember:

    # this is the initializer for if someone is working a full 7.25 hours
    def __init__(self, start_work_slot):
        self.__init__(start_work_slot, DAILY_OPS_MEMBER_HOURS)

    def __init__(self, start_work_slot, work_hours):
        self.active_task = None
        self.task_prior = 0  # they can do any task at this point
        self.slots_worked = 0
        self.start_work_slot = start_work_slot
        self.shift_slots = M.floor(work_hours * 60 / SLOT_TIME) # 60 minutes in an hour. Slot time is in minutes
        # numb switches is the amount of times the ops member had to switch tasks throughout the day
        self.numb_switches = 0
        self.idle_slots = 0

    # Adds the parameter *time* to the amount of time this ops member has worked today
    # returns true if they can continue to work, and false if they
    # can't continue to work. ie: if their hours_worked > DAILY_OPS_MEMBER_HOURS
    def add_work_slot(self):
        self.slots_worked += 1
        return self.check_if_complete()

    # returns true if the ops member has worked more than they can today
    def check_if_complete(self):
        return self.slots_worked + self.idle_slots >= self.shift_slots

    # sets the ops member's new task to the task passed in, returns old task
    def switch_task(self, new_task):
        old_task = self.active_task
        self.set_active_task(new_task)
        self.numb_switches += 1
        return old_task

    # this is called when an ops member is done with a task. It puts them into 'give me a task to do' mode
    def set_available(self):
        self.active_task = None
        self.task_prior = 0  # they can do any task at this point

    # sets a new active task for the ops member, updating priority level the ops member is currently working for
    def set_active_task(self, task):
        self.active_task = task
        self.task_prior = task.prior

    # performs the task that the current ops member is assigned to. This is where we assume time is passing, 5 minutes
    # of the ops member working only on this job, returns whether or not the job is finished
    def perform_task(self, time_slot):
        # if this ops person has switched tasks 3 times, there is a 5 minute penalty of inefficiency
        if self.numb_switches == 3:
            self.numb_switches = 0
            self.add_work_slot()
            return False
        elif self.active_task is None:
            self.idle_slots += 1
            return False
        else:
            self.add_work_slot()
            return self.active_task.work_on_task(time_slot)

    # updates the priority of the active task on an ops member, updating it the amount of priority for being active for
    # one time slot (5 minutes)
    def update_active_task(self):
        if self.active_task is not None:
            self.active_task.update_priority()
            self.task_prior = self.active_task.prior


# helps us store information about what happened in a day
class DayStats:
    def __init__(self, finished_ops, working_ops, finished_tasks, tasks_left, ):
        self.finished_ops = finished_ops
        self.working_ops = working_ops
        self.finished_tasks = finished_tasks
        self.tasks_left = tasks_left


# the stats from day object is initialized using one of the day objects and a boolean which tells whether or not it is
# going to track an entire week
class stats_from_days:

    def __init__(self, day):
        self.__init__(day, False)

    # week is a boolean to see if this is a stat keeper for a week or for a single day
    def __init__(self, day, week):
        self.week = week
        if week:
            self.tasks_left_day_end = {'Monday': [], 'Tuesday': [], 'Wednesday': [], 'Thursday': [], 'Friday': []}
            self.finished_tasks_day_end = {'Monday': [], 'Tuesday': [], 'Wednesday': [], 'Thursday': [], 'Friday': []}
            self.ops_idle_time = {'Monday': [], 'Tuesday': [], 'Wednesday': [], 'Thursday': [], 'Friday': []}
            self.ops_number_tasks = {'Monday': [], 'Tuesday': [], 'Wednesday': [], 'Thursday': [], 'Friday': []}
            self.numb_days = 0
        else:
            self.tasks_left_day_end = []
            self.finished_tasks_day_end = []
            self.ops_idle_time = []
            self.ops_number_tasks = []
            self.numb_days = 0
        self.add_day(day, 'Monday')

    def add_day(self, day, week):
        if self.week:
            self.tasks_left_day_end[week].append(len(day.tasks_left))
            self.finished_tasks_day_end[week].append(len(day.finished_tasks))
            self.ops_idle_time[week].append([ops.idle_slots for ops in day.finished_ops])
            self.ops_number_tasks[week].append([nt for nt in day.finished_ops])
            self.numb_days = 0


