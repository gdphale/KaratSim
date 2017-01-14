import pandas as pd
from numpy.random import binomial
from math import floor
from statistics import median
from numpy import NaN

# Model variables
# Note that some of these are currently duplicated in the spreadsheet
# schedule template.

PC_TIME = 15 # minutes for profile creation
FC_TIME = 5 # minutes for final check & submission to client ATS

# Per Sarah, 1 support person can handle 3 interviews going wrong all at once
# but cannot handle more than 3 at a time even if everything goes perfectly.
INTERVIEWS_PER_OPS = 3
INTERVIEW_SUPPORT_TIME = {'ideal': 5, 'problems': 20}

# Interview problems
INTERVIEW_NOSHOWS = 0.02
INTERVIEW_TECHPROBS = 0.092

# NB: Ops interview support limit is also affected by what happens if Karatbot goes down - 
# having to reschedule interviews due to not having anyone free to manually record
# is not an acceptable adverse outcome.

# QC assumptions
# Currently static time requirement per interview, should restructure this
# later to mimic true variability
QC_TIME = 15

# Schedule is split into numbered half-hour blocks, referred to by number (0-indexed) 
# for convenience w/ pandas indexing. Currently the schedule runs from 3am to 12am.
# Index of the last ("overnight") block is:
LAST_BLOCK_NUM = 42
BLOCK_LENGTH = 30



# Maintain a record for each interview:
# Time start, current stage, time finished.

class Interview:
    
    def __init__(self, startblock):
        self.startblock = startblock
        self.status = 'Scheduled'
        
    # Status labels:
    # Scheduled, Happening, Ready for PC,
    # Ready for QC, QC, Ready for FC, Completed
    # No-show
    
    def begin(self):
        self.status='Happening'
        
    def queueForPC(self):
        self.status='Ready for PC'
        
    def queueForQC(self):
        self.status='Ready for QC'
        
    def QC(self, startblock):
        self.status='QC'
        self.QCstart = startblock
    
    def queueForFC(self):
        self.status='Ready for FC'
        
    def complete(self, endblock):
        self.status='Completed'
        self.endblock = endblock
        
    def noshow(self):
        self.status='No-show'


def time_per_interview(n):
    '''
    Return the expected amount of live support time required per interview, when n are scheduled at once.
    '''
    probability_all_good = (1-INTERVIEW_TECHPROBS)**n
    return ( probability_all_good*INTERVIEW_SUPPORT_TIME['ideal'] + (1-probability_all_good)*INTERVIEW_SUPPORT_TIME['problems']) / n


def _schedule_waste(n):
    '''
    Return the number of minutes of wasted time when N interviews are scheduled in a slot.
    '''
    if n % INTERVIEWS_PER_OPS == 0:
        return 0
    else:
        return ( (n % INTERVIEWS_PER_OPS) * (time_per_interview(n % INTERVIEWS_PER_OPS) - time_per_interview(INTERVIEWS_PER_OPS)))


def calculate_schedule_waste(sched):
    '''
    Determine how much time is "wasted" due to having an interview slot that is not booked
    at an even multiple of INTERVIEWS_PER_OPS
    '''
    sched['Schedule Waste'] = sched['Interviews'].apply(_schedule_waste)
    return sched['Schedule Waste'].sum()


