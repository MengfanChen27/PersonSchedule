import math
import pulp
from Dispensing_PS import optimize_dispensing
from Granulation_PS import optimize_granulation
from  Tab_PS import optimize_tableting
from Coating_PS import optimize_coating

def optimize_osd_schedule(
    disp_batches_req: int,
    gran_batches_req: int,
    tab_batches_req: int,
    coat_batches_req: int,
    num_workdays: int,
    # can also pass in specific weights for each sub-process
    buffer_ratio: float = 0.0,
    # Common weights:
    w_staff: float = 100.0,
    w_morning: float = 0.0,
    w_evening: float = 0.1,
    w_night: float = 2.0,
    w_weekend: float = 3.0,
    w_daysUsed: float = 1.0,
    # Tableting machine usage toggles:
    use_p3030=True,
    use_p3090i=True,
    use_ima=True,
    # Coating machine usage toggles:
    use_bosch=True,
    use_glatt=True,
    # Whether to print the big combined summary:
    print_combined: bool = True
):
    """
    Calls each of the 4 sub-process optimizers (dispensing, granulation, 
    tableting, coating) in sequence with the given demands. Returns a 
    consolidated dictionary of results, and can print a combined summary table.

    Note:
      - Each sub-optimizer is still an *independent* LP model, so staff are 
        not shared across processes in this approach. The total staff is just 
        the sum of staff from each sub-model. 
    """
    
    # 1) Run Dispensing
    disp_result = optimize_dispensing(
        batches_required=disp_batches_req,
        num_workdays=num_workdays,
        buffer_ratio=buffer_ratio,
        w_staff=w_staff,
        w_night=w_night,
        w_weekend=w_weekend,
        w_daysUsed=w_daysUsed,
        w_morning=w_morning,
        w_evening=w_evening,
        print_solution=False  # We'll handle printing in the combined summary
    )
    
    # If infeasible, disp_result will be None. We can short-circuit:
    if disp_result is None:
        return None  # or handle partial success

    # 2) Run Granulation
    gran_result = optimize_granulation(
        batches_required=gran_batches_req,
        num_workdays=num_workdays,
        buffer_ratio=buffer_ratio,
        w_staff=w_staff,
        w_morning=w_morning,
        w_evening=w_evening,
        w_night=w_night,
        w_weekend=w_weekend,
        w_daysUsed=w_daysUsed,
        print_solution=False
    )
    if gran_result is None:
        return None

    # 3) Run Tableting
    tab_result = optimize_tableting(
        batches_required=tab_batches_req,
        num_workdays=num_workdays,
        use_p3030=use_p3030,
        use_p3090i=use_p3090i,
        use_ima=use_ima,
        buffer_ratio=buffer_ratio,
        w_staff=w_staff,
        w_morning=w_morning,
        w_evening=w_evening,
        w_night=w_night,
        w_weekend=w_weekend,
        w_daysUsed=w_daysUsed,
        print_solution=False
    )
    if tab_result is None:
        return None

    # 4) Run Coating
    coat_result = optimize_coating(
        batches_required=coat_batches_req,
        num_workdays=num_workdays,
        use_bosch=use_bosch,
        use_glatt=use_glatt,
        buffer_ratio=buffer_ratio,
        w_staff=w_staff,
        w_morning=w_morning,
        w_evening=w_evening,
        w_night=w_night,
        w_weekend=w_weekend,
        w_daysUsed=w_daysUsed,
        print_solution=False
    )
    if coat_result is None:
        return None

    # -------------------------------------------------
    # Combine results
    # -------------------------------------------------
    combined_results = {
        "dispensing": disp_result,
        "granulation": gran_result,
        "tableting": tab_result,
        "coating": coat_result,
    }

    # Summarize total staff (remember: each sub-problem is separate right now)
    total_staff = (
        disp_result["min_staff_required"]
        + gran_result["min_staff_required"]
        + tab_result["min_staff_required"]
        + coat_result["min_staff_required"]
    )
    # Or staff with buffer:
    total_staff_with_buffer = (
        disp_result["staff_with_buffer"]
        + gran_result["staff_with_buffer"]
        + tab_result["staff_with_buffer"]
        + coat_result["staff_with_buffer"]
    )

    # If you want to see how many total batches are produced across each process, you can track it,
    # but note that each process has a separate measure. 
    # For instance:
    total_batches_dispensed = disp_result["total_batches_produced"]
    total_batches_granulated = gran_result["total_batches_produced"]
    total_batches_tableted   = tab_result["total_batches_produced"]  # "pct_demand_completed" also available
    total_batches_coated    = coat_result["final_batches_count"]     # in Coating, we use final_batches_count

    if print_combined:
        print("\n" + "="*60)
        print("           Combined OSD Production Schedule")
        print("="*60)
        print(f"Time Horizon: {num_workdays} days")
        print()
        print("1) Dispensing Results:")
        print("   -------------------")
        print(f"   Batches Required: {disp_batches_req}")
        print(f"   Batches Produced: {disp_result['total_batches_produced']}")
        print(f"   Staff (min)     : {disp_result['min_staff_required']}")
        print(f"   Days Used       : {disp_result['days_used']}")
        print(f"   Solver Status   : {disp_result['solver_status']}")
        print()

        print("2) Granulation Results:")
        print("   --------------------")
        print(f"   Batches Required: {gran_batches_req}")
        print(f"   Batches Produced: {gran_result['total_batches_produced']}")
        print(f"   Staff (min)     : {gran_result['min_staff_required']}")
        print(f"   Days Used       : {gran_result['days_used']}")
        print(f"   Solver Status   : {gran_result['solver_status']}")
        print()

        print("3) Tableting Results:")
        print("   -------------------")
        print(f"   Batches Required: {tab_batches_req}")
        print(f"   Batches Produced: {tab_result['total_batches_produced']}")
        print(f"   Staff (min)     : {tab_result['min_staff_required']}")
        print(f"   Days Used       : {tab_result['days_used']}")
        print(f"   Solver Status   : {tab_result['solver_status']}")
        print()

        print("4) Coating Results:")
        print("   -----------------")
        print(f"   Batches Required: {coat_batches_req}")
        print(f"   Final Batches Produced: {coat_result['final_batches_count']} "
              f"(Solution={coat_result['total_solution_produced']}, "
              f"Coating={coat_result['total_coating_produced']})")
        print(f"   Staff (min)     : {coat_result['min_staff_required']}")
        print(f"   Days Used       : {coat_result['days_used']}")
        print(f"   Solver Status   : {coat_result['solver_status']}")
        print()
        print("------------------------------------------------------------")
        print(f"Approx. SUM of minimal staff across all 4 processes: {total_staff}")
        print(f"Approx. SUM with buffer: {total_staff_with_buffer}")
        print("------------------------------------------------------------")
        print("="*60)
        print()

    # Optionally, add these "combined" fields to the dictionary:
    combined_results["total_min_staff_summed"] = total_staff
    combined_results["total_staff_with_buffer_summed"] = total_staff_with_buffer

    return combined_results

