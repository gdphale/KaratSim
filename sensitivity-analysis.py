import simulate
import pandas as pd
from numpy import ceil  # must use the numpy one, the math one can't handle Series objs

# Run a series of simulated interview days

# Track:
# - Total minutes required for interview support tasks
# - Total Ops idle time during scheduled shifts
# - Number of interview slots not scheduled to a perfect multiple of what 1 Ops person can support
#   (expressed in minutes of wasted time compared to the ideal case)


# FTE Conversion includes estimated allowance for breaks (45min total for an 8 hour shift) & PTO
FTE = 34*60

## Import interview schedule scenarios. 
#  This should be 1 week of interviews with column headers as days of the week.


def measure_one_week(filename, volume):

    week = pd.read_excel(filename) #may have to chance this to csv or xlsx
    metrics = {
        'Interview Volume': volume,
        'Scheduled minutes': 0,
        'EOD todo minutes': 0,
        'Ops idle minutes': 0,
        'Schedule Waste': 0
    }

    for day in ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']:

        # Create a 'schedule' data frame
        sched = pd.DataFrame(week[day])
        sched['Interviews'] = sched[day]
        # Add the minimal required Ops shifts to cover scheduled interviews
        sched['Final Ops'] = ceil(sched['Interviews'] / simulate.INTERVIEWS_PER_OPS)
        metrics['Scheduled minutes'] += sched['Final Ops'].sum() * simulate.BLOCK_LENGTH
        # Fill NaN values from blank cells with zeros
        sched = sched.fillna(value=0)

        # Calculate schedule inefficiencies
        metrics['Schedule Waste'] += simulate.calculate_schedule_waste(sched)

        # Monte Carlo the day.
        result = simulate.montecarlo_one_day(sched, 250)
        metrics['EOD todo minutes'] += result['EOD todo minutes'].mean()
        metrics['Ops idle minutes'] += result['Ops idle minutes'].mean()

    return metrics


results = []
results.append(measure_one_week('sample_day.xlsx', 656))
print("1 done")

results = pd.DataFrame(results)

results.to_csv("average_week_scaled_lower_pc_time.csv")
print("all done!")
