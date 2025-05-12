import math
import pulp
from PS_GUI3 import SOLVER_INSTANCE  # Import the global solver instance

def optimize_dispensing(
    batches_required: int,
    num_workdays: int,
    buffer_ratio: float = 0.0,
    # We now have six weights the user can tune:
    w_staff: float = 100.0,
    w_night: float = 2.0,
    w_weekend: float = 3.0,
    w_daysUsed: float = 1.0,
    w_morning: float = 0.0,   # penalty for morning shift usage
    w_evening: float = 0.1,   # penalty for evening shift usage
    print_solution: bool = True,
    solver=None  # Add solver parameter with default None
):
    """
      - 3 shifts/day (morning M, evening E, night N)
      - Each shift can produce up to 3 batches (2.6 hours per batch + set up time in an 8hr shift)
      - 1 dispensing room => at most 3 batches per shift
      - 6 people needed per shift (4 excipients + 2 API)
      - Weighted objective to minimize:
         1) total staff (primary),
         2) night shifts,
         3) weekend shifts,
         4) total days used,
         5) morning shifts (small penalty),
         6) evening shifts (slightly higher penalty than morning).

    :param batches_required: total number of batches demanded
    :param num_workdays: how many days in this horizon
    :param buffer_ratio: fraction of buffer on staff (0.0 -> 0.3)
    :param w_staff: weight on total staff usage
    :param w_night: penalty for each night shift
    :param w_weekend: penalty for each shift run on a weekend day
    :param w_daysUsed: penalty for each day that is used
    :param w_morning: penalty for morning shift usage
    :param w_evening: penalty for evening shift usage
    :param print_solution: whether to print out the results
    :param solver: Optional solver instance to use. If None, uses the global solver instance.
    :return: dict with solution details or None if infeasible
    """

    # Use provided solver or fall back to global instance
    solver_to_use = solver if solver is not None else SOLVER_INSTANCE

    # ------------------------------------------------
    # Quick feasibility check: 9 batches max per day
    # ------------------------------------------------
    max_daily_batches = 9  # 3 shifts x 3 batches each
    if max_daily_batches * num_workdays < batches_required:
        # Infeasible from the start. We can't produce enough batches.
        if print_solution:
            needed_days = math.ceil(batches_required / max_daily_batches)
            more_days_needed = needed_days - num_workdays
            print("No optimal solution found (Infeasible):")
            print(f"  Demand of {batches_required} batches cannot be met in {num_workdays} days.")
            print(f"  At max capacity (9 batches/day), you need at least {needed_days} days.")
            print(f"  => You need {more_days_needed} more day(s).")
        return None

    # ------------------------------------------------
    # 1. CREATE THE LP PROBLEM
    # ------------------------------------------------
    model = pulp.LpProblem("DispensingSchedule", pulp.LpMinimize)

    # ------------------------------------------------
    # 2. DECISION VARIABLES
    # ------------------------------------------------
    M_vars = {d: pulp.LpVariable(f"M_{d}", cat=pulp.LpBinary) for d in range(num_workdays)}
    E_vars = {d: pulp.LpVariable(f"E_{d}", cat=pulp.LpBinary) for d in range(num_workdays)}
    N_vars = {d: pulp.LpVariable(f"N_{d}", cat=pulp.LpBinary) for d in range(num_workdays)}

    # Staff variable
    staff_var = pulp.LpVariable("Staff", lowBound=0, cat=pulp.LpInteger)

    # dayUsed variable (1 if any shift scheduled on day d, 0 otherwise)
    dayUsed = {
        d: pulp.LpVariable(f"dayUsed_{d}", cat=pulp.LpBinary)
        for d in range(num_workdays)
    }

    # ------------------------------------------------
    # 3. WEEKEND DAYS
    # ------------------------------------------------
    weekend_days = set(d for d in range(num_workdays) if d % 7 in [5, 6])
    # If day 0 = Monday, then day 5 = Saturday, day 6 = Sunday, day 12 = next Saturday, etc.

    # ------------------------------------------------
    # 4. OBJECTIVE FUNCTION
    # ------------------------------------------------
    obj_night = w_night * pulp.lpSum(N_vars[d] for d in range(num_workdays))
    obj_weekend = w_weekend * pulp.lpSum(
        (M_vars[d] + E_vars[d] + N_vars[d]) for d in weekend_days
    )
    obj_daysUsed = w_daysUsed * pulp.lpSum(dayUsed[d] for d in range(num_workdays))
    obj_morning = w_morning * pulp.lpSum(M_vars[d] for d in range(num_workdays))
    obj_evening = w_evening * pulp.lpSum(E_vars[d] for d in range(num_workdays))

    model += (
        w_staff * staff_var + 
        obj_night + 
        obj_weekend + 
        obj_daysUsed + 
        obj_morning + 
        obj_evening
    ), "WeightedObjective"

    # ------------------------------------------------
    # 5. CONSTRAINTS
    # ------------------------------------------------

    # (a) Demand constraint
    total_batches = pulp.lpSum(M_vars[d] + E_vars[d] + N_vars[d] for d in range(num_workdays)) * 3
    model += (total_batches >= batches_required), "DemandConstraint"

    # (b) Staff constraints
    for d in range(num_workdays):
        model += staff_var >= 6 * (M_vars[d] + E_vars[d] + N_vars[d]), f"StaffReq_{d}"

    # (c) Link dayUsed[d] with shift usage
    # If M_d + E_d + N_d >= 1, we want dayUsed[d] = 1
    # We can enforce dayUsed[d] >= (M_d + E_d + N_d) / 3. 
    # But since M/E/N are binary, any sum>0 => dayUsed=1. 
    # A simpler approach is:
    #   dayUsed[d] >= M_d, dayUsed[d] >= E_d, dayUsed[d] >= N_d
    for d in range(num_workdays):
        model += dayUsed[d] >= M_vars[d]
        model += dayUsed[d] >= E_vars[d]
        model += dayUsed[d] >= N_vars[d]
    # This ensures that if any shift is used on day d, dayUsed[d] = 1.

    # ------------------------------------------------
    # 6. SOLVE THE MODEL
    # ------------------------------------------------
    solver_status = model.solve(solver_to_use)

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

    # ------------------------------------------------
    # 7. EXTRACT RESULTS
    # ------------------------------------------------
    morning_days = sum(int(M_vars[d].varValue) for d in range(num_workdays))
    evening_days = sum(int(E_vars[d].varValue) for d in range(num_workdays))
    night_days   = sum(int(N_vars[d].varValue) for d in range(num_workdays))

    min_staff = int(staff_var.varValue)
    staff_with_buffer = math.ceil(min_staff * (1 + buffer_ratio))

    total_produced = 3 * (morning_days + evening_days + night_days)
    pct_completed = (total_produced / batches_required) * 100 if batches_required > 0 else 0

    used_days_count = sum(int(dayUsed[d].varValue) for d in range(num_workdays))

    # ------------------------------------------------
    # 8. PRINT OR RETURN THE RESULTS
    # ------------------------------------------------
    if print_solution:
        print("Optimal Schedule for Dispensing (Single Process):")
        print("================================================")
        print(f"Number of Workdays in Horizon: {num_workdays}")
        print(f"Demanded Batches: {batches_required}")
        print()
        print("Shifts Summary:")
        print(f"  Morning shifts: {morning_days}")
        print(f"  Evening shifts: {evening_days}")
        print(f"  Night   shifts: {night_days}")
        print()
        print(f"Total Batches Produced: {total_produced}")
        print(f"% of Demand Completed:  {pct_completed:.1f}%")
        print()
        print(f"Minimal Headcount (no buffer): {min_staff}")
        print(f"Headcount with {int(buffer_ratio*100)}% buffer: {staff_with_buffer}")
        print()
        print(f"Number of days used: {used_days_count}")
        print("=" * 50)

    return {
        "morning_shifts": morning_days,
        "evening_shifts": evening_days,
        "night_shifts": night_days,
        "total_batches_produced": total_produced,
        "pct_demand_completed": pct_completed,
        "min_staff_required": min_staff,
        "staff_with_buffer": staff_with_buffer,
        "days_used": used_days_count,
        "num_workdays_horizon": num_workdays,
        "solver_status": solver_status
    }

if __name__ == "__main__":
    # Example usage with default weights
    result = optimize_dispensing(
        batches_required=8*6,
        num_workdays=6,
        buffer_ratio=0.20,
        w_staff=100.0,      # strong emphasis on minimizing staff
        w_night=0.0,        # moderate penalty on night shifts
        w_weekend=3.0,      # higher penalty for weekend shifts
        w_daysUsed=1.0,     # some penalty on each day used
        w_morning=0.0,      # no penalty for morning shifts
        w_evening=0.0,      # small penalty for evening shifts
        print_solution=True
    )