def optimize_osd_schedule_with_total(
    total_batches: int,
    initial_workdays: int = 14,  # start with a reasonable estimate
    buffer_ratio: float = 0.0,
    w_staff: float = 100.0,
    w_morning: float = 0.0,
    w_evening: float = 0.1,
    w_night: float = 2.0,
    w_weekend: float = 3.0,
    w_daysUsed: float = 1.0,
    use_p3030=True,
    use_p3090i=True,
    use_ima=True,
    use_bosch=True,
    use_glatt=True,
    print_combined: bool = True
):
    """
    Optimizes the OSD schedule when given a total batch target.
    Each process needs to produce the same number of batches, but considers
    sequential dependencies between processes.
    
    Returns:
    - Dictionary containing schedule details and total days needed
    - None if infeasible
    """
    # First try with initial workdays estimate
    result = optimize_osd_schedule(
        disp_batches_req=total_batches,
        gran_batches_req=total_batches,
        tab_batches_req=total_batches,
        coat_batches_req=total_batches,
        num_workdays=initial_workdays,
        buffer_ratio=buffer_ratio,
        w_staff=w_staff,
        w_morning=w_morning,
        w_evening=w_evening,
        w_night=w_night,
        w_weekend=w_weekend,
        w_daysUsed=w_daysUsed,
        use_p3030=use_p3030,
        use_p3090i=use_p3090i,
        use_ima=use_ima,
        use_bosch=use_bosch,
        use_glatt=use_glatt,
        print_combined=False
    )

    # If infeasible, try increasing workdays until we find a feasible solution
    current_days = initial_workdays
    while result is None and current_days <= 365:  # 1 year max
        current_days += 7  # Try adding a week at a time
        result = optimize_osd_schedule(
            disp_batches_req=total_batches,
            gran_batches_req=total_batches,
            tab_batches_req=total_batches,
            coat_batches_req=total_batches,
            num_workdays=current_days,
            buffer_ratio=buffer_ratio,
            w_staff=w_staff,
            w_morning=w_morning,
            w_evening=w_evening,
            w_night=w_night,
            w_weekend=w_weekend,
            w_daysUsed=w_daysUsed,
            use_p3030=use_p3030,
            use_p3090i=use_p3090i,
            use_ima=use_ima,
            use_bosch=use_bosch,
            use_glatt=use_glatt,
            print_combined=False
        )

    if result is None:
        if print_combined:
            print("No feasible solution found even with 365 days!")
        return None

    # Calculate the total time needed considering sequential dependencies
    disp_days = result['dispensing']['days_used']
    gran_days = result['granulation']['days_used']
    tab_days = result['tableting']['days_used']
    coat_days = result['coating']['days_used']

    # Calculate the minimum total days needed considering parallel operations
    # For sequential processes, we need to consider the overlap
    # Assuming each process can start as soon as the first batch from previous process is ready
    total_days_needed = max(
        disp_days,  # Dispensing starts at day 0
        disp_days + 1,  # Granulation can start after first dispensing batch
        disp_days + 2,  # Tableting can start after first granulation batch
        disp_days + 3   # Coating can start after first tableting batch
    )

    result['total_days_needed'] = total_days_needed
    result['workdays_allocated'] = current_days

    if print_combined:
        print("\n" + "="*60)
        print(f"Production Schedule for {total_batches} Total Batches")
        print("="*60)
        print(f"Total Days Needed: {total_days_needed} days")
        print(f"Workdays Allocated: {current_days} days")
        print("\nProcess Breakdown:")
        print(f"Dispensing:   {disp_days} days")
        print(f"Granulation:  {gran_days} days")
        print(f"Tableting:    {tab_days} days")
        print(f"Coating:      {coat_days} days")
        print("\nStaffing Requirements:")
        print(f"Total Staff (min): {result['total_min_staff_summed']}")
        print(f"Total Staff (with buffer): {result['total_staff_with_buffer_summed']}")
        print("="*60)

    return result

