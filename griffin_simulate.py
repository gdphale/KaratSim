
# these will all be made


# ***************************** #
# Amount of time tasks take     #     - eventually expand these into intervals. This will be implemented once we get the day to be simulated with static task-times
# ***************************** #
CREATION_TIME = 20
SUP_TIME_NI = 5  # no issue
SUP_TIME_I = 20  # issue
SUP_KB_PROB = 0.063
NO_SHOW_PERC = 0.02
IV_ISSUE =


# time penalty in minutes for switching a task in the middle of it
# ------------------------------------------------------------------------------------
SWITCH_TIME = 1


# ***************************** #
# Priority Level of Tasks       #
# ***************************** #


# priority level that a support task starts out at - priority only grows
# ------------------------------------------------------------------------------------#
START_SUP_PRIOR = 95 # support
START_CREATION_PRIOR = 60 # creation
START_FINAL_PRIOR = 40 # final check
START_EMAIL_PRIOR = 30 # answering a Zendesk ticket


# Priority level growth rate of the different tasks. units/minute
# ------------------------------------------------------------------------------------#
SUP_PRIOR_GROWTH = 1 # this way it reaches 100 after 5 minutes, meaning the interview MUST be supported
CREATION_PRIOR_GROWTH = 0.4 # MUST be created after 1.5 hours
FINAL_PRIOR_GROWTH = 0.5 # higher growth rate than creation, only it starts further behind.
EMAIL_PRIOR_GROWTH = 0.2










# A somewhat Abstract class which encompasses all the tasks that support members must do. Things such as support, creation, etc. are all children of this class
class Task:

    # makes a new test of the type
    def __init__(self, tasktype):
        self.type = tasktype


    def setStart(self, time):
        self.start = time

    def setEnd(self, time):
        self.end = time

    def printChildValues(self):
        print(self.priority)




# Defines a support task that an Ops support member must fulfill
class Support(Task):

    type = 'Support'

    def __init__(self):
        Task.__init__(self, type)
        self.priority = START_SUP_PRIOR





# Defines a creation task for an Ops member to do - these will be stores as lists during the day
class Creation(Task):

    type = 'Creation'

    def __init__(self):
        super.__init__(self.super, type)
        self.priority = START_CREATION_PRIOR



# Defines a Final Check and publishing task of an interview - these will be stored as lists during the day
class Publishing(Task):
    type = 'Publishing'

    def __init__(self):
        super.__init__(self.super, type)
        self.priority = START_FINAL_PRIOR



# Defines the task of answering a zendesk email.
class Email(Task):
    type = 'Email'

    def __init__(self):
        super.__init__(self.super, type)
        self.priority = START_EMAIL_PRIOR





def main():
    t1 = Support()
    t1.printChildValues()


def RunDay(numbInterviews, numEmails, numbFailures):

    # get the task distribution of theday



main()