def simulate_one_day(sched):
    '''
    Simulate a day's worth of interviews. 

    sched should be a dataframe with at least the following columns:
        Interviews - number of interviews scheduled at the start of each half-hour block
        Final Ops - number of Ops people scheduled for each half-hour block

    Function returns a dictionary of stuff. Hopefully all key names will be self-explanatory 
    in the event that this documentation goes stale.
        'EOD todo' - number of minutes of work remaining for a "mop-up" shift at the end of the day
        'Ops idle minutes' - number of minutes during the day that Ops people have no interview related tasks
    '''

    interviews = []

    # Create the interview list.
    for block, row in sched.iterrows():
        for _ in range(int(row['Interviews'])):
            i = Interview(block)
            i.status = 'Scheduled'
            interviews.append(i)  

    # Set up extra variables to record information about work queues throughout the day
    sched['QC queue'] = 0 # Number of interviews ready to send out for code-only review
    sched['Ops idle minutes'] = 0 # Ops flex minutes happening when no profiles/final check are ready to be worked

    ## Loop through the day
    for current_block, row in sched.iterrows():
        # Interviews that started 3 blocks ago (2 for interview, 1 for write-up)
        # should be ready for profile creation now. Update them.
        writeups = [i for i in interviews if i.startblock==current_block-3 and i.status=='Happening']
        for i in writeups:
            i.queueForPC()
        
        # Interviews that started QC 2 blocks ago should be ready for final check now.
        # Update them.
        qcs = [i for i in interviews if i.status=='QC']
        qcs = [i for i in qcs if i.QCstart==current_block-2]
        for i in qcs:
            i.queueForFC()
            
        # What does the to-do list look like at the beginning of this block?
        pcs = [i for i in interviews if i.status=='Ready for PC']
        fcs = [i for i in interviews if i.status=='Ready for FC']
        qcs = [i for i in interviews if i.status=='Ready for QC']
        
        sched.set_value(current_block, 'QC queue', len(qcs))
 
        # Roll for how many interviews go wrong.
        ints = row['Interviews']
        happening = [i for i in interviews if i.startblock==current_block]
        
        for i in happening:
            i.begin()

        # If there are multiple Ops on duty, roll separately for each of them.

        # Num interviews per op:
        # Caseloads is a list of amount of interviews each ops member is supporting
        ops_caseloads = []
        num_full = floor(row['Interviews'] / INTERVIEWS_PER_OPS) # Number of Ops working at full capacity
        if num_full > 0:
            ops_caseloads = [INTERVIEWS_PER_OPS] * num_full
        if row['Interviews'] % INTERVIEWS_PER_OPS > 0:
            ops_caseloads.append(row['Interviews'] % INTERVIEWS_PER_OPS)

        total_noshows = 0

        if row['Interviews'] == 0:
            ops_time = BLOCK_LENGTH * row['Final Ops'] # this will always be zero, no?
        else:
            op_leftover_times = []
            for op in ops_caseloads:
                techprobs = binomial(op, INTERVIEW_TECHPROBS)
                noshows = binomial(op, INTERVIEW_NOSHOWS)
                total_noshows += noshows
                if techprobs > 0 or noshows > 0:
                    time_left = BLOCK_LENGTH - INTERVIEW_SUPPORT_TIME['problems'] # if no_shows if > 1, time_left = 10
                else:
                    time_left = BLOCK_LENGTH - INTERVIEW_SUPPORT_TIME['ideal'] # else, time_left = 25
                op_leftover_times.append(time_left)
            ops_time = sum(op_leftover_times) # sum of the time_left which is time that ops has to do stuff not support

        ints = ints - total_noshows

        if total_noshows > 0:
            # find interview(s) in the list with the right startblock,
            # change their statuses to 'No-show'
            while total_noshows > 0 and len(happening) > 0:
                happening[0].noshow()
                happening.pop(0)
                total_noshows -= 1
       
        # Apply leftover Ops time for the block to outstanding profile tasks.
        # This is slightly more efficient than reality, as it assumes multiple Ops might work on the same profile creation.
        # Pick profile creation first if possible, else final check.
        while ops_time >= min(PC_TIME, FC_TIME) and max(len(pcs), len(fcs)) > 0:
            if ops_time >= PC_TIME and len(pcs) > 0:
                # do a profile creation task
                # pick the profile, update it, drop it from pcs list
                ops_time -= PC_TIME
                pcs[0].queueForQC()
                pcs.pop(0)
                continue
            elif ops_time >= FC_TIME and len(fcs) > 0:
                ops_time = ops_time - FC_TIME
                fcs[0].complete(current_block)
                fcs.pop(0)
            else:
                break
        
        # Remaining Ops time is idle, record it
        sched.set_value(current_block, 'Ops idle minutes', ops_time)

        # If 4 interviews are ready for QC, create a QC shift.
        # Move the interviews to QC.
        # NB: Adjust this magic 4 if the assumed QC time changes!!!
        if len(qcs) >= 4:
            qcs_to_do = 4 * floor(len(qcs)/4)
            sched.set_value(current_block, 'QC called', floor(len(qcs)/4))
            
            while qcs_to_do > 0:
                qcs[0].QC(current_block)
                qcs.pop(0)
                qcs_to_do -= 1
    
    
    # End-of-day housekeeping - create dictionary of metrics

    results = {}

    # How many interviews are left to deal with at the end of the day, and how much Ops time will that take?
    todos = [i for i in interviews if i.status != 'Completed' and i.status != 'No-show'] # how many interviews are not yet published by the end of the day
    num_pc = len([i for i in todos if i.status in ['Ready for PC', 'Happening']]) # number of profiles still needed to be created
    num_fc = len([i for i in todos if i.status in ['Ready for QC', 'QC', 'Ready for FC']]) # number of profiles that need to be final-checked (after having been QC'ed)
    num_fc += num_pc # add them up since the ones to be created will also need to be published

    todo_minutes = num_fc*FC_TIME + num_pc*PC_TIME

    results['EOD todo minutes'] = todo_minutes

    # How much idle time did the interviewers have throughout the day? --- interviewers???
    results['Ops idle minutes'] = sched['Ops idle minutes'].sum()
   
    return results 



def montecarlo_one_day(sched, n):
    ''' Run N simulations of a day's schedule
    '''

    results = []    # this will be a list of dictionaries, converted at the end to a data frame.

    for _ in range(n):
        results.append(simulate_one_day(sched))

    return pd.DataFrame(results)