def optimize_max_batches(
    num_workdays: int,
    buffer_ratio: float = 0.0,
    w_staff: float = 100.0,
    w_morning: float = 0.0,
    w_evening: float = 0.1,
    w_night: float = 2.0,
    w_weekend: float = 3.0,
    w_daysUsed: float = 1.0,
    use_p3030=True,
    use_p3090i=True,
    use_ima=True,
    use_bosch=True,
    use_glatt=True,
    max_iterations: int = 50,  # to prevent infinite loops
    print_solution: bool = True
) -> dict:
    """
    Find the maximum number of batches that can be produced through all processes
    using binary search approach.
    
    Returns:
    - Dictionary containing the maximum feasible batches and the detailed schedule
    - None if no feasible solution found
    """
    
    # Initialize binary search bounds
    lower_bound = 1
    upper_bound = num_workdays * 27  # Maximum theoretical (9 batches/day * 3 shifts)
    max_feasible_result = None
    max_feasible_batches = 0
    
    iteration = 0
    while lower_bound <= upper_bound and iteration < max_iterations:
        iteration += 1
        current_batches = (lower_bound + upper_bound) // 2
        
        # Try to optimize with current batch target
        result = optimize_osd_schedule(
            disp_batches_req=current_batches,
            gran_batches_req=current_batches,
            tab_batches_req=current_batches,
            coat_batches_req=current_batches,
            num_workdays=num_workdays,
            buffer_ratio=buffer_ratio,
            w_staff=w_staff,
            w_morning=w_morning,
            w_evening=w_evening,
            w_night=w_night,
            w_weekend=w_weekend,
            w_daysUsed=w_daysUsed,
            use_p3030=use_p3030,
            use_p3090i=use_p3090i,
            use_ima=use_ima,
            use_bosch=use_bosch,
            use_glatt=use_glatt,
            print_combined=False
        )
        
        if result is not None:
            # Solution is feasible, try more batches
            lower_bound = current_batches + 1
            max_feasible_result = result
            max_feasible_batches = current_batches
        else:
            # Solution is infeasible, try fewer batches
            upper_bound = current_batches - 1
    
    if max_feasible_result is None:
        if print_solution:
            print("No feasible solution found!")
        return None
    
    # Add maximum batches information to result
    max_feasible_result['max_feasible_batches'] = max_feasible_batches
    
    if print_solution:
        print("\n" + "="*70)
        print(f"Maximum Feasible Production Schedule ({num_workdays} days)")
        print("="*70)
        print(f"Maximum Batches Achievable: {max_feasible_batches}")
        print("\nProcess Breakdown:")
        print("-----------------")
        for process in ['dispensing', 'granulation', 'tableting', 'coating']:
            result = max_feasible_result[process]
            print(f"\n{process.capitalize()}:")
            print(f"  Batches Produced: {result.get('total_batches_produced', result.get('final_batches_count', 'N/A'))}")
            print(f"  Staff Required : {result['min_staff_required']} (with buffer: {result['staff_with_buffer']})")
            print(f"  Days Used     : {result['days_used']}")
            
            # Print shift distribution if available
            shifts = {
                'Morning': result.get('morning_shifts', 'N/A'),
                'Evening': result.get('evening_shifts', 'N/A'),
                'Night': result.get('night_shifts', 'N/A')
            }
            print("  Shifts Distribution:")
            for shift_type, count in shifts.items():
                print(f"    {shift_type}: {count}")
        
        print("\nTotal Resources Required:")
        print("--------------------------")
        print(f"Total Staff (minimum): {max_feasible_result['total_min_staff_summed']}")
        print(f"Total Staff (with {int(buffer_ratio*100)}% buffer): {max_feasible_result['total_staff_with_buffer_summed']}")
        print("="*70)
    
    return max_feasible_result

