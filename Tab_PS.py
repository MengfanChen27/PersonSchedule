import math
import pulp
from PS_GUI3 import solver


def optimize_tableting(
    batches_required: int,
    num_workdays: int,
    use_p3030: bool = True,
    use_p3090i: bool = True,
    use_ima: bool = True,
    buffer_ratio: float = 0.0,
    w_staff: float = 100.0,
    w_morning: float = 0,    # New parameter: small penalty for morning shifts
    w_evening: float = 0.1,    # New parameter: slightly higher penalty for evening shifts
    w_night: float = 2.0,
    w_weekend: float = 3.0,
    w_daysUsed: float = 1.0,
    print_solution: bool = True
):
    """
    Optimization for Tableting (OSD) scheduling with up to three machines:
      - P3030   => 1 batch/shift
      - P3090i  => 2 batches/shift
      - IMA     => 1 batch/shift

    Each machine requires 3 people per shift. We have 3 shifts/day (M/E/N).

    The model's objective is a weighted sum to minimize:
      1) Total staff usage (primary),
      2) Night shifts,
      3) Weekend shifts,
      4) Days used.

    :param batches_required: total number of batches demanded
    :param num_workdays: planning horizon in days
    :param use_p3030: whether P3030 is available
    :param use_p3090i: whether P3090i is available
    :param use_ima: whether IMA is available
    :param buffer_ratio: fraction of buffer on staff (e.g., 0.0 -> 0.3)
    :param w_staff: weight on total staff usage
    :param w_night: penalty for each night shift
    :param w_weekend: penalty for each shift run on a weekend day
    :param w_daysUsed: penalty for each day that is used
    :param print_solution: whether to print out the results
    :return: dict with solution details or None if infeasible
    """

    # ------------------------------------------------------------------
    # 1. Quick feasibility check based on maximum daily capacity
    # ------------------------------------------------------------------
    # Each machine can produce a certain number of batches per shift:
    machine_output = 0
    if use_p3030:
        machine_output += 1  # P3030 => 1 batch/shift
    if use_p3090i:
        machine_output += 2  # P3090i => 2 batches/shift
    if use_ima:
        machine_output += 1  # IMA => 1 batch/shift

    # Maximum daily capacity = machine_output * 3 shifts
    max_daily_batches = machine_output * 3
    if max_daily_batches == 0:
        # No machines are used => can't produce anything
        if print_solution:
            print("No machines selected => cannot produce any batches. Infeasible.")
        return None

    # If even at full capacity we can't meet the demand, it's infeasible
    if max_daily_batches * num_workdays < batches_required:
        if print_solution:
            needed_days = math.ceil(batches_required / max_daily_batches)
            more_days_needed = needed_days - num_workdays
            print("No optimal solution found (Infeasible):")
            print(f"  Demand of {batches_required} batches cannot be met in {num_workdays} days.")
            print(f"  With the selected machines, max capacity is {max_daily_batches} batches/day.")
            print(f"  => Need at least {needed_days} days total.")
            print(f"  => {more_days_needed} more day(s).")
        return None

    # ------------------------------------------------------------------
    # 2. CREATE THE LP PROBLEM
    # ------------------------------------------------------------------
    model = pulp.LpProblem("TabletingSchedule", pulp.LpMinimize)

    # ------------------------------------------------------------------
    # 3. DECISION VARIABLES
    # ------------------------------------------------------------------
    # We'll define binary variables for each machine and each shift/day, e.g.:
    #   M_p3030[d], E_p3030[d], N_p3030[d]  => 1 if P3030 is run in that shift/day, else 0
    #
    # We only include them if the machine is "used"; otherwise, we fix them to 0.

    # For convenience, define a small function to create or fix to zero:
    def make_var(name, use_machine):
        return pulp.LpVariable(name, cat=pulp.LpBinary) if use_machine else 0

    # Create shift variables for each machine/day
    M_p3030 = {d: make_var(f"M_p3030_{d}", use_p3030) for d in range(num_workdays)}
    E_p3030 = {d: make_var(f"E_p3030_{d}", use_p3030) for d in range(num_workdays)}
    N_p3030 = {d: make_var(f"N_p3030_{d}", use_p3030) for d in range(num_workdays)}

    M_p3090i = {d: make_var(f"M_p3090i_{d}", use_p3090i) for d in range(num_workdays)}
    E_p3090i = {d: make_var(f"E_p3090i_{d}", use_p3090i) for d in range(num_workdays)}
    N_p3090i = {d: make_var(f"N_p3090i_{d}", use_p3090i) for d in range(num_workdays)}

    M_ima = {d: make_var(f"M_ima_{d}", use_ima) for d in range(num_workdays)}
    E_ima = {d: make_var(f"E_ima_{d}", use_ima) for d in range(num_workdays)}
    N_ima = {d: make_var(f"N_ima_{d}", use_ima) for d in range(num_workdays)}

    # Staff variable (integer)
    staff_var = pulp.LpVariable("Staff", lowBound=0, cat=pulp.LpInteger)

    # dayUsed variable (1 if any shift scheduled on day d, 0 otherwise)
    dayUsed = {
        d: pulp.LpVariable(f"dayUsed_{d}", cat=pulp.LpBinary)
        for d in range(num_workdays)
    }

    # ------------------------------------------------------------------
    # 4. WEEKEND DAYS IDENTIFICATION
    # ------------------------------------------------------------------
    # Assuming day 0 = Monday => day 5 = Saturday, day 6 = Sunday, etc.
    weekend_days = set(d for d in range(num_workdays) if d % 7 in [5, 6])

    # ------------------------------------------------------------------
    # 5. OBJECTIVE FUNCTION
    # ------------------------------------------------------------------
    # Weighted sum of:
    #   1) staff_var * w_staff
    #   2) night shifts * w_night
    #   3) weekend shifts * w_weekend
    #   4) total days used * w_daysUsed

    total_morning_shifts = pulp.lpSum([
    M_p3030[d] + M_p3090i[d] + M_ima[d] for d in range(num_workdays)
    ])

    total_evening_shifts = pulp.lpSum([
        E_p3030[d] + E_p3090i[d] + E_ima[d] for d in range(num_workdays)
    ])

    total_night_shifts = pulp.lpSum([
        N_p3030[d] + N_p3090i[d] + N_ima[d] for d in range(num_workdays)
    ])


    # 5b) Sum of weekend shifts
    total_weekend_shifts = pulp.lpSum([
        (M_p3030[d] + E_p3030[d] + N_p3030[d] +
         M_p3090i[d] + E_p3090i[d] + N_p3090i[d] +
         M_ima[d] + E_ima[d] + N_ima[d])
        for d in weekend_days
    ])

    # 5c) Sum of days used
    total_days_used = pulp.lpSum(dayUsed[d] for d in range(num_workdays))

    # Define objective
    model += (
    w_staff * staff_var
    + w_morning * total_morning_shifts
    + w_evening * total_evening_shifts
    + w_night * total_night_shifts
    + w_weekend * total_weekend_shifts
    + w_daysUsed * total_days_used
    ), "WeightedObjective"

    # ------------------------------------------------------------------
    # 6. CONSTRAINTS
    # ------------------------------------------------------------------

    # (a) Demand constraint: total batches >= batches_required
    # Batches per shift per machine:
    #   P3030 => 1, P3090i => 2, IMA => 1
    total_batches = []
    for d in range(num_workdays):
        # morning
        total_batches.append(M_p3030[d] * 1 + M_p3090i[d] * 2 + M_ima[d] * 1)
        # evening
        total_batches.append(E_p3030[d] * 1 + E_p3090i[d] * 2 + E_ima[d] * 1)
        # night
        total_batches.append(N_p3030[d] * 1 + N_p3090i[d] * 2 + N_ima[d] * 1)

    model += (pulp.lpSum(total_batches) >= batches_required), "DemandConstraint"

    # (b) Staff constraints
    #  We follow the same logic from Dispensing, assuming staff cannot be reused
    #  in the same day across multiple shifts or machines. 
    #  => staff_var >= 3 * (# of shifts used by any machine in day d).
    for d in range(num_workdays):
        # Sum of all shift usages (for all machines) in day d
        sum_shifts_day_d = (
            M_p3030[d] + E_p3030[d] + N_p3030[d]
            + M_p3090i[d] + E_p3090i[d] + N_p3090i[d]
            + M_ima[d] + E_ima[d] + N_ima[d]
        )
        # Each shift usage requires 3 people => total staff for that day
        model += staff_var >= 3 * sum_shifts_day_d, f"StaffDay_{d}"

    # (c) Linking dayUsed[d] with shift usage:
    #     dayUsed[d] = 1 if any shift is used on day d
    for d in range(num_workdays):
        all_shifts_d = (
            M_p3030[d] + E_p3030[d] + N_p3030[d]
            + M_p3090i[d] + E_p3090i[d] + N_p3090i[d]
            + M_ima[d] + E_ima[d] + N_ima[d]
        )
        # If any shift is used, dayUsed[d] must be >= 1. Because they're binary,
        # dayUsed[d] >= (all_shifts_d / something). But simpler:
        model += dayUsed[d] >= all_shifts_d / 9.0, f"DayUsed_{d}"
        # (there are at most 9 shift variables per day if all 3 machines are used)

    # ------------------------------------------------------------------
    # 7. SOLVE THE MODEL
    # ------------------------------------------------------------------
    result_status = model.solve(solver)
    solver_status = pulp.LpStatus[model.status]

    if solver_status != 'Optimal':
        # Could be infeasible or unbounded for other reasons
        if print_solution:
            print(f"No optimal solution found! Solver status: {solver_status}")
            needed_days = math.ceil(batches_required / max_daily_batches)
            more_days_needed = max(0, needed_days - num_workdays)
            if more_days_needed > 0:
                print(f"  => You need at least {needed_days} days total.")
                print(f"  => {more_days_needed} more day(s).")
        return None

    # ------------------------------------------------------------------
    # 8. EXTRACT RESULTS
    # ------------------------------------------------------------------
    # Summaries
    morning_p3030  = sum(int(M_p3030[d].varValue) for d in range(num_workdays)) if use_p3030 else 0
    evening_p3030  = sum(int(E_p3030[d].varValue) for d in range(num_workdays)) if use_p3030 else 0
    night_p3030    = sum(int(N_p3030[d].varValue) for d in range(num_workdays)) if use_p3030 else 0

    morning_p3090i = sum(int(M_p3090i[d].varValue) for d in range(num_workdays)) if use_p3090i else 0
    evening_p3090i = sum(int(E_p3090i[d].varValue) for d in range(num_workdays)) if use_p3090i else 0
    night_p3090i   = sum(int(N_p3090i[d].varValue) for d in range(num_workdays)) if use_p3090i else 0

    morning_ima    = sum(int(M_ima[d].varValue) for d in range(num_workdays)) if use_ima else 0
    evening_ima    = sum(int(E_ima[d].varValue) for d in range(num_workdays)) if use_ima else 0
    night_ima      = sum(int(N_ima[d].varValue) for d in range(num_workdays)) if use_ima else 0

    min_staff = int(staff_var.varValue)
    staff_with_buffer = math.ceil(min_staff * (1 + buffer_ratio))

    total_produced = pulp.value(pulp.lpSum(total_batches))
    pct_completed = (total_produced / batches_required) * 100 if batches_required > 0 else 0

    used_days_count = sum(int(dayUsed[d].varValue) for d in range(num_workdays))

    # ------------------------------------------------------------------
    # 9. PRINT OR RETURN THE RESULTS
    # ------------------------------------------------------------------
    if print_solution:
        print("Optimal Schedule for Tableting:")
        print("================================")
        print(f"Selected Machines: " 
              f"P3030={use_p3030}, P3090i={use_p3090i}, IMA={use_ima}")
        print(f"Number of Workdays in Horizon: {num_workdays}")
        print(f"Demanded Batches: {batches_required}")
        print()
        print("Shifts Summary (total count of shifts across days):")
        if use_p3030:
            print(f"  P3030:   Morning={morning_p3030}, Evening={evening_p3030}, Night={night_p3030}")
        if use_p3090i:
            print(f"  P3090i:  Morning={morning_p3090i}, Evening={evening_p3090i}, Night={night_p3090i}")
        if use_ima:
            print(f"  IMA:     Morning={morning_ima}, Evening={evening_ima}, Night={night_ima}")
        print()
        print(f"Total Batches Produced: {int(total_produced)}")
        print(f"% of Demand Completed:  {pct_completed:.1f}%")
        print()
        print(f"Minimal Headcount (no buffer): {min_staff}")
        print(f"Headcount with {int(buffer_ratio*100)}% buffer: {staff_with_buffer}")
        print()
        print(f"Number of days used: {used_days_count}")
        print(f"Solver status: {solver_status}")
        print("=" * 50)

    return {
        "machines_used": {
            "P3030": use_p3030,
            "P3090i": use_p3090i,
            "IMA": use_ima
        },
        "morning_shifts": {
            "P3030": morning_p3030,
            "P3090i": morning_p3090i,
            "IMA": morning_ima
        },
        "evening_shifts": {
            "P3030": evening_p3030,
            "P3090i": evening_p3090i,
            "IMA": evening_ima
        },
        "night_shifts": {
            "P3030": night_p3030,
            "P3090i": night_p3090i,
            "IMA": night_ima
        },
        "total_batches_produced": int(total_produced),
        "pct_demand_completed": pct_completed,
        "min_staff_required": min_staff,
        "staff_with_buffer": staff_with_buffer,
        "days_used": used_days_count,
        "num_workdays_horizon": num_workdays,
        "solver_status": solver_status
    }


if __name__ == "__main__":
    result = optimize_tableting(
        batches_required=7*7,
        num_workdays=7,
        use_p3030=True,
        use_p3090i=True,
        use_ima=False,  # Suppose we do use IMA
        buffer_ratio=0.20,
        w_staff=100.0,      # strong emphasis on minimizing staff
        w_morning=0.0,   # penalty for morning shift usage
        w_evening=0.1,
        w_night=2.0,        # moderate penalty on night shifts
        w_weekend=3.0,      # higher penalty for weekend shifts
        w_daysUsed=1.0,     # some penalty on each day used
        print_solution=True
    )
