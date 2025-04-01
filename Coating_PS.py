import math
import pulp


def safe_value(x):
    """Returns .varValue if x is a PuLP variable, otherwise returns x directly."""
    return x.varValue if hasattr(x, 'varValue') else x

def optimize_coating(
    batches_required: int,
    num_workdays: int,
    use_bosch: bool = True,
    use_glatt: bool = True,
    buffer_ratio: float = 0.0,
    w_staff: float = 100.0,
    w_morning: float = 0.0,   # penalty for morning shift usage
    w_evening: float = 0.1,   # penalty for evening shift usage
    w_night: float = 2.0,
    w_weekend: float = 3.0,
    w_daysUsed: float = 1.0,
    print_solution: bool = True
):
    """
    Optimization for Coating (OSD) scheduling with up to two machines:
      - BOSCH => 2 people per shift, up to 2 batches/shift
      - GLATT => 2 people per shift, up to 2 batches/shift

    In addition, there is a "Solution" process:
      - Requires 2 people per shift, up to 4 solution-batches/shift (since each batch takes 2 hours in an 8-hour shift).

    We need:
      1) At least 'batches_required' solution-batches in total.
      2) At least 'batches_required' coating-batches in total.

    Each day has 3 shifts (Morning M, Evening E, Night N). 
    If a shift uses the Solution process + BOSCH + GLATT at the same time, 
    that shift needs 2 + 2 + 2 = 6 people.

    The model's objective is a weighted sum to minimize:
      1) Total staff usage (primary),
      2) Night shifts,
      3) Weekend shifts,
      4) Days used.

    :param batches_required: total number of final batches demanded 
                            (i.e., we need that many solutions and that many coatings)
    :param num_workdays: planning horizon in days
    :param use_bosch: whether BOSCH is available
    :param use_glatt: whether GLATT is available
    :param buffer_ratio: fraction of buffer on staff (e.g., 0.0 -> 0.3)
    :param w_staff: weight on total staff usage
    :param w_night: penalty for each night shift
    :param w_weekend: penalty for each shift run on a weekend day
    :param w_daysUsed: penalty for each day that is used
    :param print_solution: whether to print out the results
    :return: dict with solution details or None if infeasible
    """

    # ------------------------------------------------------------------
    # 1. Quick feasibility checks based on maximum daily capacity
    # ------------------------------------------------------------------
    # 1a) Solution process can make up to 4 solution-batches per shift.
    #     With 3 shifts/day => max 12 solution-batches/day if we run solution every shift.
    max_daily_solution = 12  # (3 shifts * 4 solution-batches per shift)

    # 1b) Coating process:
    #     - BOSCH => up to 2 batches/shift
    #     - GLATT => up to 2 batches/shift
    #     If both are used, each shift can produce 2 (BOSCH) + 2 (GLATT) = 4 coating-batches
    #     => up to 12 coating-batches/day if both machines run every shift
    #     If only one machine is used => up to 6 coating-batches/day (2 per shift * 3 shifts).
    coating_machines_used = 0
    if use_bosch:
        coating_machines_used += 1
    if use_glatt:
        coating_machines_used += 1

    if coating_machines_used == 0:
        if print_solution:
            print("No coating machines selected => cannot produce any coated batches. Infeasible.")
        return None

    max_daily_coating = 2 * coating_machines_used * 3  # 2*batches/shift * (#machines) * 3 shifts

    # 1c) If we cannot meet the needed solution-batches or coating-batches within the horizon, it's infeasible.
    if max_daily_solution * num_workdays < batches_required:
        if print_solution:
            needed_days_solution = math.ceil(batches_required / max_daily_solution)
            print("No optimal solution found (Infeasible for Solution):")
            print(f"  Demand of {batches_required} solution-batches cannot be met in {num_workdays} days.")
            print(f"  Max daily solution capacity: {max_daily_solution}.")
            print(f"  => Need at least {needed_days_solution} days.")
        return None

    if max_daily_coating * num_workdays < batches_required:
        if print_solution:
            needed_days_coating = math.ceil(batches_required / max_daily_coating)
            print("No optimal solution found (Infeasible for Coating):")
            print(f"  Demand of {batches_required} coating-batches cannot be met in {num_workdays} days.")
            print(f"  With the selected machine(s), max daily coating capacity: {max_daily_coating}.")
            print(f"  => Need at least {needed_days_coating} days.")
        return None

    # ------------------------------------------------------------------
    # 2. CREATE THE LP PROBLEM
    # ------------------------------------------------------------------
    model = pulp.LpProblem("CoatingSchedule", pulp.LpMinimize)

    # ------------------------------------------------------------------
    # 3. DECISION VARIABLES
    # ------------------------------------------------------------------
    # We define binary variables for each shift/day, e.g.:
    #   M_solution[d], E_solution[d], N_solution[d]
    #   M_bosch[d],    E_bosch[d],    N_bosch[d]
    #   M_glatt[d],    E_glatt[d],    N_glatt[d]
    #
    # 1 if that process/machine is run in that shift/day, else 0.

    def make_var(name, use_flag=True):
        return pulp.LpVariable(name, cat=pulp.LpBinary) if use_flag else 0

    # -- Solution
    M_solution = {d: make_var(f"M_solution_{d}", True) for d in range(num_workdays)}
    E_solution = {d: make_var(f"E_solution_{d}", True) for d in range(num_workdays)}
    N_solution = {d: make_var(f"N_solution_{d}", True) for d in range(num_workdays)}

    # -- BOSCH
    M_bosch = {d: make_var(f"M_bosch_{d}", use_bosch) for d in range(num_workdays)}
    E_bosch = {d: make_var(f"E_bosch_{d}", use_bosch) for d in range(num_workdays)}
    N_bosch = {d: make_var(f"N_bosch_{d}", use_bosch) for d in range(num_workdays)}

    # -- GLATT
    M_glatt = {d: make_var(f"M_glatt_{d}", use_glatt) for d in range(num_workdays)}
    E_glatt = {d: make_var(f"E_glatt_{d}", use_glatt) for d in range(num_workdays)}
    N_glatt = {d: make_var(f"N_glatt_{d}", use_glatt) for d in range(num_workdays)}

    # Staff variable (integer) => This will represent the maximum headcount needed across all days
    staff_var = pulp.LpVariable("Staff", lowBound=0, cat=pulp.LpInteger)

    # dayUsed variable (1 if any shift scheduled on day d, 0 otherwise)
    dayUsed = {d: pulp.LpVariable(f"dayUsed_{d}", cat=pulp.LpBinary) for d in range(num_workdays)}

    # ------------------------------------------------------------------
    # 4. WEEKEND DAYS IDENTIFICATION
    # ------------------------------------------------------------------
    # Assume day 0 = Monday => day 5 = Saturday, day 6 = Sunday, etc.
    weekend_days = set(d for d in range(num_workdays) if d % 7 in [5, 6])

    # ------------------------------------------------------------------
    # 5. OBJECTIVE FUNCTION
    # ------------------------------------------------------------------
    # Weighted sum of:
    #   1) staff_var * w_staff
    #   2) night shifts * w_night
    #   3) weekend shifts * w_weekend
    #   4) total days used * w_daysUsed

    # total_morning_shifts = sum of solution + bosch + glatt in morning
    total_morning_shifts = pulp.lpSum([
        M_solution[d] + M_bosch[d] + M_glatt[d] for d in range(num_workdays)
    ])

    # total_evening_shifts = sum of solution + bosch + glatt in evening
    total_evening_shifts = pulp.lpSum([
        E_solution[d] + E_bosch[d] + E_glatt[d] for d in range(num_workdays)
    ])
    # 5a) Sum of night shifts (any usage in night shift)
    total_night_shifts = pulp.lpSum([
        N_solution[d] + N_bosch[d] + N_glatt[d]
        for d in range(num_workdays)
    ])

    # 5b) Sum of weekend shifts
    total_weekend_shifts = pulp.lpSum([
        (M_solution[d] + E_solution[d] + N_solution[d] +
         M_bosch[d]    + E_bosch[d]    + N_bosch[d]    +
         M_glatt[d]    + E_glatt[d]    + N_glatt[d])
        for d in weekend_days
    ])

    # 5c) Sum of days used
    total_days_used = pulp.lpSum([dayUsed[d] for d in range(num_workdays)])

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

    # (a) Demand constraint for solution
    #     Each shift with solution => 4 solution-batches
    total_solution_batches = []
    for d in range(num_workdays):
        total_solution_batches.append(4 * M_solution[d])
        total_solution_batches.append(4 * E_solution[d])
        total_solution_batches.append(4 * N_solution[d])
    model += (pulp.lpSum(total_solution_batches) >= batches_required), "SolutionDemand"

    # (b) Demand constraint for coating
    #     BOSCH => 2 batches/shift
    #     GLATT => 2 batches/shift
    total_coating_batches = []
    for d in range(num_workdays):
        # morning
        total_coating_batches.append(2 * M_bosch[d] + 2 * M_glatt[d])
        # evening
        total_coating_batches.append(2 * E_bosch[d] + 2 * E_glatt[d])
        # night
        total_coating_batches.append(2 * N_bosch[d] + 2 * N_glatt[d])
    model += (pulp.lpSum(total_coating_batches) >= batches_required), "CoatingDemand"

    # (c) Staff constraints (cannot reuse staff across shifts in the same day)
    #     If we run solution in a shift => +2 staff
    #     If we run BOSCH in a shift => +2 staff
    #     If we run GLATT in a shift => +2 staff
    #
    #     For day d, total staff needed = sum of staff across M/E/N.
    #     The overall staff_var must be >= staff needed on ANY single day 
    #     (i.e., staff_var is the headcount we must maintain).
    for d in range(num_workdays):
        # Staff needed in morning shift:
        staff_morning = 2 * (M_solution[d] + M_bosch[d] + M_glatt[d])
        # Staff needed in evening shift:
        staff_evening = 2 * (E_solution[d] + E_bosch[d] + E_glatt[d])
        # Staff needed in night shift:
        staff_night   = 2 * (N_solution[d] + N_bosch[d] + N_glatt[d])

        # Sum for day d (cannot be reused, so we add them):
        total_staff_day_d = staff_morning + staff_evening + staff_night

        model += (staff_var >= total_staff_day_d), f"StaffDay_{d}"

    # (d) Linking dayUsed[d] with shift usage
    #     dayUsed[d] = 1 if any shift is used on day d
    for d in range(num_workdays):
        all_shifts_d = (
            M_solution[d] + E_solution[d] + N_solution[d] +
            M_bosch[d]    + E_bosch[d]    + N_bosch[d]    +
            M_glatt[d]    + E_glatt[d]    + N_glatt[d]
        )
        # If any shift is used, dayUsed[d] must be 1 (because they're binary, use a fraction)
        # Max sum of the 9 shift-variables for that day is 9, so:
        model += dayUsed[d] >= all_shifts_d / 9.0, f"DayUsed_{d}"

    # ------------------------------------------------------------------
    # 7. SOLVE THE MODEL
    # ------------------------------------------------------------------
    result_status = model.solve(pulp.PULP_CBC_CMD(msg=0))
    solver_status = pulp.LpStatus[model.status]

    if solver_status != 'Optimal':
        # Could be infeasible or unbounded for other reasons
        if print_solution:
            print(f"No optimal solution found! Solver status: {solver_status}")
            # Quick guess of needed days if relevant:
            needed_days_sol = math.ceil(batches_required / max_daily_solution)
            needed_days_coat = math.ceil(batches_required / max_daily_coating)
            needed_days = max(needed_days_sol, needed_days_coat)
            more_days_needed = max(0, needed_days - num_workdays)
            if more_days_needed > 0:
                print(f"  => You need at least {needed_days} days total.")
                print(f"  => {more_days_needed} more day(s).")
        return None

    # ------------------------------------------------------------------
    # 8. EXTRACT RESULTS
    # ------------------------------------------------------------------
    def var_sum(vdict):
        # Summation of the binary usage across all days
        return sum(int(vdict[d].varValue) for d in range(num_workdays))

    # Summaries for shifts
    morning_solution = var_sum(M_solution)
    evening_solution = var_sum(E_solution)
    night_solution   = var_sum(N_solution)

    morning_bosch = var_sum(M_bosch) if use_bosch else 0
    evening_bosch = var_sum(E_bosch) if use_bosch else 0
    night_bosch   = var_sum(N_bosch) if use_bosch else 0

    morning_glatt = var_sum(M_glatt) if use_glatt else 0
    evening_glatt = var_sum(E_glatt) if use_glatt else 0
    night_glatt   = var_sum(N_glatt) if use_glatt else 0

    min_staff = int(staff_var.varValue)
    staff_with_buffer = math.ceil(min_staff * (1 + buffer_ratio))

    # Calculate total solution batches actually produced
    total_sol_value = 0
    for d in range(num_workdays):
        # Each solution shift => 4 batches
        total_sol_value += 4 * (M_solution[d].varValue + E_solution[d].varValue + N_solution[d].varValue)
    total_solution_produced = int(total_sol_value)

    # Calculate total coated batches actually produced
    total_coat_value = 0
    for d in range(num_workdays):
        # Each BOSCH shift => 2 batches, each GLATT shift => 2 batches
        total_coat_value += 2 * (safe_value(M_bosch[d]) + safe_value(E_bosch[d]) + safe_value(N_bosch[d]))
        total_coat_value += 2 * (safe_value(M_glatt[d]) + safe_value(E_glatt[d]) + safe_value(N_glatt[d]))
    total_coating_produced = int(total_coat_value)

    # For final product, the limiting factor is how many solution-batches 
    # and how many coating-batches we have. But typically, we aim to have >= B on both.
    # We can define "pct_completed" as min(sol_produced, coat_produced)/batches_required * 100
    # because we need both steps per final batch.
    final_batches = min(total_solution_produced, total_coating_produced)
    pct_completed = (final_batches / batches_required) * 100 if batches_required > 0 else 0

    used_days_count = sum(int(dayUsed[d].varValue) for d in range(num_workdays))

    # ------------------------------------------------------------------
    # 9. PRINT OR RETURN THE RESULTS
    # ------------------------------------------------------------------
    if print_solution:
        print("Optimal Schedule for Coating:")
        print("================================")
        print(f"Selected Machines: BOSCH={use_bosch}, GLATT={use_glatt}")
        print(f"Number of Workdays in Horizon: {num_workdays}")
        print(f"Demanded Batches (Solution & Coating): {batches_required}")
        print()
        print("Shifts Summary (Total usage across days):")
        print(f"  Solution: Morning={morning_solution}, Evening={evening_solution}, Night={night_solution}")
        if use_bosch:
            print(f"  BOSCH:    Morning={morning_bosch}, Evening={evening_bosch}, Night={night_bosch}")
        if use_glatt:
            print(f"  GLATT:    Morning={morning_glatt}, Evening={evening_glatt}, Night={night_glatt}")
        print()
        print(f"Total Solution Batches Produced: {total_solution_produced}")
        print(f"Total Coating Batches Produced:  {total_coating_produced}")
        print(f"Final Batches (limited by both steps): {final_batches}")
        print(f"% of Demand Completed:            {pct_completed:.1f}%")
        print()
        print(f"Minimal Headcount (no buffer): {min_staff}")
        print(f"Headcount with {int(buffer_ratio*100)}% buffer: {staff_with_buffer}")
        print()
        print(f"Number of days used: {used_days_count}")
        print(f"Solver status: {solver_status}")
        print("=" * 50)

    return {
        "machines_used": {
            "BOSCH": use_bosch,
            "GLATT": use_glatt
        },
        "morning_shifts": {
            "Solution": morning_solution,
            "BOSCH": morning_bosch,
            "GLATT": morning_glatt
        },
        "evening_shifts": {
            "Solution": evening_solution,
            "BOSCH": evening_bosch,
            "GLATT": evening_glatt
        },
        "night_shifts": {
            "Solution": night_solution,
            "BOSCH": night_bosch,
            "GLATT": night_glatt
        },
        "total_solution_produced": total_solution_produced,
        "total_coating_produced": total_coating_produced,
        "final_batches_count": final_batches,
        "pct_demand_completed": pct_completed,
        "min_staff_required": min_staff,
        "staff_with_buffer": staff_with_buffer,
        "days_used": used_days_count,
        "num_workdays_horizon": num_workdays,
        "solver_status": solver_status
    }


if __name__ == "__main__":
    # Example usage:
    result = optimize_coating(
        batches_required=8,
        num_workdays=2,
        use_bosch=True,
        use_glatt=False,  # Only use BOSCH in this example
        buffer_ratio=0.20,  # 20% buffer
        w_staff=100.0,     # strong emphasis on minimizing staff
        w_morning=0.0,   # penalty for morning shift usage
        w_evening=0.1,
        w_night=2.0,       # moderate penalty on night shifts
        w_weekend=3.0,     # higher penalty for weekend shifts
        w_daysUsed=1.0,    # some penalty on each day used
        print_solution=True
    )
