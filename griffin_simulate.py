from ksim_functions import *
import copy
import matplotlib.pyplot as plt


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
    day = Day(finished_ops_members, ops_members, completed_tasks, active_tasks.queue)
    return day


#
def determine_stability(interviews, emails, ops_start, ops_hours):
    max_task_queue = 100
    ITERS = 50
    yesterdays_tasks = None
    differences = []
    for i in range(ITERS):
        ops_hours_c = copy.copy(ops_hours)
        ops_start_c = copy.copy(ops_start)
        schedule = populate_day(interviews, emails)
        day = simday_ops_hours(schedule, ops_start_c, ops_hours_c, yesterdays_tasks)
        yesterdays_tasks = day.tasks_left
        if len(yesterdays_tasks) > max_task_queue:
            return(differences)
            #return 'Failure after ' + str(i) + ' days.'
        differences.append(len(yesterdays_tasks))
    return differences


# This function simulates a day of operations, returning a map of relevant information. Takes in the number of
# interviews and the number of emails that will occur within the day, as well as two arrays ops_start and ops_hours,
# which define the starting slots where ops members will begin working in a day and the amount of hours that each
# member will work. Indices of the arrays tell which ops member corresponds to which hour.
def run_day(interviews, emails, ops_start, ops_hours):
    info = {}
    schedule = populate_day(interviews, emails)
    info['Min Ops Hours'] = min_ops_hours(schedule)
    info['Min Ops Members'] = min_ops_members(schedule)
    info['Day'] = simday_ops_hours(schedule, ops_start, ops_hours, None)
    info['Stats'] = get_stats_from_day(day)
    return info


# Takes in two arrays ops_start and ops_hours, which define the starting slots where ops members will begin working
# in a day and the amount of hours that each member will work. Indices of the arrays tell which ops member
# corresponds to which hour. Also takes in an initial_guess which tells how many interviews iteration will begin at.
# This then simulates a day with the given initial guess of interviews, incrementing that guess until the ops team can
# no longer handle the given number of interviews. This function assumes that we receive 1/6 the amount of emails as
# interviews are occurring in a day. It then returns the amount of interviews that the team could not handle.
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
    ops_start = [18, 80, 200]
    ops_hours = [7, 7, 5]
    interviews = 40
    initial_guess = 15
    emails = 7
    a = determine_stability(interviews, emails, ops_start, ops_hours)
    print(len(a))
    plt.style.use('fivethirtyeight')
    plt.plot(a)
    plt.plot([3,17,18,3,15,4,2,6,7,4])
    plt.show()
    print(a)


main()