# -------------
# Example usage
# -------------
if __name__ == "__main__":
    # Suppose these are per-process demands:
    dispensing_demand   = 10
    granulation_demand  = 10
    tableting_demand    = 10
    coating_demand      = 10
    
    # Run the combined schedule:
    final_res = optimize_osd_schedule(
        disp_batches_req=dispensing_demand,
        gran_batches_req=granulation_demand,
        tab_batches_req=tableting_demand,
        coat_batches_req=coating_demand,
        num_workdays=7,
        buffer_ratio=0.2,  # for testing, 20% staffing buffer
        w_staff=100.0,  # strong emphasis on minimizing staff
        w_morning=0.0,
        w_evening=0.0,
        w_night=0,
        w_weekend=3.0,
        w_daysUsed=1.0,
        use_p3030=True,  # for tableting
        use_p3090i=True, # for tableting
        use_ima=False,   # let's say we do not use IMA
        use_bosch=True,  # for coating
        use_glatt=False, # only BOSCH for coating
        print_combined=True
    )

    # `final_res` is now a dictionary with keys:
    #   {
    #     'dispensing': {...},
    #     'granulation': {...},
    #     'tableting': {...},
    #     'coating': {...},
    #     'total_min_staff_summed': <int>,
    #     'total_staff_with_buffer_summed': <int>
    #   }

    # New example with total batches
    print("\nTesting total batch optimization:")
    result = optimize_osd_schedule_with_total(
        total_batches=48,
        initial_workdays=6,
        buffer_ratio=0.2,
        w_staff=100.0,
        w_morning=0.0,
        w_evening=0.0,
        w_night=0.0,
        w_weekend=3.0,
        w_daysUsed=1.0,
        print_combined=True
    )

    # Test maximum batch calculation
    print("\nTesting maximum batch calculation:")
    max_result = optimize_max_batches(
        num_workdays=14,
        buffer_ratio=0.2,
        w_staff=100.0,
        w_morning=0.0,
        w_evening=0.1,
        w_night=2.0,
        w_weekend=3.0,
        w_daysUsed=1.0,
        use_p3030=True,
        use_p3090i=True,
        use_ima=True,
        use_bosch=True,
        use_glatt=True,
        print_solution=True
    )
