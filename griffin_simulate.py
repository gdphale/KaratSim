from ksim_functions import *
import copy


# returns metrics from the day's simulation.
# Total idle time of ops people.
# Amount of ops people necessary.
# Amount of ops people ideally.
# Heat map of the day
def simday_ops_hours(schedule, starting_ops_times, ops_hours, yesterday):
    # queues for storing the day's tasks
    active_tasks = Q.PriorityQueue()
    if yesterday is not None:
        for i in yesterday:
            active_tasks.put(i)
    completed_tasks = []

    # lists of the ops members, and a list of when each ops person starts working
    starting_ops_times.sort()
    ops_members = []
    finished_ops_members = []

    # iterate through all 288 5 minute periods of a day
    for slot in range(TOTAL_TIME_SLOTS):
        # first we must take all the tasks that are starting now and add them to the active tasks
        add_tasks(schedule, active_tasks, slot)
        # second see if any ops people start working at this time
        add_ops_from_list(ops_members, starting_ops_times, ops_hours, slot)
        # now see which active tasks need to be completed, and which ops members need to switch tasks to account for different priorities
        allocate_ops_tasks(active_tasks, ops_members)
        # iterate through and have ops members perform their tasks, adding creation and publishing in the correct places, and removing completed tasks
        perform_ops_tasks(ops_members, schedule, completed_tasks, slot)
        # now check to see if any ops people need to be removed because they are over their time
        ops_members = check_finished_ops(ops_members, active_tasks, finished_ops_members)
        # now we must update the priority of all the tasks, as though 5 minutes have gone by. We also have to update
        # the priority of the current tasks that ops members are working on. Also, sort the list of ops members so
        # that we know what the minimum priority is for ops people on the next iteration
        active_tasks = update_priorities(active_tasks, ops_members)
        #if slot > 150 and active_tasks.empty():
        #    print('ye')
    day = DayStats(finished_ops_members, ops_members, completed_tasks, active_tasks.queue)
    return day


def determine_stability(numbInterviews, numbEmails, ops_start, ops_hours):
    max_task_queue = 15
    ITERS = 20
    yesterdays_tasks = None
    differences = []
    for i in range(ITERS):
        ops_hours_c = copy.copy(ops_hours)
        ops_start_c = copy.copy(ops_start)
        schedule = populate_day(numbInterviews, numbEmails)
        day = simday_ops_hours(schedule, ops_start_c, ops_hours_c, yesterdays_tasks)
        yesterdays_tasks = day.tasks_left
        if len(yesterdays_tasks) > max_task_queue:
            return 'Failure after ' + str(i) + ' days.'
        differences.append(len(yesterdays_tasks))
    return differences


# there are 24 hours in a day, that's 48 30 min sections, and 288 5 minute sections
def run_day(numbInterviews, numbEmails, ops_start, ops_hours):
    schedule = populate_day(numbInterviews, numbEmails)
    print(min_ops_hours(schedule))
    print(min_ops_members(schedule))
    day = simday_ops_hours(schedule, ops_start, ops_hours, None)
    return day


def find_break_point(ops_start, ops_hours, initial_guess):
    ivs = initial_guess
    unbroken = True
    while unbroken:
        emails = M.floor(ivs / 6)
        a = determine_stability(ivs, emails, ops_start, ops_hours)
        if type(a) is not list:
            return ivs - 1
        ivs += 2


def main():
    #print(timeslot_to_time(100))
    ops_start = [18, 80, 125, 200]
    ops_hours = [7, 7, 7, 5]
    interviews = 52
    initial_guess = 20
    emails = 7
    print(find_break_point(ops_start, ops_hours, initial_guess))



main()